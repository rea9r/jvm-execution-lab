"""Print the median per-round time (us) of rounds in [first, last] for each CSV.

usage: python3 steady.py first last a.csv [b.csv ...]
"""
import statistics
import sys

first, last = int(sys.argv[1]), int(sys.argv[2])
for path in sys.argv[3:]:
    values = []
    with open(path) as f:
        next(f)
        for row in f:
            r, _, e = row.strip().split(",")
            if first <= int(r) <= last:
                values.append(int(e) / 1000)
    print(f"{path}\t{statistics.median(values):8.2f}")
