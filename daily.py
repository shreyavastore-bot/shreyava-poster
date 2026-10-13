"""SHREYAVA daily poster.
  python daily.py generate   -> makes post.jpg, reel.mp4, caption.txt in /output
  python daily.py publish    -> posts them to Instagram + Facebook
Add --dry-run to publish to see what WOULD be posted, without posting.
"""
import os
import sys
import json
import time

import requests

from make_post import get_product, download, make_image_post, make_reel, OUT, STORE
from make_caption import make_caption

GRAPH = "https://graph.facebook.com/v25.0"          # Meta's API version
GRAPH_VIDEO = "https://graph-video.facebook.com/v25.0"


# ---------- 1. generate ----------
def generate():
    product = get_product()
    print("Product:", product["title"])
    photos = download(product)
    OUT.mkdir(exist_ok=True)
    make_image_post(product, photos[0], OUT / "post.jpg")
    make_reel(product, photos, OUT / "reel.mp4")
    caption = make_caption(product, photos[0])
    (OUT / "caption.txt").write_text(caption, encoding="utf-8")
    info = {"title": product["title"], "handle": product["handle"]}
    (OUT / "product.json").write_text(json.dumps(info), encoding="utf-8")
    print("Caption:\n" + caption)


# ---------- 2. publish ----------
def api(method, path, base=GRAPH, **kw):
    r = requests.request(method, f"{base}/{path}", timeout=300, **kw)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.status_code >= 400 or "error" in data:
        msg = data.get("error", {}).get("message", r.text[:400])
        raise SystemExit(f"Meta API error ({path.split('/')[-1]}): {msg}")
    return data


def instagram(kind, url, caption, token, ig_id):
    params = {"caption": caption, "access_token": token}
    if kind == "image":
        params["image_url"] = url
    else:
        params.update(media_type="REELS", video_url=url, share_to_feed="true")
    container = api("POST", f"{ig_id}/media", data=params)["id"]

    for _ in range(40):                      # wait up to ~10 minutes
        s = api("GET", container,
                params={"fields": "status_code,status", "access_token": token})
        if s.get("status_code") == "FINISHED":
            break
        if s.get("status_code") in ("ERROR", "EXPIRED"):
            raise SystemExit(f"Instagram could not process the {kind}: {s}")
        time.sleep(15)
    else:
        raise SystemExit(f"Instagram took too long to process the {kind}")

    done = api("POST", f"{ig_id}/media_publish",
               data={"creation_id": container, "access_token": token})
    print(f"Instagram {kind} posted, id {done.get('id')}")


def facebook_photo(path, caption, token, page_id):
    with open(path, "rb") as f:
        done = api("POST", f"{page_id}/photos", files={"source": f},
                   data={"caption": caption, "published": "true",
                         "access_token": token})
    print("Facebook photo posted, id", done.get("id"))


def facebook_video(path, caption, token, page_id):
    with open(path, "rb") as f:
        done = api("POST", f"{page_id}/videos", base=GRAPH_VIDEO,
                   files={"source": f},
                   data={"description": caption, "access_token": token})
    print("Facebook video posted, id", done.get("id"))


def publish(dry_run=False):
    caption = (OUT / "caption.txt").read_text(encoding="utf-8")
    info = json.loads((OUT / "product.json").read_text(encoding="utf-8"))
    link = f"{STORE}/products/{info['handle']}"
    fb_caption = caption.replace("Shop via the link in bio.", f"Shop: {link}")
    base_url = os.environ.get("MEDIA_BASE", "https://example.com/output")

    if dry_run:
        print("DRY RUN - nothing is posted.\nProduct:", info["title"])
        print("Instagram image URL:", f"{base_url}/post.jpg")
        print("Instagram reel URL: ", f"{base_url}/reel.mp4")
        print("\nInstagram caption:\n" + caption)
        print("\nFacebook caption:\n" + fb_caption)
        return

    token = os.environ["META_PAGE_TOKEN"]
    ig_id = os.environ["IG_USER_ID"]
    page_id = os.environ["FB_PAGE_ID"]

    instagram("image", f"{base_url}/post.jpg", caption, token, ig_id)
    instagram("reel", f"{base_url}/reel.mp4", caption, token, ig_id)
    facebook_photo(OUT / "post.jpg", fb_caption, token, page_id)
    facebook_video(OUT / "reel.mp4", fb_caption, token, page_id)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "generate":
        generate()
    elif cmd == "publish":
        publish(dry_run="--dry-run" in sys.argv)
    else:
        raise SystemExit("Use: python daily.py generate   or   python daily.py publish")
