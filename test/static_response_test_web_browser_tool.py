import sys
import os
import asyncio

# Ensure the parent directory is in sys.path so 'core' can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.tool_management.web_browser_tool import WebBrowserTool

RESULT_DIR = os.path.join(os.path.dirname(__file__), 'result_fetch')
os.makedirs(RESULT_DIR, exist_ok=True)

def write_result(index, task, content, ext="txt"):
    filename = f"{index:02d}_{task}.{ext}"
    filepath = os.path.join(RESULT_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[Saved: {filepath}]")

async def main():
    tool = WebBrowserTool()
    # 1. Visit Amazon
    print("\n--- Testing 'visit' action (Amazon) ---")
    result_visit = await tool.execute_async(
        url="https://www.amazon.com",
        action="visit"
    )
    print(result_visit)
    write_result(1, "visit_amazon", str(result_visit))

    # 2. Extract Stack Overflow main content
    print("\n--- Testing 'extract_content' action (Stack Overflow main content) ---")
    result_extract = await tool.execute_async(
        url="https://stackoverflow.com",
        action="extract_content",
        selector="#mainbar"
    )
    print(result_extract)
    extract_content = result_extract.get("result", {}).get("content", str(result_extract))
    write_result(2, "extract_stackoverflow", extract_content, ext="html")

    # 3. Click GitHub Sign In button
    print("\n--- Testing 'click' action (GitHub Sign In button) ---")
    result_click = await tool.execute_async(
        url="https://github.com/login",
        action="click",
        selector="button[type=submit]"
    )
    print(result_click)
    write_result(3, "click_github_signin", str(result_click))

    # 4. Fill X.com search box
    print("\n--- Testing 'fill_form' action (X.com search box) ---")
    result_fill = await tool.execute_async(
        url="https://x.com/explore",
        action="fill_form",
        selector="input[data-testid=searchInput]",
        value="AI"
    )
    print(result_fill)
    write_result(4, "fillform_x_search", str(result_fill))

    # 5. Screenshot Samsung homepage
    print("\n--- Testing 'screenshot' action (Samsung homepage) ---")
    result_screenshot = await tool.execute_async(
        url="https://www.samsung.com",
        action="screenshot"
    )
    print(result_screenshot)
    screenshot_info = result_screenshot.get("result", {}).get("screenshot_path", str(result_screenshot))
    write_result(5, "screenshot_samsung", screenshot_info)

    # 6. Error: missing selector for click
    print("\n--- Testing error: missing selector for click ---")
    result_error = await tool.execute_async(
        url="https://github.com/login",
        action="click"
    )
    print(result_error)
    write_result(6, "error_missing_selector_click", str(result_error))

if __name__ == "__main__":
    asyncio.run(main())
