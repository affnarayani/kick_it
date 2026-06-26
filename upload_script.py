import os
import yt_dlp
from huggingface_hub import HfApi

# --- CONFIGURATION ---
# YouTube ka video link (Invidious proxy link use kar rahe hain taaki block na ho)
YT_URL = "https://yewtu.be/watch?v=InJ8BdFyQ1o" 
REPO_ID = "ujjawal247/stream-repo"
FILE_NAME = "background_video.mp4"
HF_TOKEN = os.getenv("HF_TOKEN")

def download_and_upload():
    # 1. YouTube se download (Spoofed Browser Headers ke sath)
    print(f"Downloading from: {YT_URL}")
    ydl_opts = {
        'format': 'best',
        'outtmpl': FILE_NAME,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'quiet': False,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([YT_URL])
    except Exception as e:
        print(f"Download Error: {e}")
        return

    # 2. Hugging Face par upload (Overwrites automatically)
    print("Uploading to Hugging Face...")
    api = HfApi(token=HF_TOKEN)
    
    # HfApi.upload_file automatically file ko check karta hai aur agar 
    # path_in_repo same hai, toh woh existing file ko overwrite (update) kar deta hai.
    api.upload_file(
        path_or_fileobj=FILE_NAME,
        path_in_repo=FILE_NAME,
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="Automated video update"
    )
    
    print("✅ Upload Success! Streaming link ready.")

    # 3. Cleanup
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)
        print("Temporary file cleaned up.")

if __name__ == "__main__":
    download_and_upload()