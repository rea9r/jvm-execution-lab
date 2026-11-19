"""Split each warmup run into stages at the points where the code of Cart.total changed, and print the median time per stage.

The stage boundaries come from the compilation log:
  - C1 OSR version started      ("% tier 3 Cart::total" without "made not entrant")
  - C1 normal version installed  (first round after the tier 3 normal compile started)
  - C2 OSR version installed     (tier 3 OSR version "made not entrant")
  - C2 normal version installed  (tier 3 normal version "made not entrant")

usage: python3 warmup_report.py results/warmup
"""
import bisect
import glob
import os
import re
import statistics
import sys

LINE = re.compile(r"^\[(\d+)ns\]\s+(\d+)\s+([%sbn!]*)\s*(\d)?\s+(\S+)(.*)$")


def load_rounds(path):
    starts, elapsed = [], []
    with open(path) as f:
        next(f)
        for row in f:
            _, s, e = row.strip().split(",")
            starts.append(int(s))
            elapsed.append(int(e) / 1000)
    return starts, elapsed


def total_events(path):
    events = {}
    with open(path) as f:
        for row in f:
            m = LINE.match(row.rstrip())
            if not m or m.group(5) != "Cart::total":
                continue
            ts, _, attrs, tier, _, rest = m.groups()
            osr = "%" in attrs
            replaced = "made not entrant" in rest
            key = (tier, osr, replaced)
            events.setdefault(key, int(ts))
    return events


def round_of(starts, ts):
    return bisect.bisect_right(starts, ts)


def main():
    directory = sys.argv[1]
    stage_names = [
        "1回目",
        "2回目〜C1 の OSR 版まで",
        "C1 の OSR 版・通常の版",
        "C2 の OSR 版ができてから通常の版まで",
        "C2 の通常の版",
    ]
    per_stage = {name: [] for name in stage_names}
    for csv in sorted(glob.glob(os.path.join(directory, "jit-*.csv"))):
        log = csv.replace(".csv", ".log")
        starts, elapsed = load_rounds(csv)
        ev = total_events(log)
        c1_osr = round_of(starts, ev[("3", True, False)])
        c2_osr = round_of(starts, ev[("3", True, True)])
        c2 = round_of(starts, ev[("3", False, True)])
        # rounds are 1-based; a boundary round is a mix of two stages, so it is left out
        ranges = [(1, 1), (2, c1_osr - 1), (c1_osr + 3, c2_osr - 1), (c2_osr + 1, c2 - 1), (c2 + 1, len(starts))]
        row = []
        for name, (lo, hi) in zip(stage_names, ranges):
            values = elapsed[lo - 1:hi]
            median = statistics.median(values)
            per_stage[name].append(median)
            row.append(f"{lo}-{hi}:{median:.1f}")
        print(os.path.basename(csv), " ".join(row), f"(C1 OSR {c1_osr}, C2 OSR {c2_osr}, C2 {c2})")

    xint = []
    for csv in sorted(glob.glob(os.path.join(directory, "xint-*.csv"))):
        _, elapsed = load_rounds(csv)
        xint.append((elapsed[0], statistics.median(elapsed[1:])))
    print()
    print("| ラウンド | 1回の時間（5回の中央値） |")
    print("| --- | ---: |")
    for name in stage_names:
        print(f"| {name} | {statistics.median(per_stage[name]):.1f}µs |")
    print(f"| -Xint の1回目 | {statistics.median(x[0] for x in xint):.1f}µs |")
    print(f"| -Xint の2回目以降 | {statistics.median(x[1] for x in xint):.1f}µs |")


if __name__ == "__main__":
    main()
