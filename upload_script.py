import os
import yt_dlp
from huggingface_hub import HfApi
from dotenv import load_dotenv

# .env file se token load karein
load_dotenv()

# --- CONFIGURATION ---
YT_URL = "https://www.youtube.com/watch?v=4P_miyGJb5A"
REPO_ID = "ujjawal247/stream-repo"
FILE_NAME = "background_video.mp4"
HF_TOKEN = os.getenv("HF_TOKEN")

def download_and_upload():
    # Token check
    if not HF_TOKEN:
        print("ERROR: HF_TOKEN not found in environment variables!")
        return

    # 1. Download with Web Client Spoofing
    print(f"Downloading from: {YT_URL}")
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
            ydl.download([YT_URL])
    except Exception as e:
        print(f"Download Error: {e}")
        return

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
            commit_message="Automated video update via script"
        )
        print("✅ Upload & Overwrite Successful!")
        print(f"Stream URL: https://huggingface.co/datasets/{REPO_ID}/resolve/main/{FILE_NAME}")
        
    except Exception as e:
        print(f"Upload Error: {e}")

    # 3. Cleanup
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)
        print("Temporary file deleted.")

if __name__ == "__main__":
    download_and_upload()