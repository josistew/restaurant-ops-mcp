"""End-to-end: spawn the server over stdio, speak MCP to it."""

import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

EXPECTED_TOOLS = {
    "list_menu_items",
    "get_item_margin",
    "get_price_history",
    "get_catering_order",
    "get_nutrition",
}


def test_stdio_handshake_and_tool_call():
    async def run():
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "restaurant_ops_mcp.server"]
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                assert {t.name for t in tools.tools} == EXPECTED_TOOLS
                for t in tools.tools:
                    assert t.description, f"{t.name} is missing a description"

                result = await session.call_tool("get_item_margin", {"item": "asada"})
                assert not result.is_error
                text = result.content[0].text
                assert "Asada Bowl" in text and "food_cost_pct" in text

    asyncio.run(run())
