import urllib.request, json

token = "gho_YOUR_TOKEN_HERE"
release_id = "335571696"

path = r"C:\Users\xxs\Desktop\CDG\dist\CDG Launcher.exe"
with open(path, "rb") as f:
    data = f.read()
print(f"Uploading {len(data)} bytes...")

upload_url = f"https://uploads.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{release_id}/assets?name=CDG%20Launcher.exe"
req = urllib.request.Request(upload_url, data=data, method="POST")
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("Content-Type", "application/octet-stream")

try:
    resp = urllib.request.urlopen(req, timeout=600)
    asset = json.loads(resp.read())
    print(f"Uploaded! {asset['browser_download_url']}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:300]}")
except Exception as e:
    print(f"Error: {e}")
