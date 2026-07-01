#!/usr/bin/env python3
"""Visual-first HTML vs Typst resume checker.

Renders BOTH documents to A4 portrait PNGs (HTML via print PDF, Typst via PDF)
then compares pixels. Source files are used only to suggest Typst fixes.

Usage:
  python compare_html_typst.py
  python compare_html_typst.py --dpi 150 --tolerance 2.0

Requires: pip install -r requirements-compare.txt && python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
RESUME_DIR = TOOLS_DIR.parent
FONTS_DIR = RESUME_DIR / "fonts"
DEFAULT_HTML = RESUME_DIR / "Dylan_General_Resume.html"
DEFAULT_TYP = RESUME_DIR / "Dylan_General_Resume.typ"
DEFAULT_PDF = RESUME_DIR / "Dylan_General_Resume.pdf"
OUTPUT_DIR = TOOLS_DIR / "output"

# A4 portrait (ISO 216)
A4_WIDTH_MM = 210.0
A4_HEIGHT_MM = 297.0
A4_ASPECT = A4_WIDTH_MM / A4_HEIGHT_MM  # ~0.707


@dataclass
class RenderInfo:
    source: str
    path: str
    width_px: int
    height_px: int
    dpi: int
    page_count: int
    a4_valid: bool
    aspect_ratio: float
    notes: list[str] = field(default_factory=list)


@dataclass
class RegionResult:
    name: str
    diff_pct: float
    bbox: tuple[int, int, int, int]  # x0, y0, x1, y1 in pixels


@dataclass
class FixAdvice:
    region: str
    severity: str  # high | medium | low
    issue: str
    typst_hint: str
    reference: str  # HTML CSS selector / property for reverse-engineering


@dataclass
class Report:
    html: str
    typst: str
    pdf: str
    dpi: int
    html_render: RenderInfo | None = None
    pdf_render: RenderInfo | None = None
    overall_diff_pct: float = 0.0
    regions: list[RegionResult] = field(default_factory=list)
    advice: list[FixAdvice] = field(default_factory=list)
    passed: bool = False


def a4_pixels(dpi: int) -> tuple[int, int]:
    w = round(A4_WIDTH_MM / 25.4 * dpi)
    h = round(A4_HEIGHT_MM / 25.4 * dpi)
    return w, h


def validate_a4(width: int, height: int, tolerance: float = 0.02) -> tuple[bool, float, list[str]]:
    notes: list[str] = []
    if width <= 0 or height <= 0:
        return False, 0.0, ["zero or negative dimensions"]
    aspect = width / height
    expected = A4_ASPECT
    aspect_ok = abs(aspect - expected) / expected <= tolerance
    if not aspect_ok:
        notes.append(
            f"aspect ratio {aspect:.4f} != A4 portrait {expected:.4f} "
            f"(got {width}x{height}px — likely not true A4)"
        )
    return aspect_ok, aspect, notes


def font_face_css(fonts_dir: Path) -> str:
    """Inject local fonts so HTML print matches bundled Typst fonts."""
    faces = [
        ("Lato", "Lato-Regular.ttf", "400", "normal"),
        ("Lato", "Lato-Bold.ttf", "700", "normal"),
        ("Cormorant Garamond", "CormorantGaramond-SemiBold.ttf", "600", "normal"),
        ("JetBrains Mono", "JetBrainsMono-Regular.ttf", "400", "normal"),
        ("JetBrains Mono", "JetBrainsMono-Medium.ttf", "500", "normal"),
    ]
    blocks = []
    for family, file, weight, style in faces:
        p = (fonts_dir / file).resolve().as_uri()
        blocks.append(
            f"@font-face {{ font-family: '{family}'; src: url('{p}') format('truetype'); "
            f"font-weight: {weight}; font-style: {style}; }}"
        )
    return "\n".join(blocks)


def render_html_a4_pdf(html_path: Path, out_pdf: Path, fonts_dir: Path) -> None:
    from playwright.sync_api import sync_playwright

    inject = font_face_css(fonts_dir) + """
    @page { size: A4 portrait; margin: 0; }
    html, body {
      margin: 0 !important; padding: 0 !important;
      background: white !important;
      width: 210mm !important;
    }
    .page {
      width: 210mm !important;
      min-height: 297mm !important;
      max-height: 297mm !important;
      margin: 0 !important;
      box-shadow: none !important;
      overflow: hidden !important;
    }
    """
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.add_style_tag(content=inject)
        page.wait_for_timeout(1200)
        page.pdf(
            path=str(out_pdf),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        browser.close()


def pdf_to_png(pdf_path: Path, dpi: int, page_index: int = 0):
    import fitz
    from PIL import Image

    doc = fitz.open(pdf_path)
    if page_index >= len(doc):
        page_index = 0
    page_count = len(doc)
    page = doc[page_index]
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    w_pt, h_pt = page.rect.width, page.rect.height
    doc.close()
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img, page_count, w_pt, h_pt


def crop_to_a4(img, target_w: int, target_h: int):
    """Center-crop or pad to exact A4 pixel dimensions."""
    from PIL import Image

    w, h = img.size
    target_aspect = target_w / target_h
    current_aspect = w / h

    if abs(current_aspect - target_aspect) > 0.01:
        if current_aspect > target_aspect:
            new_w = int(h * target_aspect)
            left = (w - new_w) // 2
            img = img.crop((left, 0, left + new_w, h))
        else:
            new_h = int(w / target_aspect)
            top = (h - new_h) // 2
            img = img.crop((0, top, w, top + new_h))

    if img.size != (target_w, target_h):
        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
    return img


def render_html_a4_png(html_path: Path, dpi: int, out_dir: Path) -> tuple[Any, RenderInfo]:
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_pdf = out_dir / "_html_print.pdf"
    render_html_a4_pdf(html_path, tmp_pdf, FONTS_DIR)
    img, page_count, w_pt, h_pt = pdf_to_png(tmp_pdf, dpi, 0)
    target_w, target_h = a4_pixels(dpi)
    img = crop_to_a4(img, target_w, target_h)
    img.save(out_dir / "html_render.png")

    a4_ok, aspect, notes = validate_a4(img.width, img.height)
    notes.append(f"PDF page size: {w_pt:.1f}x{h_pt:.1f}pt (expect ~595x842pt)")
    if abs(w_pt - 595) > 5 or abs(h_pt - 842) > 5:
        notes.append("WARNING: HTML print PDF page is not standard A4 point size")

    info = RenderInfo(
        source="html",
        path=str(out_dir / "html_render.png"),
        width_px=img.width,
        height_px=img.height,
        dpi=dpi,
        page_count=page_count,
        a4_valid=a4_ok,
        aspect_ratio=aspect,
        notes=notes,
    )
    return img, info


def render_typst_a4_png(pdf_path: Path, dpi: int, out_dir: Path) -> tuple[Any, RenderInfo]:
    out_dir.mkdir(parents=True, exist_ok=True)
    img, page_count, w_pt, h_pt = pdf_to_png(pdf_path, dpi, 0)
    target_w, target_h = a4_pixels(dpi)
    img = crop_to_a4(img, target_w, target_h)
    img.save(out_dir / "pdf_render.png")

    a4_ok, aspect, notes = validate_a4(img.width, img.height)
    notes.append(f"PDF page size: {w_pt:.1f}x{h_pt:.1f}pt (expect ~595x842pt)")
    if page_count > 1:
        notes.append(f"WARNING: Typst PDF has {page_count} pages; comparing page 1 only")

    info = RenderInfo(
        source="typst_pdf",
        path=str(out_dir / "pdf_render.png"),
        width_px=img.width,
        height_px=img.height,
        dpi=dpi,
        page_count=page_count,
        a4_valid=a4_ok,
        aspect_ratio=aspect,
        notes=notes,
    )
    return img, info


def compute_diff(html_img, pdf_img, threshold: int = 20) -> tuple[float, Any, list[list[int]]]:
    from PIL import Image, ImageChops

    if html_img.size != pdf_img.size:
        pdf_img = pdf_img.resize(html_img.size, Image.Resampling.LANCZOS)

    diff = ImageChops.difference(html_img, pdf_img)
    diff_gray = diff.convert("L")
    pixels = list(diff_gray.get_flattened_data())
    changed = [1 if px > threshold else 0 for px in pixels]
    w, h = diff_gray.size
    total = w * h
    pct = (sum(changed) / total) * 100 if total else 0.0

    # reshape into rows for region analysis
    grid = [changed[i * w : (i + 1) * w] for i in range(h)]
    return pct, diff, grid


def analyze_regions(grid: list[list[int]], width: int, height: int) -> list[RegionResult]:
    """Split A4 page into layout regions matching the HTML grid."""
    sidebar_w = round(width * (68 / 210))  # 68mm of 210mm
    header_h = round(height * 0.11)  # ~11% for dark header band

    regions = {
        "header_full": (0, 0, width, header_h),
        "sidebar": (0, header_h, sidebar_w, height),
        "main": (sidebar_w, header_h, width, height),
        "header_name": (0, 0, sidebar_w, header_h),
        "header_contact": (sidebar_w, 0, width, header_h),
    }

    results: list[RegionResult] = []
    for name, (x0, y0, x1, y1) in regions.items():
        changed = 0
        total = 0
        for y in range(max(0, y0), min(height, y1)):
            row = grid[y]
            for x in range(max(0, x0), min(width, x1)):
                total += 1
                changed += row[x]
        pct = (changed / total * 100) if total else 0.0
        results.append(RegionResult(name=name, diff_pct=pct, bbox=(x0, y0, x1, y1)))
    return results


def read_typst(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_html_css(html_path: Path) -> dict[str, dict[str, str]]:
    html = html_path.read_text(encoding="utf-8")
    m = re.search(r"<style>(.*?)</style>", html, re.DOTALL | re.IGNORECASE)
    if not m:
        return {}
    css = re.sub(r"/\*.*?\*/", "", m.group(1), flags=re.DOTALL)
    css = re.sub(r"@media[^{]+\{([^{}]|\{[^{}]*\})*\}", "", css, flags=re.DOTALL)
    rules: dict[str, dict[str, str]] = {}
    for block in re.finditer(r"([^{]+)\{([^}]+)\}", css):
        for sel in block.group(1).split(","):
            sel = sel.strip()
            if sel.startswith("@") or "::" in sel:
                continue
            props = rules.setdefault(sel, {})
            for line in block.group(2).split(";"):
                if ":" in line:
                    k, v = line.split(":", 1)
                    props[k.strip()] = v.strip()
    return rules


def generate_advice(
    regions: list[RegionResult],
    overall_pct: float,
    html_render: RenderInfo,
    pdf_render: RenderInfo,
    typst_path: Path,
    html_css: dict[str, dict[str, str]],
) -> list[FixAdvice]:
    advice: list[FixAdvice] = []
    typ = read_typst(typst_path)

    if not html_render.a4_valid:
        advice.append(FixAdvice(
            region="render",
            severity="high",
            issue=f"HTML render is not A4 portrait ({html_render.width_px}x{html_render.height_px}px)",
            typst_hint="Checker fixed this via print PDF; verify html_render.png manually.",
            reference="tools/compare_html_typst.py render_html_a4_pdf()",
        ))
    if not pdf_render.a4_valid:
        advice.append(FixAdvice(
            region="render",
            severity="high",
            issue=f"Typst PDF render is not A4 portrait ({pdf_render.width_px}x{pdf_render.height_px}px)",
            typst_hint='Ensure #set page(paper: "a4", margin: 0pt) and outer #box(width: 210mm).',
            reference="Dylan_General_Resume.typ page setup",
        ))

    by_name = {r.name: r for r in regions}

    def sev(pct: float) -> str:
        if pct >= 15:
            return "high"
        if pct >= 5:
            return "medium"
        return "low"

    # Header
    hdr = by_name.get("header_full")
    if hdr and hdr.diff_pct >= 5:
        css_hdr = html_css.get("header", {})
        css_name = html_css.get(".header-name h1", {})
        advice.append(FixAdvice(
            region="header",
            severity=sev(hdr.diff_pct),
            issue=f"Header band differs {hdr.diff_pct:.1f}% - likely padding, font size, or bottom accent line",
            typst_hint=(
                "Match header inset to CSS padding:22px 26px 18px - use inset:(top:16.5pt,right:19.5pt,bottom:13.5pt,left:19.5pt) "
                "OR keep 22pt if intentionally matching screen px numerals. "
                "Verify #grid align:(left+top,left+bottom) on header inner grid. "
                "Accent bar: stroke:(bottom:3pt+accent) on header block."
            ),
            reference=f"HTML header padding={css_hdr.get('padding','')}, h1 size={css_name.get('font-size','')}",
        ))

    # Header name vs contact split
    hn = by_name.get("header_name")
    hc = by_name.get("header_contact")
    if hn and hn.diff_pct > hc.diff_pct + 8 if hc else 8:
        advice.append(FixAdvice(
            region="header_name",
            severity=sev(hn.diff_pct),
            issue=f"Name/pronouns column differs {hn.diff_pct:.1f}% - serif font or size mismatch",
            typst_hint=(
                'Use font: garamond, size: 28pt, weight: "semibold", tracking: -0.5pt for "Dylan Bitar". '
                "Compile with --font-path fonts. Confirm CormorantGaramond-SemiBold.ttf loads."
            ),
            reference="HTML .header-name h1: Cormorant Garamond 28pt weight 600",
        ))
    if hc and hc.diff_pct >= 8:
        advice.append(FixAdvice(
            region="header_contact",
            severity=sev(hc.diff_pct),
            issue=f"Role/contact row differs {hc.diff_pct:.1f}% - mono font, spacing, or wrap",
            typst_hint=(
                "Role: font:mono, size:8.5pt, weight:medium. Contact row: h(18pt) gap between items. "
                "Ensure header right column uses align bottom not #v(1fr) which expands header to full page."
            ),
            reference="HTML .header-title .role 8.5pt, .header-contact gap 4px 18px",
        ))

    # Sidebar
    sb = by_name.get("sidebar")
    if sb and sb.diff_pct >= 8:
        advice.append(FixAdvice(
            region="sidebar",
            severity=sev(sb.diff_pct),
            issue=f"Sidebar differs {sb.diff_pct:.1f}% - section spacing, tags, or coursework rows",
            typst_hint=(
                "Check section-label spacing (margin-bottom:7px, padding-bottom:4px in CSS). "
                "Use #section with block(below:16pt). Skill tags need inline wrap: box with h(3pt) gaps. "
                "Course rows: grid columns (1fr, auto) with 4pt gutter. "
                "Aside padding CSS 20px 18px 24px - convert px to pt (x0.75) for print accuracy."
            ),
            reference=f"HTML aside padding={html_css.get('aside',{}).get('padding','')}, .section margin-bottom 16px",
        ))

    # Main column
    mn = by_name.get("main")
    if mn and mn.diff_pct >= 8:
        advice.append(FixAdvice(
            region="main",
            severity=sev(mn.diff_pct),
            issue=f"Main column differs {mn.diff_pct:.1f}% - experience blocks, projects, or profile",
            typst_hint=(
                "Profile: stroke left 2pt + accent, inset left 10pt, text 8.8pt leading 1.6em. "
                "Experience: exp-item margin-bottom 11pt; highlighted box fill accent-soft with 9pt/11pt inset. "
                "Projects: box fill sidebar-bg, stroke left 2.5pt + accent. "
                "All #for loop bodies inside [...] must use # prefix on function calls."
            ),
            reference="HTML main padding 20px 22px 24px 20px, .exp-item margin-bottom 11px",
        ))

    # Global overflow / page break
    if pdf_render.page_count > 1 and html_render.page_count <= 1:
        advice.append(FixAdvice(
            region="page_break",
            severity="high",
            issue=f"Typst PDF is {pdf_render.page_count} pages but HTML fits on 1 A4 page",
            typst_hint=(
                "Reduce vertical spacing: section below 16pt, tighten #v() gaps, reduce par leading slightly. "
                "Or set #set page(height: 297mm) and reduce content. Check for duplicate content blocks."
            ),
            reference="Compare page counts in render info",
        ))

    if overall_pct >= 10:
        advice.append(FixAdvice(
            region="global",
            severity="high",
            issue=f"Overall pixel diff {overall_pct:.1f}% - documents are visually distinct",
            typst_hint=(
                "Work region-by-region using tools/output/visual_diff.png (red = mismatch). "
                "Recompile after each fix: typst compile Dylan_General_Resume.typ Dylan_General_Resume.pdf "
                "--root . --font-path fonts. Re-run: python tools/compare_html_typst.py"
            ),
            reference="Open tools/output/html_render.png vs pdf_render.png side by side",
        ))

    # Detect common Typst bugs from source (reference only)
    if re.search(r"block\([^)]*\)\[\s*(grid|text|exp-header|box)\(", typ):
        advice.append(FixAdvice(
            region="typst_syntax",
            severity="high",
            issue="Typst content blocks may be missing # prefix — causes raw code in PDF",
            typst_hint="Inside [...] content mode, prefix all calls with #: #grid(...), #text(...), #exp-header(...).",
            reference="Typst content vs code mode rules",
        ))

    px_pt = html_css.get("header", {}).get("padding", "")
    if "px" in px_pt and "inset: (top: 22pt" in typ:
        advice.append(FixAdvice(
            region="units",
            severity="medium",
            issue="HTML uses px padding but Typst uses same numerals in pt - causes ~25% size drift",
            typst_hint="Convert px to pt: multiply by 0.75 (e.g. 22px -> 16.5pt). Or use 0.75 * px for all inset values.",
            reference=f"HTML header {px_pt} vs Typst inset 22pt 26pt 18pt",
        ))

    return advice


def save_annotated_diff(html_img, diff_img, regions: list[RegionResult], path: Path) -> None:
    from PIL import ImageDraw

    out = html_img.copy()
    draw = ImageDraw.Draw(out, "RGBA")
    for r in regions:
        if r.diff_pct < 3:
            continue
        x0, y0, x1, y1 = r.bbox
        alpha = min(180, int(r.diff_pct * 8))
        draw.rectangle([x0, y0, x1, y1], outline=(255, 0, 0, 200), width=3)
        draw.rectangle([x0, y0, x1, y1], fill=(255, 0, 0, alpha // 4))
        draw.text((x0 + 4, y0 + 4), f"{r.name} {r.diff_pct:.0f}%", fill=(200, 0, 0, 255))
    out.save(path)
    diff_img.save(path.parent / "visual_diff.png")


def print_report(report: Report) -> None:
    print("=" * 72)
    print("HTML <-> Typst VISUAL Comparison (A4 portrait renders)")
    print("=" * 72)
    print(f"HTML:  {report.html}")
    print(f"Typst: {report.typst}")
    print(f"PDF:   {report.pdf}")
    print(f"DPI:   {report.dpi}  (A4 = {a4_pixels(report.dpi)[0]}x{a4_pixels(report.dpi)[1]}px)")
    print()

    for info in (report.html_render, report.pdf_render):
        if not info:
            continue
        ok = "OK" if info.a4_valid else "INVALID"
        print(f"  [{ok}] {info.source}: {info.width_px}x{info.height_px}px, "
              f"aspect={info.aspect_ratio:.4f}, pages={info.page_count}")
        for n in info.notes:
            print(f"        ! {n}")
    print()

    print(f"Overall pixel diff: {report.overall_diff_pct:.2f}%")
    print()
    print("-- REGIONS --")
    for r in sorted(report.regions, key=lambda x: -x.diff_pct):
        flag = "XX" if r.diff_pct >= 10 else ("!!" if r.diff_pct >= 5 else "OK")
        print(f"  {flag} {r.name:20s} {r.diff_pct:5.1f}%  bbox={r.bbox}")
    print()

    if report.advice:
        print("-- TYPST FIX ADVICE (from visual diff + source reference) --")
        for i, a in enumerate(report.advice, 1):
            print(f"  [{a.severity.upper()}] #{i} {a.region}")
            print(f"      Issue:  {a.issue}")
            print(f"      Fix:    {a.typst_hint}")
            print(f"      Ref:    {a.reference}")
            print()

    status = "PASS" if report.passed else "FAIL"
    print(f"RESULT: {status}")
    if not report.passed:
        print("  Open tools/output/html_render.png, pdf_render.png, visual_diff.png, regions.png")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--typ", type=Path, default=DEFAULT_TYP)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--dpi", type=int, default=150, help="A4 render DPI (default 150)")
    parser.add_argument("--tolerance", type=float, default=2.0, help="Max overall pixel diff %% to pass")
    parser.add_argument("--json", type=Path, default=OUTPUT_DIR / "report.json")
    args = parser.parse_args()

    for path, label in [(args.html, "HTML"), (args.typ, "Typst"), (args.pdf, "PDF")]:
        if not path.exists():
            print(f"ERROR: {label} not found: {path}", file=sys.stderr)
            return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        html_img, html_info = render_html_a4_png(args.html, args.dpi, OUTPUT_DIR)
        pdf_img, pdf_info = render_typst_a4_png(args.pdf, args.dpi, OUTPUT_DIR)
    except Exception as exc:
        print(f"ERROR: render failed: {exc}", file=sys.stderr)
        print("Install deps: pip install -r tools/requirements-compare.txt", file=sys.stderr)
        print("Then: python -m playwright install chromium", file=sys.stderr)
        return 1

    overall_pct, diff_img, grid = compute_diff(html_img, pdf_img)
    regions = analyze_regions(grid, html_img.width, html_img.height)
    html_css = read_html_css(args.html)
    advice = generate_advice(regions, overall_pct, html_info, pdf_info, args.typ, html_css)
    save_annotated_diff(html_img, diff_img, regions, OUTPUT_DIR / "regions.png")

    renders_ok = html_info.a4_valid and pdf_info.a4_valid
    report = Report(
        html=str(args.html),
        typst=str(args.typ),
        pdf=str(args.pdf),
        dpi=args.dpi,
        html_render=html_info,
        pdf_render=pdf_info,
        overall_diff_pct=overall_pct,
        regions=regions,
        advice=advice,
        passed=renders_ok and overall_pct <= args.tolerance,
    )

    payload = {
        "passed": report.passed,
        "overall_diff_pct": overall_pct,
        "tolerance_pct": args.tolerance,
        "a4_expected_px": {"width": a4_pixels(args.dpi)[0], "height": a4_pixels(args.dpi)[1]},
        "html_render": asdict(html_info),
        "pdf_render": asdict(pdf_info),
        "regions": [asdict(r) for r in regions],
        "advice": [asdict(a) for a in advice],
    }
    args.json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print_report(report)
    print(f"JSON: {args.json}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
