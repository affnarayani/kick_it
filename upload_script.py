import os
import yt_dlp
from huggingface_hub import HfApi

# Configuration
YT_URL = "https://www.youtube.com/watch?v=InJ8BdFyQ1o"
REPO_ID = "ujjawal247/stream-repo"
FILE_NAME = "background_video.mp4"

def main():
    # 1. YouTube se download
    print(f"Downloading: {YT_URL}")
    ydl_opts = {
        'format': 'best',
        'outtmpl': FILE_NAME,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([YT_URL])

    # 2. Hugging Face par upload
    # Token hum environment variable se uthayenge
    token = os.getenv("HF_TOKEN")
    api = HfApi(token=token)
    
    print("Uploading to Hugging Face...")
    api.upload_file(
        path_or_fileobj=FILE_NAME,
        path_in_repo=FILE_NAME,
        repo_id=REPO_ID,
        repo_type="dataset"
    )
    
    print("Upload Successful!")
    print(f"Stream URL: https://huggingface.co/datasets/{REPO_ID}/resolve/main/{FILE_NAME}")

    # 3. Cleanup
    if os.path.exists(FILE_NAME):
        os.remove(FILE_NAME)

if __name__ == "__main__":
    main()