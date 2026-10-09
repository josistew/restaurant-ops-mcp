"""Bundled demo dataset: "Sol Bowl", a fictional two-location fast-casual
bowl restaurant. Every number is fabricated, but the shapes and the
relationships (lines sum to cost, prices dated to a source, one vendor
price spike in the history) mirror what a live engagement produces.
"""

from __future__ import annotations

import json
from importlib import resources

from ..models import (
    CateringLine,
    CateringOrder,
    CostLine,
    Ingredient,
    MenuItem,
    Nutrition,
    PricePoint,
)
from .base import Connector

_DATA_PKG = "restaurant_ops_mcp.data.demo"


def _load(filename: str):
    with resources.files(_DATA_PKG).joinpath(filename).open("r", encoding="utf-8") as f:
        return json.load(f)


def _nutrition(d: dict | None) -> Nutrition | None:
    if not d:
        return None
    return Nutrition(
        calories=d.get("calories"),
        protein_g=d.get("protein_g"),
        fat_g=d.get("fat_g"),
        carbs_g=d.get("carbs_g"),
        status=d.get("status"),
    )


class DemoConnector(Connector):
    name = "demo"

    def __init__(self):
        self._menu = _load("menu.json")
        self._ingredients = _load("ingredients.json")
        self._history = _load("price_history.json")
        self._orders = _load("catering_orders.json")

    def menu_items(self) -> list[MenuItem]:
        items = []
        for raw in self._menu:
            lines = [
                CostLine(
                    component_id=l["component_id"],
                    name=l["name"],
                    qty=l.get("qty", 1.0),
                    cost=l["cost"],
                    portion=l.get("portion"),
                    nutrition=_nutrition(l.get("nutrition")),
                )
                for l in raw.get("lines", [])
            ]
            items.append(
                MenuItem(
                    id=raw["id"],
                    name=raw["name"],
                    category=raw.get("category"),
                    price=raw.get("price"),
                    # cost is derived, never stored: lines are the truth
                    cost=round(sum(l.cost for l in lines), 4) if lines else raw.get("cost"),
                    lines=lines,
                    allergens=raw.get("allergens"),
                    dietary=raw.get("dietary"),
                    nutrition=_nutrition(raw.get("nutrition")),
                    status=raw.get("status"),
                )
            )
        return items

    def ingredients(self) -> list[Ingredient]:
        return [
            Ingredient(
                id=raw["id"],
                name=raw["name"],
                brand=raw.get("brand"),
                pack=raw.get("pack"),
                case_cost=raw.get("case_cost"),
                unit=raw.get("unit"),
                cost_per_unit=raw.get("cost_per_unit"),
                price_date=raw.get("price_date"),
                vendor_sku=raw.get("vendor_sku"),
                category=raw.get("category"),
                used_in=raw.get("used_in", []),
            )
            for raw in self._ingredients
        ]

    def price_points(self, ingredient_id: str) -> list[PricePoint]:
        return [
            PricePoint(date=p["date"], price=p["price"], note=p.get("note"))
            for p in self._history.get(ingredient_id, [])
        ]

    def catering_orders(self) -> list[CateringOrder]:
        return [
            CateringOrder(
                id=raw["id"],
                location_id=raw.get("location_id"),
                pickup_at=raw.get("pickup_at"),
                customer=raw.get("customer"),
                status=raw.get("status"),
                total=raw.get("total"),
                lines=[
                    CateringLine(
                        name=l["name"],
                        quantity=l["quantity"],
                        catalog_object_id=l.get("catalog_object_id"),
                        modifiers=l.get("modifiers", []),
                    )
                    for l in raw.get("lines", [])
                ],
                prep_servings=raw.get("prep_servings", {}),
                packaging=raw.get("packaging", {}),
            )
            for raw in self._orders
        ]
