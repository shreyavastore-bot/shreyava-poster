"""SHREYAVA weekly content maker.

Makes ready-to-upload posts for the next N days (default 7).
Each day gets its own folder with:
    post.jpg              -> image post
    reel.mp4              -> Reel
    caption_instagram.txt -> caption (says "link in bio")
    caption_facebook.txt  -> same caption with the product link
Also writes ALL_CAPTIONS.txt so you can see everything in one place.

Usage (Windows cmd):
    set GEMINI_API_KEY=your_key
    python weekly.py          -> next 7 days
    python weekly.py 14       -> next 14 days
"""
import sys
import time
import datetime
from pathlib import Path

import requests

from make_post import STORE, download, make_image_post, make_reel, price_text
from make_caption import make_caption

OUT_DIR = Path("weekly_output")


def all_products():
    r = requests.get(f"{STORE}/products.json?limit=250", timeout=30)
    r.raise_for_status()
    return r.json()["products"]


def caption_with_retry(product, photo):
    for attempt in range(4):
        try:
            return make_caption(product, photo), True
        except SystemExit as e:
            msg = str(e)
            busy = "429" in msg or "503" in msg or "UNAVAILABLE" in msg
            if busy and attempt < 3:              # Gemini is busy: wait and retry
                print("   Gemini is busy, waiting 40 seconds and trying again...")
                time.sleep(40)
                continue
            print("   WARNING: AI caption failed:", msg[:150])
            break
    plain = (f"{product['title']} - {price_text(product)}. "
             "Shop via the link in bio.\n\n#SHREYAVA")
    return plain + "\n[PLAIN CAPTION - AI failed, please edit]", False


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    products = all_products()
    start = datetime.date.today() + datetime.timedelta(days=1)   # from tomorrow
    OUT_DIR.mkdir(exist_ok=True)
    summary = []

    for i in range(days):
        day = start + datetime.timedelta(days=i)
        product = products[day.toordinal() % len(products)]
        folder = OUT_DIR / f"{day.isoformat()}_{product['handle'][:40]}"
        print(f"[{i + 1}/{days}] {day}  {product['title']}")

        media_ok = (folder / "reel.mp4").exists() and (folder / "post.jpg").exists()
        cap_file = folder / "caption_instagram.txt"
        cap_ok = cap_file.exists() and "[PLAIN CAPTION" not in cap_file.read_text(encoding="utf-8")

        if media_ok and cap_ok:
            print("   already made, skipping")
        else:
            folder.mkdir(exist_ok=True)
            if media_ok:
                print("   video/image already made, redoing only the caption")
                photos = download(product, n=1)
            else:
                photos = download(product)
                make_image_post(product, photos[0], folder / "post.jpg")
                make_reel(product, photos, folder / "reel.mp4")
            caption, ok = caption_with_retry(product, photos[0])
            link = f"{STORE}/products/{product['handle']}"
            fb = caption.replace("Shop via the link in bio.", f"Shop: {link}")
            cap_file.write_text(caption, encoding="utf-8")
            (folder / "caption_facebook.txt").write_text(fb, encoding="utf-8")
            time.sleep(4)          # be gentle with the free Gemini limit

        cap = (folder / "caption_instagram.txt").read_text(encoding="utf-8")
        summary.append(f"=== {day}  |  {product['title']} ===\n{cap}\n")

    (OUT_DIR / "ALL_CAPTIONS.txt").write_text("\n".join(summary), encoding="utf-8")
    print(f"\nDone! Open the '{OUT_DIR}' folder.")


if __name__ == "__main__":
    main()