"""Program-level compilation: translation units, symbols, types, global data.

A Compiler owns every translation unit of one program (CoreMark is five .c
files plus the port plus lc2kcc's own runtime). Functions and data objects
are emitted only when reachable from main, so unused code costs nothing.
"""

from dataclasses import dataclass, field

from pycparser import c_ast

from . import cty
from .asmwriter import Line, Program
from .cty import Array, Func, Ptr, Struct
from .frontend import CompileError
from .labels import Mangler

RESERVED = ("Stack", "Result", "spinit")


def s32w(v: int) -> int:
    return v - (1 << 32) if v >> 31 else v


# ---------------------------------------------------------------- symbols


@dataclass(eq=False)
class Addr:
    """Address of a global object plus a word offset (a .fill operand)."""

    obj: "GObj"
    off: int = 0


@dataclass(eq=False)
class GObj:
    """A global function or data object (including statics and string literals)."""

    name: str
    type: cty.Type
    kind: str  # 'var' | 'func' | 'str'
    static: bool = False
    tu: "TU | None" = None
    fdef: c_ast.FuncDef | None = None
    init: c_ast.Node | None = None
    defined: bool = False
    words: list | None = None  # for 'str' objects and resolved data
    label: str | None = None
    aux: dict = field(default_factory=dict)  # word offset -> label
    needed: bool = False
    coord: object = None
    weak: bool = False  # library definition that a program may replace
    llval: int | None = None  # for 64-bit constants: the value, as an unsigned 64-bit integer

    @property
    def size(self):
        return max(1, self.type.size) if self.kind != "func" else 1


@dataclass(eq=False)
class Local:
    type: cty.Type
    slot: int


@dataclass(eq=False)
class EnumConst:
    value: int


@dataclass(eq=False)
class TypedefSym:
    type: cty.Type


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.names: dict[str, object] = {}
        self.tags: dict[str, cty.Type] = {}

    def lookup(self, name):
        s = self
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        return None

    def lookup_tag(self, tag):
        s = self
        while s is not None:
            if tag in s.tags:
                return s.tags[tag]
            s = s.parent
        return None


@dataclass(eq=False)
class TU:
    name: str
    scope: Scope = field(default_factory=Scope)


# ---------------------------------------------------------------- types


def parse_int_name(names: list[str], node) -> cty.Type:
    """IdentifierType names like ['unsigned', 'char'] -> Int."""
    words = sorted(names)
    unsigned = "unsigned" in words
    signed = "signed" in words
    rest = [w for w in words if w not in ("unsigned", "signed")]
    if rest == ["void"]:
        return cty.VOID
    if rest in (["char"],):
        if unsigned:
            return cty.UCHAR
        return cty.CHAR
    if rest in (["short"], ["int", "short"]):
        return cty.USHORT if unsigned else cty.SHORT
    if rest in ([], ["int"], ["long"], ["int", "long"]):
        return cty.UINT if unsigned else cty.INT
    if rest in (["long", "long"], ["int", "long", "long"]):
        return cty.ULLONG if unsigned else cty.LLONG
    if rest in (["float"], ["double"], ["double", "long"]):
        raise CompileError("floating point is not supported", node)
    if rest == ["_Bool"]:
        return cty.BOOL
    raise CompileError(f"unsupported type specifier {' '.join(names)}", node)


class Compiler:
    def __init__(self, output_names=("ee_outbuf", "__stdout")):
        self.mangler = Mangler(reserved=RESERVED)
        self.program = Program(mangler=self.mangler)
        self.externs: dict[str, GObj] = {}
        self.tus: list[TU] = []
        self.strings: dict[tuple, GObj] = {}
        self.statics_local = 0
        self.worklist: list[GObj] = []  # functions to generate
        self.datalist: list[GObj] = []  # data objects to emit
        self.cells: dict[tuple, str] = {}
        self.output_names = set(output_names)
        self.helpers_needed: set[str] = set()
        self.func_ptr_cells: list[Line] = []
        self.data_cells: list[Line] = []
        from .runtime import HELPERS

        self.helper_labels = {h: self.mangler.named(h, f"runtime {h}", capital=True) for h in HELPERS}

    # ------------------------------------------------------------ labels

    def label_of(self, g: GObj) -> str:
        if g.label is None:
            if g.kind == "func":
                g.label = self.mangler.named(g.name, f"func {g.name}", capital=True)
            elif g.kind == "str":
                g.label = self.mangler.fresh("s", "string literal")
            else:
                g.label = self.mangler.named(g.name, f"{'static ' if g.static else ''}{g.name}", capital=not g.static)
        return g.label

    def label_at(self, g: GObj, off: int) -> str | None:
        """Label naming word `off` of g, or None if off is outside the object."""
        self.need(g)
        if off == 0:
            return self.label_of(g)
        if g.kind == "func" or not 0 <= off < g.size:
            return None
        if off not in g.aux:
            g.aux[off] = self.mangler.fresh("d", f"{g.name}+{off}")
        return g.aux[off]

    def addr_cell(self, g: GObj, off: int = 0) -> str:
        """Label of a word holding the address of g+off (for `lw 0 r cell`)."""
        key = (id(g), off)
        if key not in self.cells:
            target = self.label_at(g, off)
            if target is None:
                raise CompileError(f"address of {g.name}+{off} is outside the object")
            if g.kind == "func":
                cell = self.mangler.named(g.name, f"&{g.name}", capital=True, prefix="P")
                self.func_ptr_cells.append(Line(".fill", (target,), cell))
            else:
                cell = self.mangler.fresh("a", f"&{g.name}+{off}" if off else f"&{g.name}")
                self.data_cells.append(Line(".fill", (target,), cell))
            self.cells[key] = cell
        return self.cells[key]

    def immutable_labels(self) -> set:
        """Labels of words the program never writes: constants and address cells."""
        return set(self.program._consts.values()) | set(self.cells.values())

    def need(self, g: GObj):
        if g.needed:
            return
        g.needed = True
        if g.kind == "func":
            if g.fdef is None:
                raise CompileError(f"undefined reference to function '{g.name}'", g.coord)
            self.worklist.append(g)
        else:
            self.datalist.append(g)

    # ------------------------------------------------------------ strings

    @staticmethod
    def decode_string(text: str, node=None) -> list[int]:
        """Decode the quoted pieces of a (possibly concatenated) string literal."""
        out = []
        i = 0
        in_quote = False
        simple = {"n": 10, "t": 9, "r": 13, "0": 0, "a": 7, "b": 8, "f": 12, "v": 11, "\\": 92, "'": 39, '"': 34, "?": 63, "e": 27}
        while i < len(text):
            ch = text[i]
            if ch == '"':
                in_quote = not in_quote
                i += 1
                continue
            if not in_quote:
                i += 1
                continue
            if ch != "\\":
                out.append(ord(ch))
                i += 1
                continue
            i += 1
            ch = text[i]
            if ch == "x":
                j = i + 1
                while j < len(text) and text[j] in "0123456789abcdefABCDEF":
                    j += 1
                out.append(int(text[i + 1 : j], 16) & 0xFF)
                i = j
            elif ch in "01234567":
                j = i
                while j < len(text) and j < i + 3 and text[j] in "01234567":
                    j += 1
                out.append(int(text[i:j], 8) & 0xFF)
                i = j
            elif ch in simple:
                out.append(simple[ch])
                i += 1
            else:
                raise CompileError(f"unknown escape sequence \\{ch}", node)
        return out

    def ll_const(self, value: int) -> GObj:
        """Read-only data object holding a 64-bit constant (low word at +0, high word at +4)."""
        value &= (1 << 64) - 1
        key = ("ll", value)
        if key not in self.strings:
            g = GObj("llconst", cty.LLONG, "str", static=True, words=[s32w(value & 0xFFFFFFFF), 0, 0, 0, s32w(value >> 32), 0, 0, 0], defined=True)
            g.llval = value
            self.strings[key] = g
        return self.strings[key]

    def string_obj(self, text: str, node=None) -> GObj:
        chars = self.decode_string(text, node) + [0]
        key = tuple(chars)
        if key not in self.strings:
            g = GObj("str", Array(cty.CHAR, len(chars)), "str", static=True, words=[c for c in chars], defined=True)
            self.strings[key] = g
        return self.strings[key]

    # ------------------------------------------------------------ types

    def build_type(self, node, scope: Scope, fg=None) -> cty.Type:
        if isinstance(node, c_ast.TypeDecl):
            return self.build_base(node.type, scope, fg)
        if isinstance(node, c_ast.Typename):
            return self.build_type(node.type, scope, fg)
        if isinstance(node, c_ast.PtrDecl):
            return Ptr(self.build_type(node.type, scope, fg))
        if isinstance(node, c_ast.ArrayDecl):
            elem = self.build_type(node.type, scope, fg)
            count = None
            if node.dim is not None:
                count = self.const_int(node.dim, scope, fg)
            return Array(elem, count)
        if isinstance(node, c_ast.FuncDecl):
            ret = self.build_type(node.type, scope, fg)
            params, variadic = self.build_params(node.args, scope, fg)
            return Func(ret, params, variadic)
        if isinstance(node, (c_ast.IdentifierType, c_ast.Struct, c_ast.Union, c_ast.Enum)):
            return self.build_base(node, scope, fg)
        raise CompileError(f"unsupported declarator {type(node).__name__}", node)

    def build_params(self, plist, scope, fg):
        if plist is None:
            return None, False
        params = []
        variadic = False
        for p in plist.params:
            if isinstance(p, c_ast.EllipsisParam):
                variadic = True
                continue
            ty = self.build_type(p.type if isinstance(p, (c_ast.Decl, c_ast.Typename)) else p, scope, fg)
            params.append(ty)
        if len(params) == 1 and params[0].is_void():
            params = []
        return [cty.decay(t) for t in params], variadic

    def build_base(self, node, scope: Scope, fg=None) -> cty.Type:
        if isinstance(node, c_ast.IdentifierType):
            if len(node.names) == 1:
                sym = scope.lookup(node.names[0])
                if isinstance(sym, TypedefSym):
                    return sym.type
            return parse_int_name(node.names, node)
        if isinstance(node, (c_ast.Struct, c_ast.Union)):
            return self.build_struct(node, scope, fg)
        if isinstance(node, c_ast.Enum):
            return self.build_enum(node, scope, fg)
        raise CompileError(f"unsupported type {type(node).__name__}", node)

    def build_struct(self, node, scope, fg):
        is_union = isinstance(node, c_ast.Union)
        ty = None
        if node.name:
            ty = scope.lookup_tag(node.name)
            if ty is not None and (not isinstance(ty, Struct) or ty.is_union != is_union):
                ty = None
        if node.decls is None:  # reference or forward declaration
            if ty is None:
                ty = Struct(node.name, is_union)
                scope.tags[node.name] = ty
            return ty
        if ty is None or ty.complete or node.name not in scope.tags:
            ty = Struct(node.name, is_union)
            if node.name:
                scope.tags[node.name] = ty
        members = []
        for d in node.decls:
            if getattr(d, "bitsize", None) is not None:
                raise CompileError("bit-fields are not supported", d)
            mty = self.build_type(d.type, scope, fg)
            members.append((d.name, mty))
        ty.define(members)
        return ty

    def build_enum(self, node, scope, fg):
        if node.values is None:
            return cty.INT
        value = 0
        for e in node.values.enumerators:
            if e.value is not None:
                value = self.const_int(e.value, scope, fg)
            scope.names[e.name] = EnumConst(value)
            value += 1
        return cty.INT

    def const_int(self, node, scope, fg=None) -> int:
        from .funcgen import FuncGen

        gen = fg or FuncGen(self, None, scope)
        return gen.eval_const_int(node, scope)

    # ------------------------------------------------------------ translation units

    def add_tu(self, ast: c_ast.FileAST, name: str) -> TU:
        tu = TU(name)
        self.tus.append(tu)
        for ext in ast.ext:
            self.declare_toplevel(tu, ext)
        return tu

    def declare_toplevel(self, tu: TU, ext):
        scope = tu.scope
        if isinstance(ext, c_ast.Typedef):
            scope.names[ext.name] = TypedefSym(self.build_type(ext.type, scope))
        elif isinstance(ext, c_ast.FuncDef):
            self.declare_function(tu, ext.decl, ext)
        elif isinstance(ext, c_ast.Decl):
            if ext.name is None:
                self.build_type(ext.type, scope)  # struct/union/enum declaration
            elif isinstance(ext.type, c_ast.FuncDecl):
                self.declare_function(tu, ext, None)
            else:
                self.declare_variable(tu, ext)
        elif isinstance(ext, c_ast.Pragma):
            pass
        else:
            raise CompileError(f"unsupported top-level {type(ext).__name__}", ext)

    def _lookup_global(self, tu: TU, name: str, static: bool):
        if static:
            g = tu.scope.names.get(name)
            return g if isinstance(g, GObj) else None
        g = self.externs.get(name)
        if g is None:
            g = tu.scope.names.get(name)
            if isinstance(g, GObj) and g.static:
                return None
        return g

    def declare_function(self, tu, decl, fdef):
        scope = tu.scope
        ty = self.build_type(decl.type, scope)
        static = "static" in decl.storage
        g = self._lookup_global(tu, decl.name, static)
        if g is None or g.kind != "func":
            g = GObj(decl.name, ty, "func", static=static, tu=tu, coord=decl.coord)
            if static:
                scope.names[decl.name] = g
            else:
                self.externs[decl.name] = g
                scope.names[decl.name] = g
        elif fdef is not None or g.type.params is None:
            g.type = ty
        if fdef is not None:
            if g.fdef is not None and not g.weak:
                raise CompileError(f"redefinition of function '{decl.name}'", decl)
            g.weak = tu.name == "runtime:libc" and not static
            g.fdef = fdef
            g.tu = tu
            g.defined = True
            g.type = ty
            if static:
                scope.names[decl.name] = g
        elif not static:
            scope.names[decl.name] = g
        return g

    def declare_variable(self, tu, decl):
        scope = tu.scope
        ty = self.build_type(decl.type, scope)
        static = "static" in decl.storage
        is_extern = "extern" in decl.storage and decl.init is None
        g = self._lookup_global(tu, decl.name, static)
        if g is None or g.kind != "var":
            g = GObj(decl.name, ty, "var", static=static, tu=tu, coord=decl.coord)
            if static:
                scope.names[decl.name] = g
            else:
                self.externs[decl.name] = g
                scope.names[decl.name] = g
        else:
            scope.names[decl.name] = g
            if isinstance(ty, Array) and ty.count is not None and isinstance(g.type, Array) and g.type.count is None:
                g.type = ty
        if not is_extern:
            if not isinstance(ty, Array) or ty.count is not None or decl.init is not None:
                if ty.is_void() or (ty.is_struct() and not ty.complete):
                    raise CompileError(f"variable '{decl.name}' has incomplete type {ty}", decl)
            if decl.init is not None or not g.defined:
                if g.defined and decl.init is not None and g.init is not None:
                    raise CompileError(f"redefinition of '{decl.name}'", decl)
                if decl.init is not None:
                    g.init = decl.init
                    g.tu = tu
                    g.type = ty
                    if isinstance(ty, Array) and ty.count is None:
                        from .funcgen import FuncGen

                        g.type = Array(ty.elem, FuncGen(self, None, scope).init_count(ty, decl.init))
                if not g.defined:
                    g.defined = True
                    g.tu = tu
                    if decl.init is None:
                        g.type = ty if not (isinstance(g.type, Array) and g.type.count is not None) else g.type
        return g

    # ------------------------------------------------------------ data layout

    def resolve_data(self, g: GObj):
        """Compute the word list of a data object (ints and Addr)."""
        if g.words is not None:
            return
        if not g.defined:
            raise CompileError(f"undefined reference to '{g.name}'", g.coord)
        from .funcgen import FuncGen

        ty = g.type
        fg = FuncGen(self, None, g.tu.scope)
        if g.init is not None and isinstance(ty, Array) and ty.count is None:
            ty = Array(ty.elem, fg.init_count(ty, g.init))
            g.type = ty
        if isinstance(ty, Array) and ty.count is None:
            raise CompileError(f"array '{g.name}' has incomplete type", g.coord)
        words = [0] * max(1, ty.size)
        if g.init is not None:
            fg.fill_init(words, 0, ty, g.init)
        g.words = words

    def data_lines(self, g: GObj):
        label = self.label_of(g)
        lines = []
        for i, w in enumerate(g.words):
            if isinstance(w, Addr):
                target = self.label_at(w.obj, w.off)
                if target is None:
                    raise CompileError(f"initializer address {w.obj.name}+{w.off} is outside the object", g.coord)
                w = target
            elif w >= 1 << 31:
                w -= 1 << 32
            lab = label if i == 0 else g.aux.get(i)
            comment = None
            if i == 0 and g.kind == "var":
                comment = f"OUTPUT: {g.name}" if g.name in self.output_names else g.name
            elif i == 0 and g.kind == "str":
                text = "".join(chr(c) if 32 <= c < 127 else "." for c in g.words[:-1])
                comment = '"' + (text if len(text) <= 28 else text[:25] + "...") + '"'
            lines.append(Line(".fill", (w,), lab, comment))
        return lines

    # ------------------------------------------------------------ runtime and driver

    def helper_cell(self, name: str) -> str:
        self.helpers_needed.add(name)
        key = ("helper", name)
        if key not in self.cells:
            cell = self.mangler.named(name, f"&{name}", capital=True, prefix="P")
            self.func_ptr_cells.append(Line(".fill", (self.helper_labels[name],), cell))
            self.cells[key] = cell
        return self.cells[key]

    def runtime_func(self, name: str) -> GObj:
        g = self.externs.get(name)
        if g is None:
            raise CompileError(f"runtime function {name} is missing")
        self.need(g)
        return g

    def load_runtime(self):
        from pathlib import Path

        from .frontend import parse_file

        for name in ("rt", "ll", "libc"):
            path = Path(__file__).parent / "runtime" / f"{name}.c"
            self.add_tu(parse_file(path), "runtime:libc" if name == "libc" else "runtime")

    def need_everything(self):
        """Compile all user code, reachable or not, so errors in dead code are reported too."""
        for tu in self.tus:
            if tu.name.startswith("runtime"):
                continue
            for g in list(tu.scope.names.values()):
                if isinstance(g, GObj) and g.defined and (g.kind == "var" or g.fdef is not None):
                    self.need(g)

    def build(self, entry: str = "main", all_code: bool = False) -> Program:
        from .funcgen import FuncGen
        from .runtime import emit_helpers

        p = self.program
        main = self.externs.get(entry)
        if main is None or main.kind != "func" or main.fdef is None:
            raise CompileError(f"no {entry} function")
        self.need(main)
        if all_code:
            self.need_everything()
        main_ptr = self.addr_cell(main)
        p.emit("lw", 0, 5, "spinit", comment="initialize stack pointer")
        p.emit("lw", 0, 6, main_ptr, comment="load address of main")
        p.emit("jalr", 6, 7, comment="call main")
        p.emit("sw", 0, 1, "Result", comment="record main's return value")
        p.emit("halt")
        p.io.append(Line(".fill", (0,), "Result", "OUTPUT: main's return value"))
        p.data.append(Line(".fill", (p.stack_label,), "spinit"))
        done_funcs = 0
        done_data = 0
        while done_funcs < len(self.worklist) or done_data < len(self.datalist):
            while done_funcs < len(self.worklist):
                g = self.worklist[done_funcs]
                done_funcs += 1
                p.text.extend(FuncGen(self, g, g.tu.scope).compile_function())
            while done_data < len(self.datalist):
                self.resolve_data(self.datalist[done_data])
                done_data += 1
        for g in self.datalist:
            lines = self.data_lines(g)
            if g.type.is_scalar():
                p.data.extend(lines)
            else:
                p.arrays.append(lines)
        emit_helpers(self, self.helpers_needed)
        p.func_ptrs.extend(self.func_ptr_cells)
        p.data[1:1] = self.data_cells
        return p
