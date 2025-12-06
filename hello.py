import ytmusicapi
import yt_dlp
import sys
import os
import subprocess
import tempfile
import time

# --- कॉन्फ़िगरेशन ---
SEARCH_QUERY = "Pahale to kabhi kabhi gam tha"
# एक अस्थायी फ़ाइल का पथ प्राप्त करें (.m4a Windows 11 Media Player के लिए अच्छा है)
temp_dir = tempfile.gettempdir()
temp_filepath = os.path.join(temp_dir, 'temp_audio.m4a') 
# --------------------

# 1. YTMusic शुरू करें और गाना खोजें
ytmusic = ytmusicapi.YTMusic()
print(f"Searching for: '{SEARCH_QUERY}'...")

url = None 

try:
    results = ytmusic.search(SEARCH_QUERY, filter="songs")
    if not results:
        print("Song not found.")
        sys.exit()
    
    song = results[0]

    url = f"https://www.youtube.com/watch?v={song['videoId']}"
    print(f"Found song: {song['title']} by {song['artists'][0]['name']}")
    
except Exception as e:
    print(f"Error during YTMusic search: {e}")
    sys.exit()

# 2. yt-dlp का उपयोग करके फ़ाइल को सीधे डिस्क पर डाउनलोड करें (M4A फॉर्मेट)

temp_filepath = os.path.join(temp_dir, f"{song['title']}.m4a") 
print(f"Downloading audio file to: {temp_filepath}...")

# पिछली अस्थायी फ़ाइल हटा दें
if os.path.exists(temp_filepath):
    os.remove(temp_filepath)

# yt-dlp को M4A (140) फॉर्मेट में डाउनलोड करने के लिए मजबूर करें
# M4A फॉर्मेट को transcode करने के लिए FFmpeg की आवश्यकता नहीं होती है।
ydl_opts = {
    'format': '140', 
    'outtmpl': temp_filepath, 
    'quiet': True,
    'noplaylist': True,
    'skip_download': False,
    'noprogress': False, # प्रगति दिखाएं
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    print("Download complete.")
    
except Exception as e:
    print(f"\nError during file download: {e}")
    print("Check your yt-dlp installation.")
    # सुनिश्चित करें कि फ़ाइल डाउनलोड न होने पर हम उसे प्ले करने की कोशिश न करें
    sys.exit()

# 3. Windows Media Player में फ़ाइल खोलें
if os.path.exists(temp_filepath):
    print("Opening Windows Media Player...")
    
    # Windows Media Player (wmplayer.exe) का उपयोग करके फ़ाइल खोलें।
    # 'start' कमांड या 'os.startfile' अक्सर अधिक विश्वसनीय होता है।
    try:
        # os.startfile Windows पर फ़ाइल को उसके डिफ़ॉल्ट प्रोग्राम में खोलता है (जो कि Media Player है)
        os.startfile(temp_filepath)
        print("Playback started in Windows Media Player. Closing Python script...")
        
    except Exception as e:
        print(f"Error opening file with OS default program: {e}")
        print("Attempting to use direct command (might fail if path is incorrect).")
        try:
             # बैकअप कमांड: सीधे wmplayer को कॉल करें
            subprocess.Popen(['wmplayer.exe', temp_filepath])
        except Exception as e:
            print(f"Failed to open wmplayer: {e}. Check if wmplayer is in your PATH.")
            
    # स्क्रिप्ट को बंद करने से पहले 2 सेकंड का विराम
    time.sleep(2) 
    
else:
    print("Error: Downloaded file not found.")

# 4. सफाई (Cleanup) - आप उपयोगकर्ता को बाद में फ़ाइल हटाने के लिए कह सकते हैं।
# फ़ाइल को स्वचालित रूप से हटाना है या नहीं, यह तय करें। सुरक्षा के लिए, इसे अभी छोड़ दें।

print("Program finished.")