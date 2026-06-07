import urllib.request, json

token = "gho_YOUR_TOKEN_HERE"

# Step 1: Delete existing release (id=335570621 already deleted, need to find new one)
# Let me list releases
list_req = urllib.request.Request(
    "https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases?per_page=5",
    method="GET"
)
list_req.add_header("Authorization", f"Bearer {token}")
list_req.add_header("Accept", "application/vnd.github+json")
resp = urllib.request.urlopen(list_req, timeout=30)
releases = json.loads(resp.read())
for r in releases:
    print(f"Delete: id={r['id']} tag={r['tag_name']}")
    del_req = urllib.request.Request(
        f"https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{r['id']}",
        method="DELETE"
    )
    del_req.add_header("Authorization", f"Bearer {token}")
    del_req.add_header("Accept", "application/vnd.github+json")
    try:
        del_resp = urllib.request.urlopen(del_req, timeout=15)
        print(f"  Deleted (status={del_resp.status})")
    except urllib.error.HTTPError as e:
        print(f"  Failed: {e.code}")

# Also delete remote tag
# Note: we do this via git command line, skip here

print("\nNow creating DRAFT release...")
body = json.dumps({
    "tag_name": "v0.4.1-release",
    "target_commitish": "master",
    "name": "v0.4.1 - Codex DeepSeek Gateway",
    "body": "## Codex DeepSeek Gateway v0.4.1\r\n\r\n### Features\r\n- Single exe: double-click to run, no Python needed\r\n- Built-in uvicorn FastAPI gateway\r\n- PySide6 desktop launcher\r\n\r\n### Requirements\r\n- Windows 10/11 64-bit\r\n- DeepSeek API Key (https://platform.deepseek.com)",
    "draft": True,
    "prerelease": False
}).encode()

req = urllib.request.Request(
    "https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases",
    data=body, method="POST"
)
req.add_header("Authorization", f"Bearer {token}")
req.add_header("Accept", "application/vnd.github+json")
req.add_header("Content-Type", "application/json")

try:
    resp = urllib.request.urlopen(req, timeout=30)
    release = json.loads(resp.read())
    release_id = release["id"]
    print(f"Draft: {release['html_url']} (draft={release['draft']})")
    
    # Upload
    path = r"C:\Users\xxs\Desktop\CDG\dist\CDG Launcher.exe"
    with open(path, "rb") as f:
        data = f.read()
    print(f"Uploading {len(data)} bytes...")
    
    upload_url = f"https://uploads.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{release_id}/assets?name=CDG%20Launcher.exe"
    req2 = urllib.request.Request(upload_url, data=data, method="POST")
    req2.add_header("Authorization", f"Bearer {token}")
    req2.add_header("Accept", "application/vnd.github+json")
    req2.add_header("Content-Type", "application/octet-stream")
    
    resp2 = urllib.request.urlopen(req2, timeout=600)
    asset = json.loads(resp2.read())
    print(f"Asset uploaded: {asset['browser_download_url']}")
    
    # Publish
    print("Publishing...")
    pub_body = json.dumps({"draft": False}).encode()
    pub_req = urllib.request.Request(
        f"https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{release_id}",
        data=pub_body, method="PATCH"
    )
    pub_req.add_header("Authorization", f"Bearer {token}")
    pub_req.add_header("Accept", "application/vnd.github+json")
    pub_req.add_header("Content-Type", "application/json")
    pub_resp = urllib.request.urlopen(pub_req, timeout=30)
    final = json.loads(pub_resp.read())
    print(f"Published! {final['html_url']}")
    
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}: {e.read().decode()[:500]}")
except Exception as e:
    print(f"Error: {e}")
