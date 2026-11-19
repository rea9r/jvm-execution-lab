"""Summarize the jcmd output recorded at each phase of the code cache experiment.

usage: python3 codecache_report.py results/codecache/copies1000-1 [more run directories ...]
"""
import os
import re
import sys

PHASES = ["started", "loaded", "hot", "after-gc1", "after-gc2", "after-gc3"]
USED = re.compile(r"CodeHeap '([^']+)': size=\d+Kb used=(\d+)Kb")
TOTAL = re.compile(r"total_blobs=(\d+), nmethods=(\d+), adapters=(\d+)")
ENTRY = re.compile(r"^(\d+) (\d) (-?\d) (\S+) \[(0x[0-9a-f]+), (0x[0-9a-f]+) - (0x[0-9a-f]+)\]")
METASPACE = re.compile(r"Both:.*?committed,\s+([\d.]+) ([KMG]?B) \(\s*\d+%\) used")


def read(directory, phase, kind):
    with open(os.path.join(directory, f"{phase}.{kind}.txt")) as f:
        return f.read()


def cart_entries(codelist):
    """Count the entries of Cart and Cart$Item by (tier, state)"""
    counts = {}
    for line in codelist.splitlines():
        m = ENTRY.match(line)
        if m and m.group(4).startswith("Cart"):
            key = (m.group(2), m.group(3))
            counts[key] = counts.get(key, 0) + 1
    return counts


def cart_bytes(codelist):
    """Sum the size of the Cart entries, measured up to the start of the next entry in address order.
    The range printed by Compiler.codelist ends at the end of the code (instructions and stubs), before the data that follows."""
    entries = []
    for line in codelist.splitlines():
        m = ENTRY.match(line)
        if m:
            entries.append((int(m.group(5), 16), int(m.group(7), 16), m.group(4)))
    entries.sort()
    total = 0
    for i, (start, end, method) in enumerate(entries):
        if not method.startswith("Cart"):
            continue
        following = entries[i + 1][0] if i + 1 < len(entries) else None
        # The next entry may be in another code heap; then only the printed range is counted
        total += following - start if following is not None and following - start < 64 * 1024 else end - start
    return total


def to_mb(value, unit):
    return float(value) / {"B": 1024 * 1024, "KB": 1024, "MB": 1, "GB": 1 / 1024}[unit]


def summarize(directory):
    rows = []
    for phase in PHASES:
        if not os.path.exists(os.path.join(directory, f"{phase}.codecache.txt")):
            continue
        codecache = read(directory, phase, "codecache")
        used = {k.split()[0]: int(v) for k, v in USED.findall(codecache)}
        nmethods = int(TOTAL.search(codecache).group(2))
        cart = cart_entries(read(directory, phase, "codelist"))
        meta = METASPACE.search(read(directory, phase, "metaspace"))
        rows.append((phase, used, nmethods, cart, to_mb(*meta.groups())))
    return rows


def main():
    for directory in sys.argv[1:]:
        print(f"## {directory}")
        print("| 段階 | non-nmethods | profiled | non-profiled | nmethods | Cart のエントリー | メタスペース |")
        print("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for phase, used, nmethods, cart, meta in summarize(directory):
            print(
                f"| {phase} | {used['non-nmethods']:,}KB | {used['profiled']:,}KB | {used['non-profiled']:,}KB "
                f"| {nmethods:,} | {sum(cart.values()):,} | {meta:.2f}MB |"
            )
        rows = summarize(directory)
        for phase, _, _, cart, _ in rows:
            detail = ", ".join(f"tier {t} / state {s}: {n:,}" for (t, s), n in sorted(cart.items()))
            print(f"    {phase}: {detail}")
        used = {phase: u for phase, u, _, _, _ in rows}
        if "loaded" in used and "hot" in used:
            growth = sum(used["hot"][k] - used["loaded"][k] for k in ("profiled", "non-profiled"))
            size = cart_bytes(read(directory, "hot", "codelist")) / 1024
            print(f"    loaded -> hot: profiled + non-profiled grew {growth:,}KB, Cart entries take {size:,.0f}KB")
        print()


if __name__ == "__main__":
    main()
