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
        if not item.get("streamed", False):
            target_index = i
            break
            
    if target_index is None:
        print("Sabhi videos pehle se hi stream ho chuke hain!")
        sys.exit(0)
        
    return data, target_index

def update_json_status(data, index):
    data[index]["streamed"] = True
    data[index]["uploaded"] = True  # Backwards compatibility ke liye
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print("✅ JSON updated successfully.")

def start_pipeline():
    json_data, index = get_next_target()
    yt_url = json_data[index]["url"]
    
    # --- ARIA2C HIGH SPEED ENGINE OPTIONS ---
    print(f"Starting Multi-threaded Download directly to GitHub Runner: {yt_url}")
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': LOCAL_VIDEO_FILE,
        
        # Aria2c configuration with safer connections
        'external_downloader': 'aria2c',
        'external_downloader_args': [
            '--min-split-size=4M',
            '--max-connection-per-server=4', 
            '--split=4',
            '--no-netrc=true',
            '--check-certificate=false'
        ],
        
        # YouTube Extraction with proper list format for ios client
        'extractor_args': {
            'youtube': {
                'player_client': ['ios'],  # <--- Isko list bracket [] me kar diya hai
                'skip': ['dash', 'hls']
            }
        },
        'quiet': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        print("✅ High-Speed Download Complete!")
    except Exception as e:
        print(f"Download Error: {e}")
        sys.exit(1)

    # --- KICK STREAM ENGINE VIA LOCAL STORAGE ---
    full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
    print(f"Starting Stream to Kick from 100% stable local cache...")
    
    command = [
        'ffmpeg', '-re',
        '-i', LOCAL_VIDEO_FILE,  # Direct local block read (No online lag)
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'main',
        '-preset', 'veryfast',
        '-b:v', '8000k',
        '-maxrate', '8000k',
        '-minrate', '8000k',
        '-bufsize', '16000k',
        '-g', '120',
        '-r', '60',
        '-s', '1920x1080',
        '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
        '-f', 'flv', full_rtmp_path
    ]
    
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE)

        # 4 Hours (14400 seconds) streaming countdown timer
        def stop_process():
            if process.poll() is None:
                print("\n[TIMER] 4 Hours completed! Gracefully closing FFmpeg...")
                try:
                    process.stdin.write(b'q')
                    process.stdin.flush()
                except BrokenPipeError:
                    pass

        timer = threading.Timer(60, stop_process)
        timer.start()

        # Wait until FFmpeg completes its operation
        process.wait()
        timer.cancel()
        
        if process.returncode == 0:
            update_json_status(json_data, index)
            print("Streaming successfully finished.")
        else:
            print(f"Streaming exited with code: {process.returncode}")
            
    except Exception as e:
        print(f"Streaming Error: {e}")
        
    finally:
        # Secure cleanup: Runner space release policy
        if os.path.exists(LOCAL_VIDEO_FILE):
            os.remove(LOCAL_VIDEO_FILE)
            print("Temporary local cached file successfully cleaned up from runner.")

if __name__ == "__main__":
    start_pipeline()