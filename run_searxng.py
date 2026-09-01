import subprocess
import time
import re
import os
import sys

print("Starting SearXNG Host Script...")

settings_path = "/tmp/searxng/searx/settings.yml"
with open(settings_path) as f:
    content = f.read()

# Stock default: secret_key: 'ultrasecretkey'
import re as _re
content = _re.sub(r'secret_key:.*', 'secret_key: "gh-actions-searx-key-2026"', content, count=1)
# add json to formats
if "- json" not in content:
    content = content.replace('- html', '- html\n    - json', 1)
# disable limiter
content = _re.sub(r'limiter: true', 'limiter: false', content)
# debug off
content = _re.sub(r'debug: true', 'debug: false', content)

with open(settings_path, "w") as f:
    f.write(content)

print("Patched. secret_key present:", "gh-actions-searx-key-2026" in content, "| json in formats:", "- json" in content)

os.environ["SEARXNG_SETTINGS_PATH"] = settings_path

searx_log = open("searx.log", "w")
searx_proc = subprocess.Popen(
    ["waitress-serve", "--listen=127.0.0.1:8888", "--threads=4", "searx.webapp:app"],
    cwd="/tmp/searxng",
    stdout=searx_log,
    stderr=subprocess.STDOUT,
    text=True
)
print("SearXNG spawned.")

time.sleep(6)

import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("Port open:", is_open)

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
subprocess.run(["git", "commit", "-m", f"url: {public_url} selftest={self_test}"])
subprocess.run(["git", "push"])
print("Pushed!")

for i in range(270):
    time.sleep(60)
    if i % 10 == 0:
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
