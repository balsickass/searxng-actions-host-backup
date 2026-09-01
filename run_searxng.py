import subprocess
import time
import re
import os
import sys

print("Starting SearXNG Host Script...")

# Use the STOCK settings.yml from the repo, just patch it minimally:
# 1. secret_key must be set
# 2. json format must be in search.formats
# 3. limiter off (otherwise botdetection blocks us)
settings_path = "/tmp/searxng/searx/settings.yml"
with open(settings_path) as f:
    content = f.read()

content = content.replace('secret_key: "ultrasecret"', 'secret_key: "gh-actions-searx-key-2026"')
# formats block: stock has only html + csv + rss. Add json.
content = content.replace('- html\n    - csv', '- html\n    - csv\n    - json')
# disable limiter
content = content.replace('limiter: true', 'limiter: false')

with open(settings_path, "w") as f:
    f.write(content)

print("Settings patched (secret_key, json format, limiter off)")
print("Verifying 'json' present:", "- json" in content)

os.environ["SEARXNG_SETTINGS_PATH"] = settings_path

searx_log = open("searx.log", "w")
searx_proc = subprocess.Popen(
    ["waitress-serve", "--listen=127.0.0.1:8888", "--threads=4", "searx.webapp:app"],
    cwd="/tmp/searxng",
    stdout=searx_log,
    stderr=subprocess.STDOUT,
    text=True
)
print("SearXNG spawned with stock settings.")

time.sleep(5)

import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("Port open:", is_open)

# SELF-TEST
import urllib.request as ur
self_test = "UNKNOWN"
try:
    r = ur.urlopen("http://127.0.0.1:8888/search?q=hello&format=json", timeout=30)
    data = json.loads(r.read().decode())
    self_test = f"OK ({len(data.get('results', []))} results)"
except Exception as e:
    self_test = f"FAILED: {e}"
print(f"SELF-TEST: {self_test}")

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
    f.write(f"# 🌐 Live SearXNG URL\n\n👉 **[{public_url}]({public_url})**\n\n- **Started:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift:** 270 mins\n- **Self-test:** {self_test}\n- **JSON test:** {public_url}/search?q=hello&format=json\n")

subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md", "searx.log"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url} self-test={self_test}"])
subprocess.run(["git", "push"])
print("Pushed with self-test result!")

for i in range(270):
    time.sleep(60)
    if i % 10 == 0:
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
