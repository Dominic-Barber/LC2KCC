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


class Gen2(Gen):
    """Statement-level programs over arrays, structs and pointers."""

    def idx(self, n):
        return f"(({self.expr(2)}) & {n - 1})"

    def lval(self):
        r = self.r
        k = r.random()
        if k < 0.2:
            return f"recs[{self.idx(4)}].a"
        if k < 0.3:
            return f"recs[{self.idx(4)}].b"
        if k < 0.4:
            return f"recs[{self.idx(4)}].c"
        if k < 0.5:
            return f"recs[{self.idx(4)}].arr[{self.idx(4)}]"
        if k < 0.6:
            return f"garr[{self.idx(16)}]"
        if k < 0.7:
            return f"gc[{self.idx(16)}]"
        if k < 0.75:
            return "*pp"
        if k < 0.8:
            return "pp[1]"
        return self.pick_var()[0]

    def stmt(self, depth):
        r = self.r
        k = r.random()
        e = lambda d=2: self.expr(d)
        if depth <= 0 or k < 0.35:
            op = r.choice(["=", "=", "+=", "-=", "^=", "|=", "&="])
            return f"{self.lval()} {op} {e()};"
        if k < 0.42:
            return f"pp = garr + {self.idx(8)}; *pp++ = {e()}; pp[1] = *pp + {e(1)};"
        if k < 0.48:
            return f"rp = &recs[{self.idx(4)}]; rp->arr[{self.idx(4)}] = rp->a + {e(1)}; rp->b += {e(1)};"
        if k < 0.53:
            return f"recs[{self.idx(4)}] = recs[{self.idx(4)}];"
        if k < 0.6:
            return f"mix(fn(&recs[{self.idx(4)}], {e(1)}));"
        if k < 0.67:
            return f"if ({e()}) {{ {self.stmt(depth - 1)} }} else {{ {self.stmt(depth - 1)} }}"
        if k < 0.75:
            n = r.randint(1, 5)
            v = f"i{depth}"
            return f"for ({v} = 0; {v} < {n}; {v}++) {{ {self.stmt(depth - 1)} if ({e(1)}) continue; {self.stmt(depth - 1)} if ({e(1)} == 3) break; }}"
        if k < 0.82:
            v = f"i{depth}"
            return f"{v} = {r.randint(0, 3)}; while ({v} < 5) {{ {self.stmt(depth - 1)} {v} += {r.randint(1, 3)}; }}"
        if k < 0.9:
            return (
                f"switch ({self.idx(4)}) {{ case 0: {self.stmt(depth - 1)} break; case 1: {self.stmt(depth - 1)} "
                f"case 2: {self.stmt(depth - 1)} break; default: {self.stmt(depth - 1)} }}"
            )
        if k < 0.95:
            return f"do {{ {self.stmt(depth - 1)} }} while (0);"
        return f"mix({e(3)});"

    def program(self):
        r = self.r
        out = [
            "struct R { int a; short b; unsigned char c; int arr[4]; };",
            "struct R recs[4]; int garr[16]; char gc[16];",
            "static int mixh = 0; static void mix(int v) { mixh = mixh * 33 + v; }",
            "int f0(int a, int b, int c) { return a * 3 + (b ^ c); }",
            "unsigned f1(unsigned a, unsigned b, unsigned c) { return (a >> 3) + b * 5 - c; }",
            "int f2(int a, int b, int c) { int t = a < b ? a : b; return t + f0(c, a, b); }",
            "int fn(struct R *p, int x) { p->a += x; return p->a + p->arr[x & 3] + p->c; }",
            "int main(void) {",
            "  int i0 = 0, i1 = 0, i2 = 0, i3 = 0, k; int *pp = garr; struct R *rp = recs;",
        ]
        for i in range(r.randint(2, 4)):
            out.append(f"  int v{i} = {self.expr(1)};")
            self.vars.append((f"v{i}", "int"))
        out.append("  for (k = 0; k < 16; k++) { garr[k] = k * 7 - 20; gc[k] = k * 3; recs[k & 3].arr[k & 3] = k; recs[k & 3].a = k * 11; recs[k & 3].b = k; recs[k & 3].c = k * 5; }")
        for _ in range(r.randint(6, 12)):
            out.append("  " + self.stmt(3))
            out.append(f"  mix({self.pick_var()[0]});")
        out.append("  for (k = 0; k < 16; k++) mix(garr[k] + gc[k] + recs[k & 3].a + recs[k & 3].b + recs[k & 3].c + recs[k & 3].arr[k & 3]);")
        out.append("  return mixh;")
        out.append("}")
        return "\n".join(out) + "\n"


def run_one(args):
    seed, keep, mode = args
    rng = random.Random(seed)
    src = (Gen2 if mode == 'stmt' else Gen)(rng).program()
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
    ap.add_argument("--mode", choices=["expr", "stmt"], default="expr")
    args = ap.parse_args()
    bad = 0
    with ProcessPoolExecutor() as ex:
        for seed, status, msg, d in ex.map(run_one, [(s, args.keep, args.mode) for s in range(args.seed, args.seed + args.n)]):
            if status != "ok":
                bad += 1
                print(f"seed {seed}: {status}: {msg}  ({d}/t.c)")
    print(f"{args.n - bad}/{args.n} ok")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
