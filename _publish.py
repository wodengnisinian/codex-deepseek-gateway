import urllib.request, json

token = "gho_YOUR_TOKEN_HERE"

# Find the draft release
list_req = urllib.request.Request(
    "https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases?per_page=5",
    method="GET"
)
list_req.add_header("Authorization", f"Bearer {token}")
list_req.add_header("Accept", "application/vnd.github+json")
resp = urllib.request.urlopen(list_req, timeout=30)
releases = json.loads(resp.read())

draft_id = None
for r in releases:
    if r["draft"]:
        draft_id = r["id"]
        print(f"Found draft: id={draft_id} tag={r['tag_name']} url={r['html_url']}")
        # Now publish - only changing draft field
        pub_body = json.dumps({"draft": False}).encode()
        pub_req = urllib.request.Request(
            f"https://api.github.com/repos/wodengnisinian/codex-deepseek-gateway/releases/{draft_id}",
            data=pub_body, method="PATCH"
        )
        pub_req.add_header("Authorization", f"Bearer {token}")
        pub_req.add_header("Accept", "application/vnd.github+json")
        pub_req.add_header("Content-Type", "application/json")
        try:
            pub_resp = urllib.request.urlopen(pub_req, timeout=30)
            final = json.loads(pub_resp.read())
            print(f"Published! {final['html_url']}")
        except urllib.error.HTTPError as e:
            print(f"Publish failed: {e.code} - {e.read().decode()[:300]}")
        break

if not draft_id:
    print("No draft found")
