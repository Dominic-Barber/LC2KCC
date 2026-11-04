"""Label rules and C-name mangling.

Assembler rule: at most 6 characters, letters and digits only, starting
with a letter. Project convention (programs/_LC2K_Format.txt): global
labels (functions, the stack, non-static data) start with a capital
letter; everything else starts lowercase.
"""

import re

_VALID = re.compile(r"[A-Za-z][A-Za-z0-9]{0,5}")
_BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def is_valid_label(name: str) -> bool:
    return _VALID.fullmatch(name) is not None


def base36(n: int) -> str:
    digits = ""
    while True:
        n, r = divmod(n, 36)
        digits = _BASE36[r] + digits
        if n == 0:
            return digits


class Mangler:
    """Hands out unique labels and remembers which C entity each one names."""

    def __init__(self, reserved=()):
        self.used: set[str] = set(reserved)
        self.names: dict[object, str] = {}
        self.counter = 0

    def global_label(self, key: object, cname: str, prefix: str = "") -> str:
        """Capitalized label for a global; readable when the name fits."""
        if key in self.names:
            return self.names[key]
        readable = prefix + cname if prefix else cname[:1].upper() + cname[1:]
        label = readable if is_valid_label(readable) and readable not in self.used else None
        while label is None:
            candidate = "G" + base36(self.counter)
            self.counter += 1
            if candidate not in self.used:
                label = candidate
        self.used.add(label)
        self.names[key] = label
        return label

    def symbol_map(self) -> str:
        """Label-to-C-name map, written next to the .as for debugging."""
        rows = sorted((label, " ".join(map(str, key)) if isinstance(key, tuple) else str(key)) for key, label in self.names.items())
        return "".join(f"{label}\t{key}\n" for label, key in rows)
