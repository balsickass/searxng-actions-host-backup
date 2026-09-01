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

# Export env vars for SearXNG settings path
os.environ["SEARXNG_SETTINGS_PATH"] = "/tmp/searxng/searx/settings.yml"

# Let's run it with python directly via its built-in server or uvicorn
# The webapp entry point is 'searx.webapp' and the app is 'app'
searx_log = open("searx.log", "w")
searx_proc = subprocess.Popen(
    ["python3", "-m", "uvicorn", "searx.webapp:app", "--host", "127.0.0.1", "--port", "8888"],
    cwd="/tmp/searxng",
    stdout=searx_log,
    stderr=subprocess.STDOUT,
    text=True
)
print("SearXNG process spawned with uvicorn.")

time.sleep(5)

# Check if port is open
import socket
s = socket.socket()
s.settimeout(2)
is_open = s.connect_ex(('127.0.0.1', 8888)) == 0
s.close()
print("SearXNG port 8888 open:", is_open)

print("Starting localtunnel setup...")
subprocess.run(["sudo", "npm", "install", "-g", "localtunnel"])

lt_log = open("lt.log", "w")
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
    lt_log.write(line)
    if "your url is:" in line.lower():
        match = re.search(r"https://[a-zA-Z0-9.-]+", line)
        if match:
            public_url = match.group(0)
            break

lt_log.close()

if not public_url:
    print("Failed to start tunnel. Exiting...")
    searx_proc.terminate()
    sys.exit(1)

print("SUCCESS! Public URL parsed:", public_url)

# Write to LIVE_URL.md
with open("LIVE_URL.md", "w") as f:
    f.write(f"# 🌐 Live SearXNG URL\n\nYour cloud-hosted SearXNG is active at:\n\n👉 **[{public_url}]({public_url})**\n\n### ⚠️ CRITICAL - BYPASS INSTRUCTIONS FOR APIS / CURL:\nTo query this API from scripts/Hermes, you **MUST** send this HTTP Header:\n`Bypass-Tunnel-Reminder: true`\n\n### Status Info:\n- **Started at:** {time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n- **Shift Duration:** 4 hours 30 minutes (270 mins)\n")

# Commit and Push
subprocess.run(["git", "config", "--global", "user.name", "balsicl1234"])
subprocess.run(["git", "config", "--global", "user.email", "balsicl1234@users.noreply.github.com"])
subprocess.run(["git", "add", "LIVE_URL.md", "searx.log"])
subprocess.run(["git", "commit", "-m", f"update live url: {public_url}"])
subprocess.run(["git", "push"])
print("LIVE_URL.md and logs pushed to GitHub!")

# Holding loop
for i in range(270):
    time.sleep(60)
    print(f"Shift uptime: {i+1} minutes")
    # Quick check if processes are alive, push logs updates periodically
    if i % 15 == 0:
        # push logs update
        subprocess.run(["git", "add", "searx.log"])
        subprocess.run(["git", "commit", "-m", "logs sync"])
        subprocess.run(["git", "push"])
