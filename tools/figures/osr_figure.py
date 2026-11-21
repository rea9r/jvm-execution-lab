"""Draw the OSR figure of chapter 2 as a static SVG: one long call that moves from the interpreter to the OSR code
at the head of its loop, and the next call that enters the normal compiled code at the head of the method.

Colors, text sizes and the lane faces follow the Archify overview (teal for the interpreter, dark gray for compiled
code, 11px names, 10px frame names and pills). The fonts are left to the page.

usage: python3 tools/figures/osr_figure.py > figures/osr.svg
"""

W, H = 640, 270
TEAL, GRAY, INK, NAME, NOTE = "#00708F", "#595959", "#4A4A4A", "#2E3A42", "#555555"
LANE_FILL, LANE_LINE, PILL_LINE = "#EAF1F4", "#A7BCC4", "#CBD5E1"


def width(text, size):
    """Rendered width: CJK characters take 1em, the rest about 0.6em"""
    return sum(size if ord(c) > 0x2E7F else size * 0.6 for c in text)


def bar(x1, x2, y, h, fill, left=True, right=True, r=6):
    """A bar with rounded corners only on the chosen ends"""
    lr, rr = (r if left else 0), (r if right else 0)
    return (f'<path d="M{x1 + lr} {y} H{x2 - rr} Q{x2} {y} {x2} {y + rr} V{y + h - rr} Q{x2} {y + h} {x2 - rr} {y + h} '
            f'H{x1 + lr} Q{x1} {y + h} {x1} {y + h - lr} V{y + lr} Q{x1} {y} {x1 + lr} {y}Z" fill="{fill}"/>')


def ticks(x1, x2, y, step=12):
    """One tick per loop iteration along the bottom of a bar"""
    xs = range(x1 + step, x2 - 4, step)
    return "".join(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 6}" stroke="#FFFFFF" stroke-opacity="0.55"/>' for x in xs)


def text(x, y, s, size, fill, weight=None, anchor="start"):
    w = f' font-weight="{weight}"' if weight else ""
    return f'<text x="{x}" y="{y}" font-size="{size}px"{w} fill="{fill}" text-anchor="{anchor}">{s}</text>'


def pill(x, cy, s, ink):
    """A label pill whose left edge is at x"""
    w = width(s, 10) + 10
    return (f'<rect x="{x}" y="{cy - 8}" width="{w:.1f}" height="16" rx="3" fill="#FFFFFF" stroke="{PILL_LINE}" stroke-width="0.75"/>'
            + text(x + w / 2, cy + 3.6, s, 10, ink, anchor="middle"))


def entry(x, y1, y2, color):
    """A short arrow pointing down at the place where execution enters a piece of code"""
    return (f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2 - 7}" stroke="{color}" stroke-width="1.5"/>'
            f'<polygon points="{x - 4},{y2 - 8} {x + 4},{y2 - 8} {x},{y2}" fill="{color}"/>')


def lane(y, h, name):
    return (f'<rect x="0.5" y="{y + 0.5}" width="{W - 1}" height="{h}" rx="12" fill="{LANE_FILL}" stroke="{LANE_LINE}"/>'
            + text(8, y + 17, name, 10, NAME, 600))


def main():
    parts = []
    # A long call: the loop starts in the interpreter and moves to the OSR code at the head of the loop
    parts.append(lane(0, 120, "1回の呼び出しの途中で切り替わる（OSR）"))
    switch = 310
    parts.append(bar(28, switch, 60, 36, TEAL, right=False))
    parts.append(bar(switch, 612, 60, 36, GRAY, left=False))
    parts.append(ticks(28, switch, 86) + ticks(switch, 612, 86))
    parts.append(text((28 + switch) / 2, 81, "インタプリタ", 11, "#FFFFFF", 600, "middle"))
    parts.append(text((switch + 612) / 2, 81, "OSR 用のコード（tier 3・4）", 11, "#FFFFFF", 600, "middle"))
    parts.append(entry(switch, 34, 58, TEAL))
    parts.append(pill(switch + 8, 40, "ループの先頭（位置 11）から入る", TEAL))
    parts.append(text(28, 112, "目盛り1つが、ループの1周", 9, NOTE))
    # The next call enters the normal compiled code at the head of the method
    parts.append(lane(136, 100, "次の呼び出しは、先頭から通常のコードで実行"))
    parts.append(bar(28, 380, 196, 36, GRAY))
    parts.append(ticks(28, 380, 222))
    parts.append(text(204, 217, "通常のコード（tier 3・4）", 11, "#FFFFFF", 600, "middle"))
    parts.append(entry(36, 170, 194, TEAL))
    parts.append(pill(44, 176, "メソッドの先頭から入る", TEAL))
    # Time inside each call
    parts.append(f'<line x1="28" y1="254" x2="604" y2="254" stroke="{INK}" stroke-width="1"/>'
                 f'<polygon points="604,250 612,254 604,258" fill="{INK}"/>')
    parts.append(text(612, 268, "それぞれの呼び出しの中の時間", 9, NOTE, anchor="end"))
    print(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 -12 {W + 24} {H + 24}" role="img">')
    print("\n".join(parts))
    print("</svg>")


if __name__ == "__main__":
    main()
