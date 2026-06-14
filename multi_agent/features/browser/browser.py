from __future__ import annotations

import base64
from typing import Any


class _PageState:
    def __init__(self) -> None:
        self.url = ""
        self.title = ""
        self.tree_text = ""
        self.screenshot_b64: str | None = None
        self.element_count = 0


class BrowserTool:
    def __init__(self, headless: bool = True, viewport_width: int = 1280, viewport_height: int = 720) -> None:
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self._playwright: Any = None
        self._browser: Any = None
        self._page: Any = None
        self._state = _PageState()

    async def _ensure_browser(self) -> None:
        if self._page is not None:
            return
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise ImportError(
                "playwright is required. Install: pip install 'multi-agent[browser]'"
            ) from None

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(
            viewport={"width": self.viewport_width, "height": self.viewport_height},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )
        self._page = await context.new_page()

    def _tree_node_to_text(self, node: dict, depth: int = 0) -> str:
        role = node.get("role", "")
        name = node.get("name", "")
        if not role and not name:
            return ""
        interactive_roles = {
            "button", "link", "textbox", "combobox", "checkbox",
            "radio", "menuitem", "tab", "searchbox", "listbox",
            "switch", "slider", "spinbutton", "progressbar",
        }
        is_interactive = role in interactive_roles
        indent = "  " * depth
        idx = self._state.element_count
        self._state.element_count += 1
        mark = " [ACTIVE]" if is_interactive else ""
        line = f"{indent}[{idx}] <{role}>{name[:120]}{mark}\n"
        for child in node.get("children", []):
            line += self._tree_node_to_text(child, depth + 1)
        return line

    async def _extract_page_tree(self) -> str:
        js = """
        (function() {
            const interactiveTags = new Set([
                'a', 'button', 'input', 'select', 'textarea', 'details', 'summary'
            ]);
            const interactiveRoles = new Set([
                'button', 'link', 'textbox', 'combobox', 'checkbox',
                'radio', 'menuitem', 'tab', 'searchbox', 'listbox',
                'switch', 'slider', 'spinbutton', 'progressbar'
            ]);
            function isInteractive(el) {
                if (interactiveTags.has(el.tagName.toLowerCase())) return true;
                const role = el.getAttribute('role');
                if (role && interactiveRoles.has(role)) return true;
                if (el.hasAttribute('tabindex') && el.getAttribute('tabindex') !== '-1') return true;
                if (el.tagName.toLowerCase() === 'body') return false;
                if (el.tagName.toLowerCase() === 'div' || el.tagName.toLowerCase() === 'span') {
                    return el.hasAttribute('onclick') || el.getAttribute('role') !== null;
                }
                return false;
            }
            function getNode(el, depth, maxDepth) {
                if (depth > maxDepth) return null;
                const tag = el.tagName.toLowerCase();
                if (tag === 'script' || tag === 'style' || tag === 'noscript') return null;
                if (el.offsetParent === null && tag !== 'body' && tag !== 'html') return null;
                const role = el.getAttribute('role') || tag;
                const ariaLabel = el.getAttribute('aria-label') || '';
                const alt = el.getAttribute('alt') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const title = el.getAttribute('title') || '';
                let text = (el.textContent || '').trim().slice(0, 120);
                if (tag === 'img') text = alt || text;
                if (tag === 'input') text = placeholder || ariaLabel || tag;
                if (tag === 'a' && el.getAttribute('href')) {
                    text = text || el.getAttribute('href');
                }
                let name = ariaLabel || alt || placeholder || title || text;
                if (!name) return null;
                name = name.slice(0, 120);
                const interactive = isInteractive(el);
                const result = { role: interactive ? tag : role, name: name, children: [] };
                for (const child of el.children) {
                    const c = getNode(child, depth + 1, maxDepth);
                    if (c) result.children.push(c);
                }
                return result;
            }
            const tree = getNode(document.body, 0, 8);
            return JSON.stringify(tree || {role: 'empty', name: 'empty'});
        })();
        """
        try:
            result = await self._page.evaluate(js)
            import json
            tree = json.loads(result)
            return self._tree_node_to_text(tree)
        except Exception as e:
            return f"(error extracting tree: {e})"

    async def _capture_state(self) -> _PageState:
        if self._page is None:
            return _PageState()
        self._state.url = self._page.url
        self._state.title = await self._page.title()
        self._state.element_count = 0
        self._state.tree_text = await self._extract_page_tree()
        try:
            screenshot = await self._page.screenshot(type="png", full_page=False)
            self._state.screenshot_b64 = base64.b64encode(screenshot).decode("utf-8")
        except Exception:
            self._state.screenshot_b64 = None
        return self._state

    async def navigate(self, url: str) -> dict[str, Any]:
        await self._ensure_browser()
        try:
            await self._page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            return {"success": False, "error": str(e), "url": url}
        await self._page.wait_for_timeout(1000)
        state = await self._capture_state()
        return {
            "success": True,
            "url": state.url,
            "title": state.title,
            "page": state.tree_text[:6000],
            "element_count": state.element_count,
        }

    async def _find_element_by_index(self, index: int):
        js = """
        (function(targetIdx) {
            let idx = 0;
            function find(el, depth) {
                if (depth > 8) return null;
                const tag = el.tagName.toLowerCase();
                if (tag === 'script' || tag === 'style' || tag === 'noscript') return null;
                if (el.offsetParent === null && tag !== 'body' && tag !== 'html') return null;
                const ariaLabel = el.getAttribute('aria-label') || '';
                const alt = el.getAttribute('alt') || '';
                const placeholder = el.getAttribute('placeholder') || '';
                const title = el.getAttribute('title') || '';
                let text = (el.textContent || '').trim().slice(0, 120);
                if (tag === 'img') text = alt || text;
                if (tag === 'input') text = placeholder || ariaLabel || tag;
                if (tag === 'a' && el.getAttribute('href')) {
                    text = text || el.getAttribute('href');
                }
                const name = ariaLabel || alt || placeholder || title || text;
                if (!name) {
                    for (const child of el.children) {
                        const r = find(child, depth + 1);
                        if (r) return r;
                    }
                    return null;
                }
                if (idx === targetIdx) return el;
                idx++;
                for (const child of el.children) {
                    const r = find(child, depth + 1);
                    if (r) return r;
                }
                return null;
            }
            const found = find(document.body, 0);
            if (found) {
                const rect = found.getBoundingClientRect();
                return {
                    tag: found.tagName,
                    x: rect.x + rect.width/2,
                    y: rect.y + rect.height/2,
                    text: (found.textContent || '').trim().slice(0, 100),
                    isLink: found.tagName === 'A',
                    href: found.getAttribute('href') || ''
                };
            }
            return null;
        })(%d);
        """ % index
        return await self._page.evaluate(js)

    async def click(self, element_index: int) -> dict[str, Any]:
        await self._ensure_browser()
        target = await self._find_element_by_index(element_index)
        if target is None:
            return {"success": False, "error": f"Element {element_index} not found"}
        try:
            if target.get("isLink") and target.get("href"):
                await self._page.goto(target["href"], wait_until="domcontentloaded", timeout=30000)
            else:
                await self._page.mouse.click(target["x"], target["y"])
            await self._page.wait_for_timeout(500)
            state = await self._capture_state()
            return {"success": True, "page": state.tree_text[:6000], "url": state.url}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def type(self, element_index: int, text: str) -> dict[str, Any]:
        await self._ensure_browser()
        target = await self._find_element_by_index(element_index)
        if target is None:
            return {"success": False, "error": f"Element {element_index} not found"}
        try:
            await self._page.mouse.click(target["x"], target["y"])
            await self._page.wait_for_timeout(200)
            await self._page.keyboard.type(text, delay=20)
            state = await self._capture_state()
            return {"success": True, "page": state.tree_text[:6000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def scroll(self, direction: str = "down", amount: int = 500) -> dict[str, Any]:
        await self._ensure_browser()
        delta = -amount if direction == "up" else amount
        try:
            await self._page.evaluate(f"window.scrollBy(0, {delta})")
            await self._page.wait_for_timeout(300)
            state = await self._capture_state()
            return {"success": True, "page": state.tree_text[:6000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def screenshot(self) -> dict[str, Any]:
        await self._ensure_browser()
        state = await self._capture_state()
        return {
            "success": True,
            "screenshot_b64": state.screenshot_b64,
            "url": state.url,
            "title": state.title,
        }

    async def get_state(self) -> dict[str, Any]:
        state = await self._capture_state()
        return {
            "success": True,
            "url": state.url,
            "title": state.title,
            "page": state.tree_text[:6000],
            "element_count": state.element_count,
            "has_screenshot": state.screenshot_b64 is not None,
        }

    async def close(self) -> None:
        if self._page is not None:
            try:
                await self._page.close()
            except Exception:
                pass
            self._page = None
        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    def make_tools(self) -> list:
        from multi_agent.core.tool import Tool, ToolResult, PermissionLevel

        async def navigate_fn(url: str) -> ToolResult:
            result = await self.navigate(url)
            return ToolResult(success=result.get("success", False), output=str(result))

        async def click_fn(element_index: int) -> ToolResult:
            result = await self.click(element_index)
            return ToolResult(success=result.get("success", False), output=str(result))

        async def type_fn(element_index: int, text: str) -> ToolResult:
            result = await self.type(element_index, text)
            return ToolResult(success=result.get("success", False), output=str(result))

        async def scroll_fn(direction: str = "down", amount: int = 500) -> ToolResult:
            result = await self.scroll(direction, amount)
            return ToolResult(success=result.get("success", False), output=str(result))

        async def screenshot_fn() -> ToolResult:
            result = await self.screenshot()
            return ToolResult(success=result.get("success", False), output=str(result))

        return [
            Tool(
                name="browser_navigate",
                description="Navigate to a URL. Returns the page content as an accessibility tree with numbered elements. Use this to start browsing.",
                parameters={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to visit"}
                    },
                    "required": ["url"],
                },
                function=navigate_fn,
                permission=PermissionLevel.allow,
            ),
            Tool(
                name="browser_click",
                description="Click an element by its index number from the accessibility tree. Use this to interact with buttons, links, and other interactive elements.",
                parameters={
                    "type": "object",
                    "properties": {
                        "element_index": {
                            "type": "integer",
                            "description": "The element index from the page tree",
                        }
                    },
                    "required": ["element_index"],
                },
                function=click_fn,
                permission=PermissionLevel.ask,
            ),
            Tool(
                name="browser_type",
                description="Type text into an input field identified by its element index.",
                parameters={
                    "type": "object",
                    "properties": {
                        "element_index": {
                            "type": "integer",
                            "description": "The input element index from the page tree",
                        },
                        "text": {"type": "string", "description": "The text to type"},
                    },
                    "required": ["element_index", "text"],
                },
                function=type_fn,
                permission=PermissionLevel.ask,
            ),
            Tool(
                name="browser_scroll",
                description="Scroll the page up or down by a given number of pixels.",
                parameters={
                    "type": "object",
                    "properties": {
                        "direction": {
                            "type": "string",
                            "enum": ["up", "down"],
                            "description": "Scroll direction",
                        },
                        "amount": {
                            "type": "integer",
                            "description": "Pixels to scroll",
                        },
                    },
                },
                function=scroll_fn,
                permission=PermissionLevel.allow,
            ),
            Tool(
                name="browser_screenshot",
                description="Take a screenshot of the current page. Returns a base64-encoded PNG.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
                function=screenshot_fn,
                permission=PermissionLevel.allow,
            ),
        ]
