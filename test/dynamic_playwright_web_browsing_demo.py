import os
import uuid
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime

ROOT_LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'LOGER', 'web_browsing')
os.makedirs(ROOT_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(ROOT_LOG_DIR, "web_browsing_log.txt")

def log_action(task, message):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"[{datetime.now()}] [{task}] {message}\n")
    print(f"[LOG] [{task}] {message}")

def unique_filename(task, ext):
    return os.path.join(ROOT_LOG_DIR, f"{task}_{uuid.uuid4().hex[:8]}.{ext}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 1. Visit Amazon and save HTML
        task = "visit_amazon"
        url = "https://www.amazon.com"
        await page.goto(url)
        html = await page.content()
        html_file = unique_filename(task, "html")
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html)
        log_action(task, f"Visited {url} and saved HTML to {html_file}")

        # 2. Extract Stack Overflow mainbar content
        task = "extract_stackoverflow"
        url = "https://stackoverflow.com"
        await page.goto(url)
        await page.wait_for_selector("#mainbar")
        content = await page.inner_html("#mainbar")
        content_file = unique_filename(task, "html")
        with open(content_file, 'w', encoding='utf-8') as f:
            f.write(content)
        log_action(task, f"Extracted #mainbar from {url} and saved to {content_file}")

        # 3. Click GitHub Sign In button (with improved error handling)
        task = "click_github_signin"
        url = "https://github.com/login"
        await page.goto(url)
        try:
            await page.wait_for_selector("button[type=submit]", state="attached", timeout=15000)
            await page.click("button[type=submit]")
            log_action(task, f"Clicked Sign In button on {url}")
            screenshot_file = unique_filename(task, "png")
            await page.screenshot(path=screenshot_file)
            log_action(task, f"Saved screenshot after click to {screenshot_file}")
        except Exception as e:
            log_action(task, f"ERROR: Could not click Sign In button on {url}: {e}")

        # 4. Fill X.com search box
        task = "fillform_x_search"
        url = "https://x.com/explore"
        await page.goto(url)
        try:
            await page.wait_for_selector("input[data-testid=searchInput]", timeout=10000)
            await page.fill("input[data-testid=searchInput]", "AI")
            log_action(task, f"Filled search box on {url} with 'AI'")
            screenshot_file = unique_filename(task, "png")
            await page.screenshot(path=screenshot_file)
            log_action(task, f"Saved screenshot after fill to {screenshot_file}")
        except Exception as e:
            log_action(task, f"ERROR: Could not fill search box on {url}: {e}")

        # 5. Screenshot Samsung homepage
        task = "screenshot_samsung"
        url = "https://www.samsung.com"
        await page.goto(url)
        screenshot_file = unique_filename(task, "png")
        await page.screenshot(path=screenshot_file)
        log_action(task, f"Took screenshot of {url} and saved to {screenshot_file}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
