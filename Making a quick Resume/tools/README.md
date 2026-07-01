# HTML vs Typst Resume Checker (visual-first)

Compares rendered A4 portrait output — not source code.

## Setup

```powershell
pip install -r tools/requirements-compare.txt
python -m playwright install chromium
```

## Run

```powershell
python tools/compare_html_typst.py
# or
compare.bat
```

## How it works

1. **HTML** — Chromium print-to-PDF (`format=A4`, zero margins, local fonts injected) → PNG
2. **Typst** — existing PDF page 1 → PNG at same DPI
3. Both PNGs validated as A4 portrait (`210:297` aspect, expected pixel size)
4. **Pixel diff** overall + per region (header, sidebar, main, etc.)
5. **Fix advice** — uses diff regions + HTML CSS / Typst source *only* to suggest Typst changes

## Output (`tools/output/`)

| File | Purpose |
|------|---------|
| `html_render.png` | A4 HTML print render |
| `pdf_render.png` | A4 Typst PDF render |
| `visual_diff.png` | Red = pixels that differ |
| `regions.png` | Diff % overlaid on layout regions |
| `report.json` | Machine-readable results + advice |

## Pass criteria

- Both renders are valid A4 portrait
- Overall pixel diff <= tolerance (default 2%)

## Options

```
--dpi 150          Render resolution (default 150 → 1240×1754px)
--tolerance 2.0    Max allowed pixel diff %
```
