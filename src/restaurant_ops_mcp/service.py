"""Lookup and summary logic shared by every connector.

Tools call these functions; connectors only supply data. All matching is
forgiving (id, exact name, then substring) because agents pass names the
way people say them, and an honest "no match, here are the candidates"
beats a silent guess - the same rule the catering mapper lives by.
"""

from __future__ import annotations

from datetime import date, timedelta

from .connectors.base import Connector
from .models import Ingredient, MenuItem, to_dict

# A move this large (either direction) between consecutive points gets
# flagged in price history summaries. Mirrors a typical invoice-watch band.
ALERT_BAND_PCT = 5.0


def _match(query: str, candidates, keys) -> tuple[object | None, list[str]]:
    """Resolve a query against candidates; returns (hit, suggestions).

    Order: exact id -> exact name (case-insensitive) -> unique substring.
    Multiple substring hits return no object and the candidate names.
    """
    q = query.strip().lower()
    for c in candidates:
        if c.id.lower() == q:
            return c, []
    for c in candidates:
        if any((getattr(c, k) or "").lower() == q for k in keys):
            return c, []
    partial = [c for c in candidates if any(q in (getattr(c, k) or "").lower() for k in keys)]
    if len(partial) == 1:
        return partial[0], []
    return None, [c.name for c in partial][:10]


def find_menu_item(conn: Connector, query: str) -> tuple[MenuItem | None, list[str]]:
    return _match(query, conn.menu_items(), ("name",))


def find_ingredient(conn: Connector, query: str) -> tuple[Ingredient | None, list[str]]:
    return _match(query, conn.ingredients(), ("name", "vendor_sku"))


def _not_found(kind: str, query: str, candidates: list[str]) -> dict:
    return {
        "found": False,
        "query": query,
        "message": f"No single {kind} matches '{query}'."
        + (" Did you mean one of these?" if candidates else ""),
        "candidates": candidates,
    }


def list_menu_items(conn: Connector, category: str | None = None) -> dict:
    items = conn.menu_items()
    if category:
        items = [i for i in items if (i.category or "").lower() == category.strip().lower()]
    return {
        "connector": conn.name,
        "count": len(items),
        "items": [
            {
                "id": i.id,
                "name": i.name,
                "category": i.category,
                "price": i.price,
                "food_cost_pct": round(i.food_cost_pct, 4) if i.food_cost_pct is not None else None,
            }
            for i in items
        ],
    }


def item_margin(conn: Connector, item: str) -> dict:
    hit, candidates = find_menu_item(conn, item)
    if hit is None:
        return _not_found("menu item", item, candidates)
    return {
        "found": True,
        "id": hit.id,
        "name": hit.name,
        "category": hit.category,
        "price": hit.price,
        "cost": round(hit.cost, 4) if hit.cost is not None else None,
        "margin": round(hit.margin, 4) if hit.margin is not None else None,
        "food_cost_pct": round(hit.food_cost_pct, 4) if hit.food_cost_pct is not None else None,
        "status": hit.status,
        "lines": [
            {"component": l.component_id, "name": l.name, "qty": l.qty, "cost": l.cost, "portion": l.portion}
            for l in hit.lines
        ],
    }


def price_history(conn: Connector, ingredient: str, weeks: int = 12) -> dict:
    hit, candidates = find_ingredient(conn, ingredient)
    if hit is None:
        return _not_found("ingredient", ingredient, candidates)

    points = conn.price_points(hit.id)
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
    recent = [p for p in points if p.date >= cutoff] or points[-2:]

    alerts = []
    for prev, cur in zip(recent, recent[1:]):
        if prev.price:
            move = (cur.price - prev.price) / prev.price * 100
            if abs(move) >= ALERT_BAND_PCT:
                alerts.append(
                    {"date": cur.date, "from": prev.price, "to": cur.price, "move_pct": round(move, 1)}
                )

    prices = [p.price for p in recent]
    first, last = (prices[0], prices[-1]) if prices else (None, None)
    return {
        "found": True,
        "id": hit.id,
        "name": hit.name,
        "brand": hit.brand,
        "pack": hit.pack,
        "vendor_sku": hit.vendor_sku,
        "unit": hit.unit,
        "cost_per_unit": hit.cost_per_unit,
        "price_date": hit.price_date,
        "weeks": weeks,
        "points": [{"date": p.date, "price": p.price, "note": p.note} for p in recent],
        "summary": {
            "current": last,
            "low": min(prices) if prices else None,
            "high": max(prices) if prices else None,
            "move_pct_over_window": round((last - first) / first * 100, 1) if first else None,
            "alerts": alerts,
        },
        "used_in": hit.used_in,
    }


def catering_order(conn: Connector, order_id: str | None = None) -> dict:
    orders = conn.catering_orders()
    if not orders:
        return {
            "found": False,
            "message": f"No catering orders available from the '{conn.name}' connector.",
        }
    if order_id:
        hit = next((o for o in orders if o.id.lower() == order_id.strip().lower()), None)
        if hit is None:
            return _not_found("catering order", order_id, [o.id for o in orders])
    else:
        hit = orders[-1]  # latest
    d = to_dict(hit)
    d["found"] = True
    d["note"] = None if order_id else "No order_id given - returning the most recent order."
    return d


def nutrition(conn: Connector, item: str) -> dict:
    hit, candidates = find_menu_item(conn, item)
    if hit is None:
        return _not_found("menu item", item, candidates)
    n = hit.nutrition
    return {
        "found": True,
        "id": hit.id,
        "name": hit.name,
        "per_serving": {
            "calories": n.calories if n else None,
            "protein_g": n.protein_g if n else None,
            "fat_g": n.fat_g if n else None,
            "carbs_g": n.carbs_g if n else None,
        },
        "status": (n.status if n else None) or "ok",
        "allergens": hit.allergens,
        "dietary": hit.dietary,
        "components": [
            {
                "name": l.name,
                "portion": l.portion,
                "calories": l.nutrition.calories if l.nutrition else None,
                "protein_g": l.nutrition.protein_g if l.nutrition else None,
                "fat_g": l.nutrition.fat_g if l.nutrition else None,
                "carbs_g": l.nutrition.carbs_g if l.nutrition else None,
                "status": l.nutrition.status if l.nutrition else None,
            }
            for l in hit.lines
        ],
    }
