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

# Install tmate
subprocess.run(["sudo", "apt-get", "update"])
subprocess.run(["sudo", "apt-get", "install", "-y", "tmate"])

# Launch tmate on port 8888
# tmate can run local forward tunnel and output the URL!
tmate_proc = subprocess.Popen(
    ["tmate", "-F"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)
print("tmate session initialized...")

# Wait and retrieve the web / ssh URL from tmate
# tmate saves web link to file or displays it in console
time.sleep(5)
try:
    web_url_raw = subprocess.check_output("tmate -S /tmp/tmate.sock display -p '#{tmate_web}'", shell=True, text=True).strip()
    print("tmate raw display link:", web_url_raw)
except Exception as e:
    print("Error getting tmate link:", e)
    web_url_raw = None

# If display is empty or failed, let's parse console logs of tmate
if not web_url_raw:
    # Check tmate console log output
    print("Trying to grab URL from console...")
    # wait a bit for tmate connection
    time.sleep(5)

# For 100% stable HTTP exposure on GitHub actions: we can use dynamic port forwarding or local tunneling
# Let's write a simple python loop that listens on 8888 and we also launch localhost.run or localtunnel
print("Starting localtunnel via npm...")
subprocess.run(["sudo", "npm", "install", "-g", "localtunnel"])

lt_proc = subprocess.Popen(
    ["lt", "--port", "8888"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1
)

public_url = None
start_time = time.time()
while time.time() - start_time < 30:
    line = lt_proc.stdout.readline()
    print("localtunnel:", line.strip())
    if "your url is:" in line.lower():
        match = re.search(r"https://[a-zA-Z0-9.-]+", line)
        if match:
            public_url = match.group(0)
            break
    if not line and lt_proc.poll() is not None:
        break

if not public_url:
    print("Localtunnel failed. Trying alternative (localhost.run)...")
    # localhost.run uses port 80 / SSH (might fail but good fallback)
    lhr_proc = subprocess.Popen(
        ["ssh", "-R", "80:127.0.0.1:8888", "nokey@localhost.run"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    start_time = time.time()
    while time.time() - start_time < 30:
        line = lhr_proc.stdout.readline()
        print("localhost.run:", line.strip())
        if "https://" in line:
            match = re.search(r"https://[a-zA-Z0-9.-]+\.lhr\.life", line)
            if match:
                public_url = match.group(0)
                break
        if not line and lhr_proc.poll() is not None:
            break

if not public_url:
    print("Failed to expose port. Exiting...")
    searx_proc.terminate()
    sys.exit(1)

print("SUCCESS! Public URL parsed:", public_url)

# Write to LIVE_URL.md
with open("LIVE_URL.md", "w") as f:
    f.write(f"# 🌐 Live SearXNG URL\n\nYour cloud-hosted SearXNG is active at:\n\n👉 **[{public_url}]({public_url})**\n\n### Status Info:\n- **Started at:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift Duration:** 4 hours 30 minutes (270 mins)\n")

# Commit and Push
subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("LIVE_URL.md pushed to GitHub!")

# Keep running
try:
    for i in range(270):
        if searx_proc.poll() is not None:
            break
        time.sleep(60)
except KeyboardInterrupt:
    pass

searx_proc.terminate()
print("Clean shutdown complete.")
