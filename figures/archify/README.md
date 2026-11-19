# The overview diagram

`overview.html` (one level up) is drawn with [Archify](https://github.com/tt-a1i/archify) and frozen into a static SVG,
so that it fits a Zenn html-embed block (50KB, no scripts or web fonts).

| File | Contents |
| --- | --- |
| `jvm-flow.candidate.json` | The Archify candidate: boxes, frames and relationships with their positions |
| `archify-palette.css` | Colors by role: processing in teal, memory in dark gray, outside the JVM in white |
| `jvm-flow.css` | Colors of the frames, and the positions of the frame names |
| `jvm-flow.legend.json` | The legend drawn by `freeze_svg.mjs` |
| `jvm-flow.svg` | The static SVG |

To draw it again (Node.js, Python 3 and Google Chrome; `ARCHIFY` is the Archify skill folder):

```bash
node $ARCHIFY/bin/archify.mjs finalize architecture figures/archify/jvm-flow.candidate.json build/archify/jvm-flow.html --quality showcase --json
node tools/figures/archify-export.mjs build/archify/jvm-flow.html build/archify/export light svg-light --css figures/archify/archify-palette.css --css figures/archify/jvm-flow.css
node tools/figures/freeze_svg.mjs build/archify/export/1-jvm-light.svg figures/archify/jvm-flow.svg --legend figures/archify/jvm-flow.legend.json --legend-x classfile --legend-baseline JVM --strict
python3 tools/figures/archify_embed.py figures/archify/jvm-flow.svg jvmflow --min-width 1290 > figures/overview.html
```

`freeze_svg.mjs` also checks the diagram and prints a WARN line for each problem it finds: a line that leaves a box
away from the middle of a side, text with a contrast ratio under 4.5, parallel lines closer than 12px, a label on a
frame border or another line, boxes of different colors in one column, and a legend too close to a box.
