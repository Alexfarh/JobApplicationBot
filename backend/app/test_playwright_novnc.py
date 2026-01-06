import asyncio
from app.services.playwright_bot import launch_remote_browser

async def test_launch():
    browser, ws_endpoint = await launch_remote_browser()
    print(f"Browser launched. WebSocket endpoint: {ws_endpoint}")
    # Open a page to a neutral site for visual confirmation
    page = await browser.new_page()
    await page.goto("https://example.com")
    print("Navigated to example.com. Press Ctrl+C to exit and close browser.")
    try:
        while True:
            await asyncio.sleep(10)
    except KeyboardInterrupt:
        print("Closing browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_launch())
