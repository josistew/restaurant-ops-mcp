"""The engine-json adapter maps a margin-engine export (fabricated fixture)."""

from pathlib import Path

import pytest

from restaurant_ops_mcp import service
from restaurant_ops_mcp.connectors.engine_json import EngineJsonConnector

FIXTURE = Path(__file__).parent / "fixtures" / "engine-sample.json"


@pytest.fixture(scope="module")
def conn():
    return EngineJsonConnector(FIXTURE)


def test_menu_item_maps(conn):
    items = conn.menu_items()
    assert len(items) == 1
    item = items[0]
    assert item.name == "Test Bowl"
    assert item.food_cost_pct == pytest.approx(0.35)
    assert item.lines[0].nutrition.calories == 320.0


def test_ingredient_maps_with_humanized_name_and_sku(conn):
    ing = conn.ingredients()[0]
    assert ing.name == "Test Chicken"
    assert ing.vendor_sku == "123456"
    assert ing.case_cost == 100.0


def test_price_points_anchor_plus_watch_events(conn):
    points = conn.price_points("test_chicken")
    assert [p.price for p in points] == [100.0, 108.0, 102.0]
    assert points[0].note == "engine price of record"
    assert "+8.0%" in points[1].note


def test_watch_events_trip_the_alert_band(conn):
    out = service.price_history(conn, "test chicken", weeks=5200)
    moves = [a["move_pct"] for a in out["summary"]["alerts"]]
    assert moves == [pytest.approx(8.0, abs=0.1), pytest.approx(-5.6, abs=0.1)]


def test_catering_is_honestly_empty(conn):
    out = service.catering_order(conn)
    assert out["found"] is False
    assert "engine-json" in out["message"]


def test_missing_file_raises_helpfully():
    with pytest.raises(FileNotFoundError, match="RESTAURANT_OPS_DATA"):
        EngineJsonConnector("/nope/engine.json")
