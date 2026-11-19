"""Draw the overview of chapter 2 (how one method runs on the JVM) as an HTML snippet for a Zenn html-embed block.

The parts and colors follow the Archify diagram in the background material (fig1): teal boxes for the JVM's own
processing, dark gray boxes for memory areas, a white box for what is outside the JVM, regions as filled faces,
white pills for edge labels, a small sigil at the top left of each box, and a monospace face.
Sizes follow the article figure rules: width 800 and 14px text, so that the text stays at 12px in a 700px column.

usage: python3 tools/figures/overview_figure.py > figures/overview.html
"""

W, H = 800, 552

SIGILS = {
    "proc": '<path d="M6 3 3 8l3 5M10 3l3 5-3 5"/>',
    "mem": '<ellipse cx="8" cy="4" rx="5" ry="2"/><path d="M3 4v8c0 1.1 2.2 2 5 2s5-.9 5-2V4M3 8c0 1.1 2.2 2 5 2s5-.9 5-2"/>',
    "outside": '<rect x="2.5" y="5" width="8.5" height="8" rx="1.5"/><path d="M8 2.5h5.5V8M13.5 2.5 7.5 8.5"/>',
}


def width(text, size):
    """Rough rendered width: full-width characters take 1em, others 0.6em (monospace)"""
    return sum(size if ord(c) > 0x2E7F else size * 0.6 for c in text)


def node(kind, x, y, w, h, title, *subs):
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="box {kind}"/>',
        f'<g class="sigil" transform="translate({x + 8} {y + 8}) scale(0.875)">{SIGILS[kind]}</g>',
        f'<text x="{x + w / 2}" y="{y + 26}" class="title {kind}">{title}</text>',
    ]
    for i, sub in enumerate(subs):
        parts.append(f'<text x="{x + w / 2}" y="{y + 48 + 22 * i}" class="sub {kind}">{sub}</text>')
    return "\n".join(parts)


def region(cls, x, y, w, h, label):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="{cls}"/>\n'
            f'<text x="{x + 12}" y="{y + 20}" class="region-label">{label}</text>')


def arrow(x1, y1, x2, y2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="edge" marker-end="url(#ov-head)"/>'


def pill(cx, cy, label):
    w = width(label, 14) + 16
    return (f'<rect x="{cx - w / 2:.1f}" y="{cy - 10}" width="{w:.1f}" height="20" rx="4" class="pill"/>\n'
            f'<text x="{cx}" y="{cy + 5}" class="pill-text">{label}</text>')


def badge(cx, cy, n):
    return (f'<circle cx="{cx}" cy="{cy}" r="11" class="badge"/>'
            f'<text x="{cx}" y="{cy + 5}" class="badge-text">{n}</text>')


def legend(right, y):
    items = [("proc", "JVM の中の処理"), ("mem", "メモリ領域"), ("outside", "JVM の外")]
    total = sum(16 + 6 + width(label, 14) for _, label in items) + 18 * (len(items) - 1)
    x = right - total
    parts = []
    for kind, label in items:
        parts.append(f'<rect x="{x:.1f}" y="{y - 10}" width="16" height="11" rx="2.5" class="box {kind} flat"/>')
        parts.append(f'<text x="{x + 22:.1f}" y="{y}" class="legend">{label}</text>')
        x += 16 + 6 + width(label, 14) + 18
    return "\n".join(parts)


def main():
    parts = [
        legend(784, 40),
        node("outside", 28, 10, 160, 52, "クラスファイル", ".class"),
        f'<rect x="12" y="76" width="776" height="464" rx="14" class="jvm"/>',
        '<text x="146" y="100" class="region-label">JVM（HotSpot）</text>',
        region("group", 262, 88, 180, 194, "JIT のコンパイラ"),
        region("cache", 484, 88, 292, 304, "code cache（既定 240MB）"),
        region("sub", 496, 120, 268, 180, "nmethod（コンパイルしたコード）"),
        region("group", 262, 418, 514, 110, "実行中に読み書きするデータ"),
        # the data flows from the tail to the head of each arrow
        arrow(108, 62, 108, 114),
        arrow(188, 149, 272, 149),
        arrow(188, 235, 272, 235),
        arrow(188, 330, 260, 330),
        arrow(262, 366, 190, 366),
        arrow(430, 166, 506, 166),
        arrow(430, 246, 506, 246),
        arrow(350, 390, 350, 450),
        arrow(690, 392, 690, 450),
        arrow(188, 483, 272, 483),
        node("mem", 28, 118, 160, 272, "メタスペース", "バイトコード", "クラスの情報", "プロファイル"),
        node("proc", 274, 118, 156, 62, "C1", "短い時間でコンパイル"),
        node("proc", 274, 204, 156, 62, "C2", "時間をかけて最適化"),
        node("proc", 262, 306, 188, 84, "インタプリタ", "1命令ずつ実行", "回数とプロファイルを記録"),
        node("mem", 508, 150, 244, 62, "profiled（約117MB）", "C1 のコード（tier 2・3）"),
        node("mem", 508, 226, 244, 62, "non-profiled（約117MB）", "C1（tier 1）・C2（tier 4）"),
        node("mem", 496, 316, 268, 62, "non-nmethods（約5.6MB）", "インタプリタなど JVM 自身のコード"),
        node("mem", 274, 452, 236, 62, "ヒープ", "new で作ったオブジェクト"),
        node("mem", 526, 452, 238, 62, "スタック", "メソッドごとのフレーム"),
        node("proc", 28, 452, 160, 62, "GC", "使われないものを回収"),
        pill(225, 366, "記録"),
        pill(350, 404, "読み書き"),
        pill(676, 405, "実行しながら読み書き"),
        pill(231, 483, "回収"),
        badge(124, 90, 1),
        badge(225, 314, 2),
        badge(225, 133, 3),
        badge(463, 150, 3),
        badge(225, 219, 4),
        badge(463, 230, 4),
        badge(772, 405, 5),
    ]
    label = ("1つのメソッドが、クラスファイルからメタスペースに読み込まれ、インタプリタで実行されたあと、"
             "C1 と C2 でネイティブコードにコンパイルされて code cache に保存され、次の呼び出しからそのコードが実行される流れ")
    print(f'<figure class="jvmflow">\n<svg viewBox="0 0 {W} {H}" role="img" aria-label="{label}">')
    print('<defs><marker id="ov-head" viewBox="0 0 10 7" refX="9" refY="3.5" markerUnits="userSpaceOnUse" '
          'markerWidth="10" markerHeight="7" orient="auto"><polygon points="0 0, 10 3.5, 0 7" class="head"/></marker></defs>')
    print("\n".join(parts))
    print("</svg>\n</figure>")
    print(STYLE)


STYLE = """<style>
  .jvmflow {
    --bg: #ffffff; --jvm: #c9dde3; --group: #eaf1f4; --group-line: #a7bcc4;
    --cache: #eef4f6; --cache-line: #5e7a86; --sub: #dce8ed; --sub-line: #7a939c;
    --proc: #00708f; --mem: #595959; --outside: #ffffff; --outside-line: #595959;
    --ink: #222222; --label: #2e3a42; --line: #4a4a4a;
    --pill: #ffffff; --pill-line: #cbd5e1; --pill-ink: #4a4a4a; --badge: #2e3a42; --badge-ink: #ffffff;
    --shadow: drop-shadow(0 1px 1px rgba(17, 24, 39, 0.05)) drop-shadow(0 6px 12px rgba(17, 24, 39, 0.06));
    /* Below 600px the figure keeps its size and the embed scrolls sideways */
    margin: 0; padding: 8px 4px; min-width: 600px; box-sizing: border-box; background: var(--bg);
    font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, "DejaVu Sans Mono", monospace;
  }
  [data-theme="dark"] .jvmflow {
    --bg: #0f1419; --jvm: #1b2a31; --group: #22343c; --group-line: #3e5a66;
    --cache: #20323a; --cache-line: #6f8f9c; --sub: #273d47; --sub-line: #5f7f8c;
    --proc: #00708f; --mem: #5a5f66; --outside: #1b2229; --outside-line: #8b949e;
    --ink: #e6e8eb; --label: #c9d6dd; --line: #a9b4bd;
    --pill: #0f172a; --pill-line: #334155; --pill-ink: #cbd5e1; --badge: #e6edf1; --badge-ink: #0f1419;
    --shadow: drop-shadow(0 1px 1px rgba(0, 0, 0, 0.3)) drop-shadow(0 6px 12px rgba(0, 0, 0, 0.35));
  }
  .jvmflow svg { display: block; width: 100%; height: auto; }
  .jvmflow text { text-anchor: middle; font-size: 14px; }
  .jvmflow .jvm { fill: var(--jvm); }
  .jvmflow .group { fill: var(--group); stroke: var(--group-line); }
  .jvmflow .cache { fill: var(--cache); stroke: var(--cache-line); stroke-width: 1.5; }
  .jvmflow .sub { fill: var(--sub); stroke: var(--sub-line); stroke-dasharray: 4 3; }
  .jvmflow .region-label { text-anchor: start; fill: var(--label); font-weight: 700; }
  .jvmflow .box { stroke-width: 1.25; filter: var(--shadow); }
  .jvmflow .box.flat { filter: none; stroke-width: 1; }
  .jvmflow .box.proc { fill: var(--proc); stroke: var(--proc); }
  .jvmflow .box.mem { fill: var(--mem); stroke: var(--mem); }
  .jvmflow .box.outside { fill: var(--outside); stroke: var(--outside-line); }
  .jvmflow .title { font-size: 15px; font-weight: 600; }
  .jvmflow .title.proc, .jvmflow .title.mem, .jvmflow .sub.proc, .jvmflow .sub.mem { fill: #ffffff; }
  .jvmflow .title.outside, .jvmflow .sub.outside { fill: var(--ink); }
  .jvmflow text.sub { fill: #ffffff; stroke: none; }
  .jvmflow text.sub.outside { fill: var(--ink); }
  .jvmflow .sigil { fill: none; stroke: #ffffff; stroke-width: 1.35; stroke-linecap: round; stroke-linejoin: round; opacity: 0.76; }
  .jvmflow .sigil:has(+ .title.outside) { stroke: var(--outside-line); }
  .jvmflow .edge { stroke: var(--line); stroke-width: 1.5; }
  .jvmflow .head { fill: var(--line); }
  .jvmflow .pill { fill: var(--pill); stroke: var(--pill-line); stroke-width: 0.75; }
  .jvmflow .pill-text { fill: var(--pill-ink); }
  .jvmflow .badge { fill: var(--badge); }
  .jvmflow .badge-text { fill: var(--badge-ink); font-size: 14px; font-weight: 700; }
  .jvmflow .legend { text-anchor: start; fill: var(--ink); }
</style>"""


if __name__ == "__main__":
    main()
