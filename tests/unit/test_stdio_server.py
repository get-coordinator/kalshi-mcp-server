import io
import json
import unittest

from kalshi_mcp.server import StdioMCPServer, ToolRegistry
from kalshi_mcp.mcp.resources import ResourceRegistry


class StdioServerTests(unittest.TestCase):
    def test_initialize_tools_list_tools_call_and_resources(self) -> None:
        handlers = {
            "get_tags_for_series_categories": lambda arguments: {
                "tags_by_categories": {"Politics": ["Trump", "Biden"]}
            },
            "get_balance": lambda arguments: {
                "balance": 1000,
                "portfolio_value": 2500,
                "updated_ts": 1735000000123,
            },
            "get_categories": lambda arguments: {
                "categories": ["Politics"]
            },
            "get_tags_for_series_category": lambda arguments: {
                "category": arguments["category"],
                "tags": ["Trump", "Biden"],
            },
            "get_series_list": lambda arguments: {
                "series": [
                    {
                        "ticker": "KXBTCUSD",
                        "frequency": "daily",
                        "title": "Will Bitcoin close above 100k?",
                        "category": "Crypto",
                        "tags": ["BTC"],
                        "settlement_sources": [],
                        "contract_url": "https://kalshi.com/series/KXBTCUSD",
                        "contract_terms_url": "https://kalshi.com/terms/KXBTCUSD",
                        "fee_type": "linear",
                        "fee_multiplier": 1.0,
                        "additional_prohibitions": [],
                    }
                ]
            },
            "get_series_tickers_for_category": lambda arguments: {
                "category": arguments["category"],
                "tickers": ["KXBTCUSD"],
                "count": 1,
                "pages": 1,
            },
        }
        registry = ToolRegistry(handlers)
        resources = ResourceRegistry(registry)
        stdin = io.StringIO(
            "\n".join(
                [
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {
                                "protocolVersion": "2025-06-18",
                                "capabilities": {},
                                "clientInfo": {"name": "test", "version": "0.0.1"},
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "method": "notifications/initialized",
                            "params": {},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/list",
                            "params": {},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 20,
                            "method": "resources/list",
                            "params": {},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 21,
                            "method": "resources/templates/list",
                            "params": {},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 22,
                            "method": "resources/read",
                            "params": {"uri": "kalshi:///categories"},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 23,
                            "method": "resources/read",
                            "params": {"uri": "kalshi:///category/Politics/tags"},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 24,
                            "method": "resources/read",
                            "params": {"uri": "kalshi:///category/Crypto/series_tickers"},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 25,
                            "method": "resources/read",
                            "params": {"uri": "kalshi:///portfolio/balance"},
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "get_tags_for_series_categories",
                                "arguments": {},
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {
                                "name": "get_tags_for_series_category",
                                "arguments": {"category": "Politics"},
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 5,
                            "method": "tools/call",
                            "params": {
                                "name": "get_series_list",
                                "arguments": {"category": "Crypto"},
                            },
                        }
                    ),
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 6,
                            "method": "tools/call",
                            "params": {
                                "name": "get_series_tickers_for_category",
                                "arguments": {"category": "Crypto"},
                            },
                        }
                    ),
                ]
            )
            + "\n"
        )
        stdout = io.StringIO()

        server = StdioMCPServer(registry, resources=resources, stdin=stdin, stdout=stdout)
        server.run()

        lines = [line for line in stdout.getvalue().splitlines() if line.strip()]
        self.assertEqual(12, len(lines))

        initialize_response = json.loads(lines[0])
        self.assertEqual("2.0", initialize_response["jsonrpc"])
        self.assertEqual(1, initialize_response["id"])
        self.assertEqual(
            "kalshi-mcp-server", initialize_response["result"]["serverInfo"]["name"]
        )

        tools_list_response = json.loads(lines[1])
        self.assertEqual(2, tools_list_response["id"])
        tool_names = [tool["name"] for tool in tools_list_response["result"]["tools"]]
        self.assertEqual(
            [
                "search_markets",
                "get_tags_for_series_categories",
                "get_balance",
                "get_subaccount_balances",
                "get_categories",
                "get_tags_for_series_category",
                "get_series_list",
                "get_markets",
                "get_open_markets_for_series",
                "get_open_market_titles_for_series",
                "get_series_tickers_for_category",
                "get_order",
                "get_orders",
                "get_positions",
            ],
            tool_names,
        )

        resources_list_response = json.loads(lines[2])
        self.assertEqual(20, resources_list_response["id"])
        resource_uris = [r["uri"] for r in resources_list_response["result"]["resources"]]
        self.assertEqual(
            [
                "kalshi:///categories",
                "kalshi:///portfolio/balance",
                "kalshi:///portfolio/subaccount_balances",
                "kalshi:///portfolio/positions",
                "kalshi:///tags_by_categories",
            ],
            resource_uris,
        )

        templates_list_response = json.loads(lines[3])
        self.assertEqual(21, templates_list_response["id"])
        template_uris = [
            t["uriTemplate"] for t in templates_list_response["result"]["resourceTemplates"]
        ]
        self.assertEqual(
            [
                "kalshi:///category/{category}/tags",
                "kalshi:///category/{category}/series_tickers{?tags,limit,max_pages}",
                "kalshi:///series/{series_ticker}/open_markets{?limit,max_pages}",
                "kalshi:///series/{series_ticker}/open_market_titles{?limit,max_pages}",
                "kalshi:///series{?category,tags,cursor,limit,include_product_metadata,include_volume}",
                "kalshi:///portfolio/orders/{order_id}",
                "kalshi:///portfolio/orders{?ticker,event_ticker,status,min_ts,max_ts,limit,cursor,subaccount}",
                "kalshi:///portfolio/positions{?cursor,limit,count_filter,ticker,event_ticker,subaccount}",
            ],
            template_uris,
        )

        categories_read_response = json.loads(lines[4])
        self.assertEqual(22, categories_read_response["id"])
        categories_contents = categories_read_response["result"]["contents"][0]["text"]
        self.assertIn('"categories"', categories_contents)
        self.assertIn("Politics", categories_contents)

        category_tags_read_response = json.loads(lines[5])
        self.assertEqual(23, category_tags_read_response["id"])
        category_tags_contents = category_tags_read_response["result"]["contents"][0]["text"]
        self.assertIn('"category"', category_tags_contents)
        self.assertIn("Politics", category_tags_contents)

        category_tickers_read_response = json.loads(lines[6])
        self.assertEqual(24, category_tickers_read_response["id"])
        category_tickers_contents = category_tickers_read_response["result"]["contents"][0]["text"]
        self.assertIn('"tickers"', category_tickers_contents)
        self.assertIn("KXBTCUSD", category_tickers_contents)

        portfolio_balance_read_response = json.loads(lines[7])
        self.assertEqual(25, portfolio_balance_read_response["id"])
        portfolio_balance_contents = portfolio_balance_read_response["result"]["contents"][0]["text"]
        self.assertIn('"balance"', portfolio_balance_contents)
        self.assertIn("2500", portfolio_balance_contents)

        tools_call_response = json.loads(lines[8])
        self.assertEqual(3, tools_call_response["id"])
        self.assertEqual(False, tools_call_response["result"]["isError"])
        self.assertEqual(
            {"tags_by_categories": {"Politics": ["Trump", "Biden"]}},
            tools_call_response["result"]["structuredContent"],
        )

        tools_call_by_category_response = json.loads(lines[9])
        self.assertEqual(4, tools_call_by_category_response["id"])
        self.assertEqual(False, tools_call_by_category_response["result"]["isError"])
        self.assertEqual(
            {"category": "Politics", "tags": ["Trump", "Biden"]},
            tools_call_by_category_response["result"]["structuredContent"],
        )

        tools_call_series_response = json.loads(lines[10])
        self.assertEqual(5, tools_call_series_response["id"])
        self.assertEqual(False, tools_call_series_response["result"]["isError"])
        self.assertEqual(
            "KXBTCUSD",
            tools_call_series_response["result"]["structuredContent"]["series"][0]["ticker"],
        )

        tools_call_tickers_response = json.loads(lines[11])
        self.assertEqual(6, tools_call_tickers_response["id"])
        self.assertEqual(False, tools_call_tickers_response["result"]["isError"])
        self.assertEqual(
            {"category": "Crypto", "tickers": ["KXBTCUSD"], "count": 1, "pages": 1},
            tools_call_tickers_response["result"]["structuredContent"],
        )

    def test_parse_error(self) -> None:
        registry = ToolRegistry({})
        stdin = io.StringIO("{not_json}\n")
        stdout = io.StringIO()

        server = StdioMCPServer(registry, stdin=stdin, stdout=stdout)
        server.run()

        line = stdout.getvalue().strip()
        response = json.loads(line)
        self.assertEqual(-32700, response["error"]["code"])


if __name__ == "__main__":
    unittest.main()
