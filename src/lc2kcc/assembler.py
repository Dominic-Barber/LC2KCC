"""Strict two-pass assembler for the EECS 370 LC-2K spec.

Stricter than the bundled programs/lc2k-assembler.exe, which targets the
repo's extended ISA: this one allows only 8 registers and 16-bit offsets,
supports the b/jump pseudo-instructions, and rejects any program that
doesn't fit in the 65,536-word address space.
"""

import re
from dataclasses import dataclass

from . import isa
from .labels import is_valid_label

_NUMBER = re.compile(r"[-+]?[0-9]+")


class AsmError(Exception):
    def __init__(self, lineno: int, message: str):
        super().__init__(f"line {lineno}: {message}")
        self.lineno = lineno


@dataclass
class Assembled:
    words: list[int]
    symbols: dict[str, int]


@dataclass
class _Source:
    lineno: int
    label: str | None
    op: str
    fields: list[str]


_FIELD_COUNT = {
    **{op: 3 for op in isa.R_TYPE | isa.I_TYPE},
    **{op: 2 for op in isa.J_TYPE},
    **{op: 0 for op in isa.O_TYPE},
    "b": 1,
    "jump": 1,
    isa.FILL: 1,
}


def _parse(text: str) -> list[_Source]:
    raw = text.split("\n")
    if raw and raw[-1] == "":
        raw.pop()
    if len(raw) > isa.MEM_WORDS:
        raise AsmError(len(raw), f"program has {len(raw)} lines; memory holds {isa.MEM_WORDS}")
    lines = []
    for lineno, line in enumerate(raw, 1):
        tokens = line.split()
        if not tokens:
            raise AsmError(lineno, "blank line (every line is an address)")
        label = None
        if not line[0].isspace():
            label = tokens.pop(0)
            if not is_valid_label(label):
                raise AsmError(lineno, f"invalid label {label!r}")
        if not tokens:
            raise AsmError(lineno, "missing opcode")
        op = tokens[0]
        if op not in _FIELD_COUNT:
            raise AsmError(lineno, f"unrecognized opcode {op!r}")
        count = _FIELD_COUNT[op]
        if len(tokens) - 1 < count:
            raise AsmError(lineno, f"{op} needs {count} fields")
        lines.append(_Source(lineno, label, op, tokens[1 : 1 + count]))
    return lines


def _expand_pseudo(src: _Source) -> _Source:
    if src.op == "b":
        return _Source(src.lineno, src.label, "beq", ["0", "0", src.fields[0]])
    if src.op == "jump":
        return _Source(src.lineno, src.label, "jalr", [src.fields[0], "0"])
    return src


def _reg(src: _Source, token: str) -> int:
    if not _NUMBER.fullmatch(token) or not 0 <= int(token) < isa.NUM_REGS:
        raise AsmError(src.lineno, f"bad register {token!r}")
    return int(token)


def _value(src: _Source, token: str, symbols: dict[str, int]) -> tuple[int, bool]:
    """(value, is_symbolic) for a numeric or label field."""
    if _NUMBER.fullmatch(token):
        return int(token), False
    if token not in symbols:
        raise AsmError(src.lineno, f"undefined label {token!r}")
    return symbols[token], True


def assemble(text: str) -> Assembled:
    lines = [_expand_pseudo(src) for src in _parse(text)]
    symbols: dict[str, int] = {}
    for address, src in enumerate(lines):
        if src.label is not None:
            if src.label in symbols:
                raise AsmError(src.lineno, f"duplicate label {src.label!r}")
            symbols[src.label] = address

    words = []
    for pc, src in enumerate(lines):
        if src.op == isa.FILL:
            value, _ = _value(src, src.fields[0], symbols)
            if not isa.WORD_MIN <= value <= isa.WORD_MAX:
                raise AsmError(src.lineno, f".fill value {value} out of range")
            words.append(value)
            continue
        if src.op in isa.O_TYPE:
            words.append(isa.encode(src.op))
            continue
        a, b = _reg(src, src.fields[0]), _reg(src, src.fields[1])
        if src.op in isa.R_TYPE:
            words.append(isa.encode(src.op, a, b, _reg(src, src.fields[2])))
        elif src.op in isa.J_TYPE:
            words.append(isa.encode(src.op, a, b))
        else:
            offset, symbolic = _value(src, src.fields[2], symbols)
            if symbolic and src.op == "beq":
                offset -= pc + 1
            if not isa.OFFSET_MIN <= offset <= isa.OFFSET_MAX:
                raise AsmError(src.lineno, f"offset {offset} out of 16-bit range")
            words.append(isa.encode(src.op, a, b, offset))
    return Assembled(words, symbols)


def to_mc(words: list[int]) -> str:
    """Machine code file: one 32-bit word per line in hex (spec section 2.3)."""
    return "".join(f"{word & 0xFFFFFFFF:08x}\n" for word in words)


def from_mc(text: str) -> list[int]:
    return [isa.to_signed32(int(line, 16)) for line in text.split()]
