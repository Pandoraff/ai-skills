#!/usr/bin/env python3
"""
compress_image.py - Compress images to a target file size.

Supports JPEG / PNG / WebP. Auto-detects available backends:
  1. Pillow (pip install Pillow)
  2. ImageMagick (convert)
  3. ffmpeg

Strategy: reduce JPEG quality first; if still too large, scale down + retry.

Usage:
  python3 compress_image.py image1.jpg image2.png [options]

Options:
  --target-kb N      Target file size in KB (default: 300)
  --tolerance-kb N   Acceptable overshoot in KB (default: 10)
  --min-quality N    Minimum JPEG quality allowed (default: 15)
  --min-scale N      Minimum resize scale, 0.1–1.0 (default: 0.3)
  --no-overwrite     Save as <name>_compressed.jpg instead of overwriting
  --backend NAME     Force backend: pillow | imagemagick | ffmpeg
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
from pathlib import Path


# ────────────────────────────────────────────────────────────
# Backend detection
# ────────────────────────────────────────────────────────────

def detect_backend(force=None):
    if force:
        return force
    try:
        from PIL import Image  # noqa: F401
        return "pillow"
    except ImportError:
        pass
    if shutil.which("convert"):
        return "imagemagick"
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    return None


# ────────────────────────────────────────────────────────────
# Pillow backend
# ────────────────────────────────────────────────────────────

def _pil_encode(img, fmt, quality):
    buf = io.BytesIO()
    save_kwargs = {"format": fmt, "optimize": True}
    if fmt in ("JPEG", "WEBP"):
        save_kwargs["quality"] = quality
    img.save(buf, **save_kwargs)
    return buf.getvalue()


def compress_pillow(path, target, tolerance, min_quality, min_scale):
    from PIL import Image

    img = Image.open(path)
    orig_mode = img.mode
    ext = Path(path).suffix.lower()
    fmt = "JPEG" if ext in (".jpg", ".jpeg") else ("PNG" if ext == ".png" else "WEBP")

    if fmt == "PNG":
        # For PNG: try optimize first, then convert to JPEG
        buf = _pil_encode(img, "PNG", quality=9)
        if len(buf) <= target + tolerance * 1024:
            return buf, "PNG optimize"
        # Convert to JPEG for better compression
        fmt = "JPEG"
        ext = ".jpg"

    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    orig_w, orig_h = img.size

    # Phase 1: quality reduction at original size
    for quality in range(85, min_quality - 1, -5):
        data = _pil_encode(img, fmt, quality)
        if len(data) <= target + tolerance * 1024:
            return data, f"quality={quality}"

    # Phase 2: resize + quality
    for scale in [0.8, 0.7, 0.6, 0.5, 0.45, 0.4, 0.35, min_scale]:
        nw, nh = int(orig_w * scale), int(orig_h * scale)
        resized = img.resize((nw, nh), Image.LANCZOS)
        for quality in [80, 65, 50, 35, min_quality]:
            data = _pil_encode(resized, fmt, quality)
            if len(data) <= target + tolerance * 1024:
                return data, f"scale={scale:.0%},q={quality} ({nw}×{nh})"

    return None, "failed"


# ────────────────────────────────────────────────────────────
# ImageMagick backend
# ────────────────────────────────────────────────────────────

def compress_imagemagick(path, target, tolerance, min_quality, min_scale):
    target_kb = (target + tolerance * 1024) // 1024

    # Phase 1: quality only
    for quality in range(85, min_quality - 1, -5):
        tmp = path + ".cimg_tmp.jpg"
        subprocess.run(
            ["convert", "-quality", str(quality), str(path), tmp],
            capture_output=True, check=True
        )
        size = os.path.getsize(tmp)
        if size <= target + tolerance * 1024:
            data = Path(tmp).read_bytes()
            os.remove(tmp)
            return data, f"quality={quality}"
        os.remove(tmp)

    # Phase 2: resize + quality
    orig_w, orig_h = _imagemagick_size(path)
    for scale in [0.8, 0.7, 0.6, 0.5, 0.4, min_scale]:
        nw, nh = int(orig_w * scale), int(orig_h * scale)
        for quality in [80, 60, 40, min_quality]:
            tmp = path + ".cimg_tmp.jpg"
            subprocess.run(
                ["convert", "-resize", f"{nw}x{nh}", "-quality", str(quality), str(path), tmp],
                capture_output=True, check=True
            )
            size = os.path.getsize(tmp)
            if size <= target + tolerance * 1024:
                data = Path(tmp).read_bytes()
                os.remove(tmp)
                return data, f"scale={scale:.0%},q={quality} ({nw}×{nh})"
            os.remove(tmp)

    return None, "failed"


def _imagemagick_size(path):
    result = subprocess.run(
        ["identify", "-format", "%w %h", str(path)],
        capture_output=True, text=True
    )
    w, h = result.stdout.strip().split()
    return int(w), int(h)


# ────────────────────────────────────────────────────────────
# ffmpeg backend
# ────────────────────────────────────────────────────────────

def compress_ffmpeg(path, target, tolerance, min_quality, min_scale):
    # ffmpeg uses q:v 1 (best) to 31 (worst) for JPEG
    for q in [3, 5, 8, 12, 18, 24, 31]:
        tmp = path + ".cimg_tmp.jpg"
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(path), "-q:v", str(q), tmp],
            capture_output=True, check=True
        )
        size = os.path.getsize(tmp)
        if size <= target + tolerance * 1024:
            data = Path(tmp).read_bytes()
            os.remove(tmp)
            return data, f"ffmpeg q={q}"
        os.remove(tmp)

    return None, "failed"


# ────────────────────────────────────────────────────────────
# Main
# ────────────────────────────────────────────────────────────

def process_file(path, backend, target, tolerance, min_quality, min_scale, no_overwrite):
    orig_size = os.path.getsize(path)
    target_bytes = target * 1024

    if orig_size <= target_bytes + tolerance * 1024:
        return orig_size, orig_size, "already ok", str(path)

    if backend == "pillow":
        data, method = compress_pillow(path, target_bytes, tolerance, min_quality, min_scale)
    elif backend == "imagemagick":
        data, method = compress_imagemagick(path, target_bytes, tolerance, min_quality, min_scale)
    elif backend == "ffmpeg":
        data, method = compress_ffmpeg(path, target_bytes, tolerance, min_quality, min_scale)
    else:
        return orig_size, None, "no backend", str(path)

    if data is None:
        return orig_size, None, method, str(path)

    p = Path(path)
    if no_overwrite:
        out_path = p.parent / (p.stem + "_compressed.jpg")
    else:
        out_path = p

    out_path.write_bytes(data)
    return orig_size, len(data), method, str(out_path)


def main():
    parser = argparse.ArgumentParser(
        description="Compress images to a target file size",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("files", nargs="+", help="Image files to compress")
    parser.add_argument("--target-kb", type=int, default=300, help="Target KB (default: 300)")
    parser.add_argument("--tolerance-kb", type=int, default=10, help="Tolerance KB (default: 10)")
    parser.add_argument("--min-quality", type=int, default=15, help="Min JPEG quality (default: 15)")
    parser.add_argument("--min-scale", type=float, default=0.3, help="Min resize scale (default: 0.3)")
    parser.add_argument("--no-overwrite", action="store_true", help="Save as *_compressed.jpg")
    parser.add_argument("--backend", choices=["pillow", "imagemagick", "ffmpeg"],
                        default=None, help="Force backend")
    args = parser.parse_args()

    backend = detect_backend(args.backend)
    if backend is None:
        print("ERROR: No image backend found.", file=sys.stderr)
        print("Install Pillow:  pip install Pillow", file=sys.stderr)
        print("or ImageMagick:  apt install imagemagick", file=sys.stderr)
        sys.exit(1)

    print(f"Backend: {backend} | Target: {args.target_kb}KB ± {args.tolerance_kb}KB\n")
    print(f"{'File':<45} {'Before':>8} {'After':>8}  {'Method'}")
    print("─" * 85)

    exit_code = 0
    for f in args.files:
        if not os.path.exists(f):
            print(f"{'  ' + f:<45} {'NOT FOUND':>8}")
            exit_code = 1
            continue

        orig, new, method, out_path = process_file(
            f, backend,
            args.target_kb, args.tolerance_kb,
            args.min_quality, args.min_scale,
            args.no_overwrite
        )

        name = os.path.basename(out_path)
        if new is None:
            status = "✗ FAIL"
            exit_code = 1
            print(f"  {name:<43} {orig/1024:>7.1f}K {'FAIL':>8}  {method}")
        elif method == "already ok":
            print(f"  {name:<43} {orig/1024:>7.1f}K {'—':>8}  ✓ {method}")
        else:
            mark = "✓" if new <= (args.target_kb + args.tolerance_kb) * 1024 else "~"
            print(f"  {name:<43} {orig/1024:>7.1f}K {new/1024:>7.1f}K  {mark} {method}")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
