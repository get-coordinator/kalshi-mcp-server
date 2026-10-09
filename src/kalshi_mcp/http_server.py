"""Stateless Streamable HTTP transport for hosting one server for many users.

Every POST /mcp is answered on its own with the caller's Kalshi key from the
X-Kalshi-Key header ("<key id>:<private key>", the key as PEM or as the base64
body of its PEM). Only keys without any write scope are accepted. When
INTERNAL_API_SECRET is set, requests must carry it in X-Internal-Secret.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .kalshi_client import KalshiClient, KalshiClientError
from .mcp.resources import ResourceRegistry
from .server import StdioMCPServer, create_tool_registry
from .settings import Settings, load_settings

LOGGER = logging.getLogger(__name__)

KEY_HEADER = "X-Kalshi-Key"
SECRET_HEADER = "X-Internal-Secret"
MAX_BODY = 1 << 20
SCOPE_TTL_SECONDS = 600

# Tools that read the caller's own account: only listed when a key comes with the request.
ACCOUNT_TOOLS = frozenset(
    {"get_balance", "get_subaccount_balances", "get_orders", "get_order", "get_positions"}
)

WRITE_KEY_MESSAGE = (
    "This Kalshi API key can place trades. Only read-only keys are accepted: "
    "create a key with Read access only and connect that one."
)


class CredentialError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


def parse_key_header(value: str) -> tuple[str, str]:
    key_id, sep, key = value.strip().partition(":")
    key_id, key = key_id.strip(), key.strip()
    if not sep or not key_id or not key:
        raise CredentialError(401, f"{KEY_HEADER} must be '<key id>:<private key>'.")
    if key.startswith("-----BEGIN"):
        return key_id, key
    body = "".join(key.split())
    try:
        base64.b64decode(body, validate=True)
    except Exception as exc:
        raise CredentialError(401, "The Kalshi private key is not valid.") from exc
    return key_id, body


class PublicRegistry:
    """A registry without the account tools, for requests that carry no key."""

    def __init__(self, registry: Any) -> None:
        self._registry = registry

    def list_tools(self) -> list[dict[str, Any]]:
        return [t for t in self._registry.list_tools() if t["name"] not in ACCOUNT_TOOLS]

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if tool_name in ACCOUNT_TOOLS:
            raise ValueError("Reading a Kalshi account needs its read-only API key.")
        return self._registry.call_tool(tool_name, arguments)


class ScopeCache:
    """Remembers which keys were checked read-only, so each call doesn't re-ask Kalshi."""

    def __init__(self, ttl_seconds: float = SCOPE_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def require_read_only(self, client: KalshiClient, key_id: str, key: str) -> None:
        fingerprint = hashlib.sha256(f"{key_id}:{key}".encode()).hexdigest()
        now = time.monotonic()
        with self._lock:
            if self._seen.get(fingerprint, 0) > now:
                return
        try:
            client._sign_message("check")
        except KalshiClientError as exc:
            raise CredentialError(401, "The Kalshi private key is not valid.") from exc
        try:
            scopes = client.get_api_key_scopes()
        except KalshiClientError as exc:
            if exc.status in (400, 401, 403, 404):
                raise CredentialError(401, "Kalshi didn't accept this API key.") from exc
            raise CredentialError(502, "Couldn't check the key with Kalshi.") from exc
        if not scopes or any(s == "write" or s.startswith("write::") for s in scopes):
            raise CredentialError(403, WRITE_KEY_MESSAGE)
        with self._lock:
            self._seen[fingerprint] = now + self._ttl


def build_handler(base: Settings, secret: str, scopes: ScopeCache) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            LOGGER.info("%s %s", self.address_string(), fmt % args)

        def do_GET(self) -> None:
            if self.path == "/healthz":
                self._send(200, {"ok": True})
                return
            self._send(405, {"error": "method not allowed"})

        def do_DELETE(self) -> None:
            self._send(405, {"error": "method not allowed"})

        def do_POST(self) -> None:
            if self.path.split("?", 1)[0] != "/mcp":
                self._send(404, {"error": "not found"})
                return
            if secret and not hmac.compare_digest(
                self.headers.get(SECRET_HEADER, "").encode(), secret.encode()
            ):
                self._send(401, {"error": "unauthorized"})
                return

            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                self._send(400, {"error": "bad request body"})
                return
            try:
                message = json.loads(self.rfile.read(length))
            except json.JSONDecodeError:
                self._send(400, {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}})
                return

            settings = Settings(base_url=base.base_url, timeout_seconds=base.timeout_seconds)
            header = self.headers.get(KEY_HEADER)
            if header:
                try:
                    settings.api_key_id, settings.api_key_pem = parse_key_header(header)
                    scopes.require_read_only(KalshiClient(settings), settings.api_key_id, settings.api_key_pem)
                except CredentialError as exc:
                    self._send(exc.status, {"error": str(exc)})
                    return

            registry: Any = create_tool_registry(settings)
            if not header:
                registry = PublicRegistry(registry)
            server = StdioMCPServer(registry, resources=ResourceRegistry(registry))
            server._initialized = True
            if isinstance(message, list):
                replies = [r for r in (server._handle_one_message(m) for m in message) if r is not None]
                reply: Any = replies or None
            else:
                reply = server._handle_one_message(message)
            if reply is None:
                self._send(202, None)
                return
            self._send(200, reply)

        def _send(self, status: int, payload: Any) -> None:
            body = b"" if payload is None else json.dumps(payload, separators=(",", ":")).encode()
            self.send_response(status)
            if payload is not None:
                self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main() -> int:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    base = load_settings()
    secret = os.getenv("INTERNAL_API_SECRET", "")
    if not secret and os.getenv("KALSHI_MCP_ALLOW_NO_SECRET") != "true":
        raise SystemExit("set INTERNAL_API_SECRET (or KALSHI_MCP_ALLOW_NO_SECRET=true for local use)")
    port = int(os.getenv("PORT", "8000"))
    httpd = ThreadingHTTPServer(("0.0.0.0", port), build_handler(base, secret, ScopeCache()))
    LOGGER.info("kalshi mcp on :%s/mcp", port)
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
