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
TOTAL_TIMEOUT_SECONDS = 120  # 4 Ghante (Downloading + Streaming mila kar)
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
    data[index]["uploaded"] = True 
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print("✅ JSON updated successfully.")

def start_pipeline():
    # --- GLOBAL TIMEOUT TIMER (DOWNLOADING + STREAMING) ---
    def force_exit_on_timeout():
        print(f"\n🚨 {TOTAL_TIMEOUT_SECONDS} seconds (Downloading + Streaming) pure ho gaye!")
        print("Script ko force-exit kiya ja raha hai...")
        
        # Cleanup: Exit hone se pehle local file har haal me delete karein
        if os.path.exists(LOCAL_VIDEO_FILE):
            try:
                os.remove(LOCAL_VIDEO_FILE)
                print("Temporary local video cache cleared successfully before timeout exit.")
            except Exception as e:
                print(f"Timeout cleanup error: {e}")
                
        # Main aur sub-processes ko immediate terminate karne ke liye os._exit use kiya hai
        os._exit(1)

    # Timer ko pipeline ke bilkul start mein shuru kar rahe hain
    global_timer = threading.Timer(TOTAL_TIMEOUT_SECONDS, force_exit_on_timeout)
    global_timer.start()
    # ------------------------------------------------------

    try:
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

        # 3. Stream to Kick using Local File
        full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
        print(f"Starting Stream to Kick from local file...")
        
        command = [
            'ffmpeg', '-re',
            '-i', LOCAL_VIDEO_FILE,
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
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE)

        # Process khatam hone ka wait karein (FFmpeg normal chalne dein)
        process.wait()
        
        if process.returncode == 0:
            update_json_status(json_data, index)
            print("Streaming successfully khatam hui.")
        else:
            print(f"Streaming exit code {process.returncode} ke saath band hui.")
            
    except Exception as e:
        print(f"Pipeline Error: {e}")
        
    finally:
        # Agar stream ya download 4 ghante se pehle normal poora ho jaye, toh timer cancel karein
        global_timer.cancel()
        
        # Cleanup: Normal exit par local file delete karna
        if os.path.exists(LOCAL_VIDEO_FILE):
            os.remove(LOCAL_VIDEO_FILE)
            print("Temporary local video cache cleared from runner.")

if __name__ == "__main__":
    start_pipeline()