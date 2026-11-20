"""Write two classes whose method f is just at and just over the 8,000-byte limit of DontCompileHugeMethods.

f repeats `x = x * 31 + c;`, about 10 bytes of bytecode each. Huge8000.f is 8,000 bytes and Huge8004.f 8,004 bytes
with javac from JDK 25; scripts/tips.sh prints the sizes with javap so that a different javac shows up.

usage: python3 tools/huge_source.py <out-dir>
"""
import sys
from pathlib import Path


def source(name, extra):
    lines = [f"        x = x * 31 + {i % 100};" for i in range(803)] + ["        x = x + 1;"] * extra
    body = "\n".join(lines)
    return f"public class {name} {{\n    public static long f(long x) {{\n{body}\n        return x;\n    }}\n}}\n"


out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
(out / "Huge8000.java").write_text(source("Huge8000", 1))
(out / "Huge8004.java").write_text(source("Huge8004", 2))
