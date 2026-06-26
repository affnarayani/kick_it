import subprocess
import json
import os
import threading
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
JSON_FILE = "stream.json"
HF_BASE_URL = "https://huggingface.co/datasets/ujjawal247/stream-repo/resolve/main/"
KICK_RTMP_URL = os.getenv("KICK_RTMP_URL")
KICK_STREAM_KEY = os.getenv("KICK_STREAM_KEY")
# ---------------------

def get_next_stream_target():
    if not os.path.exists(JSON_FILE):
        return None, None, None
        
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    for i, item in enumerate(data):
        if item.get("uploaded", False) and not item.get("streamed", False):
            filename = item.get("filename", "background_video.mp4")
            return data, i, filename
    return None, None, None

def mark_as_streamed(data, index):
    data[index]["streamed"] = True
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def stream_video():
    data, index, filename = get_next_stream_target()
    if index is None: 
        print("Koi video stream ke liye nahi mila.")
        return

    video_url = f"{HF_BASE_URL}{filename}"
    full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
    
    command = [
        'ffmpeg', '-re',
        '-reconnect', '1',
        '-reconnect_at_eof', '1',      # End of file error par bhi reconnect karega
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '2',     # Jaldi-jaldi retry karega taaki 21s ka lag na aaye
        '-multiple_requests', '1',       # HTTP connection ko alive rakhega
        '-rw_timeout', '10000000',
        '-i', video_url,
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'main',
        '-preset', 'veryfast',
        '-b:v', '8000k',
        '-maxrate', '8000k',
        '-minrate', '8000k',
        '-bufsize', '8000k',
        '-g', '120',
        '-r', '60',
        '-s', '1920x1080',
        '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
        '-f', 'flv', full_rtmp_path
    ]
    
    # Process start karein
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

    timer = threading.Timer(14400, stop_process)
    timer.start()

    # Process ke khatam hone ka wait karein
    process.wait()
    timer.cancel()
    
    # Agar FFmpeg successfully band hua
    if process.returncode == 0:
        mark_as_streamed(data, index)
        print("Streaming successfully khatam hui aur status update ho gaya.")
    else:
        print(f"Streaming exit code {process.returncode} ke saath band hui.")

if __name__ == "__main__":
    stream_video()