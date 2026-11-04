"""Per-function code generation: C AST -> LC-2K instructions.

Register plan:
  r0        zero
  r1..r4    expression temporaries (spilled to the frame under pressure)
  r5        stack pointer (stack grows upward)
  r6        scratch: constants, call targets, helper call targets
  r7        return address

Stack frame, as offsets from r5:
  0           saved r7 (non-leaf functions)
  1..np       parameters
  then        locals, then spill slots
  FS+1+i      outgoing argument i (the callee's parameter i)
where FS is the frame size, known only after the body is generated.
A call bumps r5 by FS, jumps, and restores r5 afterwards.
"""

import os
from dataclasses import dataclass

from pycparser import c_ast

from . import cty
from .compiler import Addr, EnumConst, GObj, Local, Scope, TypedefSym
from .cty import INT, UINT, Array, Func, Ptr
from .frontend import CompileError

ZERO, SP, AT, RA = 0, 5, 6, 7

# Expression temporaries. LC2KCC_TEMPS=123 shrinks the pool to stress-test spilling.
TEMPS = tuple(int(c) for c in os.environ.get("LC2KCC_TEMPS", "1234"))
VARARG_SLOTS = 12


class NotConstant(Exception):
    pass


# ---------------------------------------------------------------- frame-dependent operands


@dataclass(frozen=True)
class Lazy:
    kind: str  # 'arg' | 'spill' | 'fs'
    n: int = 0


@dataclass
class Ins:
    op: str
    a: object = 0
    b: object = 0
    c: object = 0
    comment: str | None = None


class Tmp:
    __slots__ = ("reg", "slot", "pinned")

    def __init__(self, reg):
        self.reg = reg
        self.slot = None
        self.pinned = False


class Val:
    """An expression result.

    Value = (tmp register contents if any) + (address of sym | frame slot SP+... | nothing)
            + off.  With neither tmp nor sym nor sp it is the constant `off`.
    For aggregates (struct/union) the "value" is the address of the object.
    """

    __slots__ = ("type", "tmp", "sym", "sp", "off", "bits")

    def __init__(self, ty, tmp=None, sym=None, sp=False, off=0, bits=None):
        self.type = ty
        self.tmp = tmp
        self.sym = sym
        self.sp = sp
        self.off = off
        self.bits = bits

    @property
    def is_const(self):
        return self.tmp is None and self.sym is None and not self.sp

    def copy(self, **kw):
        v = Val(self.type, self.tmp, self.sym, self.sp, self.off, self.bits)
        for k, x in kw.items():
            setattr(v, k, x)
        return v


def const_val(ty, value):
    v = Val(ty, off=cty.wrap(value, ty))
    if ty.is_int() and v.off >= 0:
        v.bits = max(1, v.off.bit_length())
    return v


def s32(v: int) -> int:
    v &= 0xFFFFFFFF
    return v - (1 << 32) if v >> 31 else v


def int_range_bits(ty):
    """Number of value bits if the type is unsigned and narrower than 32, else None."""
    if ty is cty.BOOL:
        return 1
    if ty.is_int() and not ty.signed and ty.size < 4:
        return ty.size * 8
    return None


class FuncGen:
    def __init__(self, comp, gobj, scope):
        self.comp = comp
        self.p = comp.program
        self.gobj = gobj
        self.scope = Scope(scope)
        self.code: list[Ins] = []
        self.noemit = False
        self.pending_comment = None
        self.owner = {r: None for r in TEMPS}
        self.live: list[Tmp] = []
        self.free_slots: list[int] = []
        self.nspill = 0
        self.leaf = True
        self.local_top = 1
        self.local_max = 1
        self.break_stack: list[str] = []
        self.continue_stack: list[str] = []
        self.user_labels: dict[str, str] = {}
        self.ret_label = None
        self.ret_type = cty.INT
        self.variadic = False

    # ------------------------------------------------------------ emission

    def emit(self, op, a=0, b=0, c=0, comment=None):
        if self.noemit:
            raise NotConstant()
        if comment is None and self.pending_comment is not None:
            comment, self.pending_comment = self.pending_comment, None
        self.code.append(Ins(op, a, b, c, comment))

    def new_label(self):
        return self.comp.mangler.fresh("l")

    def place(self, label):
        self.code.append(Ins("label", c=label))

    def jmp(self, label):
        self.emit("beq", ZERO, ZERO, label)

    def internal(self, msg):
        return CompileError(f"internal compiler error: {msg}")

    # ------------------------------------------------------------ registers

    def new_tmp(self, keep=(), reg=None):
        if reg is None:
            reg = self.alloc_reg(keep)
        else:
            if self.owner[reg] is not None:
                raise self.internal(f"register r{reg} busy")
        t = Tmp(reg)
        self.owner[reg] = t
        self.live.append(t)
        return t

    def alloc_reg(self, keep=()):
        for r in TEMPS:
            if self.owner[r] is None:
                return r
        for t in self.live:
            if t.reg is not None and t not in keep and not t.pinned:
                r = t.reg
                self.spill(t)
                return r
        raise CompileError("expression too complex: out of registers")

    def alloc_slot(self):
        if self.free_slots:
            return self.free_slots.pop()
        self.nspill += 1
        return self.nspill - 1

    def spill(self, t):
        slot = self.alloc_slot()
        self.emit("sw", SP, t.reg, Lazy("spill", slot))
        self.owner[t.reg] = None
        t.reg = None
        t.slot = slot

    def reg_of(self, t, keep=()):
        if t.reg is None:
            r = self.alloc_reg(tuple(keep) + (t,))
            self.emit("lw", SP, r, Lazy("spill", t.slot))
            self.free_slots.append(t.slot)
            t.slot = None
            t.reg = r
            self.owner[r] = t
        return t.reg

    def release_tmp(self, t):
        if t.reg is not None:
            self.owner[t.reg] = None
            t.reg = None
        if t.slot is not None:
            self.free_slots.append(t.slot)
            t.slot = None
        self.live.remove(t)

    def release(self, v):
        if v is not None and v.tmp is not None:
            self.release_tmp(v.tmp)
            v.tmp = None

    def flush(self, keep=()):
        for t in list(self.live):
            if t.reg is not None and t not in keep:
                self.spill(t)

    def mov(self, dst, src):
        if dst != src:
            self.emit("add", src, ZERO, dst)

    # ------------------------------------------------------------ constants

    def k(self, value):
        """Label of the .fill word holding a constant."""
        if self.noemit:
            raise NotConstant()
        return self.p.const(s32(value))

    def cell(self, g, off=0):
        if self.noemit:
            raise NotConstant()
        return self.comp.addr_cell(g, off)

    def helper_cell(self, name):
        if self.noemit:
            raise NotConstant()
        return self.comp.helper_cell(name)

    def load_const_reg(self, reg, value):
        value = s32(value)
        if value == 0:
            self.emit("add", ZERO, ZERO, reg)
        else:
            self.emit("lw", ZERO, reg, self.k(value))

    def const_tmp(self, value, keep=()):
        t = self.new_tmp(keep)
        self.load_const_reg(t.reg, value)
        return t

    # ------------------------------------------------------------ Val plumbing

    def to_reg(self, v, keep=()):
        """Materialize a Val into a plain register Val (consumes v)."""
        plain = v.tmp is not None and v.sym is None and not v.sp and v.off == 0
        if plain:
            self.reg_of(v.tmp, keep)
            return v
        bits = v.bits if v.is_const else None
        ty = v.type
        t = v.tmp
        if v.sym is not None:
            lab = self.comp.label_at(v.sym, v.off) if v.sym.kind != "func" else None
            if lab is not None:
                cell = self.cell(v.sym, v.off)
                extra = 0
            else:
                cell = self.cell(v.sym, 0)
                extra = v.off
            if t is None:
                t = self.new_tmp(keep)
                self.emit("lw", ZERO, t.reg, cell)
            else:
                r = self.reg_of(t, keep)
                self.emit("lw", ZERO, AT, cell)
                self.emit("add", r, AT, r)
            if extra:
                self.emit("lw", ZERO, AT, self.k(extra))
                self.emit("add", t.reg, AT, t.reg)
        elif v.sp:
            if t is None:
                t = self.new_tmp(keep)
                if v.off == 0:
                    self.emit("add", SP, ZERO, t.reg)
                else:
                    self.emit("lw", ZERO, t.reg, self.k(v.off))
                    self.emit("add", SP, t.reg, t.reg)
            else:
                r = self.reg_of(t, keep)
                self.emit("add", SP, r, r)
                if v.off:
                    self.emit("lw", ZERO, AT, self.k(v.off))
                    self.emit("add", r, AT, r)
        elif t is None:
            t = self.const_tmp(v.off, keep)
        else:
            r = self.reg_of(t, keep)
            if v.off:
                self.emit("lw", ZERO, AT, self.k(v.off))
                self.emit("add", r, AT, r)
        return Val(ty, tmp=t, bits=bits)

    def src_reg(self, v, keep=()):
        """A register holding v for use as a source operand (may be r0 or r6)."""
        if v.is_const:
            if s32(v.off) == 0:
                return ZERO
            self.emit("lw", ZERO, AT, self.k(v.off))
            return AT
        if v.tmp is not None and v.sym is None and not v.sp and v.off == 0:
            return self.reg_of(v.tmp, keep)
        raise self.internal("src_reg on unmaterialized address")

    # ------------------------------------------------------------ addressing

    def addr_form(self, v, keep=()):
        """(base register, offset operand) for a memory access at address v."""
        if v.sym is not None:
            lab = self.comp.label_at(v.sym, v.off)
            if lab is not None:
                if v.tmp is None:
                    return ZERO, lab
                return self.reg_of(v.tmp, keep), lab
            nv = self.to_reg(v, keep)
            v.tmp, v.sym, v.sp, v.off = nv.tmp, None, False, 0
            return self.reg_of(v.tmp, keep), 0
        if v.sp:
            if v.tmp is None:
                return SP, v.off
            r = self.reg_of(v.tmp, keep)
            self.emit("add", SP, r, r)
            v.sp = False
        if v.tmp is None:
            return ZERO, v.off
        r = self.reg_of(v.tmp, keep)
        if not -32768 <= v.off <= 32767:
            self.emit("lw", ZERO, AT, self.k(v.off))
            self.emit("add", r, AT, r)
            v.off = 0
        return r, v.off

    def load(self, addr):
        """Load the object that pointer-Val addr points to."""
        ty = addr.type.target
        if ty.is_array():
            return addr.copy(type=Ptr(ty.elem))
        if ty.is_func():
            return addr.copy(type=Ptr(ty))
        if ty.is_struct():
            return addr.copy(type=ty)
        if ty.is_void():
            raise CompileError("dereferencing a void pointer")
        base, off = self.addr_form(addr)
        if addr.tmp is not None:
            t = addr.tmp
        else:
            t = self.new_tmp()
        self.emit("lw", base, t.reg, off)
        return Val(ty, tmp=t, bits=int_range_bits(ty))

    def store_to(self, addr, v):
        """Store v through address addr, converting to the object type (consumes addr)."""
        ty = addr.type.target
        v = self.conv(v, ty)
        akeep = (addr.tmp,) if addr.tmp is not None else ()
        if not v.is_const:
            v = self.to_reg(v, keep=akeep)
            self.reg_of(v.tmp, keep=akeep)
        base, off = self.addr_form(addr, keep=(v.tmp,) if v.tmp is not None else ())
        if v.is_const:
            if s32(v.off) == 0:
                reg = ZERO
            else:
                self.emit("lw", ZERO, AT, self.k(v.off))
                reg = AT
        else:
            reg = v.tmp.reg
        self.emit("sw", base, reg, off)
        self.release(addr)
        return v

    # ------------------------------------------------------------ conversions

    def conv(self, v, to):
        """Convert Val v to type `to` (value conversion)."""
        frm = v.type
        if to.is_void():
            self.release(v)
            return Val(to)
        if frm is to:
            return v
        if to is cty.BOOL:
            # conversion to _Bool is "!= 0", not truncation
            if v.is_const:
                return const_val(to, 1 if v.off & 0xFFFFFFFF else 0)
            if v.tmp is None:
                return const_val(to, 1)  # the address of an object is never null
            r = self.compare_value("!=", v, const_val(INT, 0), None)
            r.type = to
            return r
        if to.is_ptr() or (to.is_int() and to.size == 4):
            if v.is_const and not frm.is_struct():
                return const_val(to, v.off)
            r = v.copy(type=to)
            if to.is_int() and v.tmp is None:
                r.bits = None  # a symbol or frame address has no known range
            return r
        if to.is_int():
            # to is narrower than 32 bits (32-bit targets returned above)
            if v.is_const:
                return const_val(to, v.off)
            lo, hi = self.value_range(v)
            tlo = -(1 << (to.size * 8 - 1)) if to.signed else 0
            thi = (1 << (to.size * 8 - 1)) - 1 if to.signed else (1 << (to.size * 8)) - 1
            if tlo <= lo and hi <= thi:
                return v.copy(type=to)
            v = self.to_reg(v)
            self.normalize(v.tmp, to)
            v.type = to
            v.bits = int_range_bits(to)
            return v
        if to.is_struct() and frm.is_struct():
            return v.copy(type=to)
        raise CompileError(f"cannot convert {frm} to {to}")

    @staticmethod
    def value_range(v):
        """Inclusive (lo, hi) bounds of a non-constant integer Val."""
        if v.bits is not None:
            return 0, (1 << v.bits) - 1
        ty = v.type
        if ty.is_int():
            if ty.signed:
                return -(1 << (ty.size * 8 - 1)), (1 << (ty.size * 8 - 1)) - 1
            return 0, (1 << (ty.size * 8)) - 1
        return -(1 << 31), (1 << 32) - 1

    def normalize(self, t, to, keep=()):
        """Truncate / extend the register of tmp t to the narrow integer type."""
        r = self.reg_of(t, keep)
        bits = to.size * 8
        if to.signed:
            half = 1 << (bits - 1)
            self.emit("lw", ZERO, AT, self.k(half))
            self.emit("add", r, AT, r)
            self.emit("nor", r, r, r)
            self.emit("lw", ZERO, AT, self.k(-(1 << bits)))
            self.emit("nor", r, AT, r)
            self.emit("lw", ZERO, AT, self.k(-half))
            self.emit("add", r, AT, r)
        else:
            self.emit("nor", r, r, r)
            self.emit("lw", ZERO, AT, self.k(-(1 << bits)))
            self.emit("nor", r, AT, r)

    # ------------------------------------------------------------ helper calls

    def helper_call(self, name, args):
        """Call a runtime helper with args in r1.. ; result Val(tmp=r1, unsigned/int)."""
        vals = [self.to_reg(a, keep=()) for a in args]
        # tmps that survive: flush everything that is not an argument
        self.flush(keep=tuple(v.tmp for v in vals))
        self.place_args([v.tmp for v in vals], [1, 2, 3][: len(vals)])
        for v in vals:
            self.release(v)
        self.emit("lw", ZERO, AT, self.helper_cell(name))
        self.emit("jalr", AT, 4)
        t = self.new_tmp(reg=1)
        return Val(INT, tmp=t)

    def place_args(self, tmps, targets):
        """Move arg tmps into the target registers. All other tmps are already flushed."""
        moves = []
        reloads = []
        for t, dst in zip(tmps, targets):
            if t.reg is None:
                reloads.append((t, dst))
            elif t.reg != dst:
                moves.append([t.reg, dst])
        while moves:
            srcs = [m[0] for m in moves]
            for m in moves:
                if m[1] not in srcs:
                    self.mov(m[1], m[0])
                    moves.remove(m)
                    break
            else:
                m = moves[0]
                self.emit("add", m[0], ZERO, AT)
                for other in moves:
                    if other[0] == m[0]:
                        other[0] = AT
        for t, dst in reloads:
            self.emit("lw", SP, dst, Lazy("spill", t.slot))
        for t in tmps:
            if t.reg is not None:
                self.owner[t.reg] = None
            if t.slot is not None:
                self.free_slots.append(t.slot)
                t.slot = None
        for t, dst in zip(tmps, targets):
            t.reg = dst
            self.owner[dst] = t

    # ------------------------------------------------------------ calls

    def call(self, target, args, ret_type, params=None, variadic=False, node=None):
        """Emit a C-ABI call. target: GObj (direct) or Val (function pointer)."""
        self.leaf = False
        fp = None
        if isinstance(target, Val):
            fp = self.to_reg(target)
        arg_vals = []
        if ret_type.is_struct():
            # hidden first argument: where the callee stores the returned struct
            tmp = self.alloc_temp(ret_type.size)
            arg_vals.append(Val(Ptr(ret_type), sp=True, off=tmp))
        nfixed = len(arg_vals) + (len(params) if params is not None else 0)
        for i, a in enumerate(args):
            if params is not None and i < len(params):
                a = self.conv(a, params[i])
            else:
                a = self.conv(a, self.default_promote(a.type))
            arg_vals.append(a)
        offsets = []
        off = 0
        for a in arg_vals:
            offsets.append(off)
            off += max(1, a.type.size) if a.type.is_struct() else 1
        fixed_words = 0
        for a in arg_vals[:nfixed]:
            fixed_words += max(1, a.type.size) if a.type.is_struct() else 1
        if variadic and off - fixed_words > VARARG_SLOTS:
            raise CompileError("too many variadic arguments", node)
        for o, a in zip(offsets, arg_vals):
            self.store_arg(o, a)
        keep = (fp.tmp,) if fp is not None else ()
        if fp is not None:
            self.reg_of(fp.tmp)
        self.flush(keep=keep)
        self.emit("lw", ZERO, AT, Lazy("fs", 1))
        self.emit("add", SP, AT, SP)
        if fp is not None:
            self.emit("jalr", fp.tmp.reg, RA)
            self.release(fp)
        else:
            self.emit("lw", ZERO, AT, self.cell(target))
            self.emit("jalr", AT, RA)
        self.emit("lw", ZERO, AT, Lazy("fs", -1))
        self.emit("add", SP, AT, SP)
        if ret_type.is_void():
            return Val(cty.VOID)
        if ret_type.is_struct():
            return Val(ret_type, sp=True, off=tmp)
        t = self.new_tmp(reg=1)
        return Val(ret_type, tmp=t, bits=int_range_bits(ret_type))

    @staticmethod
    def default_promote(ty):
        return cty.promote(cty.decay(ty))

    def store_arg(self, off, v):
        """Store argument v at word offset `off` of the outgoing argument area."""
        if v.type.is_struct():
            return self.copy_to_arg(off, v)
        slot = Lazy("arg", off)
        if v.is_const:
            if s32(v.off) == 0:
                reg = ZERO
            else:
                self.emit("lw", ZERO, AT, self.k(v.off))
                reg = AT
        elif v.tmp is None or v.sym is not None or v.sp or v.off != 0:
            nv = self.to_reg(v)
            reg = nv.tmp.reg
            v = nv
        else:
            if v.tmp.reg is None:
                self.emit("lw", SP, AT, Lazy("spill", v.tmp.slot))
                reg = AT
            else:
                reg = v.tmp.reg
        self.emit("sw", SP, reg, slot)
        self.release(v)

    def copy_to_arg(self, off, src):
        """Copy a struct argument (address Val src) into the outgoing argument area."""
        n = max(1, src.type.size)
        src = self.to_reg(src)
        sr = self.reg_of(src.tmp)
        if n <= 8:
            for j in range(n):
                self.emit("lw", sr, AT, j)
                self.emit("sw", SP, AT, Lazy("arg", off + j))
        else:
            dst = self.new_tmp(keep=(src.tmp,))
            self.emit("lw", ZERO, dst.reg, Lazy("argaddr", off))
            self.emit("add", SP, dst.reg, dst.reg)
            self.copy_loop(src.tmp, dst, n)
            self.release_tmp(dst)
        self.release(src)

    def copy_loop(self, src, dst, n):
        """Copy n words from [src] to [dst] with a loop; src/dst are tmps (advanced)."""
        cnt = self.new_tmp(keep=(src, dst))
        sr = self.reg_of(src, keep=(dst, cnt))
        dr = self.reg_of(dst, keep=(src, cnt))
        self.load_const_reg(cnt.reg, n)
        top = self.new_label()
        self.place(top)
        self.emit("lw", sr, AT, 0)
        self.emit("sw", dr, AT, 0)
        self.emit("lw", ZERO, AT, self.k(1))
        self.emit("add", sr, AT, sr)
        self.emit("add", dr, AT, dr)
        self.emit("lw", ZERO, AT, self.k(-1))
        self.emit("add", cnt.reg, AT, cnt.reg)
        skip = self.new_label()
        self.emit("beq", cnt.reg, ZERO, skip)
        self.jmp(top)
        self.place(skip)
        self.release_tmp(cnt)

    def alloc_temp(self, n):
        """A fresh frame area of n words (released with the enclosing scope)."""
        slot = self.local_top
        self.local_top += max(1, n)
        self.local_max = max(self.local_max, self.local_top)
        return slot

    # ------------------------------------------------------------ constants evaluation (no code)

    def eval_const_int(self, node, scope=None):
        saved = self.scope
        if scope is not None:
            self.scope = scope
        prev_noemit = self.noemit
        self.noemit = True
        try:
            v = self.rvalue(node)
        except NotConstant:
            raise CompileError("expression is not an integer constant", node) from None
        finally:
            self.noemit = prev_noemit
            self.scope = saved
        if not v.is_const:
            raise CompileError("expression is not an integer constant", node)
        return v.off

    # ------------------------------------------------------------ static initializers

    def init_count(self, ty, init):
        if isinstance(init, c_ast.Constant) and init.type == "string":
            return len(self.comp.decode_string(init.value)) + 1
        if isinstance(init, c_ast.InitList):
            count = 0
            idx = 0
            for e in init.exprs:
                if isinstance(e, c_ast.NamedInitializer):
                    d = e.name[0]
                    if isinstance(d, c_ast.ID):
                        raise CompileError("field designator in array initializer", e)
                    idx = self.eval_const_int(d)
                idx += 1
                count = max(count, idx)
            return count
        raise CompileError("invalid array initializer", init)

    def designate(self, ty, names):
        """Walk a designator list (.field / [index]); returns (word offset, target type, first index)."""
        off = 0
        first = None
        for d in names:
            if isinstance(d, c_ast.ID):
                if not ty.is_struct():
                    raise CompileError("field designator on a non-struct", d)
                found = ty.find(d.name)
                if not found:
                    raise CompileError(f"{ty} has no member '{d.name}'", d)
                m, extra = found
                off += extra + m.offset
                if first is None:
                    first = ty.members.index(m) if m in ty.members else 0
                ty = m.type
            else:
                if not ty.is_array():
                    raise CompileError("index designator on a non-array", d)
                idx = self.eval_const_int(d)
                off += idx * ty.elem.size
                if first is None:
                    first = idx
                ty = ty.elem
        return off, ty, first

    def fill_init(self, words, base, ty, init):
        """Write static initializer `init` for an object of type `ty` at words[base:]."""
        if ty.is_array():
            elem = ty.elem
            if isinstance(init, c_ast.Constant) and init.type == "string" and elem.is_int():
                chars = self.comp.decode_string(init.value, init)
                for i, ch in enumerate(chars[: ty.count]):
                    words[base + i * elem.size] = ch
                return
            if not isinstance(init, c_ast.InitList):
                raise CompileError("array initializer must be a list", init)
            idx = 0
            for e in init.exprs:
                if isinstance(e, c_ast.NamedInitializer):
                    off, t, first = self.designate(ty, e.name)
                    self.fill_init(words, base + off, t, e.expr)
                    idx = first + 1
                    continue
                if ty.count is not None and idx >= ty.count:
                    raise CompileError("too many initializers", init)
                self.fill_init(words, base + idx * elem.size, elem, e)
                idx += 1
            return
        if ty.is_struct():
            if not isinstance(init, c_ast.InitList):
                raise CompileError("struct initializer must be a list", init)
            members = ty.members if not ty.is_union else ty.members[:1]
            idx = 0
            for e in init.exprs:
                if isinstance(e, c_ast.NamedInitializer):
                    off, t, first = self.designate(ty, e.name)
                    self.fill_init(words, base + off, t, e.expr)
                    idx = first + 1
                    continue
                if idx >= len(members):
                    raise CompileError("too many initializers", init)
                m = members[idx]
                self.fill_init(words, base + m.offset, m.type, e)
                idx += 1
            return
        if isinstance(init, c_ast.InitList):
            if len(init.exprs) == 1:
                return self.fill_init(words, base, ty, init.exprs[0])
            raise CompileError("scalar initializer must have one value", init)
        v = self.eval_static_conv(init, ty)
        words[base] = v

    def eval_static_conv(self, init, ty):
        prev_noemit = self.noemit
        self.noemit = True
        try:
            v = self.rvalue(init)
            v = self.conv(v, ty)
        except NotConstant:
            raise CompileError("initializer is not a compile-time constant", init) from None
        finally:
            self.noemit = prev_noemit
        if v.tmp is not None or v.sp:
            raise CompileError("initializer is not a compile-time constant", init)
        if v.sym is not None:
            return Addr(v.sym, v.off)
        return s32(v.off)

    # ------------------------------------------------------------ symbols

    def lookup(self, name, node):
        sym = self.scope.lookup(name)
        if sym is None:
            raise CompileError(f"undeclared identifier '{name}'", node)
        return sym

    # ------------------------------------------------------------ expressions: lvalues

    def addr_of(self, node):
        """Address Val (type Ptr(object type)) of an lvalue expression."""
        if isinstance(node, c_ast.ID):
            sym = self.lookup(node.name, node)
            if isinstance(sym, Local):
                return Val(Ptr(sym.type), sp=True, off=sym.slot)
            if isinstance(sym, GObj):
                self.comp.need(sym)
                return Val(Ptr(sym.type), sym=sym)
            raise CompileError(f"'{node.name}' is not an lvalue", node)
        if isinstance(node, c_ast.UnaryOp) and node.op == "*":
            v = self.rvalue(node.expr)
            if not v.type.is_ptr():
                raise CompileError("dereferencing a non-pointer", node)
            return v
        if isinstance(node, c_ast.ArrayRef):
            base = self.rvalue(node.name)
            idx = self.rvalue(node.subscript)
            if idx.type.is_ptr():
                base, idx = idx, base
            if not base.type.is_ptr():
                raise CompileError("subscripted value is not an array or pointer", node)
            return self.ptr_add(base, idx, node)
        if isinstance(node, c_ast.StructRef):
            if node.type == ".":
                base = self.addr_of_aggregate(node.name)
                sty = base.type.target
            else:
                base = self.rvalue(node.name)
                if not base.type.is_ptr():
                    raise CompileError("-> applied to a non-pointer", node)
                sty = base.type.target
            if not sty.is_struct():
                raise CompileError("member access on a non-struct", node)
            found = sty.find(node.field.name)
            if not found:
                raise CompileError(f"{sty} has no member '{node.field.name}'", node)
            m, extra = found
            return base.copy(type=Ptr(m.type), off=base.off + m.offset + extra)
        if isinstance(node, c_ast.Constant) and node.type == "string":
            g = self.comp.string_obj(node.value, node)
            self.comp.need(g)
            return Val(Ptr(g.type), sym=g)
        if isinstance(node, c_ast.CompoundLiteral):
            ty = self.comp.build_type(node.type, self.scope, self)
            if isinstance(ty, Array) and ty.count is None:
                ty = Array(ty.elem, self.init_count(ty, node.init))
            slot = self.alloc_temp(ty.size if (ty.is_array() or ty.is_struct()) else 1)
            self.local_init(Val(Ptr(ty), sp=True, off=slot), ty, node.init)
            return Val(Ptr(ty), sp=True, off=slot)
        raise CompileError(f"expression is not an lvalue ({type(node).__name__})", node)

    def addr_of_aggregate(self, node):
        if isinstance(node, c_ast.FuncCall):
            v = self.rvalue(node)
            if not v.type.is_struct():
                raise CompileError("member access on a non-struct", node)
            return v.copy(type=Ptr(v.type))
        return self.addr_of(node)

    def ptr_add_const(self, v, k):
        r = v.copy(off=v.off + k)
        if v.tmp is None and v.sym is None and not v.sp:
            r.off = cty.wrap(r.off, v.type)
        return r

    def scale_index(self, idx, size, node):
        """Multiply integer Val idx by element size; returns Val (const or reg)."""
        if size == 1:
            return idx
        if idx.is_const:
            return const_val(INT, s32(idx.off * size))
        return self.mul_const(self.to_reg(idx), size)

    def ptr_add(self, ptr, idx, node, negate=False):
        """ptr + idx (or ptr - idx) with element scaling; both rvalue Vals."""
        elem = ptr.type.target
        size = elem.size if not elem.is_void() and not elem.is_func() else 1
        if size == 0:
            raise CompileError("pointer arithmetic on incomplete type", node)
        idx = self.conv(idx, INT if not (idx.type.is_int() and idx.type.size == 4) else idx.type)
        if idx.is_const:
            k = s32(idx.off) * size
            return self.ptr_add_const(ptr, -k if negate else k)
        idx = self.scale_index(idx, size, node)
        if negate:
            idx = self.negate(idx)
        if ptr.tmp is None:
            # lazy: address = idx register + symbol/frame address + off
            return ptr.copy(tmp=idx.tmp)
        pr = self.reg_of(ptr.tmp, keep=(idx.tmp,))
        ir = self.reg_of(idx.tmp, keep=(ptr.tmp,))
        self.emit("add", pr, ir, pr)
        self.release(idx)
        return ptr

    # ------------------------------------------------------------ arithmetic emission

    def negate(self, v):
        if v.is_const:
            return const_val(v.type, -v.off)
        v = self.to_reg(v)
        r = v.tmp.reg
        self.emit("nor", r, r, r)
        self.emit("lw", ZERO, AT, self.k(1))
        self.emit("add", r, AT, r)
        v.bits = None
        return v

    def mul_const(self, v, c):
        """v (a register Val) * constant c (python int)."""
        c = s32(c)
        if c == 0:
            self.release(v)
            return const_val(v.type, 0)
        if c == 1:
            return v
        if c == -1:
            return self.negate(v)
        uc = c & 0xFFFFFFFF
        bits = bin(uc).count("1")
        if bits == 1:
            k = uc.bit_length() - 1
            if k <= 8:
                r = self.reg_of(v.tmp)
                for _ in range(k):
                    self.emit("add", r, r, r)
                v.bits = None if v.bits is None or v.bits + k > 31 else v.bits + k
                return v
        if uc.bit_length() <= 10 and bits <= 3:
            # Horner from the top bit: acc = v; for each lower bit: acc = 2*acc (+ v)
            acc = self.new_tmp(keep=(v.tmp,))
            vr = self.reg_of(v.tmp, keep=(acc,))
            self.emit("add", vr, ZERO, acc.reg)
            for i in range(uc.bit_length() - 2, -1, -1):
                self.emit("add", acc.reg, acc.reg, acc.reg)
                if (uc >> i) & 1:
                    self.emit("add", acc.reg, vr, acc.reg)
            self.release(v)
            return Val(v.type, tmp=acc)
        return self.helper_call_ty("Mul", [v, const_val(v.type, c)], v.type)

    def helper_call_ty(self, name, args, ty):
        r = self.helper_call(name, args)
        r.type = ty
        return r

    # ------------------------------------------------------------ expression dispatch

    def rvalue(self, node):
        """Evaluate an expression to a Val (arrays and functions decayed)."""
        v = self.expr(node, False)
        if v is None or v.type.is_void():
            raise CompileError("void value used in an expression", node)
        return v

    def expr(self, node, discard):
        m = getattr(self, "e_" + type(node).__name__, None)
        if m is None:
            raise CompileError(f"unsupported expression {type(node).__name__}", node)
        return m(node, discard)

    def e_Constant(self, node, discard):
        if node.type == "string":
            g = self.comp.string_obj(node.value, node)
            self.comp.need(g)
            return Val(Ptr(cty.CHAR), sym=g)
        if node.type == "char":
            chars = self.comp.decode_string("\"" + node.value[1:-1].replace('"', '\\"') + "\"", node)
            if len(chars) != 1:
                raise CompileError("multi-character constants are not supported", node)
            return const_val(INT, cty.wrap(chars[0], cty.CHAR))
        if node.type in ("float", "double", "long double"):
            raise CompileError("floating point is not supported", node)
        text = node.value
        unsigned_suffix = "u" in text.lower()
        longlong = text.lower().count("l") == 2
        digits = text.rstrip("uUlL")
        if digits[:2].lower() == "0x":
            val, decimal = int(digits, 16), False
        elif len(digits) > 1 and digits[0] == "0":
            val, decimal = int(digits, 8), False
        else:
            val, decimal = int(digits), True
        if longlong or val >= 1 << 32:
            raise CompileError("64-bit integer constants are not supported", node)
        if unsigned_suffix:
            ty = UINT
        elif val < 1 << 31:
            ty = INT
        else:
            ty = UINT  # C would use long long for a decimal constant here; there is no 64-bit type
        return const_val(ty, val)

    def e_ID(self, node, discard):
        sym = self.lookup(node.name, node)
        if isinstance(sym, EnumConst):
            return const_val(INT, sym.value)
        if isinstance(sym, Local):
            return self.load(Val(Ptr(sym.type), sp=True, off=sym.slot))
        if isinstance(sym, GObj):
            self.comp.need(sym)
            if sym.kind == "func":
                return Val(Ptr(sym.type), sym=sym)
            return self.load(Val(Ptr(sym.type), sym=sym))
        raise CompileError(f"'{node.name}' is not a value", node)

    def e_CompoundLiteral(self, node, discard):
        return self.load(self.addr_of(node))

    def e_ArrayRef(self, node, discard):
        return self.load(self.addr_of(node))

    def e_StructRef(self, node, discard):
        return self.load(self.addr_of(node))

    def e_ExprList(self, node, discard):
        for e in node.exprs[:-1]:
            self.expr(e, True)
        return self.expr(node.exprs[-1], discard)

    def e_Cast(self, node, discard):
        to = self.comp.build_type(node.to_type, self.scope, self)
        v = self.rvalue(node.expr) if not to.is_void() else self.expr(node.expr, True)
        if to.is_void():
            self.release(v)
            return Val(cty.VOID)
        if not to.is_scalar():
            raise CompileError(f"cannot cast to {to}", node)
        if not (v.type.is_scalar() or v.type.is_array()):
            raise CompileError("cannot cast a non-scalar", node)
        return self.conv(v, to)

    def e_TernaryOp(self, node, discard):
        c = self.try_const_cond(node.cond)
        if c is not None:
            chosen = self.expr(node.iftrue if c else node.iffalse, discard)
            if discard or chosen is None:
                return chosen
            rty = self.ternary_type(cty.decay(self.static_type(node.iftrue)), cty.decay(self.static_type(node.iffalse)))
            return self.conv(chosen, rty)
        self.flush()
        lelse, lend = self.new_label(), self.new_label()
        self.cond_jump(node.cond, lelse, False)
        if discard:
            v = self.expr(node.iftrue, True)
            self.release(v)
            self.jmp(lend)
            self.place(lelse)
            v = self.expr(node.iffalse, True)
            self.release(v)
            self.place(lend)
            return None
        rty = self.ternary_type(cty.decay(self.static_type(node.iftrue)), cty.decay(self.static_type(node.iffalse)))
        self.to_r1(self.conv(self.rvalue(node.iftrue), rty))
        self.jmp(lend)
        self.place(lelse)
        self.to_r1(self.conv(self.rvalue(node.iffalse), rty))
        self.place(lend)
        return Val(rty, tmp=self.new_tmp(reg=1))

    def ternary_type(self, a, b):
        if a.is_int() and b.is_int():
            return cty.common(a, b)
        if a.is_ptr():
            return a
        if b.is_ptr():
            return b
        return a

    def to_r1(self, v):
        """Move a value into r1 (all other temporaries are flushed)."""
        if v.type.is_struct():
            raise CompileError("struct-valued conditional is not supported")
        if v.is_const:
            self.load_const_reg(1, v.off)
            return
        v = self.to_reg(v)
        t = v.tmp
        if t.reg is None:
            self.emit("lw", SP, 1, Lazy("spill", t.slot))
        else:
            self.mov(1, t.reg)
        self.release(v)

    def e_UnaryOp(self, node, discard):
        op = node.op
        if op == "sizeof":
            if isinstance(node.expr, c_ast.Typename):
                ty = self.comp.build_type(node.expr, self.scope, self)
            else:
                ty = self.static_type(node.expr)
            self.require_complete(ty, node)
            return const_val(UINT, ty.size)
        if op == "&":
            a = self.addr_of_for_amp(node.expr)
            return a
        if op == "*":
            v = self.rvalue(node.expr)
            if not v.type.is_ptr():
                raise CompileError("dereferencing a non-pointer", node)
            if v.type.target.is_func():
                return v
            return self.load(v)
        if op in ("++", "--", "p++", "p--"):
            return self.incdec(node, discard)
        if op == "!":
            c = self.try_const_cond(node.expr)
            if c is not None:
                return const_val(INT, 0 if c else 1)
            return self.bool_value(node)
        v = self.rvalue(node.expr)
        if not v.type.is_scalar():
            raise CompileError(f"invalid operand to unary {op}", node)
        if op == "+":
            return self.conv(v, cty.promote(v.type))
        v = self.conv(v, cty.promote(v.type))
        if op == "-":
            return self.negate(v)
        if op == "~":
            if v.is_const:
                return const_val(v.type, ~v.off)
            v = self.to_reg(v)
            r = v.tmp.reg
            self.emit("nor", r, r, r)
            v.bits = None
            return v
        raise CompileError(f"unsupported unary operator {op}", node)

    def addr_of_for_amp(self, node):
        if isinstance(node, c_ast.ID):
            sym = self.lookup(node.name, node)
            if isinstance(sym, GObj) and sym.kind == "func":
                self.comp.need(sym)
                return Val(Ptr(sym.type), sym=sym)
        if isinstance(node, c_ast.UnaryOp) and node.op == "*":
            return self.rvalue(node.expr)
        return self.addr_of(node)

    @staticmethod
    def require_complete(ty, node):
        if ty.is_void() or (ty.is_struct() and not ty.complete) or (ty.is_array() and ty.count is None):
            raise CompileError(f"invalid use of incomplete type {ty}", node)

    def static_type(self, node):
        """C type of an expression without generating code (arrays not decayed)."""
        if isinstance(node, c_ast.ID):
            sym = self.lookup(node.name, node)
            if isinstance(sym, (Local, GObj)):
                return sym.type
            if isinstance(sym, EnumConst):
                return INT
            raise CompileError(f"'{node.name}' is not a value", node)
        if isinstance(node, c_ast.Constant):
            if node.type == "string":
                return Array(cty.CHAR, len(self.comp.decode_string(node.value, node)) + 1)
            if node.type == "char":
                return INT
            return self.e_Constant(node, False).type
        if isinstance(node, c_ast.UnaryOp):
            op = node.op
            if op == "sizeof":
                return UINT
            t = self.static_type(node.expr)
            if op == "*":
                t = cty.decay(t)
                if not t.is_ptr():
                    raise CompileError("dereferencing a non-pointer", node)
                return t.target
            if op == "&":
                return Ptr(t)
            if op == "!":
                return INT
            if op in ("++", "--", "p++", "p--"):
                return t
            return cty.promote(cty.decay(t))
        if isinstance(node, c_ast.BinaryOp):
            op = node.op
            if op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
                return INT
            ta = cty.decay(self.static_type(node.left))
            tb = cty.decay(self.static_type(node.right))
            if op in ("<<", ">>"):
                return cty.promote(ta)
            if op == "+":
                if ta.is_ptr():
                    return ta
                if tb.is_ptr():
                    return tb
            if op == "-":
                if ta.is_ptr() and tb.is_ptr():
                    return INT
                if ta.is_ptr():
                    return ta
            if not (ta.is_int() and tb.is_int()):
                raise CompileError(f"invalid operands to '{op}'", node)
            return cty.common(ta, tb)
        if isinstance(node, c_ast.Assignment):
            return self.static_type(node.lvalue)
        if isinstance(node, c_ast.TernaryOp):
            return self.ternary_type(cty.decay(self.static_type(node.iftrue)), cty.decay(self.static_type(node.iffalse)))
        if isinstance(node, c_ast.Cast):
            return self.comp.build_type(node.to_type, self.scope, self)
        if isinstance(node, c_ast.ExprList):
            return self.static_type(node.exprs[-1])
        if isinstance(node, c_ast.ArrayRef):
            t = cty.decay(self.static_type(node.name))
            if not t.is_ptr():
                t = cty.decay(self.static_type(node.subscript))
            if not t.is_ptr():
                raise CompileError("subscripted value is not an array or pointer", node)
            return t.target
        if isinstance(node, c_ast.StructRef):
            t = self.static_type(node.name)
            if node.type == "->":
                t = cty.decay(t)
                if not t.is_ptr():
                    raise CompileError("-> applied to a non-pointer", node)
                t = t.target
            if not t.is_struct():
                raise CompileError("member access on a non-struct", node)
            found = t.find(node.field.name)
            if not found:
                raise CompileError(f"{t} has no member '{node.field.name}'", node)
            return found[0].type
        if isinstance(node, c_ast.FuncCall):
            t = cty.decay(self.static_type(node.name))
            if t.is_ptr() and t.target.is_func():
                return t.target.ret
            raise CompileError("called object is not a function", node)
        raise CompileError(f"cannot type expression {type(node).__name__}", node)

    # ------------------------------------------------------------ inc/dec

    def incdec(self, node, discard):
        op = node.op
        post = op.startswith("p")
        up = op.endswith("++")
        addr = self.addr_of(node.expr)
        ty = addr.type.target
        if not ty.is_scalar():
            raise CompileError("invalid operand to ++/--", node)
        step = ty.target.size if ty.is_ptr() and not ty.target.is_void() and not ty.target.is_func() else 1
        delta = step if up else -step
        akeep = (addr.tmp,) if addr.tmp is not None else ()
        base, off = self.addr_form(addr)
        akeep = (addr.tmp,) if addr.tmp is not None else ()
        cur = self.new_tmp(keep=akeep)
        base, off = self.addr_form(addr, keep=(cur,))
        self.emit("lw", base, cur.reg, off)
        keep_old = post and not discard
        if keep_old:
            new = self.new_tmp(keep=akeep + (cur,))
            self.emit("add", cur.reg, ZERO, new.reg)
        else:
            new = cur
        self.add_const_inplace(new, delta, ty, keep=akeep + ((cur,) if keep_old else ()))
        self.reg_of(new, keep=akeep)
        base, off = self.addr_form(addr, keep=(new,))
        self.emit("sw", base, new.reg, off)
        self.release(addr)
        if keep_old:
            self.release_tmp(new)
        if discard:
            self.release_tmp(cur)
            return None
        return Val(ty, tmp=cur, bits=int_range_bits(ty))

    def add_const_inplace(self, t, delta, ty, keep=()):
        r = self.reg_of(t, keep)
        self.emit("lw", ZERO, AT, self.k(delta))
        self.emit("add", r, AT, r)
        if ty.is_int() and ty.size < 4:
            self.normalize(t, ty, keep)

    # ------------------------------------------------------------ assignment

    def e_Assignment(self, node, discard):
        op = node.op
        if op == "=":
            return self.assign(node, discard)
        binop = op[:-1]
        return self.compound_assign(node, binop, discard)

    def assign(self, node, discard):
        lty = self.lvalue_type(node.lvalue)
        if lty.is_struct():
            return self.assign_struct(node)
        if lty.is_array():
            raise CompileError("assignment to an array", node)
        rhs = self.rvalue(node.rvalue)
        rhs = self.conv(rhs, lty)
        addr = self.addr_of(node.lvalue)
        if discard:
            if rhs.tmp is None and (rhs.sym is not None or rhs.sp):
                rhs = self.to_reg(rhs, keep=(addr.tmp,) if addr.tmp else ())
            stored = self.store_to(addr, rhs)
            self.release(stored)
            return None
        rhs = self.to_reg(rhs, keep=(addr.tmp,) if addr.tmp else ())
        # keep a copy of the value as the expression result
        self.reg_of(rhs.tmp, keep=(addr.tmp,) if addr.tmp else ())
        base, off = self.addr_form(addr, keep=(rhs.tmp,))
        self.emit("sw", base, rhs.tmp.reg, off)
        self.release(addr)
        return rhs

    def lvalue_type(self, node):
        return self.static_type(node)

    def assign_struct(self, node):
        lty = self.lvalue_type(node.lvalue)
        src = self.rvalue(node.rvalue)
        if not src.type.is_struct():
            raise CompileError("incompatible struct assignment", node)
        dst = self.addr_of(node.lvalue)
        self.copy_words(dst, src, lty.size)
        return Val(cty.VOID)

    def copy_words(self, dst, src, n):
        """Copy n words from address src to address dst (consumes both)."""
        n = max(1, n)
        src = self.to_reg(src, keep=(dst.tmp,) if dst.tmp is not None else ())
        dst = self.to_reg(dst, keep=(src.tmp,))
        if n <= 8:
            sr, dr = self.regs2(src, dst)
            for i in range(n):
                self.emit("lw", sr, AT, i)
                self.emit("sw", dr, AT, i)
        else:
            self.copy_loop(src.tmp, dst.tmp, n)
        self.release(src)
        self.release(dst)

    def compound_assign(self, node, binop, discard):
        lty = self.lvalue_type(node.lvalue)
        if not lty.is_scalar():
            raise CompileError("invalid compound assignment", node)
        rhs = self.rvalue(node.rvalue)
        addr = self.addr_of(node.lvalue)
        keep = (addr.tmp,) if addr.tmp else ()
        base, off = self.addr_form(addr, keep=(rhs.tmp,) if rhs.tmp else ())
        cur = self.new_tmp(keep=keep + ((rhs.tmp,) if rhs.tmp else ()))
        base, off = self.addr_form(addr, keep=(cur,) + ((rhs.tmp,) if rhs.tmp else ()))
        self.emit("lw", base, cur.reg, off)
        curv = Val(lty, tmp=cur, bits=int_range_bits(lty))
        if lty.is_ptr() and binop in ("+", "-"):
            res = self.ptr_add(curv, rhs, node, negate=(binop == "-"))
            res = self.to_reg(res)
        else:
            res = self.arith(binop, curv, rhs, node)
            res = self.conv(res, lty)
            res = self.to_reg(res)
        r = self.reg_of(res.tmp, keep=keep)
        base, off = self.addr_form(addr, keep=(res.tmp,))
        self.emit("sw", base, r, off)
        self.release(addr)
        if discard:
            self.release(res)
            return None
        return res

    # ------------------------------------------------------------ binary operators

    def e_BinaryOp(self, node, discard):
        op = node.op
        if op in ("&&", "||"):
            c = self.try_const_cond(node)
            if c is not None:
                return const_val(INT, 1 if c else 0)
            return self.bool_value(node)
        a = self.rvalue(node.left)
        b = self.rvalue(node.right)
        if op in ("==", "!=", "<", "<=", ">", ">="):
            return self.compare_value(op, a, b, node)
        return self.arith(op, a, b, node)

    def arith(self, op, a, b, node):
        ta, tb = a.type, b.type
        if (ta.is_ptr() or tb.is_ptr()) and op in ("+", "-"):
            if op == "+":
                if ta.is_ptr() and tb.is_int():
                    return self.ptr_add(a, b, node)
                if tb.is_ptr() and ta.is_int():
                    return self.ptr_add(b, a, node)
            else:
                if ta.is_ptr() and tb.is_int():
                    return self.ptr_add(a, b, node, negate=True)
                if ta.is_ptr() and tb.is_ptr():
                    return self.ptr_diff(a, b, node)
            raise CompileError("invalid pointer arithmetic", node)
        if not (ta.is_int() and tb.is_int()):
            if ta.is_ptr() or tb.is_ptr():
                # allow pointer used as an integer in bitwise ops by converting
                a = self.conv(a, UINT) if ta.is_ptr() else a
                b = self.conv(b, UINT) if tb.is_ptr() else b
                ta, tb = a.type, b.type
            if not (ta.is_int() and tb.is_int()):
                raise CompileError(f"invalid operands to '{op}'", node)
        if op in ("<<", ">>"):
            ty = cty.promote(ta)
            a = self.conv(a, ty)
            b = self.conv(b, cty.promote(tb))
            return self.shift(op, a, b, ty, node)
        ty = cty.common(ta, tb)
        a = self.conv(a, ty)
        b = self.conv(b, ty)
        return self.arith_ty(op, a, b, ty, node)

    def ptr_diff(self, a, b, node):
        size = a.type.target.size or 1
        d = self.arith_ty("-", self.conv(a, UINT), self.conv(b, UINT), UINT, node)
        d = self.conv(d, INT)
        if size == 1:
            return d
        if size & (size - 1) == 0:
            # the difference is an exact multiple of the element size
            return self.shift(">>", d, const_val(INT, size.bit_length() - 1), INT, node)
        return self.divide("/", d, const_val(INT, size), INT, node)

    def fold_arith(self, op, x, y, ty, node):
        signed = not (ty is UINT)
        sx, sy = s32(x), s32(y)
        ux, uy = x & 0xFFFFFFFF, y & 0xFFFFFFFF
        if op == "+":
            r = x + y
        elif op == "-":
            r = x - y
        elif op == "*":
            r = x * y
        elif op == "&":
            r = x & y
        elif op == "|":
            r = x | y
        elif op == "^":
            r = x ^ y
        elif op in ("/", "%"):
            if y == 0:
                raise CompileError("division by zero in constant expression", node)
            if signed:
                q = abs(sx) // abs(sy)
                if (sx < 0) != (sy < 0):
                    q = -q
                r = q if op == "/" else sx - q * sy
            else:
                r = ux // uy if op == "/" else ux % uy
        else:
            raise CompileError(f"cannot fold {op}", node)
        return const_val(ty, r)

    def arith_ty(self, op, a, b, ty, node):
        if a.is_const and b.is_const and op not in ("/", "%") or (a.is_const and b.is_const and s32(b.off) != 0):
            return self.fold_arith(op, a.off, b.off, ty, node)
        if op in ("*",):
            return self.multiply(a, b, ty, node)
        if op in ("/", "%"):
            return self.divide(op, a, b, ty, node)
        if op in ("+", "&", "|", "^") and a.is_const:
            a, b = b, a
        if op == "-" and b.is_const:
            return self.arith_ty("+", a, const_val(ty, -b.off), ty, node)
        if a.is_const and op == "-":
            b = self.to_reg(b)
            r = b.tmp.reg
            self.emit("nor", r, r, r)
            self.emit("lw", ZERO, AT, self.k(a.off + 1))
            self.emit("add", r, AT, r)
            b.type, b.bits = ty, None
            return b
        a = self.to_reg(a, keep=(b.tmp,) if b.tmp else ())
        if op == "+":
            if b.is_const and s32(b.off) == 0:
                return a
            rb = self.src_reg_keep(b, a)
            ra = self.reg_of(a.tmp, keep=(b.tmp,) if b.tmp else ())
            self.emit("add", ra, rb, ra)
            self.release(b)
            a.type, a.bits = ty, self.add_bits(a, b)
            return a
        if op == "-":
            b = self.to_reg(b, keep=(a.tmp,))
            ra, rb = self.regs2(a, b)
            self.emit("nor", rb, rb, rb)
            self.emit("add", ra, rb, ra)
            self.emit("lw", ZERO, AT, self.k(1))
            self.emit("add", ra, AT, ra)
            self.release(b)
            a.type, a.bits = ty, None
            return a
        if op == "&":
            bits = None
            if b.is_const and b.off >= 0 and ty is not UINT or (b.is_const and ty is UINT and b.off < (1 << 31)):
                bits = max(1, (b.off).bit_length())
            if a.bits is not None:
                bits = a.bits if bits is None else min(bits, a.bits)
            if b.is_const:
                if s32(b.off) == -1:
                    return a
                ra = self.reg_of(a.tmp)
                self.emit("nor", ra, ra, ra)
                self.emit("lw", ZERO, AT, self.k(~b.off))
                self.emit("nor", ra, AT, ra)
            else:
                b = self.to_reg(b, keep=(a.tmp,))
                ra, rb = self.regs2(a, b)
                self.emit("nor", ra, ra, ra)
                self.emit("nor", rb, rb, rb)
                self.emit("nor", ra, rb, ra)
                if b.bits is not None:
                    bits = b.bits if bits is None else min(bits, b.bits)
                self.release(b)
            a.type, a.bits = ty, bits
            return a
        if op == "|":
            if b.is_const and s32(b.off) == 0:
                return a
            rb = self.src_reg_keep(b, a)
            ra = self.reg_of(a.tmp, keep=(b.tmp,) if b.tmp else ())
            self.emit("nor", ra, rb, ra)
            self.emit("nor", ra, ra, ra)
            bits = None
            if a.bits is not None and b.bits is not None:
                bits = max(a.bits, b.bits)
            self.release(b)
            a.type, a.bits = ty, bits
            return a
        if op == "^":
            if b.is_const and s32(b.off) == 0:
                return a
            b = self.to_reg(b, keep=(a.tmp,))
            ra, rb = self.regs2(a, b)
            self.emit("nor", ra, rb, AT)
            self.emit("nor", ra, ra, ra)
            self.emit("nor", rb, rb, rb)
            self.emit("nor", ra, rb, ra)
            self.emit("nor", ra, AT, ra)
            bits = None
            if a.bits is not None and b.bits is not None:
                bits = max(a.bits, b.bits)
            self.release(b)
            a.type, a.bits = ty, bits
            return a
        raise CompileError(f"unsupported operator {op}", node)

    def add_bits(self, a, b):
        if a.bits is not None and b.bits is not None and max(a.bits, b.bits) < 31:
            return max(a.bits, b.bits) + 1
        return None

    def src_reg_keep(self, b, a):
        """Source register for b while a's register must stay put."""
        if b.is_const:
            return self.src_reg(b)
        b2 = self.to_reg(b, keep=(a.tmp,)) if (b.sym is not None or b.sp or b.off != 0 or b.tmp is None) else b
        if b2 is not b:
            b.tmp, b.sym, b.sp, b.off = b2.tmp, None, False, 0
        return self.reg_of(b.tmp, keep=(a.tmp,))

    def regs2(self, a, b):
        ra = self.reg_of(a.tmp, keep=(b.tmp,))
        rb = self.reg_of(b.tmp, keep=(a.tmp,))
        return ra, rb

    def multiply(self, a, b, ty, node):
        if a.is_const:
            a, b = b, a
        if b.is_const:
            a = self.to_reg(a)
            r = self.mul_const(a, b.off)
            r.type = ty
            return r
        # both variable: put the operand with fewer significant bits in r2 (the loop count)
        if a.bits is not None and (b.bits is None or a.bits < b.bits):
            a, b = b, a
        return self.helper_call_ty("Mul", [a, b], ty)

    def divide(self, op, a, b, ty, node):
        unsigned = ty is UINT
        if b.is_const and b.off > 0 and (b.off & (b.off - 1)) == 0:
            k = b.off.bit_length() - 1
            if unsigned:
                if op == "/":
                    return a if k == 0 else self.shift(">>", a, const_val(INT, k), ty, node)
                if k == 0:
                    self.release(a)
                    return const_val(ty, 0)
                return self.arith_ty("&", a, const_val(ty, b.off - 1), ty, node)
            if k == 0:
                if op == "/":
                    return a
                self.release(a)
                return const_val(ty, 0)
            if not a.is_const:
                return self.signed_pow2(op, a, k, ty, node)
        name = ("__udiv" if op == "/" else "__umod") if unsigned else ("__sdiv" if op == "/" else "__smod")
        g = self.comp.runtime_func(name)
        return self.call(g, [a, b], ty, g.type.params, False, node)

    def signed_pow2(self, op, a, k, ty, node):
        """Signed x / 2^k or x % 2^k (k >= 1), rounding toward zero."""
        a = self.to_reg(a)
        r = self.reg_of(a.tmp)
        neg, end = self.new_label(), self.new_label()
        if op == "/":
            # bias negative values by 2^k - 1, then shift arithmetically
            self.emit("lw", ZERO, AT, self.k(0x7FFFFFFF))
            self.emit("nor", r, AT, AT)  # r6 == 0 iff x < 0
            self.emit("beq", AT, ZERO, neg)
            self.jmp(end)
            self.place(neg)
            self.emit("lw", ZERO, AT, self.k((1 << k) - 1))
            self.emit("add", r, AT, r)
            self.place(end)
            return self.shift(">>", a, const_val(INT, k), ty, node)
        # x % 2^k: low bits, minus 2^k if x < 0 and the low bits are not all zero
        t = self.new_tmp(keep=(a.tmp,))
        self.emit("nor", r, r, t.reg)
        self.emit("lw", ZERO, AT, self.k(-(1 << k)))
        self.emit("nor", t.reg, AT, t.reg)  # t = x & (2^k - 1)
        self.emit("lw", ZERO, AT, self.k(0x7FFFFFFF))
        self.emit("nor", r, AT, AT)  # r6 == 0 iff x < 0
        self.emit("beq", AT, ZERO, neg)
        self.jmp(end)
        self.place(neg)
        self.emit("beq", t.reg, ZERO, end)
        self.emit("lw", ZERO, AT, self.k(-(1 << k)))
        self.emit("add", t.reg, AT, t.reg)
        self.place(end)
        self.release(a)
        return Val(ty, tmp=t)

    def shift(self, op, a, b, ty, node):
        if a.is_const and b.is_const:
            n = b.off & 31
            if op == "<<":
                return const_val(ty, a.off << n)
            if ty is UINT:
                return const_val(ty, (a.off & 0xFFFFFFFF) >> n)
            return const_val(ty, s32(a.off) >> n)
        if b.is_const:
            n = b.off & 31
            if n == 0:
                return a
            a = self.to_reg(a)
            if op == "<<":
                if n <= 6:
                    r = self.reg_of(a.tmp)
                    for _ in range(n):
                        self.emit("add", r, r, r)
                    a.type = ty
                    a.bits = None if a.bits is None or a.bits + n > 31 else a.bits + n
                    return a
                return self.helper_call_ty("Shl", [a, b], ty)
            if n == 31:
                return self.sign_bit(a, ty)
            if a.bits is not None and a.bits <= 16:
                return self.shift_right_small(a, n, ty)
            name = "Shru" if (ty is UINT or (a.bits is not None and a.bits < 32)) else "Shrs"
            res = self.helper_call_ty(name, [a, const_val(UINT, 1 << n)], ty)
            res.bits = None if a.bits is None else max(1, a.bits - n)
            return res
        a = self.to_reg(a, keep=(b.tmp,) if b.tmp else ())
        b = self.to_reg(b, keep=(a.tmp,))
        if op == "<<":
            return self.helper_call_ty("Shl", [a, b], ty)
        mask = self.helper_call_ty("Shl", [const_val(INT, 1), b], UINT)
        name = "Shru" if ty is UINT else "Shrs"
        return self.helper_call_ty(name, [a, mask], ty)

    def shift_right_small(self, a, n, ty):
        """a >> n for a value known to be in [0, 2^16): test each bit that survives the shift."""
        width = a.bits
        if n >= width:
            self.release(a)
            return const_val(ty, 0)
        a = self.to_reg(a)
        q = self.new_tmp(keep=(a.tmp,))
        t = self.new_tmp(keep=(a.tmp, q))
        rx = self.reg_of(a.tmp, keep=(q, t))
        self.emit("nor", rx, rx, rx)  # rx = ~a
        self.emit("add", ZERO, ZERO, q.reg)
        for i in range(n, width):
            skip = self.new_label()
            self.emit("lw", ZERO, AT, self.k(~(1 << i)))
            self.emit("nor", rx, AT, t.reg)  # t = a & (1 << i)
            self.emit("beq", t.reg, ZERO, skip)
            self.emit("lw", ZERO, AT, self.k(1 << (i - n)))
            self.emit("add", q.reg, AT, q.reg)
            self.place(skip)
        self.release(a)
        self.release_tmp(t)
        return Val(ty, tmp=q, bits=max(1, width - n))

    def sign_bit(self, a, ty):
        """a >> 31: 1 (logical) or -1 (arithmetic) if a < 0, else 0."""
        a = self.to_reg(a)
        r = self.reg_of(a.tmp)
        neg, end = self.new_label(), self.new_label()
        self.emit("lw", ZERO, AT, self.k(0x7FFFFFFF))
        self.emit("nor", r, AT, r)  # r == 0 iff a < 0
        self.emit("beq", r, ZERO, neg)
        self.emit("add", ZERO, ZERO, r)
        self.jmp(end)
        self.place(neg)
        self.load_const_reg(r, 1 if ty is UINT else -1)
        self.place(end)
        a.type = ty
        a.bits = 1 if ty is UINT else None
        return a

    # ------------------------------------------------------------ comparisons and conditions

    def compare_value(self, op, a, b, node):
        c = self.fold_compare(op, a, b)
        if c is not None:
            self.release(a)
            self.release(b)
            return const_val(INT, 1 if c else 0)
        self.flush(keep=tuple(x.tmp for x in (a, b) if x.tmp is not None))
        lfalse, lend = self.new_label(), self.new_label()
        self.branch_cmp(op, a, b, lfalse, False, node)
        self.emit("lw", ZERO, 1, self.k(1))
        self.jmp(lend)
        self.place(lfalse)
        self.emit("add", ZERO, ZERO, 1)
        self.place(lend)
        t = self.new_tmp(reg=1)
        return Val(INT, tmp=t, bits=1)

    def bool_value(self, node):
        self.flush()
        lfalse, lend = self.new_label(), self.new_label()
        self.cond_jump(node, lfalse, False)
        self.emit("lw", ZERO, 1, self.k(1))
        self.jmp(lend)
        self.place(lfalse)
        self.emit("add", ZERO, ZERO, 1)
        self.place(lend)
        t = self.new_tmp(reg=1)
        return Val(INT, tmp=t, bits=1)

    def try_const_cond(self, node):
        """True/False if the condition is a compile-time constant, else None."""
        if isinstance(node, c_ast.BinaryOp) and node.op in ("&&", "||"):
            left = self.try_const_cond(node.left)
            if left is None:
                return None
            if node.op == "&&":
                return False if left is False else self.try_const_cond(node.right)
            return True if left is True else self.try_const_cond(node.right)
        if isinstance(node, c_ast.UnaryOp) and node.op == "!":
            c = self.try_const_cond(node.expr)
            return None if c is None else not c
        saved_code = self.code
        saved = (list(self.live), dict(self.owner), list(self.free_slots), self.nspill, self.leaf)
        self.code = []
        prev_noemit = self.noemit
        self.noemit = True
        try:
            v = self.rvalue(node)
        except (NotConstant, CompileError):
            return None
        finally:
            self.noemit = prev_noemit
            self.code = saved_code
            self.live, self.owner, self.free_slots, self.nspill, self.leaf = saved
        if v.is_const:
            return s32(v.off) != 0
        return None

    def fold_compare(self, op, a, b):
        if not (a.is_const and b.is_const):
            return None
        ty = self.cmp_type(a, b)
        x, y = cty.wrap(a.off, ty), cty.wrap(b.off, ty)
        return {"==": x == y, "!=": x != y, "<": x < y, "<=": x <= y, ">": x > y, ">=": x >= y}[op]

    def cmp_type(self, a, b):
        ta, tb = a.type, b.type
        if ta.is_ptr() or tb.is_ptr():
            return UINT
        return cty.common(ta, tb)

    def cond_jump(self, node, label, when):
        """Jump to `label` if truth(node) == when; otherwise fall through."""
        if isinstance(node, c_ast.UnaryOp) and node.op == "!":
            return self.cond_jump(node.expr, label, not when)
        if isinstance(node, c_ast.BinaryOp) and node.op in ("&&", "||"):
            is_and = node.op == "&&"
            if is_and != when:  # (&&, jump-if-false) or (||, jump-if-true): either side decides
                self.cond_jump(node.left, label, when)
                self.cond_jump(node.right, label, when)
            else:
                skip = self.new_label()
                self.cond_jump(node.left, skip, not when)
                self.cond_jump(node.right, label, when)
                self.place(skip)
            return
        c = self.try_const_cond(node)
        if c is not None:
            if c == when:
                self.jmp(label)
            return
        if isinstance(node, c_ast.BinaryOp) and node.op in ("==", "!=", "<", "<=", ">", ">="):
            a = self.rvalue(node.left)
            b = self.rvalue(node.right)
            self.branch_cmp(node.op, a, b, label, when, node)
            return
        v = self.rvalue(node)
        if not v.type.is_scalar():
            raise CompileError("scalar condition required", node)
        v = self.to_reg(v)
        r = self.reg_of(v.tmp)
        self.branch_zero(r, label, when)
        self.release(v)

    def branch_zero(self, r, label, when):
        """Jump to label if (r != 0) == when."""
        if not when:
            self.emit("beq", r, ZERO, label)
        else:
            skip = self.new_label()
            self.emit("beq", r, ZERO, skip)
            self.jmp(label)
            self.place(skip)

    def branch_eq(self, ra, rb, label, jump_if_equal):
        if jump_if_equal:
            self.emit("beq", ra, rb, label)
        else:
            skip = self.new_label()
            self.emit("beq", ra, rb, skip)
            self.jmp(label)
            self.place(skip)

    def branch_cmp(self, op, a, b, label, when, node):
        """Compare a and b; jump to label if (a op b) == when."""
        ta, tb = a.type, b.type
        if not (ta.is_scalar() or ta.is_array()) or not (tb.is_scalar() or tb.is_array()):
            raise CompileError("invalid operands to comparison", node)
        ty = self.cmp_type(a, b)
        a = self.conv(a, ty)
        b = self.conv(b, ty)
        c = self.fold_compare(op, a, b)
        if c is not None:
            if c == when:
                self.jmp(label)
            return
        if op in ("==", "!="):
            jump_if_equal = (op == "==") == when
            if a.is_const:
                a, b = b, a
            a = self.to_reg(a, keep=(b.tmp,) if b.tmp else ())
            if b.is_const:
                rb = self.src_reg(b)
            else:
                b = self.to_reg(b, keep=(a.tmp,))
                ra, rb = self.regs2(a, b)
            ra = self.reg_of(a.tmp, keep=(b.tmp,) if b.tmp else ())
            self.branch_eq(ra, rb, label, jump_if_equal)
            self.release(a)
            self.release(b)
            return
        unsigned = ty is UINT
        # normalize to a < b or a <= b by swapping
        if op in (">", ">="):
            a, b = b, a
            op = "<" if op == ">" else "<="
        # now compute (a op b)
        if unsigned and b.is_const and s32(b.off) == 0 and op == "<":
            # a < 0u: never true
            self.release(a)
            if not when:
                self.jmp(label)
            return
        if unsigned and a.is_const and s32(a.off) == 0 and op == "<=":
            self.release(b)
            if when:
                self.jmp(label)
            return
        if unsigned and b.is_const and s32(b.off) == 0 and op == "<=":
            # a <= 0u  <=>  a == 0
            a = self.to_reg(a)
            self.branch_zero(self.reg_of(a.tmp), label, not when)
            self.release(a)
            return
        if unsigned and a.is_const and s32(a.off) == 0 and op == "<":
            # 0u < b <=> b != 0
            b = self.to_reg(b)
            self.branch_zero(self.reg_of(b.tmp), label, when)
            self.release(b)
            return
        if not unsigned and b.is_const and s32(b.off) == 0 and op == "<":
            a = self.to_reg(a)
            self.branch_sign(self.reg_of(a.tmp), label, when)
            self.release(a)
            return
        if not unsigned and a.is_const and s32(a.off) == -1 and op == "<=":
            # -1 <= b  <=>  b >= 0
            b = self.to_reg(b)
            self.branch_sign(self.reg_of(b.tmp), label, not when)
            self.release(b)
            return
        if a.bits is not None and a.bits <= 31 and b.bits is not None and b.bits <= 31:
            if op == "<":
                # a < b  <=>  not (b <= a)
                a, b = b, a
                when = not when
            self.emit_le_sign(a, b, label, when)
            return
        name = "Ltu" if unsigned else "Lts"
        if op == "<=":
            # a <= b  <=>  not (b < a)
            a, b = b, a
            when = not when
        r = self.helper_call(name, [a, b])
        self.branch_zero(r.tmp.reg, label, when)
        self.release(r)

    def emit_le_sign(self, a, b, label, when):
        """Jump if (a <= b) == when, for operands known to be in [0, 2^31)."""
        if b.is_const:
            a = self.to_reg(a)
            ra = self.reg_of(a.tmp)
            self.emit("lw", ZERO, AT, self.k(~b.off))
            self.emit("add", ra, AT, ra)
            res = a
        elif a.is_const:
            b = self.to_reg(b)
            rb = self.reg_of(b.tmp)
            self.emit("nor", rb, rb, rb)
            self.emit("lw", ZERO, AT, self.k(a.off))
            self.emit("add", rb, AT, rb)
            res = b
        else:
            a = self.to_reg(a, keep=(b.tmp,))
            b = self.to_reg(b, keep=(a.tmp,))
            ra, rb = self.regs2(a, b)
            self.emit("nor", rb, rb, rb)
            self.emit("add", ra, rb, ra)
            self.release(b)
            res = a
        r = self.reg_of(res.tmp)
        self.emit("lw", ZERO, AT, self.k(0x7FFFFFFF))
        self.emit("nor", r, AT, r)  # r == 0 iff negative iff a <= b
        self.branch_zero(r, label, not when)
        self.release(res)

    def branch_sign(self, r, label, when):
        """Jump if (r < 0) == when."""
        self.emit("lw", ZERO, AT, self.k(0x7FFFFFFF))
        self.emit("nor", r, AT, r)  # r == 0 iff negative
        self.branch_zero(r, label, not when)

    # ------------------------------------------------------------ calls

    def e_FuncCall(self, node, discard):
        fn = node.name
        args = [self.rvalue(a) for a in (node.args.exprs if node.args else [])]
        target = None
        ftype = None
        if isinstance(fn, c_ast.ID):
            sym = self.lookup(fn.name, fn)
            if isinstance(sym, GObj) and sym.kind == "func":
                self.comp.need(sym)
                target, ftype = sym, sym.type
        if target is None:
            fv = self.rvalue(fn)
            fty = fv.type
            if fty.is_ptr() and fty.target.is_func():
                ftype = fty.target
            else:
                raise CompileError("called object is not a function", node)
            target = fv
        if ftype.params is None:
            params = None
        else:
            params = ftype.params
            if len(args) < len(params) or (len(args) > len(params) and not ftype.variadic):
                raise CompileError("wrong number of arguments in call", node)
        r = self.call(target, args, ftype.ret, params, ftype.variadic, node)
        if discard:
            self.release(r)
            return None
        return r

    # ------------------------------------------------------------ statements

    def stmt(self, node):
        if node.coord is not None and not isinstance(node, (c_ast.Compound, c_ast.Case, c_ast.Default, c_ast.Label, c_ast.EmptyStatement)):
            self.pending_comment = f"{os.path.basename(node.coord.file)}:{node.coord.line}"
        m = getattr(self, "s_" + type(node).__name__, None)
        if m is not None:
            m(node)
        else:
            # expression statement
            v = self.expr(node, True)
            if v is not None:
                self.release(v)
        if self.live:
            raise self.internal(f"leaked temporaries after {type(node).__name__} at {node.coord}")

    def s_EmptyStatement(self, node):
        pass

    def s_Pragma(self, node):
        pass

    def s_Compound(self, node):
        saved_scope, saved_top = self.scope, self.local_top
        self.scope = Scope(self.scope)
        for item in node.block_items or []:
            self.stmt(item)
        self.scope, self.local_top = saved_scope, saved_top

    def s_If(self, node):
        c = self.try_const_cond(node.cond)
        if c is not None:
            if c:
                self.stmt(node.iftrue)
            elif node.iffalse is not None:
                self.stmt(node.iffalse)
            return
        lelse = self.new_label()
        self.cond_jump(node.cond, lelse, False)
        self.stmt(node.iftrue)
        if node.iffalse is not None:
            lend = self.new_label()
            self.jmp(lend)
            self.place(lelse)
            self.stmt(node.iffalse)
            self.place(lend)
        else:
            self.place(lelse)

    def s_While(self, node):
        top, end = self.new_label(), self.new_label()
        self.place(top)
        self.cond_jump(node.cond, end, False)
        self.break_stack.append(end)
        self.continue_stack.append(top)
        self.stmt(node.stmt)
        self.break_stack.pop()
        self.continue_stack.pop()
        self.jmp(top)
        self.place(end)

    def s_DoWhile(self, node):
        top, cont, end = self.new_label(), self.new_label(), self.new_label()
        self.place(top)
        self.break_stack.append(end)
        self.continue_stack.append(cont)
        self.stmt(node.stmt)
        self.break_stack.pop()
        self.continue_stack.pop()
        self.place(cont)
        self.cond_jump(node.cond, top, True)
        self.place(end)

    def s_For(self, node):
        saved_scope, saved_top = self.scope, self.local_top
        self.scope = Scope(self.scope)
        if node.init is not None:
            if isinstance(node.init, c_ast.DeclList):
                for d in node.init.decls:
                    self.local_decl(d)
            else:
                self.stmt(node.init)
        top, cont, end = self.new_label(), self.new_label(), self.new_label()
        self.place(top)
        if node.cond is not None:
            self.cond_jump(node.cond, end, False)
        self.break_stack.append(end)
        self.continue_stack.append(cont)
        self.stmt(node.stmt)
        self.break_stack.pop()
        self.continue_stack.pop()
        self.place(cont)
        if node.next is not None:
            self.stmt(node.next)
        self.jmp(top)
        self.place(end)
        self.scope, self.local_top = saved_scope, saved_top

    def s_Break(self, node):
        if not self.break_stack:
            raise CompileError("break outside loop or switch", node)
        self.jmp(self.break_stack[-1])

    def s_Continue(self, node):
        if not self.continue_stack:
            raise CompileError("continue outside loop", node)
        self.jmp(self.continue_stack[-1])

    def s_Return(self, node):
        if node.expr is not None:
            if self.ret_type.is_void():
                v = self.expr(node.expr, True)
                self.release(v)
            elif self.ret_type.is_struct():
                v = self.rvalue(node.expr)
                if not v.type.is_struct():
                    raise CompileError("incompatible return value", node)
                dst = self.new_tmp(keep=(v.tmp,) if v.tmp is not None else ())
                self.emit("lw", SP, dst.reg, 1)
                self.copy_words(Val(Ptr(self.ret_type), tmp=dst), v, self.ret_type.size)
            else:
                v = self.rvalue(node.expr)
                v = self.conv(v, self.ret_type)
                self.to_r1_final(v)
        self.emit("ret")

    def to_r1_final(self, v):
        """Move the return value into r1 (no other temporaries are live)."""
        if v.is_const:
            self.load_const_reg(1, v.off)
            return
        v = self.to_reg(v)
        t = v.tmp
        if t.reg is None:
            self.emit("lw", SP, 1, Lazy("spill", t.slot))
        else:
            self.mov(1, t.reg)
        self.release(v)

    def s_Goto(self, node):
        self.jmp(self.user_label(node.name))

    def user_label(self, name):
        if name not in self.user_labels:
            self.user_labels[name] = self.new_label()
        return self.user_labels[name]

    def s_Label(self, node):
        self.place(self.user_label(node.name))
        self.stmt(node.stmt)

    def s_Switch(self, node):
        end = self.new_label()
        cases = []  # (value, label)
        default = None
        labels_for = {}

        def collect(n):
            nonlocal default
            if isinstance(n, c_ast.Case):
                lab = self.new_label()
                labels_for[id(n)] = lab
                cases.append((n.expr, lab))
            elif isinstance(n, c_ast.Default):
                lab = self.new_label()
                labels_for[id(n)] = lab
                default = lab
            if isinstance(n, c_ast.Switch):
                return
            for _, child in n.children():
                if not isinstance(child, c_ast.Switch):
                    collect(child)

        body = node.stmt
        for _, child in body.children():
            collect(child)
        v = self.rvalue(node.cond)
        v = self.conv(v, cty.promote(v.type))
        values = []
        for expr, lab in cases:
            value = self.eval_const_int(expr)
            if any(cty.wrap(value, INT) == cty.wrap(other, INT) for other, _ in values):
                raise CompileError(f"duplicate case value {value}", expr)
            values.append((value, lab))
        if v.is_const:
            target = default or end
            for val, lab in values:
                if cty.wrap(val, v.type) == cty.wrap(v.off, v.type):
                    target = lab
                    break
            self.jmp(target)
        else:
            v = self.to_reg(v)
            r = self.reg_of(v.tmp)
            for val, lab in values:
                if s32(val) == 0:
                    self.emit("beq", r, ZERO, lab)
                else:
                    self.emit("lw", ZERO, AT, self.k(val))
                    self.emit("beq", r, AT, lab)
            self.release(v)
            self.jmp(default or end)
        self.break_stack.append(end)
        self.switch_labels = getattr(self, "switch_labels", {})
        self.switch_labels.update(labels_for)
        saved_scope = self.scope
        self.scope = Scope(self.scope)
        for item in body.block_items or []:
            self.stmt(item)
        self.scope = saved_scope
        self.break_stack.pop()
        self.place(end)

    def s_Case(self, node):
        self.place(self.switch_labels[id(node)])
        for st in node.stmts or []:
            self.stmt(st)

    def s_Default(self, node):
        self.place(self.switch_labels[id(node)])
        for st in node.stmts or []:
            self.stmt(st)

    def s_Decl(self, node):
        self.local_decl(node)

    def s_Typedef(self, node):
        self.scope.names[node.name] = TypedefSym(self.comp.build_type(node.type, self.scope, self))

    def s_DeclList(self, node):
        for d in node.decls:
            self.local_decl(d)

    # ------------------------------------------------------------ declarations

    def local_decl(self, decl):
        if isinstance(decl, c_ast.Typedef):
            return self.s_Typedef(decl)
        if decl.name is None:
            self.comp.build_type(decl.type, self.scope, self)
            return
        ty = self.comp.build_type(decl.type, self.scope, self)
        if decl.name in self.scope.names and "extern" not in decl.storage and not isinstance(ty, Func):
            raise CompileError(f"redeclaration of '{decl.name}'", decl)
        if isinstance(ty, Func):
            g = self.comp.externs.get(decl.name)
            if g is None:
                g = GObj(decl.name, ty, "func", coord=decl.coord)
                self.comp.externs[decl.name] = g
            self.scope.names[decl.name] = g
            return
        if "extern" in decl.storage:
            g = self.comp.externs.get(decl.name)
            if g is None:
                raise CompileError(f"extern '{decl.name}' is not defined", decl)
            self.scope.names[decl.name] = g
            return
        if "static" in decl.storage:
            if isinstance(ty, Array) and ty.count is None and decl.init is not None:
                ty = Array(ty.elem, self.init_count(ty, decl.init))
            g = GObj(decl.name, ty, "var", static=True, tu=self.gobj.tu if self.gobj else None, coord=decl.coord)
            g.defined = True
            g.init = decl.init
            self.scope.names[decl.name] = g
            return
        if isinstance(ty, Array) and ty.count is None:
            if decl.init is None:
                raise CompileError("array of unknown size", decl)
            ty = Array(ty.elem, self.init_count(ty, decl.init))
        self.require_complete(ty, decl)
        size = max(1, ty.size) if (ty.is_array() or ty.is_struct()) else 1
        slot = self.local_top
        self.local_top += size
        self.local_max = max(self.local_max, self.local_top)
        self.scope.names[decl.name] = Local(ty, slot)
        if decl.init is not None:
            self.local_init(Val(Ptr(ty), sp=True, off=slot), ty, decl.init)

    def local_init(self, addr, ty, init):
        """Initialize the object at address Val `addr` (no tmp) with `init`."""
        sub = lambda off, t: addr.copy(type=Ptr(t), off=addr.off + off)
        if ty.is_array():
            elem = ty.elem
            if isinstance(init, c_ast.Constant) and init.type == "string" and elem.is_int():
                chars = self.comp.decode_string(init.value, init)
                for i in range(ty.count):
                    ch = chars[i] if i < len(chars) else 0
                    self.store_to(sub(i * elem.size, elem), const_val(INT, ch))
                return
            if not isinstance(init, c_ast.InitList):
                raise CompileError("array initializer must be a list", init)
            full = ty.count == len(init.exprs) and not any(isinstance(e, c_ast.NamedInitializer) for e in init.exprs)
            if not full:
                self.zero_fill(addr, ty)
            idx = 0
            for e in init.exprs:
                if isinstance(e, c_ast.NamedInitializer):
                    off, t, first = self.designate(ty, e.name)
                    self.local_init(sub(off, t), t, e.expr)
                    idx = first + 1
                    continue
                if idx >= ty.count:
                    raise CompileError("too many initializers", init)
                self.local_init(sub(idx * elem.size, elem), elem, e)
                idx += 1
            return
        if ty.is_struct():
            if isinstance(init, c_ast.InitList):
                members = ty.members if not ty.is_union else ty.members[:1]
                full = len(init.exprs) == len(members) and not any(isinstance(e, c_ast.NamedInitializer) for e in init.exprs)
                if not full:
                    self.zero_fill(addr, ty)
                idx = 0
                for e in init.exprs:
                    if isinstance(e, c_ast.NamedInitializer):
                        off, t, first = self.designate(ty, e.name)
                        self.local_init(sub(off, t), t, e.expr)
                        idx = first + 1
                        continue
                    if idx >= len(members):
                        raise CompileError("too many initializers", init)
                    m = members[idx]
                    self.local_init(sub(m.offset, m.type), m.type, e)
                    idx += 1
                return
            src = self.rvalue(init)
            if not src.type.is_struct():
                raise CompileError("invalid struct initializer", init)
            self.copy_words(addr, src, ty.size)
            return
        if isinstance(init, c_ast.InitList):
            if len(init.exprs) != 1:
                raise CompileError("scalar initializer must have one value", init)
            init = init.exprs[0]
        v = self.rvalue(init)
        v = self.conv(v, ty)
        stored = self.store_to(addr, v)
        self.release(stored)

    def zero_fill(self, addr, ty):
        if ty.is_array():
            for i in range(ty.count):
                self.zero_fill(addr.copy(type=Ptr(ty.elem), off=addr.off + i * ty.elem.size), ty.elem)
        elif ty.is_struct():
            for m in (ty.members if not ty.is_union else ty.members[:1]):
                self.zero_fill(addr.copy(type=Ptr(m.type), off=addr.off + m.offset), m.type)
        else:
            self.emit("sw", SP, ZERO, addr.off)

    # ------------------------------------------------------------ whole function

    def compile_function(self):
        g = self.gobj
        fdef = g.fdef
        ftype = g.type
        self.ret_type = ftype.ret
        self.variadic = ftype.variadic
        plist = fdef.decl.type.args
        params = []
        if plist is not None:
            for p in plist.params:
                if isinstance(p, c_ast.EllipsisParam):
                    continue
                if isinstance(p, c_ast.Decl) and p.name is None and isinstance(p.type, c_ast.TypeDecl):
                    continue
                params.append(p)
        if len(params) == 1 and params[0].name is None:
            params = []
        slot = 1
        if self.ret_type.is_struct():
            slot += 1  # hidden pointer to the caller's result area at slot 1
        for p, pty in zip(params, ftype.params or []):
            self.scope.names[p.name] = Local(pty, slot)
            slot += max(1, pty.size) if pty.is_struct() else 1
        self.local_top = slot + (VARARG_SLOTS if self.variadic else 0)
        self.local_max = self.local_top
        self.ret_label = self.new_label()
        body = fdef.body
        # body shares the parameter scope per C rules
        for item in body.block_items or []:
            self.stmt(item)
        if g.name == "main":
            self.emit("add", ZERO, ZERO, 1, "falling off main returns 0")
        return self.finalize()

    def finalize(self):
        """Add prologue/epilogue, resolve frame operands, return Lines."""
        fs = self.local_max + self.nspill
        if fs > 30000:
            raise CompileError(f"stack frame of {fs} words is too large")
        label = self.comp.label_of(self.gobj)
        code = []
        if not self.leaf:
            code.append(Ins("sw", SP, RA, 0, "save return address"))
        for ins in self.code:
            if ins.op == "ret":
                if self.leaf:
                    code.append(Ins("jalr", RA, AT, 0, "return"))
                else:
                    code.append(Ins("beq", ZERO, ZERO, self.ret_label))
            else:
                code.append(ins)
        if self.leaf:
            code.append(Ins("jalr", RA, AT, 0, "return"))
        else:
            code.append(Ins("label", c=self.ret_label))
            code.append(Ins("lw", SP, RA, 0, "restore return address"))
            code.append(Ins("jalr", RA, AT, 0, "return"))
        return self.to_lines(code, label, fs)

    def to_lines(self, code, func_label, fs):
        from .asmwriter import Line
        from .peephole import optimize

        code = optimize(code, self.comp.immutable_labels())
        spill_base = self.local_max

        def resolve(x):
            if isinstance(x, Lazy):
                if x.kind == "arg":
                    return fs + 1 + x.n
                if x.kind == "spill":
                    return spill_base + x.n
                if x.kind == "fs":
                    return self.p.const(fs * x.n)
                if x.kind == "argaddr":
                    return self.p.const(fs + 1 + x.n)
            return x

        # consecutive labels name the same address: keep the first, alias the rest
        alias = {}
        placed = []  # (label or None, Ins)
        pending = []
        for ins in code:
            if ins.op == "label":
                pending.append(ins.c)
                continue
            for extra in pending[1:]:
                alias[extra] = pending[0]
            placed.append((pending[0] if pending else None, ins))
            pending = []
        if pending:
            for extra in pending[1:]:
                alias[extra] = pending[0]
            placed.append((pending[0], Ins("noop")))
        if placed[0][0] is not None:
            alias[placed[0][0]] = func_label
        placed[0] = (func_label, placed[0][1])

        def target(lab):
            while lab in alias:
                lab = alias[lab]
            return lab

        out = []
        for lab, ins in placed:
            a, b, c = resolve(ins.a), resolve(ins.b), resolve(ins.c)
            if ins.op in ("add", "nor"):
                args = (a, b, c)
            elif ins.op in ("lw", "sw"):
                args = (a, b, c)
            elif ins.op == "beq":
                args = (a, b, target(c) if isinstance(c, str) else c)
            elif ins.op == "jalr":
                args = (a, b)
            else:
                args = ()
            out.append(Line(ins.op, args, lab, ins.comment))
        return out

