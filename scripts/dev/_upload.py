import urllib.request, json, sys

token = "gho_YOUR_TOKEN_HERE"
release_id = "335569827"
url = f"https://uploads.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{release_id}/assets?name=CDG%20Launcher.exe"

path = r"C:\Users\xxs\Desktop\CDG\dist\CDG Launcher.exe"
with open(path, "rb") as f:
    data = f.read()

print(f"Read {len(data)} bytes, uploading...")
req = urllib.request.Request(url, data=data, method="POST")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("Content-Type", "application/octet-stream")

try:
    resp = urllib.request.urlopen(req, timeout=600)
    print(f"Status: {resp.status}")
    result = json.loads(resp.read())
    dl = result.get("browser_download_url", "N/A")
    print(f"Uploaded! Download: {dl}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code}")
    print(e.read().decode()[:500])
except Exception as e:
    print(f"Error: {e}")
