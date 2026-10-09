import base64
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib import error, request

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from kalshi_mcp.http_server import ScopeCache, build_handler, parse_key_header
from kalshi_mcp.kalshi_client import KalshiClient, KalshiClientError
from kalshi_mcp.settings import Settings

SECRET = "s3cret"


def _key(fmt: serialization.PrivateFormat) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(serialization.Encoding.PEM, fmt, serialization.NoEncryption()).decode()


def _body(pem: str) -> str:
    return "".join(line for line in pem.splitlines() if not line.startswith("-----"))


class HTTPServerTest(unittest.TestCase):
    def setUp(self) -> None:
        settings = Settings(base_url="https://api.elections.kalshi.com/trade-api/v2", timeout_seconds=5)
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(settings, SECRET, ScopeCache()))
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/mcp"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    def _post(self, message: dict, headers: dict[str, str]) -> tuple[int, dict | None]:
        req = request.Request(self.url, data=json.dumps(message).encode(), method="POST", headers=headers)
        try:
            with request.urlopen(req) as resp:
                raw = resp.read()
                return resp.status, json.loads(raw) if raw else None
        except error.HTTPError as exc:
            return exc.code, json.loads(exc.read() or b"null")

    def _list(self, headers: dict[str, str]) -> tuple[int, dict | None]:
        return self._post({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, headers)

    def test_requires_secret(self) -> None:
        status, _ = self._list({})
        self.assertEqual(status, 401)

    def test_lists_read_tools_without_key(self) -> None:
        status, body = self._list({"X-Internal-Secret": SECRET})
        self.assertEqual(status, 200)
        names = {t["name"] for t in body["result"]["tools"]}
        self.assertIn("get_markets", names)
        self.assertFalse(names & {"create_order", "cancel_order", "create_subaccount"})
        self.assertFalse(names & {"get_balance", "get_positions", "get_orders"})

    def test_account_tools_need_a_key(self) -> None:
        status, body = self._post(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "get_balance", "arguments": {}}},
            {"X-Internal-Secret": SECRET},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body["result"]["isError"])

    def test_notification_is_accepted(self) -> None:
        status, body = self._post({"jsonrpc": "2.0", "method": "notifications/initialized"}, {"X-Internal-Secret": SECRET})
        self.assertEqual((status, body), (202, None))

    def test_read_only_key_is_accepted(self) -> None:
        pem = _key(serialization.PrivateFormat.TraditionalOpenSSL)
        with patch.object(KalshiClient, "get_api_key_scopes", return_value=["read"]):
            status, body = self._list({"X-Internal-Secret": SECRET, "X-Kalshi-Key": f"kid:{_body(pem)}"})
        self.assertEqual(status, 200)
        self.assertIn("get_positions", {t["name"] for t in body["result"]["tools"]})

    def test_trading_key_is_refused(self) -> None:
        pem = _key(serialization.PrivateFormat.PKCS8)
        for scopes in (["read", "write"], ["read", "write::trade"], []):
            with patch.object(KalshiClient, "get_api_key_scopes", return_value=scopes):
                status, body = self._list({"X-Internal-Secret": SECRET, "X-Kalshi-Key": f"kid-{len(scopes)}:{_body(pem)}"})
            self.assertEqual(status, 403, scopes)
            self.assertIn("read-only", body["error"])

    def test_rejected_key_is_unauthorized(self) -> None:
        pem = _key(serialization.PrivateFormat.PKCS8)
        with patch.object(KalshiClient, "get_api_key_scopes", side_effect=KalshiClientError("nope", 401)):
            status, _ = self._list({"X-Internal-Secret": SECRET, "X-Kalshi-Key": f"kid:{_body(pem)}"})
        self.assertEqual(status, 401)


class KeyFormatTest(unittest.TestCase):
    def test_signs_with_both_key_formats(self) -> None:
        for fmt in (serialization.PrivateFormat.TraditionalOpenSSL, serialization.PrivateFormat.PKCS8):
            pem = _key(fmt)
            for value in (f"kid:{pem}", f"kid:{_body(pem)}"):
                key_id, key = parse_key_header(value)
                client = KalshiClient(Settings(base_url="https://x/trade-api/v2", timeout_seconds=1, api_key_id=key_id, api_key_pem=key))
                signature = client._sign_message("hello")
                self.assertTrue(base64.b64decode(signature))

    def test_rejects_malformed_header(self) -> None:
        for value in ("no-separator", ":body", "kid:", "kid:not base64!"):
            with self.assertRaises(Exception):
                parse_key_header(value)


if __name__ == "__main__":
    unittest.main()
