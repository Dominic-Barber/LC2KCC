"""lc2kcc command line.

  lc2kcc cc   foo.c [-o foo.as]   compile C to LC-2K assembly (+ foo.map)
  lc2kcc as   foo.as [-o foo.mc]  assemble to hex machine code
  lc2kcc sim  foo.mc              simulate machine code
  lc2kcc run  foo.c               compile, assemble, simulate; print Result
  lc2kcc lint foo.as              check layout conventions
"""

import argparse
import sys
from pathlib import Path

from . import assembler, lint, simulator
from .assembler import AsmError
from .codegen import compile_ast
from .frontend import CompileError, parse_file
from .simulator import SimError


def compile_c(path: Path, include_dirs=(), defines=()) -> tuple[str, str]:
    """(assembly text, label map) for a C file."""
    program, mangler = compile_ast(parse_file(path, include_dirs, defines))
    return program.render(), mangler.symbol_map()


def _cc(args):
    asm, symbol_map = compile_c(args.input, args.include, args.define)
    out = args.output or args.input.with_suffix(".as")
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


def _run(args):
    asm, _ = compile_c(args.input, args.include, args.define)
    assembled = assembler.assemble(asm)
    state = simulator.run(assembled.words, args.max_steps)
    _report(state)
    print(f"Result = {state.mem[assembled.symbols['Result']]}")


def _lint(args):
    problems = lint.check(args.input.read_text())
    for problem in problems:
        print(f"{args.input}: {problem}")
    if problems:
        sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="lc2kcc", description="C compiler for LC-2K")
    sub = parser.add_subparsers(dest="command", required=True)

    def command(name, func, help):
        p = sub.add_parser(name, help=help)
        p.add_argument("input", type=Path)
        p.set_defaults(func=func)
        return p

    for name, func, help in (("cc", _cc, "compile C to .as"), ("run", _run, "compile and simulate C")):
        p = command(name, func, help)
        p.add_argument("-I", dest="include", action="append", default=[], help="include directory")
        p.add_argument("-D", dest="define", action="append", default=[], help="preprocessor define")
        if name == "cc":
            p.add_argument("-o", dest="output", type=Path)
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
