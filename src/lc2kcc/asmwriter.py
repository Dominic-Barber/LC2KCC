"""In-memory assembly program and its rendering to a .as file.

Layout follows programs/_LC2K_Format.txt (tab width 4):
  - opcode at column 8 (the 3rd tab stop), operands separated by one space
  - comments at column 24 (the 7th tab stop)
  - no trailing whitespace, exactly one newline at end of file
  - code first, then data in this order: function pointers, single
    inputs/outputs, constants (positive ascending, then negative
    descending), other single data, arrays, the stack
"""

from dataclasses import dataclass, field

from .labels import base36, is_valid_label

TAB = 4
OPCODE_COL = 8
COMMENT_COL = 24


@dataclass
class Line:
    op: str
    args: tuple = ()
    label: str | None = None
    comment: str | None = None


def _pad_to(text: str, col: int) -> str:
    """Append tabs until the visual column reaches col (at least one tab)."""
    width = len(text.expandtabs(TAB))
    text += "\t"
    width = (width // TAB + 1) * TAB
    while width < col:
        text += "\t"
        width += TAB
    return text


def format_line(line: Line) -> str:
    if line.label is not None and not is_valid_label(line.label):
        raise ValueError(f"invalid label {line.label!r}")
    text = _pad_to(line.label or "", OPCODE_COL)
    text += " ".join([line.op, *map(str, line.args)])
    if line.comment:
        text = _pad_to(text, COMMENT_COL) + line.comment
    return text


@dataclass
class Program:
    text: list[Line] = field(default_factory=list)
    func_ptrs: list[Line] = field(default_factory=list)
    io: list[Line] = field(default_factory=list)
    data: list[Line] = field(default_factory=list)
    arrays: list[list[Line]] = field(default_factory=list)
    stack_label: str = "Stack"
    _consts: dict[int, str] = field(default_factory=dict)

    def emit(self, op, *args, label=None, comment=None):
        self.text.append(Line(op, args, label, comment))

    def const(self, value: int) -> str:
        """Label of a .fill holding value, shared by all users."""
        if value not in self._consts:
            prefix, digits = ("k", str(value)) if value >= 0 else ("n", str(-value))
            label = prefix + digits
            if not is_valid_label(label):
                label = prefix + "x" + base36(len(self._consts))
            self._consts[value] = label
        return self._consts[value]

    def _const_lines(self) -> list[Line]:
        positive = sorted(v for v in self._consts if v >= 0)
        negative = sorted((v for v in self._consts if v < 0), reverse=True)
        return [Line(".fill", (v,), self._consts[v]) for v in positive + negative]

    def lines(self) -> list[Line]:
        out = [*self.text, *self.func_ptrs, *self.io, *self._const_lines(), *self.data]
        for array in self.arrays:
            out.extend(array)
        out.append(Line(".fill", (0,), self.stack_label, "stack grows upward from here"))
        return out

    def render(self) -> str:
        return "".join(format_line(line) + "\n" for line in self.lines())
