"""The bundled demo dataset must stay internally consistent."""

import pytest

from restaurant_ops_mcp.connectors.demo import DemoConnector


@pytest.fixture(scope="module")
def conn():
    return DemoConnector()


def test_counts(conn):
    assert len(conn.menu_items()) == 8
    assert len(conn.ingredients()) == 18
    assert len(conn.catering_orders()) == 2


def test_cost_is_sum_of_lines(conn):
    for item in conn.menu_items():
        assert item.lines, f"{item.name} has no cost lines"
        assert item.cost == pytest.approx(sum(l.cost for l in item.lines), abs=0.001)


def test_margin_math(conn):
    for item in conn.menu_items():
        assert item.margin == pytest.approx(item.price - item.cost, abs=0.001)
        assert 0 < item.food_cost_pct < 1


def test_every_ingredient_has_history(conn):
    for ing in conn.ingredients():
        points = conn.price_points(ing.id)
        assert len(points) == 12, f"{ing.id} has {len(points)} price points"
        assert points == sorted(points, key=lambda p: p.date)


def test_catering_order_totals_match_menu(conn):
    prices = {m.name: m.price for m in conn.menu_items()}
    for order in conn.catering_orders():
        calc = sum(prices[l.name] * l.quantity for l in order.lines)
        assert calc == pytest.approx(order.total, abs=0.01)
