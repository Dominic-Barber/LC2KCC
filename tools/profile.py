#!/usr/bin/env python3
"""Instruction-count profile of an .as program, per function label.

  tools/profile.py prog.as [--map prog.map]
Functions are the capitalized labels (code section); counts include helpers.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lc2kcc import assembler, isa  # noqa: E402


def main():
    path = Path(sys.argv[1])
    asm = path.read_text()
    assembled = assembler.assemble(asm)
    words = assembled.words
    mem = list(words) + [0] * (isa.MEM_WORDS - len(words))
    counts = [0] * len(words)
    regs = [0] * 8
    pc = 0
    steps = 0
    decode = isa.decode
    s32 = isa.to_signed32
    while True:
        op, a, b, d, off = decode(mem[pc])
        counts[pc] += 1
        steps += 1
        npc = pc + 1
        if op == "add":
            regs[d] = s32(regs[a] + regs[b])
        elif op == "nor":
            regs[d] = s32(~(regs[a] | regs[b]))
        elif op == "lw":
            regs[b] = mem[regs[a] + off]
        elif op == "sw":
            mem[regs[a] + off] = regs[b]
        elif op == "beq":
            if regs[a] == regs[b]:
                npc = pc + 1 + off
        elif op == "jalr":
            t = regs[a]
            regs[b] = pc + 1
            npc = t
        elif op == "halt":
            break
        regs[0] = 0
        pc = npc
    # attribute to the nearest preceding capitalized label in the code section
    labels = sorted((addr, name) for name, addr in assembled.symbols.items() if name[0].isupper())
    code_end = next(addr for name, addr in assembled.symbols.items() if name == "PMain") if "PMain" in assembled.symbols else len(words)
    names = {}
    mp = Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--map" else None
    if mp:
        for line in mp.read_text().splitlines():
            k, _, v = line.partition("\t")
            names[k] = v
    per = {}
    li = 0
    cur = "?"
    for addr in range(code_end):
        while li < len(labels) and labels[li][0] <= addr:
            cur = labels[li][1]
            li += 1
        per[cur] = per.get(cur, 0) + counts[addr]
    print(f"total {steps} instructions")
    for name, n in sorted(per.items(), key=lambda kv: -kv[1])[:25]:
        print(f"{n:10d} {100 * n / steps:5.1f}%  {name:8s} {names.get(name, '')}")


main()
