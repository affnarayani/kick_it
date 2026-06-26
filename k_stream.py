import subprocess
import json
import os
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
    if index is None: return

    video_url = f"{HF_BASE_URL}{filename}"
    full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
    
    # 1080p 60FPS @ 8000k CBR configuration
    command = [
        'ffmpeg', '-re',
        '-i', video_url,
        # Video Encoding Settings
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-profile:v', 'main',     # Kick/IVS ke liye stable
        '-preset', 'veryfast',   # Server load balance ke liye
        '-b:v', '8000k',         # Recommended Bitrate
        '-maxrate', '8000k',     # CBR enforce karne ke liye
        '-minrate', '8000k',     # CBR enforce karne ke liye
        '-bufsize', '8000k',     # Buffer size
        '-g', '120',             # 2 seconds keyframe interval (60fps * 2s = 120)
        '-r', '60',              # Framerate
        '-s', '1920x1080',       # Resolution
        # Audio Encoding
        '-c:a', 'aac', '-b:a', '160k', '-ac', '2',
        '-f', 'flv', full_rtmp_path
    ]
    
    try:
        process = subprocess.run(command)
        if process.returncode == 0:
            mark_as_streamed(data, index)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    stream_video()