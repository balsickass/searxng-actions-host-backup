import subprocess
import time
import re
import os
import sys

print("Starting SearXNG Host Script...")

# Write settings-custom.yml
os.makedirs("/tmp/searxng/searx", exist_ok=True)
settings_content = """
use_default_settings: true
server:
  port: 8888
  bind_address: "127.0.0.1"
  secret_key: "supersecretsearxngkey"
search:
  safe_search: 0
  formats:
    - html
    - json
"""
with open("/tmp/searxng/searx/settings.yml", "w") as f:
    f.write(settings_content)

# Start SearXNG via Granian
searx_proc = subprocess.Popen(
    ["granian", "wsgi", "127.0.0.1:8888", "searx.webapp:app"],
    cwd="/tmp/searxng",
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
print("SearXNG process spawned.")

# Give it 3s to spin up
time.sleep(3)

# Start pinggy tunnel
# We use StrictHostKeyChecking=no to prevent SSH prompt blocking
tunnel_proc = subprocess.Popen(
    ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ServerAliveInterval=30", "-R", "80:127.0.0.1:8888", "py@a.pinggy.io"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)
print("Pinggy tunnel spawned. Parsing public URL...")

# Read tunnel stdout line by line to extract the https URL
public_url = None
start_time = time.time()
while time.time() - start_time < 30: # 30s timeout to grab URL
    line = tunnel_proc.stdout.readline()
    print("Tunnel:", line.strip())
    if "https://" in line:
        match = re.search(r"https://[a-zA-Z0-9.-]+\.pinggy\.link", line)
        if match:
            public_url = match.group(0)
            break
    if not line and tunnel_proc.poll() is not None:
        break

if not public_url:
    print("Failed to parse Pinggy URL. Exiting...")
    searx_proc.terminate()
    sys.exit(1)

print("SUCCESS! Public URL parsed:", public_url)

# Write to LIVE_URL.md
with open("LIVE_URL.md", "w") as f:
    f.write(f"# 🌐 Live SearXNG URL\n\nYour cloud-hosted SearXNG is active at:\n\n👉 **[{public_url}]({public_url})**\n\n### Status Info:\n- **Started at:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift Duration:** 4 hours 30 minutes (270 mins)\n- **Format:** Supports HTML and JSON search!\n")

# Git commit and push URL back to repo so the local agent/user can read it
subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("LIVE_URL.md pushed to GitHub!")

# Keep running to maintain the tunnel (270 minutes)
print("Entering holding loop (270 minutes)...")
try:
    for i in range(270):
        if searx_proc.poll() is not None:
            print("SearXNG process crashed!")
            break
        if tunnel_proc.poll() is not None:
            print("Tunnel process crashed!")
            break
        time.sleep(60) # check every minute
except KeyboardInterrupt:
    print("Terminating...")

searx_proc.terminate()
tunnel_proc.terminate()
print("Clean shutdown complete.")
