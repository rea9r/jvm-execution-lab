"""Draw the figure that lines up the source of Cart.total with its bytecode, as a static SVG.

The loop is shaded in both listings, and the two method calls are filled in teal, so that the positions 11, 27 and
30 can be found again in the JIT logs later in the article. Colors and text sizes follow the Archify overview; the
code is set in the local monospace face.

usage: python3 tools/figures/bytecode_figure.py > figures/bytecode.svg
"""

TEAL, NAME, INK, NOTE = "#00708F", "#2E3A42", "#222222", "#555555"
FACE, FACE_LINE, LOOP = "#EAF1F4", "#A7BCC4", "#C9DDE3"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

SOURCE = [
    ("public static long total(Item[] items) {", None),
    ("    long sum = 0;", None),
    ("    for (Item item : items) {", "loop"),
    ("        sum += withTax(subtotal(item));", "call"),
    ("    }", "loop"),
    ("    return sum;", None),
    ("}", None),
]

BYTECODE = [
    (0, "lconst_0"), (1, "lstore_1"), (2, "aload_0"), (3, "astore_3"), (4, "aload_3"), (5, "arraylength"),
    (6, "istore 4"), (8, "iconst_0"), (9, "istore 5"), (11, "iload 5"), (13, "iload 4"), (15, "if_icmpge 41"),
    (18, "aload_3"), (19, "iload 5"), (21, "aaload"), (22, "astore 6"), (24, "lload_1"), (25, "aload 6"),
    (27, "invokestatic subtotal"), (30, "invokestatic withTax"), (33, "ladd"), (34, "lstore_1"),
    (35, "iinc 5, 1"), (38, "goto 11"), (41, "lload_1"), (42, "lreturn"),
]

ROW = 13
TOP = 40


def text(x, y, s, size, fill, weight=None, anchor="start", mono=False):
    w = f' font-weight="{weight}"' if weight else ""
    f = f' font-family="{MONO}"' if mono else ""
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<text x="{x}" y="{y}" font-size="{size}px"{w}{f} fill="{fill}" text-anchor="{anchor}" xml:space="preserve">{s}</text>'


def card(x, y, w, h, name):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{FACE}" stroke="{FACE_LINE}"/>'
            + text(x + 8, y + 17, name, 10, NAME, 600))


def row_y(i):
    return TOP + 16 + i * ROW


def main():
    parts = []
    # Bytecode listing, 26 rows; the loop is 11 to 38
    bx, bw = 286, 200
    bh = 16 + len(BYTECODE) * ROW + 12
    parts.append(card(bx, TOP - 24, bw, bh + 24, "バイトコード（javap -c）"))
    first = next(i for i, (pos, _) in enumerate(BYTECODE) if pos == 11)
    last = next(i for i, (pos, _) in enumerate(BYTECODE) if pos == 38)
    parts.append(f'<rect x="{bx + 8}" y="{row_y(first) - 10}" width="{bw - 16}" height="{(last - first + 1) * ROW + 1}" rx="3" fill="{LOOP}"/>')
    for i, (pos, op) in enumerate(BYTECODE):
        y = row_y(i)
        color = INK
        if op.startswith("invokestatic"):
            parts.append(f'<rect x="{bx + 8}" y="{y - 10}" width="{bw - 16}" height="{ROW}" rx="2" fill="{TEAL}"/>')
            color = "#FFFFFF"
        parts.append(text(bx + 40, y, f"{pos}:", 10, color, anchor="end", mono=True))
        parts.append(text(bx + 46, y, op, 10, color, mono=True))

    # Source at ordinary line spacing; the shading and the teal fill tell which bytecode each part becomes
    sx, sw, line = 0, 262, 16
    sh = 16 + len(SOURCE) * line + 8
    parts.append(card(sx, TOP - 24, sw, sh + 24, "ソース（Cart.total）"))
    loop = [i for i, (_, kind) in enumerate(SOURCE) if kind in ("loop", "call")]
    ly = TOP + 16 + loop[0] * line - 11
    parts.append(f'<rect x="{sx + 8}" y="{ly}" width="{sw - 16}" height="{len(loop) * line + 1}" rx="3" fill="{LOOP}"/>')
    for i, (code, kind) in enumerate(SOURCE):
        y = TOP + 16 + i * line
        color = INK
        if kind == "call":
            parts.append(f'<rect x="{sx + 8}" y="{y - 11}" width="{sw - 16}" height="{line - 1}" rx="2" fill="{TEAL}"/>')
            color = "#FFFFFF"
        parts.append(text(sx + 14, y, code, 10, color, mono=True))

    # Notes on the right of the bytecode: the loop bracket and the two calls
    nx = bx + bw + 14
    y1, y2 = row_y(first) - 9, row_y(last) + 2
    parts.append(f'<path d="M{nx} {y1} H{nx + 6} V{y2} H{nx}" fill="none" stroke="{NAME}" stroke-width="1"/>')
    parts.append(text(nx + 12, row_y(first) + 2, "ループ", 10, NAME, 600))
    parts.append(text(nx + 12, row_y(first) + 16, "位置 11〜38", 9, NOTE))
    call = BYTECODE.index((27, "invokestatic subtotal"))
    parts.append(text(nx + 12, row_y(call) + 1, "メソッドの呼び出し", 10, TEAL, 600))
    parts.append(text(nx + 12, row_y(call) + 15, "位置 27・30", 9, NOTE))
    parts.append(text(nx + 12, row_y(len(BYTECODE) - 1) + 2, "位置の番号は、JIT のログに", 9, NOTE))
    parts.append(text(nx + 12, row_y(len(BYTECODE) - 1) + 15, "@ 11・@ 27 の形で出る", 9, NOTE))

    width, height = nx + 140, TOP - 24 + bh + 24 + 12
    print(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-12 4 {width + 24} {height}" role="img">')
    print("\n".join(parts))
    print("</svg>")


if __name__ == "__main__":
    main()
