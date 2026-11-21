#!/usr/bin/env node
// Open an SVG exported from the Archify viewer in headless Chrome, check it, write the computed paint and text styles
// (and positions moved by CSS) onto each element, and drop the stylesheets, viewer data attributes, titles and
// metadata. The result is a static SVG small enough for a Zenn html-embed block (50KB). Embedded web fonts and the
// background grid are dropped too.
//
// Checks, printed as WARN lines (exit code 1 with --strict when any is found):
//   - a relationship that starts or ends away from the middle of a box side (more than 3px off)
//   - text whose color has a contrast ratio under 4.5 against the shape right behind it
//   - parallel lines too close: a relationship within 12px of another relationship, a frame border or a box side,
//     or two frame borders within 8px of each other
//   - a relationship label or a frame name that touches a frame border, a box, another line or another label
//   - a relationship label on its own line, or more than 8px away from it (labels sit beside their lines)
//   - boxes of different colors stacked in the same column
//   - a legend closer than 24px to a box
//
// usage: node freeze_svg.mjs <exported.svg> <out.svg> [--legend <items.json>] [--legend-x <node-id>]
//                            [--legend-baseline <frame-name-prefix>] [--edge-label-size <px>] [--step-badges]
//                            [--labels-beside-lines] [--strict]
//   --legend draws a legend from a JSON list of {"fill", "stroke", "label"} (plus an optional {"title"} object),
//   for diagrams exported with meta.legend.mode "hidden". Its left edge lines up with the box --legend-x, and its
//   title sits on the baseline of the frame name that starts with --legend-baseline.
//   --step-badges turns a circled digit at the start of a relationship label (① to ⑳, or ❶ to ❿) into a filled circle with the
//   number in it, drawn at the left end of the label. A circled digit in 8px label text is too small to read.
//   --edge-label-size sets the text size of the relationship labels (Archify draws 8px) and resizes their pills.
//   --labels-beside-lines moves every relationship label 4px off its own line: above a horizontal segment, to the
//   right of a vertical one. Archify puts some labels on the line and some beside it.
import { spawn } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const args = process.argv.slice(2);
const positional = [];
const opts = { legend: null, legendX: null, legendBaseline: null, stepBadges: false, edgeLabelSize: null, besideLines: false };
let strict = false;
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--legend') opts.legend = args[++i];
  else if (args[i] === '--legend-x') opts.legendX = args[++i];
  else if (args[i] === '--legend-baseline') opts.legendBaseline = args[++i];
  else if (args[i] === '--step-badges') opts.stepBadges = true;
  else if (args[i] === '--edge-label-size') opts.edgeLabelSize = Number(args[++i]);
  else if (args[i] === '--labels-beside-lines') opts.besideLines = true;
  else if (args[i] === '--strict') strict = true;
  else positional.push(args[i]);
}
const [input, output] = positional;
if (!input || !output || (opts.legend && (!opts.legendX || !opts.legendBaseline))) {
  console.error('usage: freeze_svg.mjs <exported.svg> <out.svg> [--legend <items.json> --legend-x <node-id> --legend-baseline <frame-name-prefix>] [--edge-label-size <px>] [--step-badges] [--labels-beside-lines] [--strict]');
  process.exit(2);
}
let legendItems = null;
let legendTitle = '凡例';
if (opts.legend) {
  const raw = JSON.parse(readFileSync(opts.legend, 'utf8'));
  legendItems = raw.filter((item) => item.label);
  legendTitle = raw.find((item) => item.title)?.title ?? legendTitle;
}

const FREEZE = `(() => {
  const NS = 'http://www.w3.org/2000/svg';
  const svg = document.querySelector('svg');
  const style = document.createElementNS(NS, 'style');
  style.textContent = '* { animation: none !important; transition: none !important; }';
  svg.appendChild(style);
  const vb = svg.viewBox.baseVal;
  svg.style.width = vb.width + 'px';
  svg.style.height = vb.height + 'px';
  const report = [];
  const warn = (msg) => report.push('WARN  ' + msg);
  const r0 = (v) => Math.round(v);

  // Relationship labels. --edge-label-size sets the size of their text (Archify draws 8px), and --step-badges turns
  // a circled digit at the start of a label into a filled circle with the number in it. The white pill is resized to
  // fit, around the same centre. This runs before the checks, so they see the resized labels.
  const labelSize = ${JSON.stringify(opts.edgeLabelSize)}, stepBadges = ${JSON.stringify(opts.stepBadges)};
  if (labelSize || stepBadges) {
    for (const t of svg.querySelectorAll('g[data-edge-from] > text')) {
      const pill = t.parentElement.querySelector('rect.c-mask');
      if (!pill) continue;
      const m = stepBadges ? /^([\u2460-\u2473\u2776-\u277f])\s*/.exec(t.textContent) : null;
      if (!labelSize && !m) continue;
      let n = null;
      if (m) {
        const code = m[1].codePointAt(0);
        n = code >= 0x2776 ? code - 0x2776 + 1 : code - 0x2460 + 1;
        t.textContent = t.textContent.slice(m[0].length);
      }
      if (labelSize) t.style.fontSize = labelSize + 'px';
      const size = parseFloat(getComputedStyle(t).fontSize);
      const w = t.getComputedTextLength(), h = size + 6, r = h / 2;
      const cx = parseFloat(pill.getAttribute('x')) + parseFloat(pill.getAttribute('width')) / 2;
      const cy = parseFloat(pill.getAttribute('y')) + parseFloat(pill.getAttribute('height')) / 2;
      const lead = n ? 3 + 2 * r + 4 : 5, width = lead + w + 5, x = cx - width / 2, baseline = cy + 0.36 * size;
      for (const [k, v] of Object.entries({ x, y: cy - h / 2, width, height: h })) pill.setAttribute(k, v);
      t.setAttribute('x', x + lead + w / 2);
      t.setAttribute('y', baseline);
      if (n) {
        const circle = document.createElementNS(NS, 'circle');
        for (const [k, v] of Object.entries({ cx: x + 3 + r, cy, r, fill: getComputedStyle(t).fill })) circle.setAttribute(k, v);
        const num = document.createElementNS(NS, 'text');
        for (const [k, v] of Object.entries({ x: x + 3 + r, y: baseline, 'font-size': size + 'px', 'font-weight': '700', fill: '#FFFFFF', 'text-anchor': 'middle' })) num.setAttribute(k, v);
        num.textContent = String(n);
        t.after(circle, num);
      }
    }
  }

  // Labels beside their lines: each relationship label moves 4px off the nearest segment of its own line, above a
  // horizontal segment or to the right of a vertical one, and stays within that segment where it fits.
  if (${JSON.stringify(opts.besideLines)}) {
    const gap = 4;
    for (const g of svg.querySelectorAll('g[data-edge-from]')) {
      const pill = g.querySelector(':scope > rect.c-mask');
      const path = svg.querySelector('path[data-edge-id="' + g.dataset.edgeId + '"][data-composition-points]:not([data-graph-role="automatic-crossover-underlay"])');
      if (!pill || !path) continue;
      const pts = path.dataset.compositionPoints.split(';').map((p) => p.split(',').map(Number));
      const x = +pill.getAttribute('x'), y = +pill.getAttribute('y'), w = +pill.getAttribute('width'), h = +pill.getAttribute('height');
      const cx = x + w / 2, cy = y + h / 2;
      let best = null;
      for (let i = 1; i < pts.length; i++) {
        const [x1, y1] = pts[i - 1], [x2, y2] = pts[i];
        const horiz = Math.abs(y1 - y2) < 0.5, vert = Math.abs(x1 - x2) < 0.5;
        if (!horiz && !vert) continue;
        const a = horiz ? Math.min(x1, x2) : Math.min(y1, y2), b = horiz ? Math.max(x1, x2) : Math.max(y1, y2), c = horiz ? y1 : x1;
        const along = horiz ? cx : cy, across = horiz ? cy : cx;
        const d = Math.hypot(Math.max(a - along, along - b, 0), across - c);
        if (!best || d < best.d) best = { horiz, a, b, c, d };
      }
      if (!best) continue;
      const fit = (centre, size) => (best.b - best.a >= size + 12 ? Math.min(Math.max(centre, best.a + size / 2 + 6), best.b - size / 2 - 6) : (best.a + best.b) / 2);
      const nx = best.horiz ? fit(cx, w) - w / 2 : best.c + gap;
      const ny = best.horiz ? best.c - gap - h : fit(cy, h) - h / 2;
      const dx = nx - x, dy = ny - y;
      for (const el of g.querySelectorAll(':scope > rect.c-mask, :scope > text, :scope > circle')) {
        const [kx, ky] = el.tagName === 'circle' ? ['cx', 'cy'] : ['x', 'y'];
        el.setAttribute(kx, +el.getAttribute(kx) + dx);
        el.setAttribute(ky, +el.getAttribute(ky) + dy);
      }
    }
  }

  // Positions in the SVG's user space, after any CSS transform
  const toUser = (x, y) => { const p = svg.createSVGPoint(); p.x = x; p.y = y; return p.matrixTransform(svg.getScreenCTM().inverse()); };
  const userBox = (el) => {
    const r = el.getBoundingClientRect(), a = toUser(r.left, r.top), b = toUser(r.right, r.bottom);
    return { x: a.x, y: a.y, width: b.x - a.x, height: b.y - a.y };
  };
  const grow = (r, m) => ({ x: r.x - m, y: r.y - m, width: r.width + 2 * m, height: r.height + 2 * m });
  const overlaps = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
  const sides = (r, inset = 0) => [
    { o: 'h', c: r.y, a: r.x + inset, b: r.x + r.width - inset },
    { o: 'h', c: r.y + r.height, a: r.x + inset, b: r.x + r.width - inset },
    { o: 'v', c: r.x, a: r.y + inset, b: r.y + r.height - inset },
    { o: 'v', c: r.x + r.width, a: r.y + inset, b: r.y + r.height - inset },
  ];
  const segHitsBox = (s, r) => s.o === 'h'
    ? s.c >= r.y && s.c <= r.y + r.height && Math.min(s.b, r.x + r.width) > Math.max(s.a, r.x)
    : s.c >= r.x && s.c <= r.x + r.width && Math.min(s.b, r.y + r.height) > Math.max(s.a, r.y);

  const segDistance = (s, r) => {
    const [ax, ay, bx, by] = s.o === 'h' ? [s.a, s.c, s.b, s.c] : [s.c, s.a, s.c, s.b];
    const dx = Math.max(r.x - Math.max(ax, bx), Math.min(ax, bx) - (r.x + r.width), 0);
    const dy = Math.max(r.y - Math.max(ay, by), Math.min(ay, by) - (r.y + r.height), 0);
    return Math.hypot(dx, dy);
  };
  const boxes = {};
  const nodes = [];
  for (const g of svg.querySelectorAll('g[data-node-id]')) {
    const rect = g.querySelector('rect:not(.c-mask)') || g.querySelector('rect');
    if (!rect) continue;
    const box = userBox(rect);
    boxes[g.dataset.nodeId] = box;
    nodes.push({ id: g.dataset.nodeId, box, fill: getComputedStyle(rect).fill, label: (g.querySelector('text')?.textContent || g.dataset.nodeId).trim() });
  }
  const frames = [...svg.querySelectorAll('rect[data-graph-role="structural-frame"]')].map((el) => ({
    name: el.dataset.compositionFrameLabel || 'frame', box: userBox(el), rx: parseFloat(getComputedStyle(el).rx) || 0,
  }));
  const edges = [];
  for (const p of svg.querySelectorAll('path[data-edge-from]')) {
    if (p.getAttribute('data-graph-role') === 'automatic-crossover-underlay' || !p.dataset.compositionPoints) continue;
    const pts = p.dataset.compositionPoints.split(';').map((s) => s.split(',').map(Number));
    const segs = [];
    for (let i = 1; i < pts.length; i++) {
      const [x1, y1] = pts[i - 1], [x2, y2] = pts[i];
      if (Math.abs(y1 - y2) < 0.5) segs.push({ o: 'h', c: y1, a: Math.min(x1, x2), b: Math.max(x1, x2) });
      else if (Math.abs(x1 - x2) < 0.5) segs.push({ o: 'v', c: x1, a: Math.min(y1, y2), b: Math.max(y1, y2) });
    }
    edges.push({ id: p.dataset.edgeId || p.dataset.edgeFrom + '->' + p.dataset.edgeTo, from: p.dataset.edgeFrom, to: p.dataset.edgeTo, el: p, segs });
  }
  const labels = [];
  for (const rect of svg.querySelectorAll('g[data-edge-from] > rect.c-mask')) {
    const g = rect.parentElement;
    labels.push({ kind: 'edge', owner: g.dataset.edgeId, name: g.dataset.edgeLabel || g.textContent.trim(), box: userBox(rect) });
  }
  for (const g of svg.querySelectorAll('g[data-graph-role="structural-frame-label"]')) {
    const t = g.querySelector('text');
    if (t) labels.push({ kind: 'frame', owner: g.dataset.compositionFrameLabel, name: t.textContent.trim(), box: userBox(t) });
  }

  // 1. Relationship ends: each should sit at the middle of the side it touches
  const sideOffset = (pt, r) => {
    const tol = 14, inX = pt.x >= r.x - 1 && pt.x <= r.x + r.width + 1, inY = pt.y >= r.y - 1 && pt.y <= r.y + r.height + 1;
    if (inY && Math.abs(pt.x - r.x) <= tol) return ['左', Math.abs(pt.y - (r.y + r.height / 2))];
    if (inY && Math.abs(pt.x - (r.x + r.width)) <= tol) return ['右', Math.abs(pt.y - (r.y + r.height / 2))];
    if (inX && Math.abs(pt.y - r.y) <= tol) return ['上', Math.abs(pt.x - (r.x + r.width / 2))];
    if (inX && Math.abs(pt.y - (r.y + r.height)) <= tol) return ['下', Math.abs(pt.x - (r.x + r.width / 2))];
    return null;
  };
  for (const e of edges) {
    const len = e.el.getTotalLength();
    for (const [pt, id, which] of [[e.el.getPointAtLength(0), e.from, '始点'], [e.el.getPointAtLength(len), e.to, '終点']]) {
      const hit = boxes[id] && sideOffset(pt, boxes[id]);
      if (hit && hit[1] > 3) warn('線 ' + e.id + ' の' + which + 'が、' + id + ' の' + hit[0] + '辺の中央から ' + hit[1].toFixed(0) + 'px ずれている');
    }
  }

  // 2. Text contrast against the shape right behind the middle of the text
  const parse = (c) => { const m = /rgba?\\(([^)]+)\\)/.exec(c || ''); if (!m) return null; const v = m[1].split(',').map(Number); return { r: v[0], g: v[1], b: v[2], a: v.length > 3 ? v[3] : 1 }; };
  const lum = (c) => { const f = (x) => { x /= 255; return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  for (const t of svg.querySelectorAll('text')) {
    const text = t.textContent.trim();
    if (!text || getComputedStyle(t).display === 'none') continue;
    const fg = parse(getComputedStyle(t).fill);
    if (!fg) continue;
    const bb = t.getBoundingClientRect();
    let bg = { r: 255, g: 255, b: 255, a: 1 };
    for (const el of document.elementsFromPoint(bb.left + bb.width / 2, bb.top + bb.height / 2)) {
      if (el === t || ['text', 'tspan', 'svg', 'g', 'line', 'polyline'].includes(el.tagName)) continue;
      const c = parse(getComputedStyle(el).fill);
      if (c && c.a > 0) { bg = c; break; }
    }
    const l1 = lum(fg), l2 = lum(bg), ratio = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
    if (ratio < 4.5) warn('「' + text + '」の文字色 ' + getComputedStyle(t).fill + ' と下地のコントラスト比が ' + ratio.toFixed(2) + '（4.5 未満）');
  }

  // 3. Parallel lines too close. A relationship keeps 12px from other lines, frame borders and box sides; nested frame
  // borders keep 8px. Two relationships that leave the same box on one shared trunk (distance 0) are allowed.
  const lines = [];
  for (const e of edges) for (const s of e.segs) lines.push({ ...s, kind: 'edge', name: '線 ' + e.id, edge: e });
  for (const f of frames) for (const s of sides(f.box, f.rx)) lines.push({ ...s, kind: 'frame', name: '枠「' + f.name + '」' });
  for (const n of nodes) for (const s of sides(n.box, 4)) lines.push({ ...s, kind: 'box', name: '箱「' + n.label + '」' });
  const seen = new Set();
  for (let i = 0; i < lines.length; i++) {
    for (let j = i + 1; j < lines.length; j++) {
      const s = lines[i], t = lines[j];
      if (s.o !== t.o) continue;
      const withEdge = s.kind === 'edge' || t.kind === 'edge';
      if (!withEdge && !(s.kind === 'frame' || t.kind === 'frame')) continue;
      if (s.kind === 'edge' && t.kind === 'edge') {
        if (s.edge === t.edge) continue;
        if (Math.abs(s.c - t.c) < 0.5 && (s.edge.from === t.edge.from || s.edge.to === t.edge.to)) continue;
      }
      const d = Math.abs(s.c - t.c), overlap = Math.min(s.b, t.b) - Math.max(s.a, t.a), limit = withEdge ? 12 : 8;
      if (overlap <= 4 || d >= limit) continue;
      const key = s.name + '|' + t.name;
      if (seen.has(key)) continue;
      seen.add(key);
      warn(s.name + ' と ' + t.name + ' が、' + r0(overlap) + 'px の長さで ' + r0(d) + 'px まで近づいている（' + limit + 'px 以上あける）');
    }
  }

  // 4. Labels: a relationship label or a frame name keeps clear of frame borders, boxes, other lines and labels
  for (const L of labels) {
    const box = grow(L.box, 2);
    const what = (L.kind === 'edge' ? '線のラベル' : '枠の名前') + '「' + L.name + '」';
    for (const f of frames) if (sides(f.box).some((s) => segHitsBox(s, box))) warn(what + 'が、枠「' + f.name + '」の線にかかっている');
    for (const n of nodes) if (overlaps(box, n.box)) warn(what + 'が、箱「' + n.label + '」に重なっている');
    for (const e of edges) if (e.id !== L.owner && e.segs.some((s) => segHitsBox(s, box))) warn(what + 'の下を、線 ' + e.id + ' が通っている');
    if (L.kind === 'edge') {
      // Labels sit beside their own line, never on it, and close enough to read as belonging to it
      const own = edges.find((e) => e.id === L.owner);
      if (own) {
        if (own.segs.some((s) => segHitsBox(s, L.box))) warn(what + 'が、自分の線に重なっている（線のすぐ横に置く）');
        else if (Math.min(...own.segs.map((s) => segDistance(s, L.box))) > 8) warn(what + 'が、自分の線から 8px より離れている');
      }
    }
    for (const M of labels) if (M !== L && labels.indexOf(M) > labels.indexOf(L) && overlaps(box, grow(M.box, 2))) warn(what + 'と「' + M.name + '」が重なっている');
  }

  // 5. One column, one color: boxes stacked in a column (sharing most of their width) have the same fill
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i], b = nodes[j];
      const shared = Math.min(a.box.x + a.box.width, b.box.x + b.box.width) - Math.max(a.box.x, b.box.x);
      if (shared < 0.5 * Math.min(a.box.width, b.box.width) || a.fill === b.fill) continue;
      warn('同じ列に色の違う箱が縦に並んでいる：「' + a.label + '」（' + a.fill + '）と「' + b.label + '」（' + b.fill + '）');
    }
  }

  // Legend anchor, read before the attributes go: left edge of a box, baseline of a frame name
  let legendAt = null;
  const legendX = ${JSON.stringify(opts.legendX)}, legendBaseline = ${JSON.stringify(opts.legendBaseline)};
  if (legendX) {
    const g = [...svg.querySelectorAll('g[data-graph-role="structural-frame-label"]')].find((el) => (el.dataset.compositionFrameLabel || '').startsWith(legendBaseline));
    const t = g && g.querySelector('text');
    if (!boxes[legendX] || !t) throw new Error('legend anchor not found: ' + legendX + ' / ' + legendBaseline);
    const p = svg.createSVGPoint(); p.x = parseFloat(t.getAttribute('x')); p.y = parseFloat(t.getAttribute('y'));
    const q = p.matrixTransform(t.getScreenCTM()).matrixTransform(svg.getScreenCTM().inverse());
    legendAt = { x: boxes[legendX].x, y: q.y };
  }

  // Inherited properties are written only where they differ from the parent. The root keeps no font, so the text
  // uses the font of the page it is embedded in.
  // Every value is read first and written afterwards: removing a parent's class or data attributes changes which
  // rules match its children. Rectangle geometry and transforms set by CSS are kept as attributes.
  const props = ['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin',
    'stroke-opacity', 'opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor', 'dominant-baseline', 'letter-spacing'];
  const defaults = { 'fill-opacity': '1', 'stroke-opacity': '1', opacity: '1', 'stroke-dasharray': 'none', 'letter-spacing': 'normal',
    'dominant-baseline': 'auto', 'stroke-linecap': 'butt', 'stroke-linejoin': 'miter' };
  const inherited = new Set(['fill', 'fill-opacity', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap', 'stroke-linejoin',
    'stroke-opacity', 'font-family', 'font-size', 'font-weight', 'text-anchor', 'dominant-baseline', 'letter-spacing']);
  const plan = [];
  const removed = [];
  for (const el of svg.querySelectorAll('*')) {
    if (['style', 'title', 'desc', 'metadata', 'pattern'].includes(el.tagName)) continue;
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden') { removed.push(el); continue; }
    const parent = getComputedStyle(el.parentElement);
    const values = {};
    if (!(el.closest('defs') && el.tagName !== 'polygon' && el.tagName !== 'path')) {
      for (const p of props) {
        const v = cs.getPropertyValue(p);
        if (!v) continue;
        if (inherited.has(p) ? v !== parent.getPropertyValue(p) : v !== defaults[p]) values[p] = v;
      }
    }
    if (el.tagName === 'rect') {
      for (const p of ['x', 'y', 'width', 'height']) {
        const v = parseFloat(cs.getPropertyValue(p));
        if (!Number.isNaN(v) && v !== parseFloat(el.getAttribute(p))) values[p] = String(v);
      }
    }
    const tf = cs.getPropertyValue('transform');
    if (tf && tf !== 'none' && !el.closest('defs')) values.transform = tf;
    plan.push([el, values, cs.getPropertyValue('filter')]);
  }
  for (const [el, values, filter] of plan) {
    for (const a of [...el.attributes]) {
      if (a.name.startsWith('data-') || a.name === 'class' || a.name === 'style' || a.name.startsWith('aria-') || a.name === 'tabindex' || a.name === 'role') el.removeAttribute(a.name);
    }
    for (const [p, v] of Object.entries(values)) el.setAttribute(p, v);
    if (filter && filter !== 'none') el.setAttribute('style', 'filter:' + filter);
  }
  for (const el of removed) el.remove();
  for (const el of svg.querySelectorAll('style, title, desc, metadata, pattern')) el.remove();
  for (const el of svg.querySelectorAll('rect')) if (/url\\(["']?#grid["']?\\)/.test(el.getAttribute('fill') || '')) el.remove();
  for (const a of [...svg.attributes]) if (!['viewBox', 'xmlns'].includes(a.name)) svg.removeAttribute(a.name);
  // Crop Archify's outer margin: the canvas background goes
  for (const el of svg.querySelectorAll('rect')) {
    const w = parseFloat(el.getAttribute('width')), h = parseFloat(el.getAttribute('height'));
    if (w >= vb.width && h >= vb.height) el.remove();
  }

  if (legendAt) {
    const items = ${JSON.stringify(legendItems)};
    const g = document.createElementNS(NS, 'g');
    const set = (el, attrs) => { for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v); return el; };
    const title = set(document.createElementNS(NS, 'text'), { x: legendAt.x, y: legendAt.y, 'font-size': '12px', 'font-weight': '650', fill: 'rgb(34, 34, 34)' });
    title.textContent = ${JSON.stringify(legendTitle)};
    g.appendChild(title);
    items.forEach((item, i) => {
      const y = legendAt.y + 20 + 18 * i;
      g.appendChild(set(document.createElementNS(NS, 'rect'), { x: legendAt.x, y: y - 9, width: 16, height: 10, rx: 2.5, fill: item.fill, stroke: item.stroke || item.fill, 'stroke-width': 1 }));
      const t = set(document.createElementNS(NS, 'text'), { x: legendAt.x + 22, y, 'font-size': '10px', fill: 'rgb(85, 85, 85)' });
      t.textContent = item.label;
      g.appendChild(t);
    });
    svg.appendChild(g);
    // 6. The legend stays 24px away from every box, so it does not read as a note on one of them
    const lb = g.getBBox();
    for (const n of nodes) {
      const dx = Math.max(n.box.x - (lb.x + lb.width), lb.x - (n.box.x + n.box.width), 0);
      const dy = Math.max(n.box.y - (lb.y + lb.height), lb.y - (n.box.y + n.box.height), 0);
      if (Math.hypot(dx, dy) < 24) warn('凡例が箱「' + n.label + '」から ' + r0(Math.hypot(dx, dy)) + 'px しか離れていない（24px 以上あける）');
    }
    for (const f of frames) if (sides(f.box).some((s) => segHitsBox(s, grow(lb, 2)))) warn('凡例が、枠「' + f.name + '」の線にかかっている');
  }

  // The viewBox hugs what is drawn plus 12px
  const bbox = svg.getBBox();
  const m = 12;
  svg.setAttribute('viewBox', [bbox.x - m, bbox.y - m, bbox.width + 2 * m, bbox.height + 2 * m].map((v) => Math.round(v)).join(' '));
  svg.setAttribute('role', 'img');
  return { svg: svg.outerHTML, report };
})()`;

const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = mkdtempSync(join(tmpdir(), 'freeze-svg-'));
const chrome = spawn(chromePath, ['--headless=new', '--disable-gpu', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--window-size=1800,1200', 'about:blank'], { stdio: 'ignore' });

let exitCode = 1;
try {
  const port = await waitForPort(profile);
  const page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page');
  const tab = await connect(page.webSocketDebuggerUrl);
  await tab.send('Page.enable');
  const loaded = tab.once('Page.loadEventFired');
  await tab.send('Page.navigate', { url: pathToFileURL(resolve(input)).href });
  await loaded;
  await sleep(500);
  const { result, exceptionDetails } = await tab.send('Runtime.evaluate', { expression: FREEZE, returnByValue: true });
  if (exceptionDetails) throw new Error(JSON.stringify(exceptionDetails));
  const svg = result.value.svg.replace(/\n\s*\n+/g, '\n');
  writeFileSync(output, svg);
  console.log(`${output}: ${Buffer.byteLength(svg).toLocaleString()} bytes (from ${readFileSync(input).length.toLocaleString()})`);
  for (const line of result.value.report) console.log(line);
  console.log(`${result.value.report.length} WARN`);
  exitCode = strict && result.value.report.length > 0 ? 1 : 0;
} catch (e) {
  console.error(e.message);
} finally {
  chrome.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(exitCode);

async function waitForPort(dir) {
  for (let i = 0; i < 50; i++) {
    try {
      return readFileSync(join(dir, 'DevToolsActivePort'), 'utf8').split('\n')[0];
    } catch {
      await sleep(200);
    }
  }
  throw new Error('Chrome did not start (DevToolsActivePort not found)');
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const waiters = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) rej(new Error(JSON.stringify(msg.error)));
      else res(msg.result);
    } else if (msg.method) {
      for (const w of waiters.filter((x) => x.method === msg.method)) {
        waiters.splice(waiters.indexOf(w), 1);
        w.res(msg.params);
      }
    }
  };
  return new Promise((ready) => {
    ws.onopen = () => ready({
      send: (method, params = {}) => new Promise((res, rej) => {
        const i = ++id;
        pending.set(i, { res, rej });
        ws.send(JSON.stringify({ id: i, method, params }));
      }),
      once: (method) => new Promise((res) => waiters.push({ method, res })),
    });
  });
}
