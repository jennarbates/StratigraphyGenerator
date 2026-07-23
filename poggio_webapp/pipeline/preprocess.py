"""
preprocess.py — clean an archival trench-drawing scan so a vision model (or a
human) can resolve the boundary lines more accurately.

Adapted from the original CLI script into an importable function for the web
app. Logic is unchanged; only the entry point differs (function call instead
of argparse), so results match the original CLI byte-for-byte given the same
inputs.
"""

import os
import cv2
import numpy as np


def recommend_upscale(width, height, target_dim=3000):
    """Suggest an upscale factor that lands the image's longest side near
    `target_dim` pixels.

    Rationale: preprocessing's upscale exists to keep thin boundary lines
    from vanishing on LOW-DPI scans -- it has no benefit on an
    already-high-res photo, and extraction caps the longest side to
    MAX_SEND_DIMENSION (see extract_illustrator.py / extract_fieldwall.py)
    before sending to Gemini regardless. Landing near that same target means
    preprocessing's upscale doesn't do work that just gets undone again a
    step later, while a genuinely low-res scan still gets real help.
    Returned factor is clamped to [1.0, 4.0] and rounded to the nearest 0.5
    (preprocess.py never recommends downscaling below 1x here, even though
    cv2.resize would technically support it, since shrinking is not this
    stage's job).
    """
    max_dim = max(width, height) or 1
    factor = target_dim / max_dim
    factor = max(1.0, min(4.0, factor))
    factor = round(factor * 2) / 2
    if max_dim < 1500:
        reason = ("low-resolution scan -- a higher upscale helps keep thin "
                   "boundary lines from vanishing before extraction.")
    elif max_dim < target_dim:
        reason = "moderate resolution -- a modest upscale can help a bit."
    else:
        reason = ("already high-resolution -- little upscale needed; "
                   "extraction downsizes to at most 3072px on the longest "
                   "side before sending to Gemini anyway, so scaling up "
                   "further just adds processing time with no real detail "
                   "gained.")
    return {"factor": factor, "reason": reason}


def probe_dimensions(path):
    """Cheap dimension read (no full pixel decode) for non-PDF images."""
    from PIL import Image as _PILImage
    with _PILImage.open(path) as im:
        return im.size  # (width, height)


def load_image(path, pdf_dpi=300, pdf_page=1):
    """Load an input scan as a BGR array, transparently rasterizing PDFs."""
    if path.lower().endswith(".pdf"):
        try:
            from pdf2image import convert_from_path
        except ImportError:
            raise RuntimeError(
                "PDF input requires pdf2image (`pip install pdf2image "
                "--break-system-packages`) and poppler "
                "(`apt install poppler-utils`)."
            )
        pages = convert_from_path(path, dpi=pdf_dpi)
        if pdf_page < 1 or pdf_page > len(pages):
            raise RuntimeError(
                f"{path} has {len(pages)} page(s); page {pdf_page} "
                "is out of range."
            )
        pil_img = pages[pdf_page - 1].convert("RGB")
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    return cv2.imread(path)


def flatten_background(gray):
    """Divide out large-scale illumination/paper tone so faint ink is even."""
    bg = cv2.GaussianBlur(gray, (0, 0), sigmaX=25)
    bg = np.where(bg == 0, 1, bg)
    norm = (gray.astype(np.float32) / bg.astype(np.float32))
    norm = np.clip(norm * 200.0, 0, 255).astype(np.uint8)
    return norm


def deskew(gray):
    """Estimate small skew from near-horizontal strokes and rotate to correct."""
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=200)
    if lines is None:
        return gray, 0.0
    angles = []
    for rho_theta in lines[:200]:
        theta = rho_theta[0][1]
        deg = np.degrees(theta) - 90.0
        if -15 < deg < 15:
            angles.append(deg)
    if not angles:
        return gray, 0.0
    angle = float(np.median(angles))
    h, w = gray.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    rot = cv2.warpAffine(gray, M, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)
    return rot, angle


def clean(gray, upscale=2):
    """The recommended pipeline: flatten -> upscale -> CLAHE -> mild sharpen."""
    flat = flatten_background(gray)
    if upscale and upscale != 1:
        flat = cv2.resize(flat, None, fx=upscale, fy=upscale,
                           interpolation=cv2.INTER_LANCZOS4)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    eq = clahe.apply(flat)
    blur = cv2.GaussianBlur(eq, (0, 0), sigmaX=1.2)
    sharp = cv2.addWeighted(eq, 1.5, blur, -0.5, 0)
    return sharp


def high_contrast(gray, upscale=2):
    """Aggressive binarization for BOUNDARY TRACING ONLY (destroys fine fills)."""
    flat = flatten_background(gray)
    if upscale and upscale != 1:
        flat = cv2.resize(flat, None, fx=upscale, fy=upscale,
                           interpolation=cv2.INTER_LANCZOS4)
    binimg = cv2.adaptiveThreshold(
        flat, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=25, C=10)
    return binimg


def run_preprocess(input_path, outdir, upscale=2.0, deskew_flag=False,
                    highcontrast=False, pdf_dpi=300, pdf_page=1):
    """Run the full preprocess stage. Returns a dict describing outputs."""
    img = load_image(input_path, pdf_dpi=pdf_dpi, pdf_page=pdf_page)
    if img is None:
        raise RuntimeError(f"could not read {input_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    skew = 0.0
    if deskew_flag:
        gray, skew = deskew(gray)

    os.makedirs(outdir, exist_ok=True)
    name = os.path.splitext(os.path.basename(input_path))[0]

    clean_img = clean(gray, upscale=upscale)
    clean_path = os.path.join(outdir, f"{name}_clean.png")
    cv2.imwrite(clean_path, clean_img)

    outputs = {"clean": clean_path}
    if highcontrast:
        hc = high_contrast(gray, upscale=upscale)
        hc_path = os.path.join(outdir, f"{name}_highcontrast.png")
        cv2.imwrite(hc_path, hc)
        outputs["highcontrast"] = hc_path

    return {"deskew_angle": skew, "outputs": outputs}
