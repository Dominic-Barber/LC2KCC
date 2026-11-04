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
        self.described: dict[str, str] = {}  # label -> what it names
        self.counter = 0

    def _unique(self, prefix: str, desc: str) -> str:
        while True:
            suffix = base36(self.counter)
            self.counter += 1
            label = prefix[: max(1, 6 - len(suffix))] + suffix
            if label not in self.used and is_valid_label(label):
                self.used.add(label)
                self.described[label] = desc
                return label

    def fresh(self, prefix: str, desc: str = "") -> str:
        """A unique label: prefix plus a base-36 counter."""
        return self._unique(prefix, desc)

    def named(self, cname: str, desc: str, capital: bool, prefix: str = "") -> str:
        """Readable label for a C entity; falls back to a counter suffix."""
        stem = re.sub(r"[^A-Za-z0-9]", "", cname)
        if not stem:
            stem = "x"
        if not stem[0].isalpha():
            stem = "x" + stem
        stem = stem[0].upper() + stem[1:] if capital else stem[0].lower() + stem[1:]
        label = prefix + stem
        if is_valid_label(label) and label not in self.used:
            self.used.add(label)
            self.described[label] = desc
            return label
        # abbreviate: keep a prefix of the name, then a counter
        return self._unique((prefix + stem)[: 3 if len(prefix + stem) > 3 else len(prefix + stem)], desc)

    def claim(self, label: str, desc: str = ""):
        self.used.add(label)
        self.described[label] = desc

    def symbol_map(self) -> str:
        """Label-to-C-name map, written next to the .as for debugging."""
        return "".join(f"{label}\t{desc}\n" for label, desc in sorted(self.described.items()) if desc)
