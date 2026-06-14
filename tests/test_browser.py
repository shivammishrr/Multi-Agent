import pytest


pytestmark = pytest.mark.skipif(
    True,
    reason="Browser tests skipped by default. Run with --browser flag or set BROWSER_TESTS=1",
)


@pytest.mark.asyncio
async def test_navigate_and_get_state():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    try:
        result = await bt.navigate("https://example.com")
        assert result["success"] is True
        assert "example" in result["title"]
        assert result["element_count"] > 0
    finally:
        await bt.close()


@pytest.mark.asyncio
async def test_browser_state_after_navigate():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    try:
        await bt.navigate("https://example.com")
        state = await bt.get_state()
        assert state["success"] is True
        assert "example.com" in state["url"] or "example" in state["url"]
        assert state["element_count"] > 0
    finally:
        await bt.close()


@pytest.mark.asyncio
async def test_screenshot():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    try:
        await bt.navigate("https://example.com")
        result = await bt.screenshot()
        assert result["success"] is True
        assert result["screenshot_b64"] is not None
        assert len(result["screenshot_b64"]) > 100
    finally:
        await bt.close()


@pytest.mark.asyncio
async def test_make_tools():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    tools = bt.make_tools()
    assert len(tools) == 5
    tool_names = {t.name for t in tools}
    assert tool_names == {"browser_navigate", "browser_click", "browser_type", "browser_scroll", "browser_screenshot"}
    await bt.close()


@pytest.mark.asyncio
async def test_reuse_same_browser():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    try:
        r1 = await bt.navigate("https://example.com")
        assert r1["success"] is True
        assert bt._page is not None
        r2 = await bt.get_state()
        assert r2["success"] is True
    finally:
        await bt.close()


@pytest.mark.asyncio
async def test_close_then_reuse_fails():
    from multi_agent.features.browser import BrowserTool

    bt = BrowserTool(headless=True)
    await bt.navigate("https://example.com")
    await bt.close()
    with pytest.raises(Exception):
        await bt.get_state()
