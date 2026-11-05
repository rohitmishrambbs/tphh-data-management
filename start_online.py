"""
TPHH Data Management System - Online Launcher
Starts the local Streamlit application and generates a secure public HTTPS link via Cloudflare Tunnel.
"""
import subprocess
import re
import sys
import time
import socket
import urllib.request
import webbrowser
from pathlib import Path

# Ensure UTF-8 output encoding across Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_ROOT = Path(__file__).resolve().parent
CLOUDFLARED_PATH = PROJECT_ROOT / "tools" / "cloudflared.exe"
LINK_FILE = PROJECT_ROOT / "ONLINE_LINK.txt"

if not CLOUDFLARED_PATH.exists():
    print(f"Error: Tunnel tool not found at {CLOUDFLARED_PATH}")
    sys.exit(1)


def is_port_in_use(port: int = 8501) -> bool:
    """Check if port 8501 is actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) == 0


print("=" * 70)
print("           TPHH DATA MANAGEMENT SYSTEM - ONLINE LAUNCHER")
print("=" * 70)
print()

streamlit_proc = None

if is_port_in_use(8501):
    print("1. Local Streamlit data engine is already active on port 8501.")
else:
    print("1. Starting local Streamlit data engine on port 8501...")
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
    for _ in range(15):
        time.sleep(1)
        if is_port_in_use(8501):
            break

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
    # Save link to a file for easy copying
    try:
        LINK_FILE.write_text(
            f"TPHH Portal Online Web Link:\n{public_url}\n\nSecurity Access PIN: 2026\n",
            encoding="utf-8"
        )
    except Exception:
        pass

    print()
    print("=" * 70)
    print("           YOUR ONLINE WEB LINK IS READY AND ACTIVE!")
    print("=" * 70)
    print()
    print(f"   PUBLIC WEB LINK:    {public_url}")
    print(f"   LOCAL LINK:         http://localhost:8501")
    print(f"   DEFAULT ACCESS PIN: 2026")
    print()
    print("   Share this link with anyone - they can open it on their phone,")
    print("   tablet, or laptop anywhere in the world!")
    print("   All processing and database storage remains securely on this PC.")
    print()
    print("   (Link is also saved in ONLINE_LINK.txt in your folder)")
    print("   (Keep this window open while using the online app)")
    print("   (Press Ctrl+C or close this window anytime to take the app offline)")
    print("=" * 70)
    print()

    # Open the browser to the public link
    webbrowser.open(public_url)
else:
    print("Notice: Could not automatically detect public link. Falling back to local mode:")
    print(">> http://localhost:8501")
    webbrowser.open("http://localhost:8501")

# Keep running until user terminates
try:
    while True:
        time.sleep(1)
        if tunnel_proc.poll() is not None:
            break
        if streamlit_proc is not None and streamlit_proc.poll() is not None:
            break
except KeyboardInterrupt:
    print("\nStopping online application...")
finally:
    if streamlit_proc and streamlit_proc.poll() is None:
        streamlit_proc.terminate()
    if tunnel_proc and tunnel_proc.poll() is None:
        tunnel_proc.terminate()
    print("Application stopped. Goodbye!")
