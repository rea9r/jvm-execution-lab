# The Archify diagrams

`overview.html` and `tiers.html` (one level up) are drawn with [Archify](https://github.com/tt-a1i/archify) and frozen
into static SVGs, so that they fit a Zenn html-embed block (50KB, no scripts or web fonts). `osr.html` and
`bytecode.html` are drawn by `tools/figures/osr_figure.py` and `tools/figures/bytecode_figure.py` in the same colors.

| File | Contents |
| --- | --- |
| `jvm-flow.candidate.json` | The Archify candidate: boxes, frames and relationships with their positions |
| `archify-palette.css` | Colors by role: processing in teal, memory in dark gray, outside the JVM in white |
| `jvm-flow.css` | Colors of the frames, and the positions of the frame names |
| `jvm-flow.legend.json` | The legend drawn by `freeze_svg.mjs` |
| `jvm-flow.svg` | The static SVG |
| `jvm-tiers.candidate.json`, `jvm-tiers.css`, `jvm-tiers.svg` | The same for the tier figure, which has no legend |

To draw it again (Node.js, Python 3 and Google Chrome; `ARCHIFY` is the Archify skill folder):

```bash
node $ARCHIFY/bin/archify.mjs finalize architecture figures/archify/jvm-flow.candidate.json build/archify/jvm-flow.html --quality showcase --json
node tools/figures/archify-export.mjs build/archify/jvm-flow.html build/archify/export light svg-light --css figures/archify/archify-palette.css --css figures/archify/jvm-flow.css
node tools/figures/freeze_svg.mjs build/archify/export/1-jvm-light.svg figures/archify/jvm-flow.svg --legend figures/archify/jvm-flow.legend.json --legend-x classfile --legend-baseline JVM --edge-label-size 10 --step-badges --labels-beside-lines --strict
python3 tools/figures/archify_embed.py figures/archify/jvm-flow.svg jvmflow --min-width 1416 > figures/overview.html
```

The other figures:

```bash
node $ARCHIFY/bin/archify.mjs finalize architecture figures/archify/jvm-tiers.candidate.json build/archify/jvm-tiers.html --quality showcase --json
node tools/figures/archify-export.mjs build/archify/jvm-tiers.html build/archify/export light svg-light --css figures/archify/archify-palette.css --css figures/archify/jvm-tiers.css
node tools/figures/freeze_svg.mjs build/archify/export/tier-light.svg figures/archify/jvm-tiers.svg --edge-label-size 10 --labels-beside-lines --strict
python3 tools/figures/archify_embed.py figures/archify/jvm-tiers.svg jvmtiers --min-width 942 > figures/tiers.html
python3 tools/figures/osr_figure.py > figures/osr.svg && python3 tools/figures/archify_embed.py figures/osr.svg jvmosr --min-width 672 > figures/osr.html
python3 tools/figures/bytecode_figure.py > figures/bytecode.svg && python3 tools/figures/archify_embed.py figures/bytecode.svg jvmbytecode --min-width 672 > figures/bytecode.html
```

`freeze_svg.mjs` also checks the diagram and prints a WARN line for each problem it finds: a line that leaves a box
away from the middle of a side, text with a contrast ratio under 4.5, parallel lines closer than 12px, a label on a
frame border or another line, boxes of different colors in one column, and a legend too close to a box.
