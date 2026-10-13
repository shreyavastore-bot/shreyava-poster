import io
import sys
import subprocess
import datetime
from pathlib import Path

import requests
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

STORE = "https://shreyava.myshopify.com"
BRAND = "SHREYAVA"
TAGLINE = "Tradition, Beautifully Celebrated."
DARK = (63, 29, 20)       # your store's theme color
CREAM = (248, 241, 231)
GOLD = (176, 128, 40)
OUT = Path("output")

FONTS = ["georgiab.ttf", "georgia.ttf", "arialbd.ttf",
         "DejaVuSerif-Bold.ttf", "DejaVuSans-Bold.ttf"]


def font(size):
    for name in FONTS:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size)


def get_product(index=None):
    r = requests.get(f"{STORE}/products.json?limit=250", timeout=30)
    r.raise_for_status()
    products = r.json()["products"]
    if index is None:  # a different product each day
        index = datetime.date.today().toordinal()
    return products[index % len(products)]


def download(product, n=4):
    photos = []
    for img in product["images"][:n]:
        r = requests.get(img["src"], timeout=30)
        r.raise_for_status()
        photos.append(Image.open(io.BytesIO(r.content)).convert("RGB"))
    if not photos:
        raise SystemExit("This product has no photos.")
    return photos


def fit(img, w, h, bg=(255, 255, 255)):
    """Fit the whole photo inside w x h without cutting anything off."""
    s = min(w / img.width, h / img.height)
    small = img.resize((round(img.width * s), round(img.height * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (w, h), bg)
    canvas.paste(small, ((w - small.width) // 2, (h - small.height) // 2))
    return canvas


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip()
        if draw.textlength(test, font=fnt) <= max_w:
            cur = test
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def price_text(p):
    return f"Rs. {float(p['variants'][0]['price']):.0f}"


def make_image_post(p, photo, path):
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.text((W // 2, 65), BRAND, font=font(48), fill=DARK, anchor="mm")
    img.paste(fit(photo, 900, 900), (90, 120))
    y = 1050
    for line in wrap(d, p["title"], font(52), 940)[:2]:
        d.text((W // 2, y), line, font=font(52), fill=DARK, anchor="mt")
        y += 66
    d.text((W // 2, y + 10), price_text(p), font=font(46), fill=GOLD, anchor="mt")
    img.save(path, quality=95)


def make_reel(p, photos, path, secs=3, fps=30):
    W, H = 1080, 1920
    bg = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(bg)
    d.text((W // 2, 150), BRAND, font=font(64), fill=DARK, anchor="mm")
    d.text((W // 2, 225), TAGLINE, font=font(32), fill=GOLD, anchor="mm")
    y = 1560
    for line in wrap(d, p["title"], font(58), 960)[:2]:
        d.text((W // 2, y), line, font=font(58), fill=DARK, anchor="mt")
        y += 74
    d.text((W // 2, y + 15), price_text(p), font=font(52), fill=GOLD, anchor="mt")

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-",
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "fast",
           "-crf", "23", "-movflags", "+faststart", str(path)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    frames = secs * fps
    for photo in photos:
        tile = fit(photo, 1080, 1080)
        for i in range(frames):
            t = i / (frames - 1)
            crop = 1080 - 100 * t          # slow zoom-in
            off = (1080 - crop) / 2
            zoomed = tile.resize((1080, 1080), Image.BILINEAR,
                                 box=(off, off, off + crop, off + crop))
            frame = bg.copy()
            frame.paste(zoomed, (0, 420))
            proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()


if __name__ == "__main__":
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else None
    product = get_product(idx)
    print("Making post for:", product["title"])
    OUT.mkdir(exist_ok=True)
    photos = download(product)
    make_image_post(product, photos[0], OUT / "post.jpg")
    make_reel(product, photos, OUT / "reel.mp4")
    print("Done. Open the 'output' folder.")
