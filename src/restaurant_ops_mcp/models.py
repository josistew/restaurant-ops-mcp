"""Normalized data model every connector maps into.

The point of this layer: tools are written once, against these shapes,
and each POS / distributor / spreadsheet source only has to answer
"how do I become this?"
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Nutrition:
    calories: float | None = None
    protein_g: float | None = None
    fat_g: float | None = None
    carbs_g: float | None = None
    # "ok" when every component traces to a source; otherwise a short
    # reason the number needs verification (e.g. "cook-loss unverified").
    status: str | None = None


@dataclass
class CostLine:
    """One component of a menu item (a recipe serving, an ingredient, packaging)."""

    component_id: str
    name: str
    qty: float = 1.0
    cost: float = 0.0
    portion: str | None = None
    nutrition: Nutrition | None = None


@dataclass
class MenuItem:
    id: str
    name: str
    category: str | None = None
    price: float | None = None
    cost: float | None = None
    lines: list[CostLine] = field(default_factory=list)
    allergens: str | None = None
    dietary: str | None = None
    nutrition: Nutrition | None = None
    status: str | None = None

    @property
    def food_cost_pct(self) -> float | None:
        if self.price and self.cost is not None and self.price > 0:
            return self.cost / self.price
        return None

    @property
    def margin(self) -> float | None:
        if self.price is not None and self.cost is not None:
            return self.price - self.cost
        return None


@dataclass
class Ingredient:
    id: str
    name: str
    brand: str | None = None
    pack: str | None = None
    case_cost: float | None = None
    unit: str | None = None  # recipe unit: lb, each, oz...
    cost_per_unit: float | None = None
    price_date: str | None = None  # ISO date of the price's source document
    vendor_sku: str | None = None
    category: str | None = None
    used_in: list[str] = field(default_factory=list)


@dataclass
class PricePoint:
    date: str  # ISO date
    price: float  # case/invoice price on that date
    note: str | None = None


@dataclass
class CateringLine:
    name: str
    quantity: int
    catalog_object_id: str | None = None
    modifiers: list[str] = field(default_factory=list)


@dataclass
class CateringOrder:
    id: str
    location_id: str | None = None
    pickup_at: str | None = None  # ISO datetime
    customer: str | None = None
    status: str | None = None
    total: float | None = None
    lines: list[CateringLine] = field(default_factory=list)
    # Prep sheet: component id -> servings to prep, plus packaging counts.
    prep_servings: dict[str, float] = field(default_factory=dict)
    packaging: dict[str, int] = field(default_factory=dict)


def to_dict(obj) -> dict:
    """Dataclass -> plain dict, with computed MenuItem fields included."""
    d = asdict(obj)
    if isinstance(obj, MenuItem):
        d["food_cost_pct"] = obj.food_cost_pct
        d["margin"] = obj.margin
    return d
