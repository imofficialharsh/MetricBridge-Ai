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

            # Check if Streamlit Cloud returned a 404 or access denied page
            if "errors/not_found" in page.url or "not_found" in page.url:
                print(f"❌ Error: The URL '{url}' does not exist on Streamlit Community Cloud.")
                print(f"🔗 Streamlit Cloud redirected to: {page.url}")
                print(f"👉 Please check the exact URL of your deployed app in your browser!")
                print(f"👉 Then update the STREAMLIT_APP_URL variable in GitHub Settings -> Secrets and variables -> Actions -> Variables.")
                try:
                    page.screenshot(path="keep_alive_timeout.png", full_page=True)
                except Exception:
                    pass
                sys.exit(1)

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
                page.wait_for_timeout(10000)

            # 2. Check if app is active and rendered (checking main frame and iframes)
            print("🔍 Verifying active Streamlit application state...")
            app_loaded = False

            # Wait up to 60s for app container in main frame or any frame
            start_wait = time.time()
            while time.time() - start_wait < 60:
                # Check top frame
                try:
                    if page.locator('[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp').count() > 0:
                        app_loaded = True
                        break
                except Exception:
                    pass

                # Check iframes (Streamlit Cloud often nests app in an iframe)
                for frame in page.frames:
                    try:
                        if frame.locator('[data-testid="stAppViewContainer"], header[data-testid="stHeader"], .stApp').count() > 0:
                            app_loaded = True
                            print(f"✅ App container detected inside iframe!")
                            break
                    except Exception:
                        pass

                if app_loaded:
                    break
                page.wait_for_timeout(3000)

            if app_loaded:
                print("✅ App is active, responsive, and fully hydrated!")
            else:
                # If still not found, check if it's loading
                loading_text = page.locator('text="Cooking up your app", text="Your app is loading"').first
                if loading_text.is_visible():
                    print("⏳ App is currently spinning up on Streamlit Cloud (in progress).")
                else:
                    print(f"⚠️ Warning: Specific Streamlit container was not detected within 60s.")
                    print(f"📄 Page Title: {page.title()}")
                    print(f"🔗 Page URL: {page.url}")
                    page.screenshot(path="keep_alive_timeout.png", full_page=True)
                    sys.exit(1)


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
