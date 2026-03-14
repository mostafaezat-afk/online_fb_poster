import sys
from playwright.sync_api import sync_playwright

def trigger():
    url = sys.argv[1]
    print(f"Triggering: {url}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            # Navigate and wait for the JS challenge to settle
            page.goto(url, wait_until="networkidle", timeout=60000)
            print("Page loaded. Response content:")
            print(page.locator("body").inner_text())
        except Exception as e:
            print(f"Error during trigger: {e}")
            sys.exit(1)
        finally:
            browser.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python trigger_scraper.py <URL>")
        sys.exit(1)
    trigger()
