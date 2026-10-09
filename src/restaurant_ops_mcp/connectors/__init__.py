"""Connector factory.

RESTAURANT_OPS_CONNECTOR picks the source:
  demo         (default) bundled fictional dataset
  engine-json  a margin-engine export; path in RESTAURANT_OPS_DATA

Planned seams (same four methods, new source): square, toast,
invoice-pdf. See README.
"""

from __future__ import annotations

import os

from .base import Connector
from .demo import DemoConnector
from .engine_json import EngineJsonConnector

__all__ = ["Connector", "DemoConnector", "EngineJsonConnector", "get_connector"]


def get_connector() -> Connector:
    kind = os.environ.get("RESTAURANT_OPS_CONNECTOR", "demo").strip().lower()
    if kind == "demo":
        return DemoConnector()
    if kind in ("engine-json", "engine_json"):
        path = os.environ.get("RESTAURANT_OPS_DATA")
        if not path:
            raise ValueError("RESTAURANT_OPS_CONNECTOR=engine-json needs RESTAURANT_OPS_DATA=<path to engine.json>")
        return EngineJsonConnector(path)
    raise ValueError(f"Unknown connector '{kind}' (expected: demo, engine-json)")
