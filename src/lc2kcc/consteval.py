"""Integer constant-expression folding with 32-bit signed int semantics.

TODO: unsigned and 64-bit types once the type checker exists.
"""

from pycparser import c_ast

from .frontend import CompileError
from .isa import to_signed32


def _literal(node: c_ast.Constant) -> int:
    text = node.value
    if node.type == "char":
        body = text[1:-1]
        escapes = {"\\n": 10, "\\t": 9, "\\r": 13, "\\0": 0, "\\\\": 92, "\\'": 39, '\\"': 34}
        if len(body) == 1:
            return ord(body)
        if body in escapes:
            return escapes[body]
        raise CompileError(f"unsupported character literal {text}", node)
    if node.type not in ("int", "unsigned int", "long int", "unsigned long int"):
        raise CompileError(f"unsupported constant type {node.type}", node)
    digits = text.rstrip("uUlL")
    if digits.lower().startswith("0x"):
        return int(digits, 16)
    if len(digits) > 1 and digits.startswith("0"):
        return int(digits, 8)
    return int(digits)


def _div(a: int, b: int, node) -> int:
    if b == 0:
        raise CompileError("division by zero in constant expression", node)
    quotient = abs(a) // abs(b)
    return quotient if (a < 0) == (b < 0) else -quotient


_BINARY = {
    "+": lambda a, b, n: a + b,
    "-": lambda a, b, n: a - b,
    "*": lambda a, b, n: a * b,
    "/": _div,
    "%": lambda a, b, n: a - _div(a, b, n) * b,
    "<<": lambda a, b, n: a << (b & 31),
    ">>": lambda a, b, n: a >> (b & 31),
    "&": lambda a, b, n: a & b,
    "|": lambda a, b, n: a | b,
    "^": lambda a, b, n: a ^ b,
    "==": lambda a, b, n: int(a == b),
    "!=": lambda a, b, n: int(a != b),
    "<": lambda a, b, n: int(a < b),
    "<=": lambda a, b, n: int(a <= b),
    ">": lambda a, b, n: int(a > b),
    ">=": lambda a, b, n: int(a >= b),
}

_UNARY = {"-": lambda a: -a, "+": lambda a: a, "~": lambda a: ~a, "!": lambda a: int(a == 0)}


def fold(node: c_ast.Node) -> int:
    """Value of an integer constant expression, or CompileError."""
    if isinstance(node, c_ast.Constant):
        return to_signed32(_literal(node))
    if isinstance(node, c_ast.UnaryOp) and node.op in _UNARY:
        return to_signed32(_UNARY[node.op](fold(node.expr)))
    if isinstance(node, c_ast.BinaryOp):
        if node.op == "&&":
            return int(fold(node.left) != 0 and fold(node.right) != 0)
        if node.op == "||":
            return int(fold(node.left) != 0 or fold(node.right) != 0)
        if node.op in _BINARY:
            return to_signed32(_BINARY[node.op](fold(node.left), fold(node.right), node))
    if isinstance(node, c_ast.TernaryOp):
        return fold(node.iftrue) if fold(node.cond) else fold(node.iffalse)
    raise CompileError(f"not supported yet: {type(node).__name__} in expression", node)
