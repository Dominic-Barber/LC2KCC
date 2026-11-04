"""LC-2K instruction set (strict spec): opcodes, field limits, encoding."""

NUM_REGS = 8
MEM_WORDS = 65536

OFFSET_MIN, OFFSET_MAX = -32768, 32767
WORD_MIN, WORD_MAX = -(2**31), 2**31 - 1

OPCODES = {
    "add": 0b000,
    "nor": 0b001,
    "lw": 0b010,
    "sw": 0b011,
    "beq": 0b100,
    "jalr": 0b101,
    "halt": 0b110,
    "noop": 0b111,
}
MNEMONICS = {code: name for name, code in OPCODES.items()}

R_TYPE = frozenset({"add", "nor"})
I_TYPE = frozenset({"lw", "sw", "beq"})
J_TYPE = frozenset({"jalr"})
O_TYPE = frozenset({"halt", "noop"})
PSEUDO = frozenset({"b", "jump"})
FILL = ".fill"


def to_signed32(value: int) -> int:
    value &= 0xFFFFFFFF
    return value - (1 << 32) if value & 0x80000000 else value


def encode(op: str, a: int = 0, b: int = 0, field2: int = 0) -> int:
    """Encode one real instruction. field2 is destReg (R) or offset (I)."""
    word = OPCODES[op] << 22
    if op in R_TYPE:
        word |= (a << 19) | (b << 16) | field2
    elif op in I_TYPE:
        word |= (a << 19) | (b << 16) | (field2 & 0xFFFF)
    elif op in J_TYPE:
        word |= (a << 19) | (b << 16)
    return word


def decode(word: int) -> tuple[str, int, int, int, int]:
    """Return (mnemonic, regA, regB, destReg, signed offset)."""
    word &= 0xFFFFFFFF
    op = MNEMONICS[(word >> 22) & 0b111]
    a = (word >> 19) & 0b111
    b = (word >> 16) & 0b111
    offset = word & 0xFFFF
    if offset & 0x8000:
        offset -= 1 << 16
    return op, a, b, word & 0b111, offset
