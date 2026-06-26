import json
import os
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

# ================= CONFIG (Aapka Original URL) =================
YT_PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLB6x_4-4tcYPRf5w1V8beLjL3NTdmEi1K"
HEADLESS = False  # True kar sakte hain agar screen nahi dekhni hai
OUTPUT_FILE = "stream.json"

# ================= MAIN SCRAPER =================
def run_scraper():
    stealth = Stealth()
    pw_cm = stealth.use_sync(sync_playwright())
    pw = pw_cm.__enter__()

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
        
        page.goto(YT_PLAYLIST_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)  # Initial load ka wait

        all_links = []      # Strict sequence maintain karega
        seen_links = set()  # Duplicates check karne ke liye
        last_height = 0

        print("🚀 Scraping started using Index-Filtering...")

        while True:
            # Puraane aur naye saare 'a' tags nikalna jisme watch?v= ho
            elements = page.query_selector_all('a[href*="/watch?v="]')
            
            for el in elements:
                href = el.get_attribute("href")
                # CRITICAL FILTER: Sirf wahi link uthana jisme '&index=' ho (yeh sirf main playlist list mein hota hai)
                if href and "/watch?v=" in href and "&index=" in href:
                    video_id = href.split("v=")[-1].split("&")[0]
                    
                    if len(video_id) == 11:
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        
                        if video_url not in seen_links:
                            all_links.append(video_url)
                            seen_links.add(video_url)

            # Smooth Scrolling taaki YouTube links ko DOM mein render kare
            page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
            page.wait_for_timeout(3000)  # YouTube ko render hone ke liye 3s ka solid time dena
            
            new_height = page.evaluate("document.documentElement.scrollHeight")
            if new_height == last_height:
                # Double check to confirm page end
                page.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)")
                page.wait_for_timeout(2000)
                if page.evaluate("document.documentElement.scrollHeight") == last_height:
                    break  
            last_height = new_height

        browser.close()

        # --- SAVE TO JSON ---
        total_videos = len(all_links)
        print(f"\n✅ Total number of links found: {total_videos}")

        json_data = [{"url": link} for link in all_links]

        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=4)
            
        print(f"Saare naye links {OUTPUT_FILE} mein 100% EXACT SEQUENCE mein save ho gaye hain!")

    except Exception as e:
        print(f"⚠️ Scraper Error: {e}")
    finally:
        pw_cm.__exit__(None, None, None)

if __name__ == "__main__":
    run_scraper()