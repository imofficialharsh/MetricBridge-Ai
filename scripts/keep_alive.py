"""
scripts/keep_alive.py
Playwright-based health check and keep-alive probe for Streamlit Community Cloud.
Checks if the app has gone to sleep, clicks the wake-up button if present,
and verifies that the app is active and fully rendered.
"""

import os
import sys
import time
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

STREAMLIT_APP_URL = os.getenv("STREAMLIT_APP_URL", "https://metric-bridge.streamlit.app/").strip()


def probe_streamlit_app(url: str):
    print(f"==================================================")
    print(f"🚀 Starting Streamlit Keep-Alive Probe")
    print(f"🌐 Target URL: {url}")
    print(f"⏰ Timestamp : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"==================================================")

    if not url or not url.startswith("http"):
        print(f"❌ Error: Invalid URL specified: '{url}'")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()

        try:
            print(f"⏳ Navigating to {url}...")
            response = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status_code = response.status if response else "unknown"
            print(f"📡 Initial response status: {status_code}")

            # Wait a few seconds for Streamlit hydration or sleep modal
            page.wait_for_timeout(5000)

            # Check if the app has gone to sleep
            # Streamlit displays: "Yes, get this app back up!"
            wake_up_selectors = [
                'button:has-text("Yes, get this app back up!")',
                'button:has-text("Yes, get this app back up")',
                'button:has-text("get this app back up")',
                'button:has-text("Wake up")',
                'button:has-text("wake up")',
            ]

            wake_button = None
            for sel in wake_up_selectors:
                btn = page.locator(sel).first
                if btn.is_visible():
                    wake_button = btn
                    print(f"💤 Detected sleeping app with button: '{sel}'")
                    break

            if wake_button:
                print("⚡ Clicking wake-up button...")
                wake_button.click()
                print("⏳ Waiting for app to wake up and hydrate (up to 120s)...")
                page.wait_for_selector(
                    '[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp',
                    state="visible",
                    timeout=120000,
                )
                print("✅ App successfully awakened from sleep state!")
            else:
                # App was not asleep, check if it's already rendered
                print("🔍 Checking if app is already active and rendered...")
                page.wait_for_selector(
                    '[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp',
                    state="visible",
                    timeout=45000,
                )
                print("✅ App is already active, responsive, and hydrated!")

            title = page.title()
            print(f"📄 Page Title: {title}")
            print("🎉 Keep-alive probe completed successfully!")

        except PlaywrightTimeoutError as te:
            print(f"⚠️ Timeout during probe: {te}")
            # Capture error screenshot for debugging in GitHub Actions if run locally
            try:
                page.screenshot(path="keep_alive_timeout.png")
                print("📸 Saved timeout screenshot to keep_alive_timeout.png")
            except Exception:
                pass
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error during probe: {e}")
            sys.exit(1)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    probe_streamlit_app(STREAMLIT_APP_URL)
