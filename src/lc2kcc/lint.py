"""Check a .as file against the LC-2K layout conventions.

Checked: tab layout and trailing whitespace, label shape (at most 6 letters
and digits, starting with a letter), all instructions before any .fill, the
constants (positive ascending, then negative descending), and Stack as the
last line. Syntax and semantics are the assembler's job.
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
    problems += _check_structure(text)
    return problems


_CONST = re.compile(r"[kn]\d+")


def _check_structure(text: str) -> list[str]:
    problems = []
    lines = text.rstrip("\n").split("\n")
    in_data = False
    consts = []
    for lineno, line in enumerate(lines, 1):
        match = _LINE.fullmatch(line.rstrip())
        if match is None:
            continue
        label, instr = match["label"], match["instr"].split()
        if label and not (len(label) <= 6 and label.isalnum() and label[0].isalpha()):
            problems.append(f"line {lineno}: invalid label {label!r}")
        if instr[0] == ".fill":
            in_data = True
            if _CONST.fullmatch(label) and len(instr) == 2:
                consts.append((lineno, int(instr[1])))
        elif in_data:
            problems.append(f"line {lineno}: instruction after a .fill (instructions must come first)")
    positive = [v for _, v in consts if v >= 0]
    negative = [v for _, v in consts if v < 0]
    if positive != sorted(positive) or negative != sorted(negative, reverse=True) or [v for _, v in consts] != positive + negative:
        problems.append("constants must be positive ascending, then negative descending")
    if lines and not lines[-1].startswith("Stack\t"):
        problems.append("the last line must be the Stack label")
    return problems
