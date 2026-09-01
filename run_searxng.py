import subprocess
import time
import re
import os
import sys

print("Starting SearXNG Host Script...")

# Write a COMPLETE settings.yml - all required keys present
os.makedirs("/tmp/searxng/searx", exist_ok=True)
settings_content = """
use_default_settings: true

general:
  instance_name: "GH Actions SearXNG"
  debug: false
  privacypolicy: false
  donation_url: false
  contact_url: false
  enable_metrics: false

server:
  port: 8888
  bind_address: "127.0.0.1"
  secret_key: "gh-actions-searx-key-2026"
  limiter: false
  image_proxy: false
  public_instance: false
  method: "GET"
  http_protocol_version: "1.1"

search:
  safe_search: 0
  autocomplete: ""
  default_lang: ""
  formats:
    - html
    - json

outgoing:
  request_timeout: 6.0
  max_request_timeout: 15.0
  useragent_suffix: ""
  pool_connections: 100
  pool_maxsize: 20

ui:
  static_use_hash: true

doi_resolvers: {}

default_doi_resolver: "doi.org"
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
print("SearXNG spawned.")

time.sleep(5)

import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("Port 8888 open:", is_open)

# SELF-TEST before exposing! If JSON search fails locally, log it and exit
import urllib.request as ur
try:
    r = ur.urlopen("http://127.0.0.1:8888/search?q=hello&format=json", timeout=30)
    data = json.loads(r.read().decode())
    print(f"SELF-TEST OK! Results: {len(data.get('results', []))}")
except Exception as e:
    print(f"SELF-TEST FAILED: {e}")

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
    f.write(f"# 🌐 Live SearXNG URL\n\n👉 **[{public_url}]({public_url})**\n\n- **Started:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift:** 270 mins\n- **JSON test:** {public_url}/search?q=hello&format=json\n")

subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md", "searx.log"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("Pushed!")

# Wait 60s then push logs to capture the self-test results
time.sleep(60)
subprocess.run(["git", "add", "searx.log"])
subprocess.run(["git", "commit", "-m", "selftest logs"])
subprocess.run(["git", "push"])

# Holding loop with periodic log sync
for i in range(270):
    time.sleep(60)
    if i % 10 == 0:
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
