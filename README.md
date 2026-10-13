# shreyava-poster

Posts one SHREYAVA product a day to Instagram and Facebook.

Every day GitHub Actions runs `daily.py`, which:
1. picks a product from the Shopify store (`/products.json`),
2. makes `output/post.jpg` and `output/reel.mp4` from the product photos,
3. writes a caption with the Gemini API,
4. publishes to Instagram and Facebook through the Meta Graph API.

## Secrets (Settings > Secrets and variables > Actions)
`GEMINI_API_KEY`, `META_PAGE_TOKEN`, `IG_USER_ID`, `FB_PAGE_ID`

Never commit these values to the repo.

## Test locally
```
pip install -r requirements.txt
python make_post.py
python make_caption.py        # needs GEMINI_API_KEY set
```
Run `python daily.py generate` and then `python daily.py publish --dry-run` to preview a post without publishing.
