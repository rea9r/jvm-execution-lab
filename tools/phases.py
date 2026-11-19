"""Run a Java program that pauses at "PHASE <name> <pid>" lines, and record jcmd output at each pause.

usage: python3 phases.py <out-dir> <java> [java args ...]
"""
import os
import re
import subprocess
import sys

USED = re.compile(r"CodeHeap '([^']+)': size=\d+Kb used=(\d+)Kb")
TOTAL = re.compile(r"total_blobs=(\d+), nmethods=(\d+), adapters=(\d+)")
ENTRY = re.compile(r"^(\d+) (\d) (-?\d) (\S+) \[(0x[0-9a-f]+), (0x[0-9a-f]+) - (0x[0-9a-f]+)\]")


def jcmd(java, pid, command):
    tool = os.path.join(os.path.dirname(java), "jcmd")
    return subprocess.run([tool, str(pid), command], capture_output=True, text=True).stdout


def summarize(name, codecache, codelist, metaspace):
    used = dict(USED.findall(codecache))
    total = TOTAL.search(codecache)
    cart = {}
    for line in codelist.splitlines():
        m = ENTRY.match(line)
        if not m or not m.group(4).startswith("Cart"):
            continue
        _, tier, state, method, start, _, end = m.groups()
        key = f"tier{tier}/state{state}"
        count, size = cart.get(key, (0, 0))
        cart[key] = (count + 1, size + int(end, 16) - int(start, 16))
    heaps = " ".join(f"{k.split()[0]}={v}KB" for k, v in sorted(used.items()))
    print(f"[{name}] {heaps} nmethods={total.group(2) if total else '?'} metaspace_used={metaspace}")
    for key in sorted(cart):
        count, size = cart[key]
        print(f"    Cart* {key}: {count} entries, {size / 1024:.1f}KB")


def main():
    out_dir, java, *args = sys.argv[1:]
    os.makedirs(out_dir, exist_ok=True)
    proc = subprocess.Popen([java, *args], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    for line in proc.stdout:
        if not line.startswith("PHASE "):
            print(line, end="")
            continue
        _, name, pid = line.split()
        codecache = jcmd(java, pid, "Compiler.codecache")
        codelist = jcmd(java, pid, "Compiler.codelist")
        vm_metaspace = jcmd(java, pid, "VM.metaspace")
        m = re.search(r"Both:.*?committed,\s+([\d.]+) ([KMG]?B) \(\s*\d+%\) used", vm_metaspace)
        metaspace = f"{m.group(1)}{m.group(2)}" if m else "?"
        for suffix, text in (("codecache", codecache), ("codelist", codelist), ("metaspace", vm_metaspace)):
            with open(os.path.join(out_dir, f"{name}.{suffix}.txt"), "w") as f:
                f.write(text)
        summarize(name, codecache, codelist, metaspace)
        proc.stdin.write("\n")
        proc.stdin.flush()
    proc.wait()


if __name__ == "__main__":
    main()
