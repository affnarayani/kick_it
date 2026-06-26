import json
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ================= CONFIG (Aapka Original URL) =================
YT_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLB6x_4-4tcYPRf5w1V8beLjL3NTdmEi1K"
HEADLESS = True
OUTPUT_FILE = "stream.json"

# ================= MAIN SCRAPER =================
def run_scraper():
    stealth = Stealth()
    pw_cm = stealth.use_sync(sync_playwright())
    pw = pw_cm.__enter__()

    # Run ke start mein hi json file ko clear karna
    if os.path.exists(OUTPUT_FILE):
        open(OUTPUT_FILE, 'w').close()
        print(f"🧹 Purana JSON data ('{OUTPUT_FILE}') clear kar diya gaya hai.")

    try:
        browser = pw.chromium.launch(
            headless=HEADLESS,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )

        context = browser.new_context(
            no_viewport=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        print(f"🔍 Scanning Playlist: {YT_PLAYLIST_URL}")
        print("Naya playlist scan ho raha hai, please wait...")
        page.goto(YT_PLAYLIST_URL, wait_until="networkidle")

        all_links = set()
        last_height = 0

        # --- SCROLLING & LINK COLLECTION ---
        while True:
            # Playlist ke andar video links find karne ke liye selector badla hai (/watch?v=)
            elements = page.query_selector_all('a[href*="/watch?v="]')
            for el in elements:
                href = el.get_attribute("href")
                if href and "/watch?v=" in href:
                    # Video ID extract karna
                    video_id = href.split("v=")[-1].split("&")[0]
                    if len(video_id) == 11:
                        all_links.add(f"https://www.youtube.com/watch?v={video_id}")

            # Infinite Scroll: Page ko neeche scroll karna taaki 100 se zyada videos load hon
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(2500)  # Content load hone ka wait
            
            new_height = page.evaluate("document.documentElement.scrollHeight")
            if new_height == last_height:
                break  # Agar scroll height nahi badhi, matlab saare videos load ho gaye
            last_height = new_height

        browser.close()

        # --- SAVE TO JSON ---
        video_list = list(all_links)
        total_videos = len(video_list)
        print(f"\n✅ Total number of links found: {total_videos}")

        # Data format aapke original code jaisa [{"url": "..."}]
        json_data = [{"url": link} for link in video_list]

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
            
        print(f"Saare naye links {OUTPUT_FILE} mein save ho gaye hain!")

    except Exception as e:
        print(f"⚠️ Scraper Error: {e}")
    finally:
        pw_cm.__exit__(None, None, None)

if __name__ == "__main__":
    run_scraper()