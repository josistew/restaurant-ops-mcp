"""Restaurant Ops MCP server (stdio).

Five read-only tools over one normalized restaurant data model. The
connector behind them is chosen by environment variables - see
connectors/__init__.py - so the same tools answer from the bundled demo
dataset or from a live margin-engine export.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from . import service
from .connectors import get_connector

mcp = MCPServer(
    "restaurant-ops",
    instructions=(
        "Read-only restaurant operating data: menu margins, vendor price "
        "history, catering orders, nutrition. Call list_menu_items first to "
        "discover exact names. Numbers may carry verification caveats in a "
        "'status' field - always surface those alongside the number."
    ),
)

_connector = None


def _conn():
    global _connector
    if _connector is None:
        _connector = get_connector()
    return _connector


@mcp.tool()
def list_menu_items(category: str | None = None) -> dict:
    """List every menu item with its price and food-cost percent.

    Use this first to discover exact item names before calling
    get_item_margin or get_nutrition. Optionally filter by category
    (e.g. "curated", "drink", "side").
    """
    return service.list_menu_items(_conn(), category)


@mcp.tool()
def get_item_margin(item: str) -> dict:
    """Menu item economics: price, plate cost, margin, food-cost percent,
    and the per-component cost lines that make up the plate.

    `item` can be an item id, an exact name, or a partial name
    ("chicken bowl"). If the match is ambiguous the response lists
    candidates instead of guessing. food_cost_pct is a fraction
    (0.40 = 40%).
    """
    return service.item_margin(_conn(), item)


@mcp.tool()
def get_price_history(ingredient: str, weeks: int = 12) -> dict:
    """Vendor case-price history for one ingredient over the last N weeks.

    `ingredient` matches by id, name, or vendor SKU. Returns dated price
    points, a summary (current/low/high, percent move over the window),
    and alerts for any week-over-week move of 5% or more - the signal a
    distributor price creep or billing error shows up as. Also lists the
    recipes the ingredient is used in, so you can reason about which
    menu items a price move hits.
    """
    return service.price_history(_conn(), ingredient, weeks)


@mcp.tool()
def get_catering_order(order_id: str | None = None) -> dict:
    """One catering order with its prep sheet.

    Returns the order header (pickup time, location, customer, total),
    the line items as sold, and the kitchen-facing translation:
    prep_servings (component -> servings to prep) and packaging counts.
    Omit order_id to get the most recent order. Connectors without
    catering data say so rather than inventing orders.
    """
    return service.catering_order(_conn(), order_id)


@mcp.tool()
def get_nutrition(item: str) -> dict:
    """Per-serving nutrition for a menu item: calories, protein, fat,
    carbs, allergens, and the per-component breakdown.

    A `status` other than "ok" means the number is published with a
    stated verification caveat (e.g. cook-loss basis unverified) -
    surface that caveat, never present the number as settled.
    """
    return service.nutrition(_conn(), item)


def main() -> None:
    mcp.run()  # stdio transport


if __name__ == "__main__":
    main()
