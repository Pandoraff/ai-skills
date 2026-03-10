# pdf-to-image

A Claude Code skill that converts PDF files to JPEG images with precise file size control.

## Features

- **Multi-backend support** — auto-detects the best available tool
- **Target size control** — binary-search over JPEG quality to hit your desired file size
- **Multi-page handling** — each page becomes a separate JPEG (`name_1.jpg`, `name_2.jpg`, ...)
- **Cross-platform** — works on Linux, macOS, and Windows (WSL)

## Backend priority

| Priority | Tool | Install |
|----------|------|---------|
| 1 | Ghostscript (`gs`) | `apt install ghostscript` / `brew install ghostscript` |
| 2 | `pdftoppm` + ImageMagick `convert` | `apt install poppler-utils imagemagick` |
| 3 | `pdftoppm` only | `apt install poppler-utils` |
| 4 | Python `pdf2image` | `pip install pdf2image` |
| 5 | Python `fitz` (PyMuPDF) | `pip install pymupdf` |

## Usage

### As a Claude Code skill

Install via Claude Code skill manager, then just ask:

> "把这几个 PDF 转成 JPEG，大小控制在 250KB 左右"

### Direct script usage

```bash
# Basic — outputs alongside source PDF, targets 250KB
python3 skills/pdf-to-image/scripts/pdf2jpeg.py input.pdf

# Custom target size
python3 skills/pdf-to-image/scripts/pdf2jpeg.py input.pdf --target-kb 300 --tolerance-kb 40

# Custom output directory
python3 skills/pdf-to-image/scripts/pdf2jpeg.py input.pdf --output-dir ./images/

# Batch conversion
for f in *.pdf; do
    python3 skills/pdf-to-image/scripts/pdf2jpeg.py "$f" --target-kb 250
done

# Force a specific backend
python3 skills/pdf-to-image/scripts/pdf2jpeg.py input.pdf --backend gs
```

### Script options

| Option | Default | Description |
|--------|---------|-------------|
| `--target-kb` | 250 | Target file size in KB |
| `--tolerance-kb` | 30 | Acceptable deviation in KB |
| `--output-dir` | same as input | Output directory |
| `--prefix` | input filename stem | Output filename prefix |
| `--dpi` | 150 | Rendering DPI |
| `--backend` | auto | Force backend: `gs`, `pdftoppm+convert`, `pdftoppm`, `pdf2image`, `fitz` |

## File structure

```
pdf-to-image/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest
├── skills/
│   └── pdf-to-image/
│       ├── SKILL.md          # Skill definition & instructions
│       └── scripts/
│           └── pdf2jpeg.py   # Conversion script
└── README.md
```
