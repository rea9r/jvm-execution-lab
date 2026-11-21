"""Draw the charts of the practical tips as HTML snippets for Zenn html-embed blocks, in the style of the warmup chart.

usage:
  python3 tools/figures/tips_charts.py startup results/tips > figures/startup.html
  python3 tools/figures/tips_charts.py logdest results/tips > figures/logdest.html
  python3 tools/figures/tips_charts.py huge results/tips > figures/huge.html

startup and logdest draw the time per call of Cart.total over 500 calls, as the median of the 5 runs in each call.
huge draws the time of 20,000 calls of the 8,000-byte and 8,004-byte methods (median of rounds 2-5, then of the runs).
"""
import csv
import math
import statistics
import sys
from pathlib import Path

SURFACE = "#181b1f"
GRID = "#2c3038"
TEXT = "#e6e8eb"
MUTED = "#9aa0a8"
# The first three dark slots of the dataviz palette, checked all-pairs on SURFACE
BLUE, ORANGE, AQUA = "#3987e5", "#d95926", "#199e70"

W = 700
X0, X1 = 64, 684
ROUND_MAX = 500


def median_per_round(directory, key):
    runs = []
    for path in sorted(Path(directory).glob(f"{key}-[0-9]*.csv")):
        runs.append([int(r["elapsed_ns"]) / 1000 for r in csv.DictReader(open(path))])
    assert len(runs) == 5 and all(len(r) == ROUND_MAX for r in runs), (key, [len(r) for r in runs])
    return [statistics.median(values) for values in zip(*runs)]


def text(px, py, body, cls="", anchor="middle"):
    return f'<text x="{px:.1f}" y="{py:.1f}" text-anchor="{anchor}" class="{cls}">{body}</text>'


def style(name, min_width=600):
    return f"""<style>
  /* Below {min_width}px the chart keeps its size and the embed scrolls sideways, so that the 12px labels stay at 10px or more */
  .{name} {{ margin: 0; padding: 8px 4px; min-width: {min_width}px; box-sizing: border-box; background: {SURFACE};
    font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; }}
  .{name} svg {{ display: block; width: 100%; height: auto; }}
  .{name} text {{ font-size: 12px; fill: {MUTED}; }}
  .{name} .legend, .{name} .value, .{name} .row {{ fill: {TEXT}; }}
  .{name} .value {{ font-weight: 600; }}
  .{name} .axis {{ font-size: 13px; }}
</style>"""


def calls_chart(name, label, series, t_max, values):
    """Time per call against the call number, both on log scales.

    series: (legend, color, per-call times); values: (call, time, text, below) labels in the text color
    """
    H, Y0, Y1 = 400, 64, 344
    t_min = 4

    def x(r):
        return X0 + math.log10(r) / math.log10(ROUND_MAX) * (X1 - X0)

    def y(t):
        return Y1 - (math.log10(t) - math.log10(t_min)) / (math.log10(t_max) - math.log10(t_min)) * (Y1 - Y0)

    for _, _, times in series:
        assert max(times) <= t_max and min(times) >= t_min, (name, max(times), min(times))

    parts = []
    ticks = [t for t in (5, 10, 20, 50, 100, 200, 500, 1000, 2000) if t <= t_max]
    for t in ticks:
        parts.append(f'<line x1="{X0}" x2="{X1}" y1="{y(t):.1f}" y2="{y(t):.1f}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(X0 - 8, y(t) + 4, f"{t:,}", "tick", "end"))
    for r in (1, 2, 5, 10, 20, 50, 100, 200, 500):
        parts.append(text(x(r), Y1 + 18, str(r), "tick"))
    for _, color, times in series:
        points = " ".join(f"{x(i + 1):.1f},{y(t):.1f}" for i, t in enumerate(times))
        parts.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="2" '
                     'stroke-linejoin="round" stroke-linecap="round"/>')
    for r, t, body, below in values:
        parts.append(text(x(r), y(t) + (18 if below else -10), body, "value"))
    lx = X0
    for legend, color, _ in series:
        parts.append(f'<line x1="{lx}" x2="{lx + 22}" y1="20" y2="20" stroke="{color}" stroke-width="2"/>')
        parts.append(text(lx + 30, 24, legend, "legend", "start"))
        lx += 30 + 12 * len(legend) + 36
    parts.append(text((X0 + X1) / 2, H - 10, "何回目の呼び出しか（対数）", "axis"))
    parts.append(f'<text x="18" y="{(Y0 + Y1) / 2:.1f}" text-anchor="middle" class="axis" '
                 f'transform="rotate(-90 18 {(Y0 + Y1) / 2:.1f})">1回の時間（µs、対数）</text>')
    print(f'<figure class="{name}">\n<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">')
    print("\n".join(parts))
    print("</svg>\n</figure>")
    print(style(name))


def startup(directory):
    default, aot, c1 = (median_per_round(directory, k) for k in ("jar", "aot", "c1"))
    calls_chart(
        "startup", "起動のしかたごとの、Cart.total を500回呼んだときの1回ごとの時間（5回の中央値）",
        [("既定", BLUE, default), ("AOT キャッシュ", AQUA, aot), ("C1 だけ", ORANGE, c1)],
        1000,
        [(3.5, 222, "約220µs", False), (6.5, 10, "約10µs", False), (22, 31, "約31µs", False),
         (22, 7.6, "約7µs", True), (250, 6.1, "約6µs", True)],
    )


def logdest(directory):
    inside, shared, shared_async = (median_per_round(directory, k) for k in ("jar", "logsync", "logasync"))
    calls_chart(
        "logdest", "コンパイルの記録の書き先ごとの、Cart.total を500回呼んだときの1回ごとの時間（5回の中央値）",
        [("コンテナの中", BLUE, inside), ("共有しているフォルダ", ORANGE, shared),
         ("同じフォルダ・async", AQUA, shared_async)],
        2000,
        [(3.5, 646, "約650µs", False), (3.5, 211, "約210〜220µs", True), (250, 6.0, "約6µs", True)],
    )


def huge(directory):
    def ms(key):
        per_run = []
        for path in sorted(Path(directory).glob(f"{key}-[0-9]*.csv")):
            rounds = [float(r["elapsed_us"]) for r in csv.DictReader(open(path))]
            per_run.append(statistics.median(rounds[1:]))
        assert len(per_run) == 5, key
        return statistics.median(per_run) / 1000

    rows = [("8,000バイト", ms("Huge8000"), "tier 3・4", BLUE),
            ("8,004バイト", ms("Huge8004"), "コンパイルされない", ORANGE),
            ("8,004バイト（オプションあり）", ms("Huge8004-forced"), "tier 3・4", BLUE)]
    H, top, row_h, left, right = 210, 24, 44, 228, 520
    t_max = 70
    assert max(v for _, v, _, _ in rows) <= t_max

    def x(v):
        return left + v / t_max * (right - left)

    parts = []
    base = top + row_h * len(rows)
    for t in range(0, t_max + 1, 10):
        parts.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{top - 6}" y2="{base}" stroke="{GRID}" stroke-width="1"/>')
        parts.append(text(x(t), base + 18, str(t), "tick"))
    for i, (name, value, compiled, color) in enumerate(rows):
        cy = top + row_h * i + row_h / 2
        parts.append(text(left - 12, cy + 4, name, "row", "end"))
        parts.append(f'<rect x="{left}" y="{cy - 9:.1f}" width="{x(value) - left:.1f}" height="18" rx="3" fill="{color}"/>')
        parts.append(text(x(value) + 8, cy + 4, f"{value:.1f}ms（{compiled}）", "value", "start"))
    parts.append(text((left + right) / 2, H - 10, "2万回の時間（ms）", "axis"))
    label = "バイトコードが8,000バイトと8,004バイトのメソッドを2万回呼んだ時間"
    print(f'<figure class="huge">\n<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">')
    print("\n".join(parts))
    print("</svg>\n</figure>")
    print(style("huge"))


if __name__ == "__main__":
    {"startup": startup, "logdest": logdest, "huge": huge}[sys.argv[1]](sys.argv[2])
