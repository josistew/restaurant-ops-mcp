# Restaurant Ops MCP

![tests](https://github.com/josistew/restaurant-ops-mcp/actions/workflows/tests.yml/badge.svg)

An [MCP](https://modelcontextprotocol.io) server that gives AI agents eyes on restaurant operating data: **menu margins, vendor price history, catering orders, and nutrition** — the numbers an owner actually runs the business on.

Ask Claude things like:

> *"Which menu items does the avocado price spike hit, and what does it do to their food cost?"*
> *"What's on the prep sheet for tomorrow's catering pickup?"*
> *"Has anything moved more than 5% on the last few invoices?"*

...and the answers come from your data, with the same caveats your data carries.

## Why this exists

I build food-cost and margin systems for independent restaurants. The pattern is always the same: the data lives in a POS, a distributor portal, and a spreadsheet, and the owner only trusts a number when it keeps its provenance — what it costs, as of when, per which invoice. This server packages that pattern as MCP tools so any agent can reason over it, and isolates the messy part (where the data comes from) behind a small connector interface.

Design rules carried over from live engagements:

- **No silent guesses.** An ambiguous item name returns candidates, not a best guess. A connector without catering data says so.
- **Caveats travel with numbers.** A nutrition figure with an unverified cook-loss basis arrives marked that way; the tool description tells the agent to surface it.
- **Price moves are the signal.** History comes back with a 5% week-over-week alert band (how distributor price creep and billing errors actually show up) plus which recipes the ingredient feeds.

## Tools

| Tool | What it answers |
|---|---|
| `list_menu_items` | Discovery: every item with price and food-cost % (optional category filter) |
| `get_item_margin` | Price, plate cost, margin, food-cost %, and the per-component cost lines |
| `get_price_history` | Dated vendor case prices, window summary, ≥5% move alerts, affected recipes |
| `get_catering_order` | One order with its kitchen prep sheet (servings per component + packaging) |
| `get_nutrition` | Per-serving calories/protein/fat/carbs, allergens, per-component breakdown, verification status |

All tools are read-only.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/josistew/restaurant-ops-mcp
cd restaurant-ops-mcp
uv sync
uv run pytest        # 27 tests, includes a live stdio handshake
```

### Claude Code

```bash
claude mcp add restaurant-ops -- uv --directory /path/to/restaurant-ops-mcp run restaurant-ops-mcp
```

(Or just open this repo in Claude Code — the included `.mcp.json` registers the server at project scope.)

### Claude Desktop

```json
{
  "mcpServers": {
    "restaurant-ops": {
      "command": "uv",
      "args": ["--directory", "/path/to/restaurant-ops-mcp", "run", "restaurant-ops-mcp"]
    }
  }
}
```

Out of the box it serves the bundled demo dataset. Try: *"What's the food cost on the Asada Bowl?"* or *"Show me 12 weeks of avocado prices."*

## Connectors

The tools are written once against a normalized model (`models.py`); each data source is a connector that produces four lists — menu items, ingredients, price points, catering orders. Pick one with environment variables:

| `RESTAURANT_OPS_CONNECTOR` | Source |
|---|---|
| `demo` (default) | **Sol Bowl**, a fictional two-location fast-casual bowl restaurant. Fabricated numbers, realistic shapes: costs sum from component lines, prices are dated, the history contains one supply-shock spike and one slow creep, one dessert ships with an honest "estimate, not weighed" nutrition caveat. |
| `engine-json` | A margin-engine export (`engine.json`) — the format produced by the ingredient & margin engine I run for client restaurants. Set `RESTAURANT_OPS_DATA=/path/to/engine.json`. Read-only; catering orders are not part of that export. |

Planned seams (same interface, new source): **Square** (catalog + orders are already the shape the catering model uses), **Toast**, and **invoice-PDF extraction** for distributors without an API.

### Writing a connector

Subclass `Connector` (four methods), map your source into the dataclasses in `models.py`, add a branch in `connectors/__init__.py`. Everything else — matching, summaries, alert bands, the tools themselves — comes free. The demo connector (~100 lines) is the reference implementation; `tests/test_engine_adapter.py` shows how to test one against a fabricated fixture.

## What the demo data demonstrates

- `get_price_history("avocado")` → a +18.1% jump on 2026-09-14 trips the alert band
- `get_price_history("skirt steak")` → +6.8% over the window with **no** single-week alert: the creep you only see with history
- `get_catering_order()` → tomorrow's pickup, translated to prep servings and packaging counts
- `get_nutrition("churro")` → a number that arrives with its verification caveat attached
- `get_item_margin("bowl")` → ambiguous on purpose; returns candidates instead of guessing

## Project layout

```
src/restaurant_ops_mcp/
  server.py            # FastMCP app: 5 tools, stdio transport
  service.py           # matching, summaries, alert math (connector-agnostic)
  models.py            # the normalized model connectors map into
  connectors/
    base.py            # the 4-method contract
    demo.py            # bundled fictional dataset (default)
    engine_json.py     # margin-engine export adapter
  data/demo/           # Sol Bowl: menu, ingredients, 12 weeks of prices, 2 orders
tests/                 # 27 tests incl. an end-to-end stdio MCP handshake
```

No client data ships in this repository; the demo dataset is fictional end to end.

## License

MIT — see [LICENSE](LICENSE).

---

Built by [Josiah Stewart](mailto:josiah.stewart@gmail.com) · Josi Stew LLC · from patterns developed on live restaurant engagements (margin engine, catering intake, invoice QA).
