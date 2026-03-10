---
name: compress-image
description: 'Compress one or more images to a target file size. Use when user asks to compress images, reduce image size, or mentions "/compress-image". Supports JPEG/PNG/WebP, batch compression, custom target sizes, auto-detects Pillow / ImageMagick / ffmpeg.'
license: MIT
allowed-tools: Bash
---

# Image Compression Skill

Compress images to a target file size using `scripts/compress_image.py`.

## Quick decision: script vs one-liner

**Use the script** (default) for all cases — single file, batch, or size-controlled compression.

**Use a one-liner** only when the user explicitly wants a quick shell command without the script.

---

## Script location

The script lives at `scripts/compress_image.py` relative to this SKILL.md.

Resolve the absolute path at runtime:

```bash
SKILL_DIR=$(python3 -c "
import subprocess, json
skills_out = subprocess.check_output(['claude', 'skills', 'list', '--json'], text=True)
# fallback: well-known location
print('$HOME/.claude/skills/compress-image')
" 2>/dev/null || echo "$HOME/.claude/skills/compress-image")
SCRIPT="$SKILL_DIR/scripts/compress_image.py"
```

Or simply hard-code the known path:
```bash
SCRIPT="$HOME/.claude/skills/compress-image/scripts/compress_image.py"
```

---

## Argument parsing

From user message, extract:

| Token pattern | Meaning |
|---|---|
| Path-like strings | Input files (absolute or relative) |
| `250k` / `250kb` / `250KB` | Target = 250 KB |
| `1.5m` / `1.5mb` / `1.5MB` | Target = 1536 KB |
| Bare number, e.g. `300` | Target = 300 KB |
| No size given | Default 300 KB |

---

## Execution — ONE Bash call

```bash
python3 "$HOME/.claude/skills/compress-image/scripts/compress_image.py" \
  "/abs/path/file1.jpg" "/abs/path/file2.png" \
  --target-kb 250
```

Add flags as needed:

| Flag | Default | Purpose |
|---|---|---|
| `--target-kb N` | 300 | Target file size in KB |
| `--tolerance-kb N` | 10 | Allowed overshoot in KB |
| `--min-quality N` | 15 | Min JPEG quality before giving up |
| `--min-scale N` | 0.3 | Min resize ratio (0.1–1.0) |
| `--no-overwrite` | off | Save as `*_compressed.jpg` instead of overwriting |
| `--backend pillow\|imagemagick\|ffmpeg` | auto | Force a specific backend |

---

## Output

The script prints a result table. Show it to the user as-is — no extra commentary needed.
