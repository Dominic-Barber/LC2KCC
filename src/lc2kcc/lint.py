"""Check a .as file against the layout rules in programs/_LC2K_Format.txt.

Only layout is checked here. Syntax and semantics are the assembler's job,
and data-section ordering is guaranteed by asmwriter.Program.
"""

import re

from .asmwriter import COMMENT_COL, OPCODE_COL, TAB

_LINE = re.compile(r"(?P<label>[^\t ]*)(?P<pre>\t+)(?P<instr>\S+(?: \S+)*)(?:(?P<mid>\t+)(?P<comment>\S.*))?")


def _col(text: str) -> int:
    return len(text.expandtabs(TAB))


def check(text: str) -> list[str]:
    problems = []
    if not text.endswith("\n") or text.endswith("\n\n"):
        problems.append("file must end with exactly one newline")
    for lineno, line in enumerate(text.rstrip("\n").split("\n"), 1):
        if line != line.rstrip():
            problems.append(f"line {lineno}: trailing whitespace")
        match = _LINE.fullmatch(line.rstrip())
        if match is None:
            problems.append(f"line {lineno}: expected [label]<tabs>opcode operands[<tabs>comment]")
            continue
        head = match["label"] + match["pre"]
        if _col(head) != OPCODE_COL:
            problems.append(f"line {lineno}: opcode at column {_col(head)}, expected {OPCODE_COL}")
        if match["comment"] is not None:
            before = head + match["instr"]
            expected = max(COMMENT_COL, (_col(before) // TAB + 1) * TAB)
            got = _col(before + match["mid"])
            if got != expected:
                problems.append(f"line {lineno}: comment at column {got}, expected {expected}")
    return problems
