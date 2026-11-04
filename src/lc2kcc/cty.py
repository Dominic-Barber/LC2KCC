"""C types for the sparse-ILP32 memory model.

sizeof and struct layout follow ordinary 32-bit C. A "byte address" is also
a word address, and a scalar is stored whole in the word at its own address;
the words after it (up to sizeof) are padding that is never read.
"""

from dataclasses import dataclass, field


class Type:
    def is_int(self):
        return False

    def is_ptr(self):
        return False

    def is_array(self):
        return False

    def is_func(self):
        return False

    def is_void(self):
        return False

    def is_struct(self):
        return False

    def is_scalar(self):
        return self.is_int() or self.is_ptr()


@dataclass(eq=False)
class Int(Type):
    name: str
    size: int
    signed: bool

    @property
    def align(self):
        return self.size

    def is_int(self):
        return True

    @property
    def bits(self):
        return self.size * 8

    def __repr__(self):
        return self.name


CHAR = Int("char", 1, True)
UCHAR = Int("unsigned char", 1, False)
SHORT = Int("short", 2, True)
USHORT = Int("unsigned short", 2, False)
INT = Int("int", 4, True)
UINT = Int("unsigned int", 4, False)
BOOL = Int("_Bool", 1, False)


@dataclass(eq=False)
class Void(Type):
    size = 0
    align = 1

    def is_void(self):
        return True

    def __repr__(self):
        return "void"


VOID = Void()


@dataclass(eq=False)
class Ptr(Type):
    target: Type
    size = 4
    align = 4

    def is_ptr(self):
        return True

    def __repr__(self):
        return f"{self.target!r}*"


@dataclass(eq=False)
class Array(Type):
    elem: Type
    count: int | None

    @property
    def size(self):
        return (self.count or 0) * self.elem.size

    @property
    def align(self):
        return self.elem.align

    def is_array(self):
        return True

    def __repr__(self):
        return f"{self.elem!r}[{self.count if self.count is not None else ''}]"


@dataclass(eq=False)
class Func(Type):
    ret: Type
    params: list  # list of Type, or None when there is no prototype
    variadic: bool = False
    size = 1
    align = 1

    def is_func(self):
        return True

    def __repr__(self):
        return f"{self.ret!r}(*)()"


@dataclass(eq=False)
class Member:
    name: str | None
    type: Type
    offset: int


@dataclass(eq=False)
class Struct(Type):
    tag: str | None
    is_union: bool = False
    members: list = field(default_factory=list)
    complete: bool = False
    _size: int = 0
    _align: int = 1

    @property
    def size(self):
        return self._size

    @property
    def align(self):
        return self._align

    def is_struct(self):
        return True

    def define(self, members):
        """members: list of (name, type); computes ILP32 layout."""
        offset = 0
        align = 1
        out = []
        for name, ty in members:
            a = max(1, ty.align)
            align = max(align, a)
            if self.is_union:
                out.append(Member(name, ty, 0))
                offset = max(offset, ty.size)
            else:
                offset = (offset + a - 1) // a * a
                out.append(Member(name, ty, offset))
                offset += ty.size
        self.members = out
        self._align = align
        self._size = (offset + align - 1) // align * align
        self.complete = True

    def find(self, name):
        """(Member, extra_offset) searching anonymous members too."""
        for m in self.members:
            if m.name == name:
                return m, 0
            if m.name is None and m.type.is_struct():
                found = m.type.find(name)
                if found:
                    return found[0], found[1] + m.offset
        return None

    def __repr__(self):
        return f"{'union' if self.is_union else 'struct'} {self.tag or '<anon>'}"


def decay(ty: Type) -> Type:
    """Array-to-pointer and function-to-pointer conversion."""
    if ty.is_array():
        return Ptr(ty.elem)
    if ty.is_func():
        return Ptr(ty)
    return ty


def promote(ty: Type) -> Type:
    """Integer promotion."""
    if ty.is_int() and ty.size < 4:
        return INT
    return ty


def common(a: Type, b: Type) -> Type:
    """Usual arithmetic conversions for 32-bit-or-smaller integers."""
    a, b = promote(a), promote(b)
    if a is UINT or b is UINT:
        return UINT
    return INT


def wrap(value: int, ty: Type) -> int:
    """Wrap an integer into the range of an integer or pointer type."""
    bits = 32 if ty.is_ptr() else ty.size * 8
    value &= (1 << bits) - 1
    if ty.is_int() and ty.signed and value >> (bits - 1):
        value -= 1 << bits
    return value
