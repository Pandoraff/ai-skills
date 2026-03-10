#!/usr/bin/env python3
"""
pdf2jpeg.py - Convert PDF to JPEG with target file size control.

Supports multiple backends (auto-detected):
  1. Ghostscript (gs)
  2. pdftoppm + ImageMagick convert
  3. pdftoppm (built-in jpeg output)
  4. pdf2image (Python library)
  5. PyMuPDF / fitz (Python library)

Usage:
  python3 pdf2jpeg.py input.pdf [options]

Options:
  --output-dir DIR     Output directory (default: same as input)
  --target-kb N        Target file size in KB (default: 250)
  --tolerance N        Acceptable deviation in KB (default: 30)
  --dpi N              Starting DPI hint (default: auto)
  --prefix NAME        Output filename prefix (default: input filename stem)
  --backend NAME       Force a specific backend (gs|pdftoppm|pdf2image|fitz)
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


# --------------------------------------------------------------------------- #
# Backend detection
# --------------------------------------------------------------------------- #

def has_cmd(name):
    return shutil.which(name) is not None


def detect_backend(force=None):
    """Return the best available backend name."""
    if force:
        return force
    if has_cmd("gs"):
        return "gs"
    if has_cmd("pdftoppm") and has_cmd("convert"):
        return "pdftoppm+convert"
    if has_cmd("pdftoppm"):
        return "pdftoppm"
    try:
        import pdf2image  # noqa: F401
        return "pdf2image"
    except ImportError:
        pass
    try:
        import fitz  # noqa: F401
        return "fitz"
    except ImportError:
        pass
    return None


# --------------------------------------------------------------------------- #
# Render helpers — each returns a list of paths to temporary PPM/PNG/JPEG files
# --------------------------------------------------------------------------- #

def render_gs(pdf_path, dpi, tmp_dir):
    """Render all pages with Ghostscript → PPM files."""
    out_pattern = os.path.join(tmp_dir, "page_%04d.ppm")
    cmd = [
        "gs", "-dNOPAUSE", "-dBATCH", "-dSAFER",
        "-sDEVICE=ppmraw", f"-r{dpi}",
        f"-sOutputFile={out_pattern}", str(pdf_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(Path(tmp_dir).glob("page_*.ppm"))


def render_pdftoppm(pdf_path, dpi, tmp_dir):
    """Render all pages with pdftoppm → PPM files."""
    prefix = os.path.join(tmp_dir, "page")
    cmd = ["pdftoppm", "-r", str(dpi), str(pdf_path), prefix]
    subprocess.run(cmd, check=True, capture_output=True)
    return sorted(Path(tmp_dir).glob("page-*.ppm"))


def render_pdf2image(pdf_path, dpi, tmp_dir):
    """Render with pdf2image → PIL Images (saved as temp PNG)."""
    from pdf2image import convert_from_path
    images = convert_from_path(str(pdf_path), dpi=dpi)
    paths = []
    for i, img in enumerate(images):
        p = Path(tmp_dir) / f"page_{i+1:04d}.png"
        img.save(str(p), "PNG")
        paths.append(p)
    return paths


def render_fitz(pdf_path, dpi, tmp_dir):
    """Render with PyMuPDF → PNG files."""
    import fitz
    doc = fitz.open(str(pdf_path))
    paths = []
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat)
        p = Path(tmp_dir) / f"page_{i+1:04d}.png"
        pix.save(str(p))
        paths.append(p)
    return paths


# --------------------------------------------------------------------------- #
# JPEG save — works for both PIL-loadable files and raw PPM via ImageMagick
# --------------------------------------------------------------------------- #

def save_jpeg_pil(src_path, dst_path, quality):
    from PIL import Image
    img = Image.open(str(src_path)).convert("RGB")
    img.save(str(dst_path), "JPEG", quality=quality, optimize=True)


def save_jpeg_convert(src_path, dst_path, quality):
    """Use ImageMagick convert as fallback JPEG encoder."""
    cmd = ["convert", str(src_path), "-quality", str(quality), str(dst_path)]
    subprocess.run(cmd, check=True, capture_output=True)


def save_jpeg_gs_direct(pdf_path, page_num, dpi, quality, dst_path, total_pages):
    """Use Ghostscript to render + encode a single page directly to JPEG."""
    cmd = [
        "gs", "-dNOPAUSE", "-dBATCH", "-dSAFER",
        "-sDEVICE=jpeg", f"-r{dpi}", f"-dJPEGQ={quality}",
        f"-dFirstPage={page_num}", f"-dLastPage={page_num}",
        f"-sOutputFile={dst_path}", str(pdf_path)
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def _has_pil():
    try:
        import PIL  # noqa: F401
        return True
    except ImportError:
        return False


# --------------------------------------------------------------------------- #
# Binary-search quality tuning
# --------------------------------------------------------------------------- #

def tune_quality(render_fn, dst_path, target_bytes, tolerance_bytes):
    """
    Binary search over JPEG quality [10, 95] to hit target ± tolerance.
    render_fn(quality) → writes JPEG to dst_path, returns file size in bytes.
    Returns final file size.
    """
    lo, hi = 10, 95
    best_size = None
    best_quality = 75

    for _ in range(8):  # max 8 iterations → precision < 1 quality unit
        mid = (lo + hi) // 2
        size = render_fn(mid)
        if abs(size - target_bytes) <= tolerance_bytes:
            best_size = size
            best_quality = mid
            break
        if size > target_bytes:
            hi = mid - 1
        else:
            lo = mid + 1
        # track closest so far
        if best_size is None or abs(size - target_bytes) < abs(best_size - target_bytes):
            best_size = size
            best_quality = mid

    # Final render at best quality (already rendered if we broke early)
    render_fn(best_quality)
    return os.path.getsize(dst_path)


# --------------------------------------------------------------------------- #
# Main conversion logic
# --------------------------------------------------------------------------- #

def convert_pdf(pdf_path, output_dir, target_kb, tolerance_kb, dpi_hint, prefix, backend_name):
    pdf_path = Path(pdf_path).resolve()
    output_dir = Path(output_dir) if output_dir else pdf_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    target_bytes = target_kb * 1024
    tolerance_bytes = tolerance_kb * 1024

    backend = detect_backend(backend_name)
    if backend is None:
        print("ERROR: No supported PDF backend found.", file=sys.stderr)
        print("Install one of: ghostscript, poppler-utils, pdf2image, PyMuPDF", file=sys.stderr)
        sys.exit(1)

    print(f"Backend: {backend}")

    # Determine DPI: start with hint or auto (150 is a good default)
    dpi = dpi_hint or 150

    with tempfile.TemporaryDirectory() as tmp_dir:
        # ---------- Render pages ----------
        if backend == "gs":
            page_files = render_gs(pdf_path, dpi, tmp_dir)
        elif backend in ("pdftoppm+convert", "pdftoppm"):
            page_files = render_pdftoppm(pdf_path, dpi, tmp_dir)
        elif backend == "pdf2image":
            page_files = render_pdf2image(pdf_path, dpi, tmp_dir)
        elif backend == "fitz":
            page_files = render_fitz(pdf_path, dpi, tmp_dir)
        else:
            print(f"ERROR: Unknown backend '{backend}'", file=sys.stderr)
            sys.exit(1)

        n_pages = len(page_files)
        if n_pages == 0:
            print("ERROR: No pages rendered from PDF.", file=sys.stderr)
            sys.exit(1)

        # ---------- Encode each page to JPEG ----------
        for i, src in enumerate(page_files):
            page_num = i + 1
            if n_pages == 1:
                out_name = f"{prefix}.jpg"
            else:
                out_name = f"{prefix}_{page_num}.jpg"
            dst = output_dir / out_name

            # Choose JPEG encoder
            use_pil = _has_pil()
            use_convert = has_cmd("convert")

            def render_fn(quality, _src=src, _dst=dst):
                if use_pil:
                    save_jpeg_pil(_src, _dst, quality)
                elif use_convert:
                    save_jpeg_convert(_src, _dst, quality)
                else:
                    # gs can encode from PPM if we just call convert via gs
                    # Fallback: write PPM as-is (no size tuning possible)
                    import shutil as _sh
                    _sh.copy(_src, _dst)
                return os.path.getsize(_dst)

            final_size = tune_quality(render_fn, dst, target_bytes, tolerance_bytes)
            print(f"  Page {page_num}/{n_pages}: {dst.name}  ({final_size // 1024}KB)")

    print("Done.")


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main():
    parser = argparse.ArgumentParser(description="Convert PDF to JPEG with target size control")
    parser.add_argument("pdf", help="Input PDF file")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--target-kb", type=int, default=250, help="Target size in KB (default: 250)")
    parser.add_argument("--tolerance-kb", type=int, default=30, help="Size tolerance in KB (default: 30)")
    parser.add_argument("--dpi", type=int, default=None, help="Rendering DPI (default: auto 150)")
    parser.add_argument("--prefix", default=None, help="Output filename prefix")
    parser.add_argument("--backend", default=None,
                        choices=["gs", "pdftoppm+convert", "pdftoppm", "pdf2image", "fitz"],
                        help="Force backend")
    args = parser.parse_args()

    prefix = args.prefix or Path(args.pdf).stem
    convert_pdf(
        pdf_path=args.pdf,
        output_dir=args.output_dir,
        target_kb=args.target_kb,
        tolerance_kb=args.tolerance_kb,
        dpi_hint=args.dpi,
        prefix=prefix,
        backend_name=args.backend,
    )


if __name__ == "__main__":
    main()
