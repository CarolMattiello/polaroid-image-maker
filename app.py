import os
import io
import zipfile
import shutil
import uuid

from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image, ImageOps, ImageDraw

app = Flask(__name__)

TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_polaroid(img: Image.Image) -> Image.Image:
    """Apply the Polaroid transformation to a PIL Image."""
    # 1. Respect EXIF orientation
    img = ImageOps.exif_transpose(img)

    # Convert to RGB (handles RGBA, palette, etc.)
    img = img.convert("RGB")

    # 2. Center-crop to square (shortest side)
    min_side = min(img.width, img.height)
    left = (img.width - min_side) // 2
    top = (img.height - min_side) // 2
    img = img.crop((left, top, left + min_side, top + min_side))

    S = min_side  # square side length

    # 3. Build canvas
    #   Width  = S + 0.2*S = 1.2*S   (10% left + 10% right)
    #   Height = S + 0.35*S = 1.35*S (10% top  + 25% bottom)
    canvas_w = round(S * 1.2)
    canvas_h = round(S * 1.35)
    canvas = Image.new("RGB", (canvas_w, canvas_h), color=(255, 255, 255))

    paste_x = round(S * 0.1)
    paste_y = round(S * 0.1)
    canvas.paste(img, (paste_x, paste_y))

    # 4. Draw grey cross cut-marks at each corner
    draw = ImageDraw.Draw(canvas)
    cross_color = (128, 128, 128)  # #808080
    span = 10  # 10 px in each direction → total 20 px span

    corners = [
        (0, 0),
        (canvas_w - 1, 0),
        (0, canvas_h - 1),
        (canvas_w - 1, canvas_h - 1),
    ]
    for cx, cy in corners:
        # Horizontal bar of the cross
        draw.line(
            [(max(0, cx - span), cy), (min(canvas_w - 1, cx + span), cy)],
            fill=cross_color,
            width=1,
        )
        # Vertical bar of the cross
        draw.line(
            [(cx, max(0, cy - span)), (cx, min(canvas_h - 1, cy + span))],
            fill=cross_color,
            width=1,
        )

    return canvas


def ensure_dirs():
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def cleanup_dirs():
    for d in (TEMP_DIR, OUTPUT_DIR):
        if os.path.isdir(d):
            shutil.rmtree(d)
            os.makedirs(d)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    ensure_dirs()

    files = request.files.getlist("images")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files uploaded."}), 400

    processed_paths = []

    for f in files:
        if not allowed_file(f.filename):
            continue

        # Save to temp
        ext = f.filename.rsplit(".", 1)[1].lower()
        temp_name = f"{uuid.uuid4().hex}.{ext}"
        temp_path = os.path.join(TEMP_DIR, temp_name)
        f.save(temp_path)

        try:
            with Image.open(temp_path) as img:
                polaroid = make_polaroid(img)

            # Save processed image (always as JPEG for print-readiness)
            base = os.path.splitext(f.filename)[0]
            out_name = f"{base}_polaroid.jpg"
            out_path = os.path.join(OUTPUT_DIR, out_name)

            # Handle filename collisions
            counter = 1
            while os.path.exists(out_path):
                out_name = f"{base}_polaroid_{counter}.jpg"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                counter += 1

            polaroid.save(out_path, "JPEG", quality=95)
            processed_paths.append(out_path)
        except Exception as e:
            app.logger.error(f"Failed to process {f.filename}: {e}")

    if not processed_paths:
        cleanup_dirs()
        return jsonify({"error": "No valid images could be processed."}), 422

    # Build ZIP in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in processed_paths:
            zf.write(path, arcname=os.path.basename(path))
    zip_buffer.seek(0)

    cleanup_dirs()

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name="polaroids_to_print.zip",
    )


if __name__ == "__main__":
    ensure_dirs()
    app.run(debug=True)
