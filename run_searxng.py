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

os.environ["SEARXNG_SETTINGS_PATH"] = "/tmp/searxng/searx/settings.yml"

# Waitress is pure-python WSGI server
# Waitress serves Flask apps perfectly!
searx_log = open("searx.log", "w")
searx_proc = subprocess.Popen(
    ["waitress-serve", "--listen=127.0.0.1:8888", "--threads=4", "searx.webapp:app"],
    cwd="/tmp/searxng",
    stdout=searx_log,
    stderr=subprocess.STDOUT,
    text=True
)
print("SearXNG process spawned with Waitress WSGI server.")

time.sleep(5)

import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("SearXNG port 8888 open:", is_open)

if not is_open:
    print("SearXNG failed to start!")
    searx_proc.terminate()
    sys.exit(1)

print("Starting localtunnel setup...")
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
    print("localtunnel output:", line.strip())
    if "your url is:" in line.lower():
        match = re.search(r"https://[a-zA-Z0-9.-]+", line)
        if match:
            public_url = match.group(0)
            break

if not public_url:
    print("Failed to start tunnel.")
    searx_proc.terminate()
    sys.exit(1)

print("SUCCESS! Public URL parsed:", public_url)

with open("LIVE_URL.md", "w") as f:
    f.write(f"# 🌐 Live SearXNG URL\n\nYour cloud-hosted SearXNG is active at:\n\n👉 **[{public_url}]({public_url})**\n\n### Status Info:\n- **Started at:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift Duration:** 4 hours 30 minutes (270 mins)\n- **Test JSON:** [{public_url}/search?q=what+is+python&format=json]({public_url}/search?q=what+is+python&format=json)\n")

subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md", "searx.log"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("LIVE_URL.md pushed!")

for i in range(270):
    time.sleep(60)
    print(f"Shift uptime: {i+1} minutes")
    if i % 10 == 0:
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
