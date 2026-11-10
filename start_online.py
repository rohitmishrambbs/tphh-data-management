"""
TPHH Data Management System - Online Launcher
Starts the local Streamlit application and generates a secure public HTTPS link via Cloudflare Tunnel.
"""
import subprocess
import re
import sys
import time
import socket
import webbrowser
from pathlib import Path
from src.config import DEFAULT_APP_PIN

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
LOG_FILE = PROJECT_ROOT / "tools" / "tunnel_log.txt"

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

# 1. Start Streamlit if not already active
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
        "--server.headless=true",
        "--server.enableCORS=false",
        "--server.enableXsrfProtection=false",
        "--browser.gatherUsageStats=false",
        "--server.port=8501",
    ]
    streamlit_proc = subprocess.Popen(
        streamlit_cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(1)
        if is_port_in_use(8501):
            break

print("2. Connecting to Cloudflare secure tunnel...")

# Ensure log directory exists
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
tunnel_log = open(LOG_FILE, "w", encoding="utf-8", errors="replace")

# 2. Start Cloudflare Tunnel (redirect stderr to file to prevent Windows pipe buffer deadlocks)
tunnel_cmd = [
    str(CLOUDFLARED_PATH),
    "tunnel",
    "--url",
    "http://127.0.0.1:8501",
]

tunnel_proc = subprocess.Popen(
    tunnel_cmd,
    stderr=tunnel_log,
    stdout=subprocess.DEVNULL,
)

public_url = None
url_regex = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

# Read from log file until the public URL appears
for _ in range(40):
    time.sleep(0.5)
    try:
        content = LOG_FILE.read_text(encoding="utf-8", errors="ignore")
        match = url_regex.search(content)
        if match:
            public_url = match.group(0)
            break
    except Exception:
        pass

if public_url:
    # Save link to a file for easy copying
    try:
        LINK_FILE.write_text(
            f"TPHH Portal Online Web Link:\n{public_url}\n\nSecurity Access PIN: {DEFAULT_APP_PIN}\n",
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
    print(f"   DEFAULT ACCESS PIN: {DEFAULT_APP_PIN}")
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

    # Open browser directly to the public link
    webbrowser.open(public_url)
else:
    print("Notice: Generating tunnel link took longer than expected. Falling back to local mode:")
    print(">> http://localhost:8501")
    webbrowser.open("http://localhost:8501")

# Keep running until user terminates
try:
    while True:
        time.sleep(1)
        if tunnel_proc.poll() is not None:
            print("\nCloudflare tunnel process ended.")
            break
        if streamlit_proc is not None and streamlit_proc.poll() is not None:
            print("\nStreamlit process ended.")
            break
except KeyboardInterrupt:
    print("\nStopping online application...")
finally:
    if streamlit_proc and streamlit_proc.poll() is None:
        streamlit_proc.terminate()
    if tunnel_proc and tunnel_proc.poll() is None:
        tunnel_proc.terminate()
    try:
        tunnel_log.close()
    except Exception:
        pass
    print("Application stopped. Goodbye!")
