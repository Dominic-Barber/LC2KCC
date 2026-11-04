"""lc2kcc command line.

  lc2kcc cc   a.c [b.c ...] [-o out.as]   compile C to LC-2K assembly (+ out.map)
  lc2kcc as   foo.as [-o foo.mc]          assemble to hex machine code
  lc2kcc sim  foo.mc                      simulate machine code
  lc2kcc run  a.c [b.c ...]               compile, assemble, simulate; print Result
  lc2kcc lint foo.as                      check layout conventions
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from . import assembler, lint, simulator
from .assembler import AsmError
from .compiler import Compiler
from .frontend import CompileError, parse_file
from .simulator import SimError

ROOT = Path(__file__).resolve().parents[2]
SIM_EXE = ROOT / "lc2k-sim.exe"
MEM_WORDS = 65536


def compile_files(paths, include_dirs=(), defines=(), output_names=("ee_outbuf",)) -> tuple[str, str]:
    """(assembly text, label map) for a set of C files linked into one program."""
    comp = Compiler(output_names=output_names)
    comp.load_runtime()
    for path in paths:
        comp.add_tu(parse_file(Path(path), include_dirs, defines), str(path))
    program = comp.build()
    return program.render(), comp.mangler.symbol_map()


def _cc(args):
    asm, symbol_map = compile_files(args.inputs, args.include, args.define)
    out = args.output or args.inputs[0].with_suffix(".as")
    out.write_text(asm)
    out.with_suffix(".map").write_text(symbol_map)


def _as(args):
    assembled = assembler.assemble(args.input.read_text())
    (args.output or args.input.with_suffix(".mc")).write_text(assembler.to_mc(assembled.words))


def _report(state):
    print(f"halted after {state.steps} instructions, pc={state.pc}")
    print("regs: " + " ".join(f"r{i}={v}" for i, v in enumerate(state.regs)))


def _sim(args):
    _report(simulator.run(assembler.from_mc(args.input.read_text()), args.max_steps))


ASM_EXE = ROOT / "lc2k-assembler.exe"


def run_exe(asm: str) -> tuple[list[int], int]:
    """Assemble and run on the bundled tools; returns (final memory, instruction count).

    lc2k-assembler.exe / lc2k-sim.exe implement the extended 470 encoding
    (16 registers, 4-bit opcodes) of the same assembly language, so they are
    a fast independent check of the program, not of the strict 370 encoding.
    """
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "prog.as"
        mc = Path(tmp) / "prog.mc"
        src.write_text(asm)
        proc = subprocess.run([str(ASM_EXE), str(src), str(mc)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise SimError(f"lc2k-assembler.exe failed: {proc.stdout.strip()} {proc.stderr.strip()}")
        proc = subprocess.run(
            [str(SIM_EXE), "-m", str(mc), "-z", str(MEM_WORDS), "-o", tmp],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise SimError(f"lc2k-sim.exe failed: {proc.stderr.strip()}")
        steps = int(re.search(r"Retired:\s+(\d+)", proc.stdout).group(1))
        mem = [0] * MEM_WORDS
        for m in re.finditer(r"mem\[0x([0-9a-f]+)\] = 0x([0-9a-f]+)", (Path(tmp) / "prog.fmem").read_text()):
            mem[int(m.group(1), 16)] = int(m.group(2), 16)
        return [w - (1 << 32) if w >> 31 else w for w in mem], steps


def read_cstring(mem, addr, limit=4096):
    out = []
    while len(out) < limit and mem[addr + len(out)] != 0:
        out.append(chr(mem[addr + len(out)] & 0xFF))
    return "".join(out)


def execute(asm: str, fast: bool, max_steps: int):
    """Assemble and run; returns (assembled, memory, steps)."""
    assembled = assembler.assemble(asm)  # strict 370 assembler always validates
    if fast:
        mem, steps = run_exe(asm)
    else:
        state = simulator.run(assembled.words, max_steps)
        mem, steps = state.mem, state.steps
    return assembled, mem, steps


def _run(args):
    asm, _ = compile_files(args.inputs, args.include, args.define)
    assembled, mem, steps = execute(asm, args.fast, args.max_steps)
    print(f"halted after {steps} instructions; image {len(assembled.words)} words")
    print(f"Result = {mem[assembled.symbols['Result']]}")
    for name in args.dump:
        label = _find_label(assembled, name)
        print(f"--- {name} ---")
        print(read_cstring(mem, assembled.symbols[label]), end="")


def _find_label(assembled, cname):
    """Label of a C global, via the .map written by `cc` (looked up in-process)."""
    from .compiler import Compiler  # noqa: F401

    if cname in assembled.symbols:
        return cname
    raise SystemExit(f"label {cname} not found (use the label from the .map file)")


def _lint(args):
    problems = lint.check(args.input.read_text())
    for problem in problems:
        print(f"{args.input}: {problem}")
    if problems:
        sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lc2kcc", description="C compiler for LC-2K")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, func, help, many=False):
        p = sub.add_parser(name, help=help)
        if many:
            p.add_argument("inputs", type=Path, nargs="+")
        else:
            p.add_argument("input", type=Path)
        p.set_defaults(func=func)
        return p

    for name, func, help in (("cc", _cc, "compile C to .as"), ("run", _run, "compile and simulate C")):
        p = command(name, func, help, many=True)
        p.add_argument("-I", dest="include", action="append", default=[], help="include directory")
        p.add_argument("-D", dest="define", action="append", default=[], help="preprocessor define")
        if name == "cc":
            p.add_argument("-o", dest="output", type=Path)
        else:
            p.add_argument("--fast", action="store_true", help="use the bundled lc2k-sim.exe")
            p.add_argument("--dump", action="append", default=[], help="print this label as a C string")
    command("as", _as, "assemble .as to .mc").add_argument("-o", dest="output", type=Path)
    command("sim", _sim, "simulate .mc")
    command("lint", _lint, "check .as layout conventions")
    for name in ("run", "sim"):
        sub.choices[name].add_argument("--max-steps", type=int, default=50_000_000)

    args = parser.parse_args(argv)
    try:
        args.func(args)
    except (CompileError, AsmError, SimError) as error:
        print(f"lc2kcc: error: {error}", file=sys.stderr)
        sys.exit(1)
