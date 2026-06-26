import subprocess
import json
import os
import sys
import threading
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
JSON_FILE = "stream.json"
LOCAL_VIDEO_FILE = "local_cache_video.mp4"
KICK_RTMP_URL = os.getenv("KICK_RTMP_URL")
KICK_STREAM_KEY = os.getenv("KICK_STREAM_KEY")
# ---------------------

def get_next_target():
    if not os.path.exists(JSON_FILE):
        print(f"ERROR: {JSON_FILE} nahi mili!")
        sys.exit(1)
        
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    target_index = None
    for i, item in enumerate(data):
        # Ab hum 'uploaded' flag par nahi, seedhe 'streamed' flag par depend hain
        if not item.get("streamed", False):
            target_index = i
            break
            
    if target_index is None:
        print("Sabhi videos pehle se hi stream ho chuke hain!")
        sys.exit(0)
        
    return data, target_index

def update_json_status(data, index):
    data[index]["streamed"] = True
    # Ab 'uploaded' flag ki zaroorat nahi hai, fir bhi compatibility ke liye True rakh sakte hain
    data[index]["uploaded"] = True 
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print("✅ JSON updated successfully.")

def start_pipeline():
    # 1. JSON check aur target video lena
    json_data, index = get_next_target()
    yt_url = json_data[index]["url"]
    
    # 2. Local Disk par download shuru (yt-dlp)
    print(f"Starting Download directly to GitHub Runner: {yt_url}")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': LOCAL_VIDEO_FILE,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': 'web',
                'skip': ['dash', 'hls']
            }
        },
        'quiet': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        print("✅ Download Complete! File saved locally on Runner.")
    except Exception as e:
        print(f"Download Error: {e}")
        sys.exit(1)

    # 3. Stream to Kick using Local File (No internet buffering hassle)
    full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
    print(f"Starting Stream to Kick from local file...")
    
    command = [
        'ffmpeg', '-re',
        '-i', LOCAL_VIDEO_FILE,  # <--- Internet URL ki jagah 100% LOCAL FILE!
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'main',
        '-preset', 'veryfast',
        '-b:v', '8000k',
        '-maxrate', '8000k',
        '-minrate', '8000k',
        '-bufsize', '16000k', # Good buffer for encoder stability
        '-g', '120',
        '-r', '60',
        '-s', '1920x1080',
        '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
        '-f', 'flv', full_rtmp_path
    ]
    
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE)

        # 4 ghante (14400 seconds) ka timer setup
        def stop_process():
            if process.poll() is None:
                print("\n4 ghante pure ho gaye, FFmpeg ko gracefully band kar rahe hain...")
                try:
                    process.stdin.write(b'q')
                    process.stdin.flush()
                except BrokenPipeError:
                    pass

        timer = threading.Timer(60, stop_process)
        timer.start()

        # Process khatam hone ka wait karein
        process.wait()
        timer.cancel()
        
        if process.returncode == 0:
            update_json_status(json_data, index)
            print("Streaming successfully khatam hui.")
        else:
            print(f"Streaming exit code {process.returncode} ke saath band hui.")
            
    except Exception as e:
        print(f"Streaming Error: {e}")
        
    finally:
        # Cleanup: Har haal me local 6GB ki file runner se delete karo taaki space clear rahe
        if os.path.exists(LOCAL_VIDEO_FILE):
            os.remove(LOCAL_VIDEO_FILE)
            print("Temporary local video cache cleared from runner.")

if __name__ == "__main__":
    start_pipeline()