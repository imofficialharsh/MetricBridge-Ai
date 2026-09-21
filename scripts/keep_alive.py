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

STREAMLIT_APP_URL = os.getenv("STREAMLIT_APP_URL", "https://metricbridge-ai.streamlit.app/").strip()


def probe_streamlit_app(url: str):
    print("==================================================")
    print("🚀 Starting Streamlit Keep-Alive Probe")
    print(f"🌐 Target URL: {url}")
    print(f"⏰ Timestamp : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print("==================================================")

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
            print(f"🔗 Current Page URL: {page.url}")

            # Wait 6 seconds for initial Streamlit hydration / sleep modal
            page.wait_for_timeout(6000)
            print(f"📄 Page Title: {page.title()}")

            # 1. Search for Wake-Up Button (both top frame & iframes)
            wake_up_patterns = [
                "Yes, get this app back up!",
                "Yes, get this app back up",
                "get this app back up",
                "Wake up",
                "wake up",
            ]

            wake_button = None
            # Check main page
            for pat in wake_up_patterns:
                btn = page.locator(f'button:has-text("{pat}")').first
                try:
                    if btn.is_visible():
                        wake_button = btn
                        print(f"💤 Detected sleeping app with button pattern: '{pat}'")
                        break
                except Exception:
                    pass

            # Check inside child frames/iframes if not found in main frame
            if not wake_button:
                for frame in page.frames:
                    for pat in wake_up_patterns:
                        try:
                            f_btn = frame.locator(f'button:has-text("{pat}")').first
                            if f_btn.is_visible():
                                wake_button = f_btn
                                print(f"💤 Detected sleeping app inside iframe with pattern: '{pat}'")
                                break
                        except Exception:
                            pass
                    if wake_button:
                        break

            if wake_button:
                print("⚡ Clicking wake-up button...")
                wake_button.click()
                print("⏳ Waiting for app to awaken and hydrate (up to 120s)...")
                page.wait_for_selector(
                    '[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp',
                    state="visible",
                    timeout=120000,
                )
                print("✅ App successfully awakened from sleep state!")
            else:
                # 2. Check if app is currently spinning up / loading
                loading_patterns = ["Cooking up your app", "Your app is loading", "Spinning up", "Connecting"]
                is_loading = False
                for lp in loading_patterns:
                    try:
                        if page.locator(f'text="{lp}"').count() > 0:
                            is_loading = True
                            print(f"⏳ Streamlit Cloud is preparing app ('{lp}'). Waiting for completion...")
                            break
                    except Exception:
                        pass

                timeout_duration = 90000 if is_loading else 45000
                print(f"🔍 Checking if app is active and rendered (timeout: {timeout_duration//1000}s)...")
                
                # Check for active Streamlit container
                page.wait_for_selector(
                    '[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp',
                    state="visible",
                    timeout=timeout_duration,
                )
                print("✅ App is active, responsive, and fully hydrated!")

            print(f"📄 Final Page Title: {page.title()}")
            print("🎉 Keep-alive probe completed successfully!")

        except PlaywrightTimeoutError as te:
            print(f"⚠️ Playwright timeout during probe: {te}")
            try:
                page.screenshot(path="keep_alive_timeout.png", full_page=True)
                print("📸 Saved timeout screenshot to keep_alive_timeout.png")
            except Exception as se:
                print(f"Could not take screenshot: {se}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Unexpected error during probe: {e}")
            try:
                page.screenshot(path="keep_alive_timeout.png", full_page=True)
                print("📸 Saved error screenshot to keep_alive_timeout.png")
            except Exception:
                pass
            sys.exit(1)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    probe_streamlit_app(STREAMLIT_APP_URL)
