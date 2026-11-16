import subprocess
import json
import os
import sys
import threading
import time
import yt_dlp
from dotenv import load_dotenv
from common.utils import load_config

load_dotenv()

# Load configuration
config = load_config()

# Configuration from config.json
JSON_FILE = config["json_file"]
LOCAL_VIDEO_FILE = config["local_video_file"]
KICK_RTMP_URL = os.getenv("KICK_RTMP_URL")
KICK_STREAM_KEY = os.getenv("KICK_STREAM_KEY")
TOTAL_TIMEOUT_SECONDS = config["total_timeout_seconds"]

DOWNLOAD_FORMAT = config["download"]["format"]
DOWNLOAD_USER_AGENT = config["download"]["user_agent"]
DOWNLOAD_EXTRACTOR_ARGS = config["download"]["extractor_args"]

STREAM_SLEEP_SECONDS = config["stream"]["sleep_between_download_and_stream"]
FFMPEG_CONFIG = config["stream"]["ffmpeg"]

ERROR_SCREENSHOT_PATH = config["error"]["screenshot_path"]


def get_next_target():
    if not os.path.exists(JSON_FILE):
        print(f"ERROR: {JSON_FILE} not found!", flush=True)
        sys.exit(1)
        
    with open(JSON_FILE, 'r') as f:
        data = json.load(f)
    
    target_index = None
    for i, item in enumerate(data):
        if not item.get("streamed", False):
            target_index = i
            break
            
    if target_index is None:
        print("All videos have already been streamed!", flush=True)
        sys.exit(0)
        
    return data, target_index


def update_json_status(data, index):
    data[index]["streamed"] = True
    data[index]["uploaded"] = True 
    with open(JSON_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    print("JSON updated successfully.", flush=True)


def start_pipeline():
    # 1. Check JSON and get target video first so timeout function has the index
    json_data, index = get_next_target()
    yt_url = json_data[index]["url"]

    # 2. GLOBAL TIMEOUT TIMER (DOWNLOADING + SLEEP + STREAMING)
    def force_exit_on_timeout():
        print(f"\nTimeout of {TOTAL_TIMEOUT_SECONDS} seconds reached!", flush=True)
        print("Updating JSON status due to timeout and exiting safely...", flush=True)
        
        # Update JSON status first on timeout
        try:
            update_json_status(json_data, index)
        except Exception as e:
            print(f"Timeout JSON update error: {e}", flush=True)

        # Cleanup: Delete local file in any case
        if os.path.exists(LOCAL_VIDEO_FILE):
            try:
                os.remove(LOCAL_VIDEO_FILE)
                print("Temporary local video cache cleared successfully before timeout exit.", flush=True)
            except Exception as e:
                print(f"Timeout cleanup error: {e}", flush=True)
                
        os._exit(0)

    # Start timer at the very beginning
    global_timer = threading.Timer(TOTAL_TIMEOUT_SECONDS, force_exit_on_timeout)
    global_timer.start()

    try:
        # 3. Start download to local disk (yt-dlp)
        print(f"Starting Download directly to GitHub Runner: {yt_url}", flush=True)
        ydl_opts = {
            'format': DOWNLOAD_FORMAT,
            'outtmpl': LOCAL_VIDEO_FILE,
            'user_agent': DOWNLOAD_USER_AGENT,
            'extractor_args': DOWNLOAD_EXTRACTOR_ARGS,
            'quiet': False,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            print("Download Complete! File saved locally on Runner.", flush=True)
        except Exception as e:
            print(f"Download Error: {e}", flush=True)
            global_timer.cancel()
            sys.exit(1)

        # 4. SLEEP BETWEEN DOWNLOAD AND STREAM
        print(f"Download completed. Waiting {STREAM_SLEEP_SECONDS} seconds before starting stream...", flush=True)
        time.sleep(STREAM_SLEEP_SECONDS)
        print("Sleep time completed. Starting stream now...", flush=True)

        # 5. Stream to Kick using Local File
        full_rtmp_path = f"{KICK_RTMP_URL}{KICK_STREAM_KEY}"
        print("Starting Stream to Kick from local file...", flush=True)
        
        command = [
            'ffmpeg', '-re',
            '-i', LOCAL_VIDEO_FILE,
            '-c:v', FFMPEG_CONFIG["video_codec"],
            '-pix_fmt', FFMPEG_CONFIG["pixel_format"],
            '-profile:v', FFMPEG_CONFIG["profile"],
            '-preset', FFMPEG_CONFIG["preset"],
            '-b:v', FFMPEG_CONFIG["video_bitrate"],
            '-maxrate', FFMPEG_CONFIG["max_rate"],
            '-bufsize', FFMPEG_CONFIG["buffer_size"],
            '-g', str(FFMPEG_CONFIG["gop_size"]),
            '-r', str(FFMPEG_CONFIG["frame_rate"]),
            '-s', FFMPEG_CONFIG["resolution"],
            '-c:a', FFMPEG_CONFIG["audio_codec"],
            '-b:a', FFMPEG_CONFIG["audio_bitrate"],
            '-ac', str(FFMPEG_CONFIG["audio_channels"]),
            '-f', FFMPEG_CONFIG["format"], full_rtmp_path
        ]
        
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        process.wait()
        
        if process.returncode == 0:
            update_json_status(json_data, index)
            print("Streaming completed successfully.", flush=True)
        else:
            print(f"Streaming ended with exit code {process.returncode}.", flush=True)
            sys.exit(1)
            
    except Exception as e:
        print(f"Pipeline Error: {e}", flush=True)
        
    finally:
        # If stream completes normally before 4 hours, cancel the timer
        global_timer.cancel()
        
        # Delete local file on normal exit
        if os.path.exists(LOCAL_VIDEO_FILE):
            os.remove(LOCAL_VIDEO_FILE)
            print("Temporary local video cache cleared from runner.", flush=True)


if __name__ == "__main__":
    start_pipeline()