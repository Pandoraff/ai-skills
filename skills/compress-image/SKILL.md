---
name: compress-image
description: 'Compress one or more images to a target file size. Use when user asks to compress images, reduce image size, or mentions "/compress-image". Supports JPEG/PNG/WebP, batch compression, custom target sizes, and auto-detects available tools (Pillow, ImageMagick, ffmpeg).'
license: MIT
allowed-tools: Bash
---

# Image Compression Skill

## Objective

Compress images to fit within a target file size while preserving maximum visual quality. Execute in **one single Bash call** using the embedded Python script.

## Execution Rules

- **ONE Bash call only** — embed the full script inline, do not split into multiple steps
- Parse all arguments from `$ARGUMENTS` before running
- Overwrite originals in place (no backup copies unless user requests)
- Print a concise result table at the end

## Argument Parsing

From `$ARGUMENTS`, extract:
- **File paths**: any path-like tokens (absolute or relative, space/newline separated)
- **Target size**: number followed by `k`/`kb`/`KB` → bytes = N×1024; `m`/`mb`/`MB` → N×1024²; bare number → treat as KB; default = **300KB**

Examples:
- `/path/to/a.jpg /path/to/b.png 250k` → target 256000 bytes
- `img1.jpg img2.jpg 1.5mb` → target 1572864 bytes
- `photo.jpeg` → target 307200 bytes (default 300KB)

## Script Template

Replace `FILES` and `TARGET_BYTES` with parsed values, then run as one Bash call:

```python
import sys, os, io, subprocess

FILES = ["/abs/path/file1.jpg", "/abs/path/file2.png"]  # ← fill in
TARGET = 300 * 1024  # ← fill in (bytes)

def get_backend():
    try:
        from PIL import Image
        return "pillow"
    except ImportError:
        pass
    if subprocess.run(["convert", "--version"], capture_output=True).returncode == 0:
        return "imagemagick"
    if subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0:
        return "ffmpeg"
    return None

def compress_pillow(path, target):
    from PIL import Image
    img = Image.open(path)
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    ext = os.path.splitext(path)[1].lower()
    fmt = "JPEG" if ext in (".jpg", ".jpeg") else ("PNG" if ext == ".png" else "JPEG")
    # Try quality reduction first
    for q in [85, 75, 65, 55, 45, 35, 25, 15]:
        buf = io.BytesIO()
        img.save(buf, format=fmt, quality=q, optimize=True)
        if buf.tell() <= target:
            with open(path, "wb") as f: f.write(buf.getvalue())
            return buf.tell(), "quality=" + str(q), img.size
    # Then resize + quality
    w, h = img.size
    for scale in [0.8, 0.7, 0.6, 0.5, 0.4, 0.35, 0.3]:
        nw, nh = int(w * scale), int(h * scale)
        r = img.resize((nw, nh), Image.LANCZOS)
        for q in [80, 65, 50, 35]:
            buf = io.BytesIO()
            r.save(buf, format=fmt, quality=q, optimize=True)
            if buf.tell() <= target:
                with open(path, "wb") as f: f.write(buf.getvalue())
                return buf.tell(), f"scale={scale:.0%},q={q}", (nw, nh)
    return None, "failed", img.size

def compress_imagemagick(path, target):
    orig = os.path.getsize(path)
    for q in [85, 70, 55, 40, 25]:
        tmp = path + ".tmp.jpg"
        subprocess.run(["convert", "-quality", str(q), path, tmp], capture_output=True)
        if os.path.exists(tmp):
            s = os.path.getsize(tmp)
            if s <= target:
                os.replace(tmp, path)
                return s, "quality=" + str(q), None
            os.remove(tmp)
    return None, "failed", None

def compress_ffmpeg(path, target):
    for q in [3, 5, 8, 12, 18, 25]:
        tmp = path + ".tmp.jpg"
        subprocess.run(["ffmpeg", "-y", "-i", path, "-q:v", str(q), tmp], capture_output=True)
        if os.path.exists(tmp):
            s = os.path.getsize(tmp)
            if s <= target:
                os.replace(tmp, path)
                return s, "q=" + str(q), None
            os.remove(tmp)
    return None, "failed", None

backend = get_backend()
if not backend:
    print("ERROR: No image backend found. Install Pillow: pip install Pillow")
    sys.exit(1)

print(f"Backend: {backend} | Target: {TARGET/1024:.0f}KB\n")
print(f"{'File':<40} {'Before':>8} {'After':>8} {'Method':<20} {'Status'}")
print("-" * 90)

for path in FILES:
    if not os.path.exists(path):
        print(f"{os.path.basename(path):<40} {'N/A':>8} {'N/A':>8} {'file not found':<20}")
        continue
    orig = os.path.getsize(path)
    if orig <= TARGET:
        print(f"{os.path.basename(path):<40} {orig/1024:>7.1f}K {'—':>8} {'already ok':<20} ✓")
        continue
    if backend == "pillow":
        new_size, method, dims = compress_pillow(path, TARGET)
    elif backend == "imagemagick":
        new_size, method, dims = compress_imagemagick(path, TARGET)
    else:
        new_size, method, dims = compress_ffmpeg(path, TARGET)
    if new_size:
        status = "✓"
        dims_str = f" {dims[0]}×{dims[1]}" if dims else ""
        print(f"{os.path.basename(path):<40} {orig/1024:>7.1f}K {new_size/1024:>7.1f}K {method+dims_str:<20} {status}")
    else:
        print(f"{os.path.basename(path):<40} {orig/1024:>7.1f}K {'FAIL':>8} {method:<20} ✗")
```

## Output Format

After running, show only the printed table. No extra commentary needed.
