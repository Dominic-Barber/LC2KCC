"""Shared helpers for the test suites."""

import tempfile
from pathlib import Path

from lc2kcc import lint
from lc2kcc.cli import compile_files, execute

ROOT = Path(__file__).resolve().parents[1]


def run_files(paths, include_dirs=(), defines=(), fast=False, max_steps=50_000_000):
    """Compile, assemble (strict spec), lint, run. Returns (result, steps, asm, assembled, memory)."""
    asm, _ = compile_files(paths, include_dirs, defines)
    problems = lint.check(asm)
    assert not problems, problems[:5]
    assembled, mem, steps = execute(asm, fast, max_steps)
    return mem[assembled.symbols["Result"]], steps, asm, assembled, mem


def run_source(source: str, **kw):
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "t.c"
        path.write_text(source)
        return run_files([path], **kw)


def result_of(source: str) -> int:
    return run_source(source)[0]
