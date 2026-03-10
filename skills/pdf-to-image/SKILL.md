---
name: pdf-to-image
description: Convert PDF files to JPEG images with file size control. Use this skill whenever the user wants to convert PDF to image, PDF to JPEG/JPG/PNG, compress PDF pages as images, or needs images from PDF files at a specific file size (e.g. "250KB", "under 500KB"). Also trigger when the user mentions converting documents for upload portals, forms, or email attachments that require images instead of PDFs.
---

# PDF to JPEG Conversion

Convert one or more PDF files to JPEG images. Key features:
- Auto-detects the best available backend tool
- Binary-search quality tuning to hit a target file size
- Multi-page PDFs produce one JPEG per page
- Works on Linux, macOS, and Windows (WSL)

## Quick decision: script vs manual

**Use the helper script** (`scripts/pdf2jpeg.py`) when:
- Converting multiple files, OR
- The user wants a reusable command, OR
- Fine-grained size control is needed

**Use direct shell commands** (one-liner) when:
- Converting 1–2 files quickly with a known good setting

---

## Backend priority (auto-detected)

| Priority | Tool | How to install |
|----------|------|----------------|
| 1 | `gs` (Ghostscript) | `apt install ghostscript` / `brew install ghostscript` |
| 2 | `pdftoppm` + `convert` | `apt install poppler-utils imagemagick` |
| 3 | `pdftoppm` only | `apt install poppler-utils` |
| 4 | Python `pdf2image` | `pip install pdf2image` + `apt install poppler-utils` |
| 5 | Python `fitz` (PyMuPDF) | `pip install pymupdf` |

Always check which tools are available before proceeding:
```bash
which gs pdftoppm convert 2>/dev/null
python3 -c "import pdf2image" 2>/dev/null && echo "pdf2image ok"
python3 -c "import fitz" 2>/dev/null && echo "fitz ok"
```

---

## Using the helper script

```bash
# Basic usage — outputs alongside the source PDF, targets 250KB
python3 <skill-path>/scripts/pdf2jpeg.py input.pdf

# Custom target size and output directory
python3 <skill-path>/scripts/pdf2jpeg.py input.pdf \
    --target-kb 300 --tolerance-kb 40 --output-dir ./images/

# Batch: convert multiple PDFs
for f in *.pdf; do
    python3 <skill-path>/scripts/pdf2jpeg.py "$f" --target-kb 250
done
```

The script prints each output filename and its final size. Multi-page PDFs produce `stem_1.jpg`, `stem_2.jpg`, etc.

---

## Direct one-liner commands (no script)

Use when you have a quick single conversion. The size-control is manual — adjust `-r` (DPI) and quality together.

### Ghostscript (recommended)
```bash
# Single-page PDF → JPEG
gs -dNOPAUSE -dBATCH -dSAFER \
   -sDEVICE=jpeg -r120 -dJPEGQ=75 \
   -sOutputFile="output.jpg" input.pdf

# Multi-page PDF → one JPEG per page
gs -dNOPAUSE -dBATCH -dSAFER \
   -sDEVICE=jpeg -r120 -dJPEGQ=75 \
   -sOutputFile="output_%d.jpg" input.pdf
```

### pdftoppm + ImageMagick
```bash
pdftoppm -r 150 input.pdf /tmp/page
convert /tmp/page-1.ppm -quality 75 output.jpg
```

### pdftoppm (jpeg built-in)
```bash
pdftoppm -jpeg -r 150 -jpegopt quality=75 input.pdf output
# Produces: output-1.jpg, output-2.jpg, ...
```

---

## Size tuning guide

| Target | Recommended starting point |
|--------|---------------------------|
| ~100KB | `-r100 -dJPEGQ=65` |
| ~250KB | `-r120 -dJPEGQ=75` |
| ~500KB | `-r150 -dJPEGQ=80` |
| ~1MB   | `-r150 -dJPEGQ=90` |

If a file is still too large after lowering quality, reduce DPI (`-r`). If it's too small (sparse content), raise DPI first before raising quality.

The helper script handles this automatically via binary search.

---

## Workflow

1. **Check available tools** (see backend table above)
2. **Decide**: script (multiple files / size precision) or one-liner (quick single file)
3. **Run conversion** and report output paths + actual sizes to the user
4. If any output is far from the target, rerun with adjusted parameters or use the script's `--target-kb` flag

---

## Common issues

| Problem | Fix |
|---------|-----|
| `gs: command not found` | Install ghostscript, or fall back to pdftoppm |
| Output looks blurry | Increase DPI (e.g. `-r150` or `-r200`) |
| File still too large | Lower `-dJPEGQ` (e.g. 65) AND `-r` (e.g. 100) |
| Chinese/CJK text garbled | Ghostscript font issue — use `pdftoppm` or `fitz` instead |
| PDF is password-protected | `gs -sPDFPassword=xxx ...` or ask user for password |
| ImageMagick policy error | Edit `/etc/ImageMagick-*/policy.xml`, change PDF policy to `read\|write` |
