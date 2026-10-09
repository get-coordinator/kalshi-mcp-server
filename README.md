# kalshi-mcp-server
A read-only MCP server for the Kalshi prediction market: markets, series and, with an API key, the account's own balance, positions and orders. It cannot place, change or cancel orders; the client only sends GET requests.

Fork of [xilei-wang-90/kalshi-mcp-server](https://github.com/xilei-wang-90/kalshi-mcp-server) with the order and subaccount tools removed and markets without a `subtitle` kept.

## Hosted over HTTP

`kalshi-mcp-http` serves stateless Streamable HTTP at `POST /mcp` (and `GET /healthz`) for many users at once:

- `X-Kalshi-Key: <key id>:<private key>` carries the caller's own key, as PEM or as the base64 body of the PEM. Without it, only the public market tools are listed; the account tools (`get_balance`, `get_positions`, `get_orders`, `get_order`, `get_subaccount_balances`) need the key.
- Only read-only keys are accepted: a key with any `write` scope gets 403, a key Kalshi rejects gets 401. Create the key on Kalshi with Read access only.
- `INTERNAL_API_SECRET` (required) must be sent as `X-Internal-Secret`; `KALSHI_MCP_ALLOW_NO_SECRET=true` lifts that for local use. `PORT` defaults to 8000.

```bash
docker build -t kalshi-mcp . && docker run -e INTERNAL_API_SECRET=... -p 8000:8000 kalshi-mcp
```

## Implemented Tools
- `get_tags_for_series_categories`
  - Calls Kalshi public endpoint: `GET /search/tags_by_categories`
  - No API key required
- `get_balance`
  - Calls Kalshi private endpoint: `GET /portfolio/balance`
  - Requires API key authentication (`KALSHI_API_KEY_ID` + `KALSHI_API_KEY_PATH`)
- `get_subaccount_balances`
  - Calls Kalshi private endpoint: `GET /portfolio/subaccounts/balances`
  - Requires API key authentication (`KALSHI_API_KEY_ID` + `KALSHI_API_KEY_PATH`)
- `get_orders`
  - Calls Kalshi private endpoint: `GET /portfolio/orders`
  - Optional arguments:
    - `ticker` (string; market ticker)
    - `event_ticker` (string; comma-separated event tickers, maximum 10)
    - `status` (string: resting|canceled|executed)
    - `min_ts`/`max_ts` (int; unix seconds)
    - `limit` (int, 1-200)
    - `cursor` (string)
    - `subaccount` (int, 0-32)
  - Returns portfolio orders (and optional pagination cursor)
  - Requires API key authentication (`KALSHI_API_KEY_ID` + `KALSHI_API_KEY_PATH`)
- `get_order`
  - Calls Kalshi private endpoint: `GET /portfolio/orders/{order_id}`
  - Required arguments:
    - `order_id` (string; the order identifier)
  - Returns a single order object with all order fields
  - Requires API key authentication (`KALSHI_API_KEY_ID` + `KALSHI_API_KEY_PATH`)
- `get_positions`
  - Calls Kalshi private endpoint: `GET /portfolio/positions`
  - Optional arguments:
    - `cursor` (string)
    - `limit` (int, 1-1000; defaults to 100)
    - `count_filter` (string; comma-separated from `position` and/or `total_traded`)
    - `ticker` (string; market ticker)
    - `event_ticker` (string; comma-separated event tickers, maximum 10)
    - `subaccount` (int, 0-32)
  - Returns portfolio positions with `market_positions` and `event_positions` arrays, plus pagination cursor
  - Requires API key authentication (`KALSHI_API_KEY_ID` + `KALSHI_API_KEY_PATH`)
- `get_categories`
  - Calls Kalshi public endpoint: `GET /search/tags_by_categories`
  - Returns only the category names
  - No API key required
- `get_tags_for_series_category`
  - Calls Kalshi public endpoint: `GET /search/tags_by_categories`
  - Requires one argument: `category` (exact category name)
  - Returns tags for the selected category
  - No API key required
- `get_series_list`
  - Calls Kalshi public endpoint: `GET /series`
  - Optional arguments:
    - `category` (string)
    - `tags` (string)
    - `cursor` (string)
    - `limit` (int, 1-1000)
    - `include_product_metadata` (boolean)
    - `include_volume` (boolean)
  - Returns typed series objects from Kalshi response
  - Logs warning/error details when response fields have unexpected types/shapes
  - No API key required
- `get_series_tickers_for_category`
  - Pages Kalshi public endpoint: `GET /series`
  - Required arguments:
    - `category` (string)
  - Optional arguments:
    - `tags` (string)
    - `limit` (int, 1-1000; defaults to 1000)
    - `max_pages` (int, 1-10000; defaults to 1000)
  - Returns only `ticker` values across all pages
  - No API key required
- `get_markets`
  - Calls Kalshi public endpoint: `GET /markets`
  - Optional arguments:
    - `cursor` (string)
    - `limit` (int, 1-1000)
    - `status` (string; Kalshi docs list values like unopened|open|paused|closed|settled)
    - `tickers` (string; comma-separated market tickers)
    - `event_ticker` (string; comma-separated event tickers)
    - `series_ticker` (string)
    - `mve_filter` (string: only|exclude)
    - `min_created_ts`/`max_created_ts` (int; unix seconds)
    - `min_updated_ts` (int; unix seconds)
    - `min_close_ts`/`max_close_ts` (int; unix seconds)
    - `min_settled_ts`/`max_settled_ts` (int; unix seconds)
  - Returns typed markets from Kalshi response
  - No API key required
- `get_open_markets_for_series`
  - Pages Kalshi public endpoint: `GET /markets`
  - Required arguments:
    - `series_ticker` (string)
  - Optional arguments:
    - `limit` (int, 1-1000; defaults to 1000)
    - `max_pages` (int, 1-10000; defaults to 1000)
  - Forces `status=open` and returns all markets across all pages
  - No API key required
- `get_open_market_titles_for_series`
  - Pages Kalshi public endpoint: `GET /markets`
  - Required arguments:
    - `series_ticker` (string)
  - Optional arguments:
    - `limit` (int, 1-1000; defaults to 1000)
    - `max_pages` (int, 1-10000; defaults to 1000)
  - Forces `status=open` and returns only `ticker`, `title`, `subtitle`, `yes_sub_title`, `no_sub_title` for each market across all pages
  - No API key required

## Configuration
- `KALSHI_API_BASE_URL`
  - Default: `https://api.elections.kalshi.com/trade-api/v2`
- `KALSHI_TIMEOUT_SECONDS`
  - Default: `10`
- `KALSHI_API_KEY_ID`
  - Required for authenticated/private endpoints (for example `get_balance`)
- `KALSHI_API_KEY_PATH`
  - Required for authenticated/private endpoints
  - Path to your Kalshi API private key PEM file
- `.env`
  - `load_settings()` reads a local `.env` file from the repo root and loads variables
    when they are not already set in the environment

## Run as MCP stdio server
- Command (installed/editable):
  - `python3 -m pip install -e .`
  - `python3 -m kalshi_mcp.server`
- Command (no install):
  - `PYTHONPATH=src python3 -m kalshi_mcp.server`
- Transport:
  - JSON-RPC 2.0 over newline-delimited JSON on stdin/stdout

## Development
- Run unit tests (unittest):
  - `python3 -m unittest discover -s tests -p 'test_*.py'`
- Run unit tests (pytest):
  - Install dev deps: `python3 -m pip install -r requirements-dev.txt`
  - Then: `python3 -m pytest -q`
