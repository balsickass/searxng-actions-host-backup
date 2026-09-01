import subprocess
import time
import re
import os
import sys

print("Starting SearXNG Host Script...")

# Write settings with DEBUG enabled to get full traceback
os.makedirs("/tmp/searxng/searx", exist_ok=True)
settings_content = """
use_default_settings: true
server:
  port: 8888
  bind_address: "127.0.0.1"
  secret_key: "supersecretsearxngkey"
  debug: true
search:
  safe_search: 0
  formats:
    - html
    - json
"""
with open("/tmp/searxng/searx/settings.yml", "w") as f:
    f.write(settings_content)

os.environ["SEARXNG_SETTINGS_PATH"] = "/tmp/searxng/searx/settings.yml"

searx_log = open("searx.log", "w")
searx_proc = subprocess.Popen(
    ["waitress-serve", "--listen=127.0.0.1:8888", "--threads=4", "searx.webapp:app"],
    cwd="/tmp/searxng",
    stdout=searx_log,
    stderr=subprocess.STDOUT,
    text=True
)
print("SearXNG spawned (debug mode).")

time.sleep(5)

import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("Port 8888 open:", is_open)

if not is_open:
    print("SearXNG failed to bind!")
    sys.exit(1)

print("Starting localtunnel...")
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
    print("lt:", line.strip())
    if "your url is:" in line.lower():
        match = re.search(r"https://[a-zA-Z0-9.-]+", line)
        if match:
            public_url = match.group(0)
            break

if not public_url:
    print("Tunnel failed.")
    searx_proc.terminate()
    sys.exit(1)

print("SUCCESS:", public_url)

with open("LIVE_URL.md", "w") as f:
    f.write(f"# 🌐 Live SearXNG URL\n\n👉 **[{public_url}]({public_url})**\n\n- **Started:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift:** 270 mins\n")

subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md", "searx.log"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("Pushed!")

# Wait 30s to let someone hit it, then push logs with traceback
time.sleep(30)
subprocess.run(["git", "add", "searx.log"])
subprocess.run(["git", "commit", "-m", "debug logs sync"])
subprocess.run(["git", "push"])
print("Debug logs pushed!")

# Holding loop
for i in range(270):
    time.sleep(60)
    if i % 5 == 0:
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
