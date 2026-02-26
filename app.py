import os
import io
import zipfile
import shutil
import uuid
import tempfile

from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image, ImageOps, ImageDraw

app = Flask(__name__)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "tif"}

# ── A4 layout constants (300 DPI) ──────────────────────────────
A4_W, A4_H   = 2480, 3508
A4_MARGIN    = 100
A4_GAP       = 40
A4_COLS      = 3
A4_POL_W = (A4_W - 2 * A4_MARGIN - (A4_COLS - 1) * A4_GAP) // A4_COLS
A4_POL_H = round(A4_POL_W * (1.35 / 1.2))
A4_ROWS  = (A4_H - 2 * A4_MARGIN + A4_GAP) // (A4_POL_H + A4_GAP)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def make_polaroid(img: Image.Image) -> Image.Image:
    """Return a Polaroid-bordered PIL Image (in memory)."""
    img = ImageOps.exif_transpose(img).convert("RGB")

    min_side = min(img.width, img.height)
    left = (img.width  - min_side) // 2
    top  = (img.height - min_side) // 2
    img  = img.crop((left, top, left + min_side, top + min_side))
    S    = min_side

    canvas_w = round(S * 1.2)
    canvas_h = round(S * 1.35)
    canvas   = Image.new("RGB", (canvas_w, canvas_h), (255, 255, 255))
    canvas.paste(img, (round(S * 0.1), round(S * 0.1)))

    draw        = ImageDraw.Draw(canvas)
    cross_color = (128, 128, 128)
    span        = 10
    for cx, cy in [(0, 0), (canvas_w - 1, 0), (0, canvas_h - 1), (canvas_w - 1, canvas_h - 1)]:
        draw.line([(max(0, cx - span), cy), (min(canvas_w - 1, cx + span), cy)], fill=cross_color, width=1)
        draw.line([(cx, max(0, cy - span)), (cx, min(canvas_h - 1, cy + span))], fill=cross_color, width=1)

    return canvas


def make_a4_pages(polaroids: list) -> list:
    """Arrange polaroid images on A4 canvases (list of PIL Images)."""
    per_page = A4_COLS * A4_ROWS
    pages = []

    for page_start in range(0, len(polaroids), per_page):
        page_pols = polaroids[page_start : page_start + per_page]
        canvas = Image.new("RGB", (A4_W, A4_H), (255, 255, 255))

        for idx, pol in enumerate(page_pols):
            col = idx % A4_COLS
            row = idx // A4_COLS
            x   = A4_MARGIN + col * (A4_POL_W + A4_GAP)
            y   = A4_MARGIN + row * (A4_POL_H + A4_GAP)
            resized = pol.resize((A4_POL_W, A4_POL_H), Image.LANCZOS)
            canvas.paste(resized, (x, y))

        pages.append(canvas)

    return pages


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    files  = request.files.getlist("images")
    layout = request.form.get("layout", "individual")

    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files uploaded."}), 400

    # Per-request isolated temp directory — works locally and on Vercel (/tmp)
    work_dir   = tempfile.mkdtemp()
    temp_dir   = os.path.join(work_dir, "temp")
    output_dir = os.path.join(work_dir, "output")
    os.makedirs(temp_dir)
    os.makedirs(output_dir)

    try:
        polaroids_mem = []

        for f in files:
            if not allowed_file(f.filename):
                continue

            ext       = f.filename.rsplit(".", 1)[1].lower()
            temp_path = os.path.join(temp_dir, f"{uuid.uuid4().hex}.{ext}")
            f.save(temp_path)

            try:
                with Image.open(temp_path) as img:
                    polaroid = make_polaroid(img)
                base = os.path.splitext(f.filename)[0]
                polaroids_mem.append((base, polaroid))
            except Exception as e:
                app.logger.error(f"Failed to process {f.filename}: {e}")

        if not polaroids_mem:
            return jsonify({"error": "No valid images could be processed."}), 422

        output_paths = []

        if layout in ("individual", "both", "both_pdf"):
            for base, pol in polaroids_mem:
                out_name = f"{base}_polaroid.jpg"
                out_path = os.path.join(output_dir, out_name)
                counter  = 1
                while os.path.exists(out_path):
                    out_path = os.path.join(output_dir, f"{base}_polaroid_{counter}.jpg")
                    counter += 1
                pol.save(out_path, "JPEG", quality=95)
                output_paths.append(out_path)

        if layout in ("a4", "a4_pdf", "both", "both_pdf"):
            pil_list = [pol for _, pol in polaroids_mem]
            a4_pages = make_a4_pages(pil_list)

            if layout in ("a4", "both"):
                for i, page in enumerate(a4_pages, 1):
                    out_path = os.path.join(output_dir, f"a4_page_{i:02d}.jpg")
                    page.save(out_path, "JPEG", quality=95)
                    output_paths.append(out_path)

            if layout in ("a4_pdf", "both_pdf"):
                if a4_pages:
                    pdf_path = os.path.join(output_dir, "a4_pages.pdf")
                    a4_pages[0].save(pdf_path, "PDF", resolution=300.0, save_all=True, append_images=a4_pages[1:])
                    output_paths.append(pdf_path)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in output_paths:
                zf.write(path, arcname=os.path.basename(path))
        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name="memories_to_print.zip",
        )

    finally:
        # Always clean up the per-request temp directory
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    app.run(debug=True)
