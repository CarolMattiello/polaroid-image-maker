# 📸 Polaroid Maker

A Flask web tool that transforms standard photos into **print-ready Polaroid layouts** with precise border margins and corner cut marks for manual trimming.

## Features

- **Drag & drop** or file-browse upload (JPG, PNG, WEBP, BMP, TIFF)
- **Polaroid logic:**
  - Center-crops to a perfect 1:1 square (EXIF orientation respected)
  - Adds white borders: 10% left/right/top, 25% bottom "chin"
  - Draws grey `+` cut marks at each canvas corner
- **Batch processing** — upload multiple photos at once
- **ZIP download** — all processed photos bundled into `polaroids_to_print.zip`
- Temp and output files are automatically cleaned up after download

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the server

```bash
python app.py
```

### 3. Open the app

Go to [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

## Project Structure

```
polaroid-image-maker/
├── app.py              # Flask backend + image processing
├── requirements.txt
├── templates/
│   └── index.html      # Drag-and-drop UI
├── static/
│   └── style.css       # Dark premium styles
├── temp/               # Created automatically (upload buffer)
└── output/             # Created automatically (processed images)
```

## Polaroid Geometry

| Measurement          | Formula   |
|----------------------|-----------|
| Canvas Width         | `S × 1.2` |
| Canvas Height        | `S × 1.35`|
| Left/Right Margin    | `S × 0.1` |
| Top Margin           | `S × 0.1` |
| Bottom "Chin"        | `S × 0.25`|
| Cut mark color       | `#808080` |
| Cut mark span        | 20 px     |

Where `S` = shortest side of the original image.
