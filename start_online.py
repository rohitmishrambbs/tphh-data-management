"""
TPHH Data Management System - Online Launcher
Starts the local Streamlit application and generates a secure public HTTPS link via Cloudflare Tunnel.
"""
import subprocess
import re
import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
CLOUDFLARED_PATH = PROJECT_ROOT / "tools" / "cloudflared.exe"

if not CLOUDFLARED_PATH.exists():
    print(f"Error: Tunnel tool not found at {CLOUDFLARED_PATH}")
    sys.exit(1)

print("=" * 70)
print("           TPHH DATA MANAGEMENT SYSTEM - ONLINE LAUNCHER")
print("=" * 70)
print()
print("1. Starting local Streamlit data engine...")

# 1. Start Streamlit Process
streamlit_cmd = [
    sys.executable,
    "-m",
    "streamlit",
    "run",
    "app.py",
    "--server.headless=false",
    "--browser.gatherUsageStats=false",
    "--server.port=8501",
]

streamlit_proc = subprocess.Popen(
    streamlit_cmd,
    cwd=str(PROJECT_ROOT),
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

time.sleep(2)

print("2. Generating secure public web link via Cloudflare...")

# 2. Start Cloudflare Tunnel
tunnel_cmd = [
    str(CLOUDFLARED_PATH),
    "tunnel",
    "--url",
    "http://localhost:8501",
]

tunnel_proc = subprocess.Popen(
    tunnel_cmd,
    stderr=subprocess.PIPE,
    stdout=subprocess.DEVNULL,
    text=True,
    encoding="utf-8",
    errors="replace",
)

public_url = None
url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

# Read lines from tunnel process to capture the public URL
for _ in range(60):
    line = tunnel_proc.stderr.readline()
    if not line:
        time.sleep(0.5)
        continue
    match = url_regex.search(line)
    if match:
        public_url = match.group(0)
        break

if public_url:
    print()
    print("=" * 70)
    print("          🎉 YOUR ONLINE WEB LINK IS READY AND ACTIVE!")
    print("=" * 70)
    print()
    print(f"  👉 PUBLIC WEB LINK:  {public_url}")
    print(f"  🏠 LOCAL LINK:        http://localhost:8501")
    print()
    print("  📱 Share this link with anyone - they can open it on their phone,")
    print("     tablet, or laptop anywhere in the world!")
    print("  🔒 All processing and database storage remains securely on this PC.")
    print()
    print("  (Keep this window open while you or others are using the app)")
    print("  (Press Ctrl+C or close this window anytime to take the app offline)")
    print("=" * 70)
    print()
    
    # Open the browser to the public link
    webbrowser.open(public_url)
else:
    print("⚠️ Could not automatically detect public link. Falling back to local mode:")
    print("👉 http://localhost:8501")
    webbrowser.open("http://localhost:8501")

# Keep running until user terminates
try:
    while True:
        time.sleep(1)
        if streamlit_proc.poll() is not None or tunnel_proc.poll() is not None:
            break
except KeyboardInterrupt:
    print("\nStopping online application...")
finally:
    if streamlit_proc and streamlit_proc.poll() is None:
        streamlit_proc.terminate()
    if tunnel_proc and tunnel_proc.poll() is None:
        tunnel_proc.terminate()
    print("Application stopped. Goodbye!")

