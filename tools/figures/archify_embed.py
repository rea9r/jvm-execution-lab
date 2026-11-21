"""Turn an SVG exported from the Archify viewer into an HTML snippet for a Zenn html-embed block.

html-embed allows 50KB and no external fonts, so the embedded web fonts are dropped (the text falls back to the
local monospace and Japanese faces) and the background grid is removed.

usage: python3 tools/figures/archify_embed.py <exported.svg> <name> [--min-width PX] [--pad-y PX] > figures/<name>.html
--min-width keeps the figure at least that wide; narrower screens scroll it sideways inside the embed.
--pad-y is the white space above and below the figure (8px by default).

The embed shows at most 500px of height and scrolls the rest. When the figure scrolls sideways, a scrollbar that
takes up space (up to about 17px) is part of that height, so the figure must leave room for it.
"""
import argparse
import re
import sys

EMBED_MAX_HEIGHT = 500
SCROLLBAR = 17
# the width of the article body on zenn.dev
ARTICLE_WIDTH = 700
PAD_X = 4


def heights(svg, min_width, pad_y):
    """The rendered height when the figure scrolls sideways, and when it fills the article width"""
    _, _, vb_w, vb_h = (float(v) for v in re.search(r'viewBox="([^"]+)"', svg).group(1).split())
    at = lambda width: vb_h * (width - 2 * PAD_X) / vb_w + 2 * pad_y
    return at(min_width), at(max(min_width, ARTICLE_WIDTH))


def strip(svg):
    svg = re.sub(r"@font-face\s*\{[^}]*\}", "", svg)
    # the dotted background grid: its pattern definition and the rectangle filled with it
    svg = re.sub(r'<pattern id="grid".*?</pattern>', "", svg, flags=re.S)
    svg = re.sub(r'<rect[^>]*fill="url\(#grid\)"[^>]*/>', "", svg)
    svg = re.sub(r"<\?xml[^>]*\?>", "", svg)
    svg = re.sub(r"\n\s*\n+", "\n", svg)
    return svg.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("svg")
    parser.add_argument("name")
    parser.add_argument("--min-width", type=int, default=600)
    parser.add_argument("--pad-y", type=int, default=8)
    args = parser.parse_args()
    svg = strip(open(args.svg, encoding="utf-8").read())
    scrolled, filled = heights(svg, args.min_width, args.pad_y)
    if scrolled + SCROLLBAR > EMBED_MAX_HEIGHT or filled > EMBED_MAX_HEIGHT:
        sys.exit(f"{args.name}: {scrolled:.0f}px high (+{SCROLLBAR}px for the sideways scrollbar), "
                 f"{filled:.0f}px at the article width; the embed shows {EMBED_MAX_HEIGHT}px. "
                 "Lower --pad-y or make the figure shorter")
    svg = re.sub(r"<svg\b", f'<svg class="{args.name}-svg"', svg, count=1)
    html = (
        f'<figure class="{args.name}">\n{svg}\n</figure>\n'
        "<style>\n"
        f"  .{args.name} {{ margin: 0; padding: {args.pad_y}px {PAD_X}px; min-width: {args.min_width}px; box-sizing: border-box; background: #ffffff; }}\n"
        f"  .{args.name} > svg {{ display: block; width: 100%; height: auto; }}\n"
        "</style>"
    )
    size = len(html.encode())
    print(f"{args.name}: {size:,} bytes", file=sys.stderr)
    if size > 50 * 1024:
        sys.exit(f"{args.name}: {size:,} bytes is over the 50KB limit of html-embed")
    print(html)


if __name__ == "__main__":
    main()
