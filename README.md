# 📸 Memories Maker

A Flask web tool that transforms standard photos into **print-ready framed layouts** with precise white borders and corner cut marks for manual trimming.

## Features

- **Drag & drop** or file-browse upload (JPG, PNG, WebP, BMP, TIFF)
- **Individual prints** — one JPEG per photo with white borders & cut marks
- **A4 print sheet** — 9 photos per A4 page at 300 DPI, ready to print
- **Both modes** in a single ZIP download
- Automatic EXIF rotation correction
- Clean, responsive UI — works on desktop and mobile

## Setup

```bash
pip install Flask Pillow
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## How it works

| Step | Detail |
|---|---|
| Square crop | Center-crops to the shortest side (1:1 ratio) |
| Canvas | Adds 10% white margin on sides & top, 25% on the bottom |
| Cut marks | Grey + crosses at each corner (±10px, #808080) |
| A4 layout | 3 cols × 3 rows = 9 per page, 733×825px cells at 300 DPI |

## Deploy to Vercel

1. Push this repo to GitHub
2. Import at [vercel.com/new](https://vercel.com/new) — `vercel.json` handles everything
