"""Draw the code cache usage per phase of experiment (3) as an HTML snippet for a Zenn html-embed block.

usage: python3 tools/figures/codecache_chart.py results/codecache/copies1000-1 > figures/codecache.html
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from codecache_report import summarize  # noqa: E402

W, H = 700, 330
X0, X1 = 172, 612
ROW0, ROW_STEP, BAR = 74, 44, 22
MAX_MB = 12

SURFACE = "#181b1f"
GRID = "#2c3038"
TEXT = "#e6e8eb"
MUTED = "#9aa0a8"
HEAPS = [
    ("non-nmethods", "non-nmethods（JVM 自身のコード）", "#6b7280"),
    ("profiled", "profiled（tier 2・3）", "#3987e5"),
    ("non-profiled", "non-profiled（tier 1・4）", "#199e70"),
]
LABELS = {
    "started": "起動した直後",
    "loaded": "読み込んで1回呼んだあと",
    "hot": "繰り返し呼んだあと",
    "after-gc1": "1回目の GC のあと",
    "after-gc2": "2回目の GC のあと",
}


def x(mb):
    return X0 + mb / MAX_MB * (X1 - X0)


def text_width(body):
    """Rough width at 12px: full-width characters take 12px, others about 6.5px"""
    return sum(12 if ord(c) > 0x2E7F else 6.5 for c in body)


def text(px, py, body, cls="", anchor="middle"):
    return f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{anchor}" class="{cls}">{body}</text>'


def main():
    rows = [(phase, used) for phase, used, _, _, _ in summarize(sys.argv[1]) if phase in LABELS]
    parts = []
    bottom = ROW0 + ROW_STEP * (len(rows) - 1) + BAR
    for mb in range(0, MAX_MB + 1, 2):
        parts.append(f'<line x1="{x(mb):.1f}" x2="{x(mb):.1f}" y1="{ROW0 - 10}" y2="{bottom + 8}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(x(mb), bottom + 26, str(mb), "tick"))

    for i, (phase, used) in enumerate(rows):
        top = ROW0 + ROW_STEP * i
        parts.append(text(X0 - 12, top + BAR / 2 + 4, LABELS[phase], "row", "end"))
        left = 0.0
        for key, _, color in HEAPS:
            mb = used[key] / 1024
            # 2px of surface between segments
            width = max(x(left + mb) - x(left) - 2, 1)
            parts.append(f'<rect x="{x(left):.1f}" y="{top}" width="{width:.1f}" height="{BAR}" fill="{color}"/>')
            left += mb
        parts.append(text(x(left) + 8, top + BAR / 2 + 4, f"{left:.1f}MB", "value", "start"))

    lx = 24
    for _, label, color in HEAPS:
        parts.append(f'<rect x="{lx}" y="20" width="12" height="12" fill="{color}"/>')
        parts.append(text(lx + 18, 31, label, "legend", "start"))
        lx += 18 + text_width(label) + 24

    parts.append(text((X0 + X1) / 2, H - 8, "code cache の使用量（MB）", "axis"))

    label = "code cache の実験の段階ごとの、3つの領域の使用量"
    print(f'<figure class="codecache">\n<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">')
    print("\n".join(parts))
    print("</svg>\n</figure>")
    print(f"""<style>
  /* Below 600px the chart keeps its size and the embed scrolls sideways, so that the 12px labels stay at 10px or more */
  .codecache {{ margin: 0; padding: 8px 4px; min-width: 600px; box-sizing: border-box; background: {SURFACE};
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; }}
  .codecache svg {{ display: block; width: 100%; height: auto; }}
  .codecache text {{ font-size: 12px; fill: {MUTED}; }}
  .codecache .row, .codecache .legend, .codecache .value {{ fill: {TEXT}; }}
  .codecache .value {{ font-weight: 600; }}
  .codecache .axis {{ font-size: 13px; }}
</style>""")


if __name__ == "__main__":
    main()
