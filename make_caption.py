import os
import io
import re
import sys
import base64

import requests

from make_post import get_product, download, price_text, OUT, STORE

MODEL = "gemini-2.5-flash"   # if Google says this model is not found, change the name here
API_KEY = os.environ.get("GEMINI_API_KEY")


def clean(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def make_caption(product, photo):
    if not API_KEY:
        raise SystemExit("GEMINI_API_KEY is not set. See the setup steps.")

    small = photo.copy()
    small.thumbnail((1024, 1024))
    buf = io.BytesIO()
    small.save(buf, "JPEG", quality=85)
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    prompt = f"""You write Instagram and Facebook captions for SHREYAVA, an Indian
gifting and home decor brand (tagline: "Tradition, Beautifully Celebrated.").

Product: {product['title']}
Price: {price_text(product)}
Store description: {clean(product.get('body_html'))[:800]}

Write ONE caption:
- 2 to 3 short, warm sentences about the product, in simple English, festive tone
- Only mention things you can see in the photo or read in the description.
  Do NOT invent materials, sizes, offers or delivery promises.
- Mention the price once, then end with "Shop via the link in bio."
- Then a blank line and 8 relevant hashtags (include #SHREYAVA)
Return only the caption text."""

    body = {"contents": [{"parts": [
        {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}},
        {"text": prompt},
    ]}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    r = requests.post(url, json=body, timeout=90,
                      headers={"x-goog-api-key": API_KEY,
                               "Content-Type": "application/json"})
    if r.status_code != 200:
        raise SystemExit(f"Gemini error {r.status_code}: {r.text[:500]}")
    parts = r.json()["candidates"][0]["content"]["parts"]
    return "".join(part.get("text", "") for part in parts).strip()


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else None
    product = get_product(idx)
    print("Writing caption for:", product["title"])
    photo = download(product, n=1)[0]
    caption = make_caption(product, photo)
    OUT.mkdir(exist_ok=True)
    (OUT / "caption.txt").write_text(caption, encoding="utf-8")
    print("\n" + caption + "\n\nSaved to output/caption.txt")
