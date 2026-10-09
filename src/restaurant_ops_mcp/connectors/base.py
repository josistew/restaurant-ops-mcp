"""Connector contract: a data source becomes four lists.

Lookup, fuzzy matching, summaries, and alert math all live in the
service layer, so a new connector gets every tool for free the moment
it can produce these shapes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import CateringOrder, Ingredient, MenuItem, PricePoint


class Connector(ABC):
    """A read-only adapter from one restaurant data source to the normalized model."""

    name: str = "base"

    @abstractmethod
    def menu_items(self) -> list[MenuItem]: ...

    @abstractmethod
    def ingredients(self) -> list[Ingredient]: ...

    @abstractmethod
    def price_points(self, ingredient_id: str) -> list[PricePoint]:
        """Dated case-price history for one ingredient, oldest first."""

    @abstractmethod
    def catering_orders(self) -> list[CateringOrder]:
        """All known catering orders, oldest first. Sources without
        catering data return an empty list."""
