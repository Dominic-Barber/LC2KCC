#!/usr/bin/env python3
"""Stamp `// expect: N` into test programs using gcc -m32 as the oracle.

  tools/expect.py tests/programs/*.c
"""

import subprocess
import sys
import tempfile
from pathlib import Path

HARNESS = '#include <stdio.h>\nint lc2k_main(void);\nint main(void){printf("%d\\n", lc2k_main());return 0;}\n'


def native(path: Path) -> int:
    with tempfile.TemporaryDirectory() as d:
        Path(d, "h.c").write_text(HARNESS)
        subprocess.run(["gcc", "-m32", "-w", "-fwrapv", "-c", "-Dmain=lc2k_main", "-o", d + "/t.o", str(path)], check=True)
        subprocess.run(["gcc", "-m32", "-o", d + "/x", d + "/t.o", d + "/h.c"], check=True)
        return int(subprocess.run([d + "/x"], capture_output=True, text=True, check=True).stdout)


for name in sys.argv[1:]:
    path = Path(name)
    lines = [l for l in path.read_text().split("\n") if not l.startswith("// expect:")]
    value = native(path)
    path.write_text(f"// expect: {value}\n" + "\n".join(lines))
    print(f"{path}: {value}")
