"""Turn an SVG exported from the Archify viewer into an HTML snippet for a Zenn html-embed block.

html-embed allows 50KB and no external fonts, so the embedded web fonts are dropped (the text falls back to the
local monospace and Japanese faces) and the background grid is removed.

usage: python3 tools/figures/archify_embed.py <exported.svg> <name> [--min-width PX] > figures/<name>.html
--min-width keeps the figure at least that wide; narrower screens scroll it sideways inside the embed.
"""
import argparse
import re
import sys


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
    args = parser.parse_args()
    svg = strip(open(args.svg, encoding="utf-8").read())
    svg = re.sub(r"<svg\b", f'<svg class="{args.name}-svg"', svg, count=1)
    html = (
        f'<figure class="{args.name}">\n{svg}\n</figure>\n'
        "<style>\n"
        f"  .{args.name} {{ margin: 0; padding: 8px 4px; min-width: {args.min_width}px; box-sizing: border-box; background: #ffffff; }}\n"
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
