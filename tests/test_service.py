"""Tool behavior: matching, summaries, honest misses."""

import pytest

from restaurant_ops_mcp import service
from restaurant_ops_mcp.connectors.demo import DemoConnector


@pytest.fixture(scope="module")
def conn():
    return DemoConnector()


# --- matching ---------------------------------------------------------------

def test_partial_name_resolves_when_unique(conn):
    out = service.item_margin(conn, "sol chicken")
    assert out["found"] and out["name"] == "Sol Chicken Bowl"


def test_id_match(conn):
    out = service.item_margin(conn, "DEMO-ASADA")
    assert out["found"] and out["name"] == "Asada Bowl"


def test_ambiguous_query_returns_candidates_not_a_guess(conn):
    out = service.item_margin(conn, "bowl")
    assert out["found"] is False
    assert len(out["candidates"]) >= 3


def test_no_match(conn):
    out = service.item_margin(conn, "pizza")
    assert out["found"] is False and out["candidates"] == []


# --- margins ----------------------------------------------------------------

def test_margin_fields(conn):
    out = service.item_margin(conn, "Sol Chicken Bowl")
    assert out["price"] == 12.75
    assert out["cost"] == pytest.approx(3.99, abs=0.001)
    assert out["food_cost_pct"] == pytest.approx(0.313, abs=0.001)
    assert out["margin"] == pytest.approx(12.75 - 3.99, abs=0.001)
    assert any(l["name"] == "Grilled Chicken" for l in out["lines"])


def test_list_menu_items_category_filter(conn):
    out = service.list_menu_items(conn, category="curated")
    assert out["count"] == 4
    assert all("price" in i for i in out["items"])


# --- price history ----------------------------------------------------------

def test_avocado_spike_is_flagged(conn):
    out = service.price_history(conn, "avocado", weeks=52)
    alerts = out["summary"]["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["date"] == "2026-09-14"
    assert alerts[0]["move_pct"] == pytest.approx(18.1, abs=0.1)


def test_slow_creep_moves_window_but_no_alert(conn):
    out = service.price_history(conn, "skirt steak", weeks=52)
    assert out["summary"]["alerts"] == []
    assert out["summary"]["move_pct_over_window"] == pytest.approx(6.8, abs=0.1)


def test_vendor_sku_lookup(conn):
    out = service.price_history(conn, "200600")  # avocado SKU
    assert out["found"] and out["id"] == "avocado"


def test_used_in_links_price_to_recipes(conn):
    out = service.price_history(conn, "avocado")
    assert "guacamole" in out["used_in"]


# --- catering ---------------------------------------------------------------

def test_latest_order_is_default(conn):
    out = service.catering_order(conn)
    assert out["found"] and out["id"] == "CAT-1057"
    assert out["prep_servings"]["carne_asada"] == 10
    assert out["packaging"]["foil_wraps"] == 8


def test_order_by_id(conn):
    out = service.catering_order(conn, "cat-1042")
    assert out["found"] and out["customer"] == "Rivera Office Group"


def test_unknown_order_lists_known_ids(conn):
    out = service.catering_order(conn, "CAT-9999")
    assert out["found"] is False and "CAT-1042" in out["candidates"]


# --- nutrition --------------------------------------------------------------

def test_nutrition_values(conn):
    out = service.nutrition(conn, "baja shrimp")
    assert out["per_serving"]["calories"] == 955
    assert "Shellfish" in out["allergens"]
    assert out["status"] == "ok"


def test_nutrition_caveat_survives_to_output(conn):
    out = service.nutrition(conn, "churro")
    assert out["status"] != "ok"
    assert "not weighed" in out["status"]
