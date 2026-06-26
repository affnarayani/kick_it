import os
import json
import sys
import yt_dlp
from huggingface_hub import HfApi
from dotenv import load_dotenv

# .env file se token load karein
load_dotenv()

# --- CONFIGURATION ---
JSON_FILE = "stream.json"
REPO_ID = "ujjawal247/stream-repo"
FILE_NAME = "background_video.mp4"
HF_TOKEN = os.getenv("HF_TOKEN")

def load_and_process_json():
    # Check karein agar json file exist karti hai
    if not os.path.exists(JSON_FILE):
        print(f"ERROR: {JSON_FILE} nahi mili!")
        sys.exit(1)
        
    with open(JSON_FILE, 'r') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"ERROR: {JSON_FILE} valid JSON nahi hai!")
            sys.exit(1)
            
    if not data or not isinstance(data, list):
        print("ERROR: JSON list khali hai ya galat format mein hai!")
        sys.exit(1)

    target_index = None
    
    # 1. Agla video dhoondhein jo upload nahi hua hai
    for i, item in enumerate(data):
        if not item.get("uploaded", False):
            target_index = i
            break
            
    if target_index is None:
        print("Sabhi videos pehle se hi uploaded hain!")
        sys.exit(0) # Saare done hain toh exit 0 kar sakte hain ya fir close
        
    # 2. Condition Check: Agar yeh pehla video nahi hai, toh pichle video ka 'streamed' True hona chahiye
    if target_index > 0:
        previous_item = data[target_index - 1]
        if not previous_item.get("streamed", False):
            print(f"ERROR: Pichla video ({previous_item.get('url')}) abhi tak stream nahi hua hai! Script terminate ho rahi hai.")
            sys.exit(1)
            
    # Agar conditions pass ho gayi hain toh target URL aur data return karein
    return data, target_index

def save_json_data(data):
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"✅ {JSON_FILE} successfully update ho gayi hai.")

def download_and_upload():
    # Token check
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN not found in environment variables!")
        sys.exit(1)

    # JSON process karein aur current target index nikaalein
    json_data, index = load_and_process_json()
    current_item = json_data[index]
    yt_url = current_item["url"]

    # 1. Download with Web Client Spoofing
    print(f"Downloading from: {yt_url}")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': FILE_NAME,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': 'web',
                'skip': ['dash', 'hls']
            }
        },
        'quiet': False,
        'no_warnings': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
    except Exception as e:
        print(f"Download Error: {e}")
        sys.exit(1)

    # 2. Upload to Hugging Face
    print("Authenticating and Uploading to Hugging Face...")
    try:
        api = HfApi(token=HF_TOKEN)
        
        # Upload & Overwrite
        api.upload_file(
            path_or_fileobj=FILE_NAME,
            path_in_repo=FILE_NAME,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"Automated video update via script - Index {index}"
        )
        print("✅ Upload & Overwrite Successful!")
        print(f"Stream URL: https://huggingface.co/datasets/{REPO_ID}/resolve/main/{FILE_NAME}")
        
        # Success hone ke baad JSON data ko update karein
        json_data[index]["uploaded"] = True
        json_data[index]["streamed"] = False
        save_json_data(json_data)
        
    except Exception as e:
        print(f"Upload Error: {e}")
        # Agar upload fail hua toh file delete karne ke baad exit 1 karein
        if os.path.exists(FILE_NAME):
            os.remove(FILE_NAME)
        sys.exit(1)

    # 3. Cleanup
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)
        print("Temporary file deleted.")

if __name__ == "__main__":
    download_and_upload()