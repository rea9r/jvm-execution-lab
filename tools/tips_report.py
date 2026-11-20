"""Summarize results/tips: the startup runs (class directory, JAR, AOT cache, C1 only), the runs that write the
compilation log into the folder shared with the host, and the 8,000-byte limit.

For the startup runs, each cell is the median over the runs of the median time per call in a range of rounds.
"C2 from" is the round in which the C2 compilation of the normal (non-OSR) code of Cart.total started.

usage: python3 tools/tips_report.py results/tips
"""
import csv
import re
import statistics
import sys
from pathlib import Path

DIR = Path(sys.argv[1])
RANGES = [(1, 1), (2, 6), (7, 20), (21, 60), (61, 100), (101, 500)]
NAMES = {"dir": "class directory", "jar": "JAR", "aot": "JAR + AOT cache", "c1": "JAR + C1 only",
         "logsync": "JAR, log in the shared folder", "logasync": "JAR, log in the shared folder, -Xlog:async"}


def load(path):
    return [(int(r["start_ns"]), int(r["elapsed_ns"]) / 1000) for r in csv.DictReader(open(path))]


def c2_round(log, rows):
    starts = [s for s, _ in rows]
    for line in open(log):
        m = re.match(r"\[(\d+)ns\]\s+\d+\s+4\s+Cart::total \(", line)
        if m and "made not entrant" not in line:
            return sum(1 for s in starts if s <= int(m.group(1)))
    return "-"


print("| run | " + " | ".join(f"{a}" if a == b else f"{a}-{b}" for a, b in RANGES) + " | sum of 1-100 | C2 from |")
print("| --- |" + " ---: |" * (len(RANGES) + 2))
for key, name in NAMES.items():
    paths = sorted(DIR.glob(f"{key}-*.csv"))
    runs = [load(p) for p in paths]
    cells = [statistics.median(statistics.median(t for _, t in r[a - 1:b]) for r in runs) for a, b in RANGES]
    first100 = statistics.median(sum(t for _, t in r[:100]) for r in runs) / 1000
    c2 = [c2_round(p.with_suffix(".log"), r) for p, r in zip(paths, runs)]
    print(f"| {name} | " + " | ".join(f"{c:.1f}" for c in cells) + f" | {first100:.2f}ms | {c2} |")

print()
for line in (DIR / "huge-size.txt").read_text().split("\n"):
    if line:
        name, last = line.split()
        print(f"{name}.f: {int(last) + 1} bytes")
for key in ("Huge8000", "Huge8004", "Huge8004-forced"):
    paths = sorted(DIR.glob(f"{key}-[0-9]*.csv"))
    per_run = [statistics.median(float(r["elapsed_us"]) for r in list(csv.DictReader(open(p)))[1:]) for p in paths]
    cls = key.split("-")[0]
    tiers = sorted({m.group(1) for p in paths for m in re.finditer(rf"\s(\d)\s+{cls}::f \(", p.with_suffix(".log").read_text())})
    print(f"{key}: rounds 2-5 median {statistics.median(per_run) / 1000:.1f}ms per 20,000 calls, tiers of f: {tiers or 'none'}")
