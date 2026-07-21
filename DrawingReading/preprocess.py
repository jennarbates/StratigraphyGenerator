"""
preprocess.py — clean an archival trench-drawing scan so a vision model (or a
human) can resolve the boundary lines more accurately.

Usage:
    python preprocess.py input.png [--outdir preprocessed] [--upscale 2]
                         [--deskew] [--highcontrast]

What it does (non-destructive — writes new files, never edits the original):
  1. Grayscale + background flattening: removes uneven paper tone / yellowing so
     faint ink stands out evenly across the sheet.
  2. Upscale (default 2x, Lanczos): low-DPI scans lose thin lines; enlarging
     before the model sees them recovers detail. (Doesn't add real information,
     but keeps thin strokes from vanishing.)
  3. Gentle local contrast (CLAHE) + mild sharpen: makes boundary strokes crisp
     WITHOUT destroying the fill hatching that distinguishes materials.
  4. Optional --deskew: straightens a slightly rotated scan.
  5. Optional --highcontrast: an extra, more aggressive binarized version for
     boundary tracing ONLY. Do NOT feed this to the material-ID step — it can
     wipe out subtle fill patterns. Provided as a separate file.

Outputs (in --outdir):
    <name>_clean.png    <- recommended input for the LLM (keeps fills + clearer)
    <name>_highcontrast.png  (only with --highcontrast; boundaries only)

Design note: the "clean" image intentionally preserves fill texture, because the
model still needs stippling/hatching to identify materials. The aggressive
version is separate so you never accidentally destroy that signal.
"""

import argparse
import os
import cv2
import numpy as np


def flatten_background(gray):
    """Divide out large-scale illumination/paper tone so faint ink is even."""
    # Large Gaussian ~ the paper/background; dividing normalizes it out.
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
        deg = np.degrees(theta) - 90.0     # deviation from horizontal
        if -15 < deg < 15:                 # only near-horizontal lines
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
    # unsharp mask: sharpen strokes gently
    blur = cv2.GaussianBlur(eq, (0, 0), sigmaX=1.2)
    sharp = cv2.addWeighted(eq, 1.5, blur, -0.5, 0)
    return sharp


def high_contrast(gray, upscale=2):
    """Aggressive binarization for BOUNDARY TRACING ONLY (destroys fine fills)."""
    flat = flatten_background(gray)
    if upscale and upscale != 1:
        flat = cv2.resize(flat, None, fx=upscale, fy=upscale,
                          interpolation=cv2.INTER_LANCZOS4)
    # adaptive threshold copes with any residual uneven lighting
    binimg = cv2.adaptiveThreshold(
        flat, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, blockSize=25, C=10)
    return binimg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--outdir", default="preprocessed")
    ap.add_argument("--upscale", type=float, default=2.0)
    ap.add_argument("--deskew", action="store_true")
    ap.add_argument("--highcontrast", action="store_true")
    args = ap.parse_args()

    img = cv2.imread(args.input)
    if img is None:
        raise SystemExit(f"could not read {args.input}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    skew = 0.0
    if args.deskew:
        gray, skew = deskew(gray)

    os.makedirs(args.outdir, exist_ok=True)
    name = os.path.splitext(os.path.basename(args.input))[0]

    clean_img = clean(gray, upscale=args.upscale)
    clean_path = os.path.join(args.outdir, f"{name}_clean.png")
    cv2.imwrite(clean_path, clean_img)

    outputs = [clean_path]
    if args.highcontrast:
        hc = high_contrast(gray, upscale=args.upscale)
        hc_path = os.path.join(args.outdir, f"{name}_highcontrast.png")
        cv2.imwrite(hc_path, hc)
        outputs.append(hc_path)

    print(f"deskew angle applied: {skew:.2f} deg")
    print("wrote:")
    for o in outputs:
        print("  ", o)
    print("\nFeed the *_clean.png to the extraction script (it keeps fill "
          "patterns). Use *_highcontrast.png only for boundary tracing.")


if __name__ == "__main__":
    main()