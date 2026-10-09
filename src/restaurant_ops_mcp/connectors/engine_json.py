"""Adapter for a margin-engine export (engine.json).

This is the format produced by the ingredient & margin engine's hub
export: menuItems / ingredients / priceWatch / tracker. Point
RESTAURANT_OPS_DATA at a local engine.json and every tool runs against
live engagement data - nothing in this repo ships that data.

Read-only and best-effort: catering orders are not part of the export,
so that tool returns empty under this connector.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ..models import CateringOrder, CostLine, Ingredient, MenuItem, Nutrition, PricePoint
from .base import Connector


def _money(value) -> float | None:
    """'$115.86' -> 115.86; passes numbers through; None for dashes/blanks."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.\-]", "", str(value))
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _humanize(slug: str) -> str:
    return slug.replace("_", " ").strip().title()


def _nutrition(raw: dict, prefix: str = "nut") -> Nutrition | None:
    cal = raw.get(f"{prefix}Cal")
    if cal is None:
        return None
    return Nutrition(
        calories=cal,
        protein_g=raw.get(f"{prefix}Pro"),
        fat_g=raw.get(f"{prefix}Fat"),
        carbs_g=raw.get(f"{prefix}Carb"),
        status=raw.get(f"{prefix}Status") or raw.get(f"{prefix}Note"),
    )


class EngineJsonConnector(Connector):
    name = "engine-json"

    def __init__(self, path: str | Path):
        self._path = Path(path).expanduser()
        if not self._path.exists():
            raise FileNotFoundError(
                f"engine.json not found at {self._path} - set RESTAURANT_OPS_DATA to the export path"
            )
        self._data = json.loads(self._path.read_text(encoding="utf-8"))

    def menu_items(self) -> list[MenuItem]:
        items = []
        for raw in self._data.get("menuItems", []):
            lines = [
                CostLine(
                    component_id=l.get("component", ""),
                    name=l.get("name", _humanize(l.get("component", ""))),
                    qty=l.get("qty", 1.0),
                    cost=l.get("cost") or 0.0,
                    portion=l.get("portion"),
                    nutrition=_nutrition(l),
                )
                for l in raw.get("lines", [])
            ]
            items.append(
                MenuItem(
                    id=raw["id"],
                    name=raw["name"],
                    category=raw.get("category"),
                    price=raw.get("price"),
                    cost=raw.get("cost"),
                    lines=lines,
                    allergens=raw.get("allergens"),
                    dietary=raw.get("dietary"),
                    nutrition=_nutrition(raw),
                    status=raw.get("status"),
                )
            )
        return items

    def ingredients(self) -> list[Ingredient]:
        out = []
        for raw in self._data.get("ingredients", []):
            out.append(
                Ingredient(
                    id=raw["id"],
                    name=_humanize(raw["id"]),
                    brand=raw.get("brand"),
                    pack=raw.get("pack"),
                    case_cost=raw.get("caseCost"),
                    unit=raw.get("unit"),
                    cost_per_unit=raw.get("costPerUnit"),
                    price_date=raw.get("priceDate"),
                    vendor_sku=str(raw["bek"]) if raw.get("bek") else None,
                    category=raw.get("tier"),
                    used_in=raw.get("usedIn", []),
                )
            )
        return out

    def price_points(self, ingredient_id: str) -> list[PricePoint]:
        ing = next((i for i in self.ingredients() if i.id == ingredient_id), None)
        if ing is None:
            return []
        points: list[PricePoint] = []
        # The ingredient's own dated price anchors the series.
        if ing.price_date and ing.case_cost is not None:
            points.append(PricePoint(date=ing.price_date, price=ing.case_cost, note="engine price of record"))
        # priceWatch events (matched on vendor sku) add every observed move.
        for ev in self._data.get("priceWatch", []):
            if ing.vendor_sku and str(ev.get("bek")) == ing.vendor_sku:
                new = _money(ev.get("new"))
                if new is not None and ev.get("date"):
                    note_bits = [b for b in (ev.get("movePct"), ev.get("note")) if b]
                    points.append(PricePoint(date=ev["date"], price=new, note=" - ".join(note_bits) or None))
        points.sort(key=lambda p: p.date)
        return points

    def catering_orders(self) -> list[CateringOrder]:
        return []  # not part of the engine export
