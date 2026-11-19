"""Draw the warmup chart of experiment (1) as an HTML snippet for a Zenn html-embed block.

usage: python3 tools/figures/warmup_chart.py results/warmup 4 > figures/warmup.html
The second argument picks which run to draw (jit-<n>.csv and xint-<n>.csv).
"""
import math
import os
import re
import sys

W, H = 700, 440
X0, X1, Y0, Y1 = 64, 684, 76, 384
ROUND_MAX = 500
T_MIN, T_MAX = 4, 1000

SURFACE = "#181b1f"
GRID = "#2c3038"
TEXT = "#e6e8eb"
MUTED = "#9aa0a8"
JIT = "#3987e5"
XINT = "#d95926"

LINE = re.compile(r"^\[(\d+)ns\]\s+(\d+)\s+([%sbn!]*)\s*(\d)?\s+(\S+)(.*)$")


def x(round_number):
    return X0 + math.log10(round_number) / math.log10(ROUND_MAX) * (X1 - X0)


def y(micros):
    span = math.log10(T_MAX) - math.log10(T_MIN)
    return Y1 - (math.log10(micros) - math.log10(T_MIN)) / span * (Y1 - Y0)


def load(path):
    starts, elapsed = [], []
    with open(path) as f:
        next(f)
        for row in f:
            _, s, e = row.strip().split(",")
            starts.append(int(s))
            elapsed.append(int(e) / 1000)
    return starts, elapsed


def switch_rounds(csv, log):
    """Rounds in which Cart.total got C1 OSR code, a C2 OSR version, and the normal C2 version"""
    starts, _ = load(csv)
    found = {}
    with open(log) as f:
        for row in f:
            m = LINE.match(row.rstrip())
            if not m or m.group(5) != "Cart::total":
                continue
            ts, _, attrs, tier, _, rest = m.groups()
            key = (tier, "%" in attrs, "made not entrant" in rest)
            found.setdefault(key, int(ts))

    def round_of(ts):
        return sum(1 for s in starts if s <= ts)

    return round_of(found[("3", True, False)]), round_of(found[("3", True, True)]), round_of(found[("3", False, True)])


def polyline(values, color):
    points = " ".join(f"{x(i + 1):.1f},{y(max(v, T_MIN)):.1f}" for i, v in enumerate(values))
    return f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'


def text(px, py, body, cls="", anchor="middle"):
    return f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{anchor}" class="{cls}">{body}</text>'


def main():
    directory, run = sys.argv[1], sys.argv[2]
    jit_csv = os.path.join(directory, f"jit-{run}.csv")
    _, jit = load(jit_csv)
    _, xint = load(os.path.join(directory, f"xint-{run}.csv"))
    c1, c2_osr, c2 = switch_rounds(jit_csv, os.path.join(directory, f"jit-{run}.log"))

    parts = []
    # Stages: which code runs Cart.total
    stages = [(1, c1, "インタプリタ"), (c1, c2_osr, "C1（tier 3）"), (c2_osr, c2, ""), (c2, ROUND_MAX, "C2（tier 4）")]
    for i, (lo, hi, label) in enumerate(stages):
        fill = "rgba(255,255,255,0.045)" if i % 2 == 1 else "rgba(255,255,255,0)"
        parts.append(f'<rect x="{x(lo):.1f}" y="{Y0}" width="{x(hi) - x(lo):.1f}" height="{Y1 - Y0}" fill="{fill}"/>')
        if label:
            # 140µs is clear of both lines in every stage
            parts.append(text((x(lo) + x(hi)) / 2, y(140), label, "stage"))

    for t in (5, 10, 20, 50, 100, 200, 500, 1000):
        parts.append(f'<line x1="{X0}" x2="{X1}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(X0 - 8, y(t) + 4, f"{t:,}", "tick", "end"))
    for r in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        parts.append(text(x(r), Y1 + 18, str(r), "tick"))

    # Boundaries where the code of Cart.total changed
    for r, anchor, dx in ((c1, "start", 4), (c2_osr, "end", -4), (c2, "start", 4)):
        parts.append(f'<line x1="{x(r):.1f}" x2="{x(r):.1f}" y1="{Y0}" y2="{Y1}" stroke="{MUTED}" stroke-width="1"/>')
        parts.append(text(x(r) + dx, Y1 - 8, f"{r}回目", "edge", anchor))

    # The narrow stage between the two C2 versions is named above the plot
    mid = (x(c2_osr) + x(c2)) / 2
    parts.append(f'<line x1="{mid:.1f}" x2="{mid:.1f}" y1="{Y0 - 10}" y2="{Y0}" stroke="{MUTED}" stroke-width="1"/>')
    parts.append(text(mid, Y0 - 16, "C1 から C2 の OSR 用のコードへ移る区間（約48µs）", "stage"))

    parts.append(polyline(xint, XINT))
    parts.append(polyline(jit, JIT))

    # Medians of the 5 runs (tools/warmup_report.py)
    for r, t, label in ((3.5, 217, "約220µs"), (22, 31, "約31µs"), (210, 5.9, "約6µs")):
        parts.append(text(x(r), y(t) - 10, label, "value"))
    parts.append(text(x(18), y(562) - 10, "約560µs", "value"))

    parts.append(f'<line x1="{X0}" x2="{X0 + 22}" y1="20" y2="20" stroke="{JIT}" stroke-width="2"/>')
    parts.append(text(X0 + 30, 24, "JIT あり（既定の設定）", "legend", "start"))
    parts.append(f'<line x1="{X0 + 200}" x2="{X0 + 222}" y1="20" y2="20" stroke="{XINT}" stroke-width="2"/>')
    parts.append(text(X0 + 230, 24, "JIT なし（-Xint）", "legend", "start"))

    parts.append(text((X0 + X1) / 2, H - 10, "何回目の呼び出しか（対数）", "axis"))
    parts.append(f'<text x="18" y="{(Y0 + Y1) / 2:.1f}" text-anchor="middle" class="axis" transform="rotate(-90 18 {(Y0 + Y1) / 2:.1f})">1回の時間（µs、対数）</text>')

    label = "Cart.total を500回呼んだときの、1回ごとの時間"
    print(f'<figure class="warmup">\n<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">')
    print("\n".join(parts))
    print("</svg>\n</figure>")
    print(f"""<style>
  /* Below 600px the chart keeps its size and the embed scrolls sideways, so that the 12px labels stay at 10px or more */
  .warmup {{ margin: 0; padding: 8px 4px; min-width: 600px; box-sizing: border-box; background: {SURFACE};
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; }}
  .warmup svg {{ display: block; width: 100%; height: auto; }}
  .warmup text {{ font-size: 12px; fill: {MUTED}; }}
  .warmup .stage, .warmup .legend, .warmup .value {{ fill: {TEXT}; }}
  .warmup .value {{ font-weight: 600; }}
  .warmup .axis {{ font-size: 13px; }}
  .warmup .edge {{ font-size: 11px; }}
</style>""")


if __name__ == "__main__":
    main()
