import json
import os
import requests
from pathlib import Path
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth
from common.utils import load_config, load_locators
from common.config_loader import get, get_error_screenshot_path

# Load configuration
config = load_config()
locators = load_locators("youtube_locators.txt")

# Configuration from config.json
YT_PLAYLIST_URL = get("scraper.playlist_url")
MAX_VIDEOS = int(get("scraper.max_videos") or 0)
HEADLESS = get("scraper.headless")
OUTPUT_FILE = get("scraper.output_file")
BROWSER_ARGS = get("scraper.browser_args")
USER_AGENT = get("scraper.user_agent")
INITIAL_WAIT_MS = get("scraper.initial_wait_ms")
SCROLL_WAIT_MS = get("scraper.scroll_wait_ms")
DOUBLE_CHECK_WAIT_MS = get("scraper.double_check_wait_ms")

# Locators from youtube_locators.txt - primary + fallbacks for same target element
VIDEO_LINK_SELECTORS = locators.get("video_link_selector", ['a[href*="/watch?v="]'])

ERROR_SCREENSHOT_PATH = get_error_screenshot_path()


# Onlyfiles upload settings
ONLYFILES_UPLOAD_URL = get("onlyfiles.upload_url")
ONLYFILES_EXPIRE = get("onlyfiles.expire_seconds")


def capture_error_screenshot(page) -> str:
    """Capture full-page error screenshot."""
    try:
        page.screenshot(path=ERROR_SCREENSHOT_PATH, full_page=True)
        print(f"[OK] Error screenshot captured: {ERROR_SCREENSHOT_PATH}", flush=True)
        return ERROR_SCREENSHOT_PATH
    except Exception as e:
        print(f"[WARNING] Could not capture error screenshot: {e}", flush=True)
        return None


def upload_to_onlyfiles(screenshot_path: str) -> str:
    """Upload screenshot to onlyfiles.io."""
    if not screenshot_path:
        return None
    
    try:
        with open(screenshot_path, "rb") as file:
            response = requests.post(
                ONLYFILES_UPLOAD_URL, 
                files={"file": file}, 
                data={"expire": ONLYFILES_EXPIRE}
            )

        if response.status_code == 200:
            res_data = response.json()
            if res_data.get("status"):
                direct_url = res_data["data"]["file"]["url"]["full"]
                print(f"DIRECT LINK (Expires in 48 Hours): {direct_url}")
                return direct_url
            error = res_data.get("error", {})
            print(f"[WARNING] Upload Failed: {error.get('message', 'Unknown error')}")
        else:
            print(f"[WARNING] Upload Failed: {response.status_code}")
    except Exception as e:
        print(f"[WARNING] Could not upload screenshot: {e}", flush=True)
    return None


def get_video_elements(page):
    """
    Try each selector in order until one returns elements.
    Returns list of elements from the first successful selector.
    """
    for i, selector in enumerate(VIDEO_LINK_SELECTORS):
        elements = page.query_selector_all(selector)
        if elements:
            if i > 0:
                print(f"Primary selector failed, using fallback {i}: {selector}")
            return elements
    return []


def run_scraper():
    stealth = Stealth()
    pw_cm = stealth.use_sync(sync_playwright())
    pw = pw_cm.__enter__()

    if os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE, 'w').close()
        print(f"Previous JSON data ('{OUTPUT_FILE}') cleared.")

    try:
        browser = pw.chromium.launch(
            headless=HEADLESS,
            args=BROWSER_ARGS
        )

        context = browser.new_context(
            no_viewport=True,
            user_agent=USER_AGENT
        )
        
        page = context.new_page()
        print(f"Scanning Playlist: {YT_PLAYLIST_URL}")
        
        page.goto(YT_PLAYLIST_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(INITIAL_WAIT_MS)

        all_links = []
        seen_links = set()
        last_height = 0

        print("Scraping started using Index-Filtering...")
        if MAX_VIDEOS > 0:
            print(f"Maximum videos to scrape: {MAX_VIDEOS}")
        else:
            print("Maximum videos to scrape: Unlimited (max_videos is 0)")

        limit_reached = False
        while True:
            elements = get_video_elements(page)
            
            for el in elements:
                href = el.get_attribute("href")
                if href and "/watch?v=" in href and "&index=" in href:
                    video_id = href.split("v=")[-1].split("&")[0]
                    
                    if len(video_id) == 11:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        if video_url not in seen_links:
                            all_links.append(video_url)
                            seen_links.add(video_url)

                            if MAX_VIDEOS > 0 and len(all_links) >= MAX_VIDEOS:
                                limit_reached = True
                                break

            if limit_reached:
                break

            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(SCROLL_WAIT_MS)
            
            new_height = page.evaluate("document.documentElement.scrollHeight")
            if new_height == last_height:
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(DOUBLE_CHECK_WAIT_MS)
                if page.evaluate("document.documentElement.scrollHeight") == last_height:
                    break  
            last_height = new_height

        browser.close()

        total_videos = len(all_links)
        print(f"\nTotal number of links found: {total_videos}")

        if MAX_VIDEOS > 0 and total_videos >= MAX_VIDEOS:
            print(f"[SUCCESS] Configured maximum of {MAX_VIDEOS} videos reached. Scraping stopped successfully.")
        elif MAX_VIDEOS > 0:
            print(f"[SUCCESS] Playlist ended before the configured maximum. Found {total_videos} available videos (limit: {MAX_VIDEOS}). Continuing with successful save.")
        else:
            print(f"[SUCCESS] Playlist scan completed. Found {total_videos} videos.")

        json_data = [{"url": link} for link in all_links]

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
            
        print(f"All new links saved to {OUTPUT_FILE} in 100% EXACT SEQUENCE!")

    except Exception as e:
        print(f"Scraper Error: {e}")
        if 'page' in locals() and page:
            screenshot_path = capture_error_screenshot(page)
            upload_to_onlyfiles(screenshot_path)
    finally:
        pw_cm.__exit__(None, None, None)


if __name__ == "__main__":
    run_scraper()