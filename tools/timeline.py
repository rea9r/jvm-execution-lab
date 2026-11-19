"""Merge per-round timings with the JIT compilation log on the System.nanoTime() axis.

usage: python3 timeline.py rounds.csv compile.log [method-filter]
"""
import bisect
import re
import sys

LINE = re.compile(r"^\[(\d+)ns\]\s+(\d+)\s+([%sbn!]*)\s*(\d)?\s+(\S+)(.*)$")


def load_rounds(path):
    starts, elapsed = [], []
    with open(path) as f:
        next(f)
        for row in f:
            _, s, e = row.strip().split(",")
            starts.append(int(s))
            elapsed.append(int(e))
    return starts, elapsed


def load_compiles(path, keyword):
    events = []
    with open(path) as f:
        for row in f:
            m = LINE.match(row.rstrip())
            if not m or keyword not in m.group(5):
                continue
            ts, cid, attrs, tier, method, rest = m.groups()
            events.append((int(ts), cid, attrs.strip(), tier, method, rest.strip()))
    return events


def main():
    starts, elapsed = load_rounds(sys.argv[1])
    keyword = sys.argv[3] if len(sys.argv) > 3 else ""
    events = load_compiles(sys.argv[2], keyword)
    for ts, cid, attrs, tier, method, rest in events:
        i = bisect.bisect_right(starts, ts) - 1
        if i < 0:
            where = "before round 1"
        else:
            offset = (ts - starts[i]) / 1000
            where = f"round {i + 1:>4} +{offset:8.1f}us"
        print(f"{where:>26}  id={cid:>4} {attrs:>2} tier={tier}  {method} {rest}")


if __name__ == "__main__":
    main()
