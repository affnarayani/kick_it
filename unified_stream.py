import subprocess
import json
import os
import sys
import threading
import time
import yt_dlp
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
JSON_FILE = "stream.json"
LOCAL_VIDEO_FILE = "local_cache_video.mp4"
KICK_RTMP_URL = os.getenv("KICK_RTMP_URL")
KICK_STREAM_KEY = os.getenv("KICK_STREAM_KEY")
TOTAL_TIMEOUT_SECONDS = 14400  # 4 Ghante (Downloading + Sleep + Streaming mila kar)
# ---------------------

def get_next_target():
    if not os.path.exists(JSON_FILE):
        print(f"ERROR: {JSON_FILE} nahi mili!", flush=True)
        sys.exit(1)
        
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    target_index = None
    for i, item in enumerate(data):
        if not item.get("streamed", False):
            target_index = i
            break
            
    if target_index is None:
        print("Sabhi videos pehle se hi stream ho chuke hain!", flush=True)
        sys.exit(0)
        
    return data, target_index

def update_json_status(data, index):
    data[index]["streamed"] = True
    data[index]["uploaded"] = True 
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print("✅ JSON updated successfully.", flush=True)

def start_pipeline():
    # 1. JSON check aur target video pehle le rahe hain taaki timeout function ko index mil sake
    json_data, index = get_next_target()
    yt_url = json_data[index]["url"]

    # 2. GLOBAL TIMEOUT TIMER (DOWNLOADING + SLEEP + STREAMING)
    def force_exit_on_timeout():
        print(f"\n🚨 {TOTAL_TIMEOUT_SECONDS} seconds pure ho gaye!", flush=True)
        print("Timeout ke wajah se JSON update kiya ja raha hai aur script safely exit ho rahi hai...", flush=True)
        
        # Timeout par sabse pehle JSON status update karein
        try:
            update_json_status(json_data, index)
        except Exception as e:
            print(f"Timeout JSON update error: {e}", flush=True)

        # Cleanup: Local file har haal me delete karein
        if os.path.exists(LOCAL_VIDEO_FILE):
            try:
                os.remove(LOCAL_VIDEO_FILE)
                print("Temporary local video cache cleared successfully before timeout exit.", flush=True)
            except Exception as e:
                print(f"Timeout cleanup error: {e}", flush=True)
                
        os._exit(0)

    # Timer ko bilkul shuruwat mein start kar rahe hain
    global_timer = threading.Timer(TOTAL_TIMEOUT_SECONDS, force_exit_on_timeout)
    global_timer.start()

    try:
        # 3. Local Disk par download shuru (yt-dlp)
        print(f"Starting Download directly to GitHub Runner: {yt_url}", flush=True)
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
            print("✅ Download Complete! File saved locally on Runner.", flush=True)
        except Exception as e:
            print(f"Download Error: {e}", flush=True)
            global_timer.cancel()
            sys.exit(1)

        # 4. 180 SECONDS SLEEP BETWEEN DOWNLOAD AND STREAM
        print("⏳ Download poora ho gaya hai. Streaming shuru karne se pehle 300 seconds ka wait kar rahe hain...", flush=True)
        time.sleep(300)
        print("✅ Sleep time poora hua. Ab streaming shuru ho rahi hai...", flush=True)

        # 5. Stream to Kick using Local File
        full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
        print(f"Starting Stream to Kick from local file...", flush=True)
        
        command = [
        'ffmpeg', '-re',
        '-i', LOCAL_VIDEO_FILE,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'main',
        '-preset', 'veryfast',
        '-b:v', '6000k',       # 8000k se kam kiya
        '-maxrate', '7000k',   # Max cap lagaya
        '-bufsize', '14000k',
        '-g', '120',
        '-r', '60',
        '-s', '1920x1080',
        '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
        '-f', 'flv', full_rtmp_path
    ]
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        process.wait()
        
        if process.returncode == 0:
            update_json_status(json_data, index)
            print("Streaming successfully khatam hui.", flush=True)
        else:
            print(f"Streaming exit code {process.returncode} ke saath band hui.", flush=True)
            sys.exit(1)
            
    except Exception as e:
        print(f"Pipeline Error: {e}", flush=True)
        
    finally:
        # Agar stream 4 ghante se pehle normal poori ho jaye, toh timer ko cancel karein
        global_timer.cancel()
        
        # Normal exit par local file delete karna
        if os.path.exists(LOCAL_VIDEO_FILE):
            os.remove(LOCAL_VIDEO_FILE)
            print("Temporary local video cache cleared from runner.", flush=True)

if __name__ == "__main__":
    start_pipeline()