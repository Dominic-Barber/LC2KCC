#!/usr/bin/env python3
"""Differential fuzzer: random C programs, compiled by gcc -m32 and by lc2kcc.

Each program is a few functions of integer/pointer/array/struct operations
that fold their state into one checksum returned from main. The two results
must match. UB is avoided by construction (masked shift counts, nonzero
divisors) and gcc runs with -fwrapv.

  tools/fuzz.py [-n COUNT] [--seed S] [--keep DIR]
"""

import argparse
import os
import random
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lc2kcc.cli import compile_files, execute  # noqa: E402

HARNESS = '#include <stdio.h>\nint lc2k_main(void);\nint main(void){printf("%d\\n", lc2k_main());return 0;}\n'

TYPES = ["int", "unsigned", "short", "unsigned short", "char", "unsigned char", "signed char"]


class Gen:
    def __init__(self, rng):
        self.r = rng
        self.vars = []  # (name, type)
        self.depth = 0

    def pick_var(self):
        return self.r.choice(self.vars)

    def const(self):
        r = self.r
        k = r.random()
        if k < 0.4:
            return str(r.randint(0, 20))
        if k < 0.6:
            return str(r.randint(-1000, 1000))
        if k < 0.8:
            return "0x%x" % r.randint(0, 0xFFFF)
        return "%du" % r.randint(0, 2**32 - 1) if r.random() < 0.5 else "(-%d)" % r.randint(1, 50000)

    def expr(self, d):
        r = self.r
        if d <= 0 or r.random() < 0.15:
            if r.random() < 0.6 and self.vars:
                return self.pick_var()[0]
            return self.const()
        k = r.random()
        a = lambda: self.expr(d - 1)
        if k < 0.45:
            op = r.choice(["+", "-", "*", "&", "|", "^"])
            return f"({a()} {op} {a()})"
        if k < 0.55:
            return f"({a()} {r.choice(['/', '%'])} (({a()} & 7) + 1))"
        if k < 0.65:
            return f"({a()} {r.choice(['<<', '>>'])} ({a()} & 15))"
        if k < 0.72:
            return f"({a()} {r.choice(['<<', '>>'])} {r.randint(0, 20)})"
        if k < 0.82:
            return f"({a()} {r.choice(['<', '<=', '>', '>=', '==', '!='])} {a()})"
        if k < 0.88:
            return f"({a()} {r.choice(['&&', '||'])} {a()})"
        if k < 0.92:
            return f"({r.choice(['-', '~', '!'])} {a()})"
        if k < 0.94:
            return f"({a()} ? {a()} : {a()})"
        if k < 0.97:
            return f"garr[({a()}) & 7]"
        return f"f{r.randint(0, 2)}({a()}, {a()}, {a()})"

    def program(self):
        r = self.r
        out = []
        out.append("int g0 = 17; unsigned g1 = 4000000000u; short g2 = -300; unsigned char g3 = 200;")
        out.append("int garr[8] = {3, 1, 4, 1, 5, 9, 2, 6}; struct S { int a; short b; char c; } gs = {5, 6, 7};")
        out.append("static int mixh = 0; static void mix(int v) { mixh = mixh * 33 + v; }")
        out.append("int f0(int a, int b, int c) { return a * 3 + (b ^ c); }")
        out.append("unsigned f1(unsigned a, unsigned b, unsigned c) { return (a >> 3) + b * 5 - c; }")
        out.append("int f2(int a, int b, int c) { int t = a < b ? a : b; return t + f0(c, a, b); }")
        out.append("int main(void) {")
        for i in range(r.randint(3, 6)):
            ty = r.choice(TYPES)
            out.append(f"  {ty} v{i} = {self.expr(1)};")
            self.vars.append((f"v{i}", ty))
        self.vars.append(("g0", "int")); self.vars.append(("g1", "unsigned")); self.vars.append(("g2", "short")); self.vars.append(("g3", "unsigned char"))
        for _ in range(r.randint(8, 16)):
            c = r.random()
            tgt = self.pick_var()[0]
            if c < 0.6:
                out.append(f"  {tgt} = {self.expr(r.randint(1, 6))};")
            elif c < 0.7:
                out.append(f"  {tgt} {r.choice(['+=', '-=', '^=', '|=', '&=', '*='])} {self.expr(2)};")
            elif c < 0.78:
                out.append(f"  garr[({self.expr(2)}) & 7] = {self.expr(2)};")
            elif c < 0.84:
                out.append(f"  {tgt} = garr[({self.expr(2)}) & 7] + gs.a + gs.b - gs.c;")
            elif c < 0.9:
                out.append(f"  if ({self.expr(2)}) {tgt} = {self.expr(2)}; else {tgt} = {self.expr(2)};")
            elif c < 0.95:
                out.append(f"  {{ int i; for (i = 0; i < {r.randint(1, 6)}; i++) {tgt} = {tgt} * 3 + ({self.expr(2)}); }}")
            else:
                out.append(f"  {tgt}++; --{tgt};")
            out.append(f"  mix({tgt});")
        out.append("  return mixh + garr[3] + gs.c;")
        out.append("}")
        return "\n".join(out) + "\n"


def run_one(args):
    seed, keep = args
    rng = random.Random(seed)
    src = Gen(rng).program()
    d = tempfile.mkdtemp(prefix="fz")
    c = os.path.join(d, "t.c")
    Path(c).write_text(src)
    Path(d, "h.c").write_text(HARNESS)
    try:
        subprocess.run(["gcc", "-m32", "-w", "-fwrapv", "-O0", "-c", "-Dmain=lc2k_main", "-o", d + "/t.o", c], check=True, capture_output=True)
        subprocess.run(["gcc", "-m32", "-w", "-o", d + "/x", d + "/t.o", d + "/h.c"], check=True, capture_output=True)
        native = subprocess.run([d + "/x"], capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError as e:
        return seed, "native-error", e.stderr.decode()[:300], d
    try:
        asm, _ = compile_files([Path(c)])
        a, mem, steps = execute(asm, True, 0)
        got = str(mem[a.symbols["Result"]])
    except Exception as e:  # noqa: BLE001
        return seed, "lc2kcc-error", f"{type(e).__name__}: {e}"[:400], d
    if got != native:
        return seed, "mismatch", f"native={native} lc2kcc={got}", d
    if not keep:
        import shutil

        shutil.rmtree(d, ignore_errors=True)
    return seed, "ok", "", d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()
    bad = 0
    with ProcessPoolExecutor() as ex:
        for seed, status, msg, d in ex.map(run_one, [(s, args.keep) for s in range(args.seed, args.seed + args.n)]):
            if status != "ok":
                bad += 1
                print(f"seed {seed}: {status}: {msg}  ({d}/t.c)")
    print(f"{args.n - bad}/{args.n} ok")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
