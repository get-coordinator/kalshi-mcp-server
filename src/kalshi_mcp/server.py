"""MCP server entrypoint and wiring."""

from __future__ import annotations

import json
import sys
from typing import Any
from typing import TextIO

from .kalshi_client import KalshiClient
from .mcp.handlers import ToolHandler, build_tool_handlers
from .mcp.resources import ResourceRegistry
from .mcp.schema import (
    GET_BALANCE_TOOL,
    GET_CATEGORIES_TOOL,
    GET_MARKETS_TOOL,
    GET_OPEN_MARKETS_FOR_SERIES_TOOL,
    GET_OPEN_MARKET_TITLES_FOR_SERIES_TOOL,
    GET_ORDER_TOOL,
    GET_ORDERS_TOOL,
    GET_POSITIONS_TOOL,
    GET_SERIES_LIST_TOOL,
    GET_SERIES_TICKERS_FOR_CATEGORY_TOOL,
    GET_SUBACCOUNT_BALANCES_TOOL,
    GET_TAGS_FOR_SERIES_CATEGORIES_TOOL,
    GET_TAGS_FOR_SERIES_CATEGORY_TOOL,
    SEARCH_MARKETS_TOOL,
)
from .scope import CategoryScope
from .services import MetadataService, PortfolioService
from .settings import Settings, load_settings

JSONRPC_VERSION = "2.0"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"


class ToolRegistry:
    def __init__(self, handlers: dict[str, ToolHandler]) -> None:
        self._handlers = handlers

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            SEARCH_MARKETS_TOOL,
            GET_TAGS_FOR_SERIES_CATEGORIES_TOOL,
            GET_BALANCE_TOOL,
            GET_SUBACCOUNT_BALANCES_TOOL,
            GET_CATEGORIES_TOOL,
            GET_TAGS_FOR_SERIES_CATEGORY_TOOL,
            GET_SERIES_LIST_TOOL,
            GET_MARKETS_TOOL,
            GET_OPEN_MARKETS_FOR_SERIES_TOOL,
            GET_OPEN_MARKET_TITLES_FOR_SERIES_TOOL,
            GET_SERIES_TICKERS_FOR_CATEGORY_TOOL,
            GET_ORDER_TOOL,
            GET_ORDERS_TOOL,
            GET_POSITIONS_TOOL,
        ]

    def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        handler = self._handlers.get(tool_name)
        if handler is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        return handler(arguments)


def create_tool_registry(settings: Settings | None = None) -> CategoryScope:
    resolved_settings = settings or load_settings()
    client = KalshiClient(resolved_settings)
    metadata_service = MetadataService(client)
    portfolio_service = PortfolioService(client)
    handlers = build_tool_handlers(metadata_service, portfolio_service)
    return CategoryScope(ToolRegistry(handlers))


class StdioMCPServer:
    def __init__(
        self,
        registry: ToolRegistry,
        resources: ResourceRegistry | None = None,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self._registry = registry
        self._resources = resources
        self._stdin = stdin or sys.stdin
        self._stdout = stdout or sys.stdout
        self._initialized = False

    def run(self) -> int:
        for raw_line in self._stdin:
            line = raw_line.strip()
            if not line:
                continue

            try:
                message = json.loads(line)
            except json.JSONDecodeError:
                self._write(self._error_response(None, -32700, "Parse error"))
                continue

            self._handle_incoming(message)
        return 0

    def _handle_incoming(self, message: Any) -> None:
        if isinstance(message, list):
            if not message:
                self._write(self._error_response(None, -32600, "Invalid Request"))
                return

            responses: list[dict[str, Any]] = []
            for item in message:
                response = self._handle_one_message(item)
                if response is not None:
                    responses.append(response)

            if not responses:
                return

            self._write(responses)
            return

        response = self._handle_one_message(message)
        if response is not None:
            self._write(response)

    def _handle_one_message(self, message: Any) -> dict[str, Any] | None:
        if not isinstance(message, dict):
            return self._error_response(None, -32600, "Invalid Request")

        if message.get("jsonrpc") != JSONRPC_VERSION:
            return self._error_response(message.get("id"), -32600, "Invalid Request")

        method = message.get("method")
        if isinstance(method, str):
            if "id" in message:
                return self._handle_request(message.get("id"), method, message.get("params"))
            self._handle_notification(method, message.get("params"))
            return None

        # Server does not send requests, so client responses are ignored.
        if "id" in message and ("result" in message or "error" in message):
            return None

        return self._error_response(message.get("id"), -32600, "Invalid Request")

    def _handle_notification(self, method: str, params: Any) -> None:
        if method == "notifications/initialized":
            self._initialized = True
            return
        # Unknown notifications are ignored.
        _ = params

    def _handle_request(self, request_id: Any, method: str, params: Any) -> dict[str, Any]:
        if request_id is None:
            return self._error_response(None, -32600, "Invalid Request")

        try:
            if method == "initialize":
                result = self._initialize(params)
                return self._result_response(request_id, result)

            if method == "ping":
                return self._result_response(request_id, {})

            if method == "tools/list":
                result = {"tools": self._registry.list_tools()}
                return self._result_response(request_id, result)

            if method == "tools/call":
                result = self._call_tool(params)
                return self._result_response(request_id, result)

            if method == "resources/list":
                if self._resources is None:
                    return self._error_response(request_id, -32601, "Method not found")
                if not self._initialized:
                    return self._error_response(
                        request_id,
                        -32603,
                        "Server is not initialized. Send initialize and notifications/initialized first.",
                    )
                result = {"resources": self._resources.list_resources()}
                return self._result_response(request_id, result)

            if method == "resources/read":
                if self._resources is None:
                    return self._error_response(request_id, -32601, "Method not found")
                if not self._initialized:
                    return self._error_response(
                        request_id,
                        -32603,
                        "Server is not initialized. Send initialize and notifications/initialized first.",
                    )
                if not isinstance(params, dict):
                    raise ValueError("Invalid params for resources/read")
                uri = params.get("uri")
                if not isinstance(uri, str) or not uri:
                    raise ValueError("Missing resource uri")
                result = self._resources.read_resource(uri)
                return self._result_response(request_id, result)

            if method == "resources/templates/list":
                if self._resources is None:
                    return self._error_response(request_id, -32601, "Method not found")
                if not self._initialized:
                    return self._error_response(
                        request_id,
                        -32603,
                        "Server is not initialized. Send initialize and notifications/initialized first.",
                    )
                result = {"resourceTemplates": self._resources.list_resource_templates()}
                return self._result_response(request_id, result)

            return self._error_response(request_id, -32601, "Method not found")
        except ValueError as exc:
            return self._error_response(request_id, -32602, str(exc))
        except Exception as exc:  # pragma: no cover - guardrail for unknown failures
            return self._error_response(request_id, -32603, "Internal error", {"detail": str(exc)})

    def _initialize(self, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise ValueError("Invalid params for initialize")

        protocol_version = params.get("protocolVersion")
        if not isinstance(protocol_version, str) or not protocol_version:
            protocol_version = DEFAULT_PROTOCOL_VERSION

        capabilities: dict[str, Any] = {"tools": {"listChanged": False}}
        if self._resources is not None:
            capabilities["resources"] = {"subscribe": False, "listChanged": False}

        return {
            "protocolVersion": protocol_version,
            "capabilities": capabilities,
            "serverInfo": {"name": "kalshi-mcp-server", "version": "0.1.0"},
        }

    def _call_tool(self, params: Any) -> dict[str, Any]:
        if not isinstance(params, dict):
            raise ValueError("Invalid params for tools/call")

        name = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(name, str) or not name:
            raise ValueError("Missing tool name")

        if arguments is not None and not isinstance(arguments, dict):
            raise ValueError("Tool arguments must be an object")

        if not self._initialized:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Server is not initialized. Send initialize and notifications/initialized first.",
                    }
                ],
                "isError": True,
            }

        try:
            structured_content = self._registry.call_tool(name, arguments)
        except Exception as exc:
            return {
                "content": [{"type": "text", "text": str(exc)}],
                "isError": True,
            }

        return {
            "content": [{"type": "text", "text": json.dumps(structured_content)}],
            "structuredContent": structured_content,
            "isError": False,
        }

    def _write(self, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
        self._stdout.write(json.dumps(payload, separators=(",", ":")))
        self._stdout.write("\n")
        self._stdout.flush()

    def _result_response(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": JSONRPC_VERSION, "id": request_id, "result": result}

    def _error_response(
        self, request_id: Any, code: int, message: str, data: Any | None = None
    ) -> dict[str, Any]:
        error: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            error["data"] = data

        return {
            "jsonrpc": JSONRPC_VERSION,
            "id": request_id,
            "error": error,
        }


def main() -> int:
    """Main entrypoint for running the MCP server."""
    registry = create_tool_registry()
    resources = ResourceRegistry(registry)
    server = StdioMCPServer(registry, resources=resources)
    return server.run()


if __name__ == "__main__":
    raise SystemExit(main())
