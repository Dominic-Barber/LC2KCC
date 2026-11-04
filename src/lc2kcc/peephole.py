"""Peephole optimizer over one function's instruction list (funcgen.Ins).

Passes, repeated until nothing changes:
  - jump threading and removal of jumps to the next instruction
  - removal of unreachable instructions and unreferenced labels
  - removal of loads whose destination already holds the loaded value
    (after a store of that register, or an earlier load), within a basic block

Instruction forms (see funcgen.Ins):
  add/nor a b -> c      lw a(base) -> b, offset c      sw a(base) b(value), offset c
  beq a b, label c      jalr a -> b                     label (c = name)
"""

SP = 5


def _is_jump(ins):
    return ins.op == "beq" and ins.a == 0 and ins.b == 0


def _is_return(ins):
    return ins.op == "jalr" and ins.a == 7 and ins.b == 6


def _terminates(ins):
    return _is_jump(ins) or _is_return(ins) or ins.op == "halt"


def _label_targets(code):
    """label -> index of the first real instruction at or after it."""
    out = {}
    pending = []
    for i, ins in enumerate(code):
        if ins.op == "label":
            pending.append(ins.c)
        else:
            for name in pending:
                out[name] = i
            pending = []
    for name in pending:
        out[name] = len(code)
    return out


def _thread_jumps(code):
    targets = _label_targets(code)
    changed = False
    for ins in code:
        if _is_jump(ins):
            seen = set()
            while ins.c in targets and ins.c not in seen:
                seen.add(ins.c)
                idx = targets[ins.c]
                if idx < len(code) and _is_jump(code[idx]) and code[idx].c != ins.c:
                    ins.c = code[idx].c
                    changed = True
                else:
                    break
    return changed


def _drop_jump_to_next(code):
    out = []
    changed = False
    for i, ins in enumerate(code):
        if _is_jump(ins):
            j = i + 1
            fall = set()
            while j < len(code) and code[j].op == "label":
                fall.add(code[j].c)
                j += 1
            if ins.c in fall:
                changed = True
                continue
        out.append(ins)
    return out, changed


def _drop_unreachable(code):
    out = []
    dead = False
    changed = False
    for ins in code:
        if ins.op == "label":
            dead = False
            out.append(ins)
        elif dead:
            changed = True
        else:
            out.append(ins)
            if _terminates(ins):
                dead = True
    return out, changed


def _drop_unused_labels(code):
    used = {ins.c for ins in code if ins.op == "beq" and isinstance(ins.c, str)}
    out = [ins for ins in code if ins.op != "label" or ins.c in used]
    return out, len(out) != len(code)


def _forward_loads(code, immutable):
    """Drop `lw` instructions that reload a value the register already holds."""
    holds = {}  # register -> key of the memory word it currently equals
    out = []
    changed = False
    for ins in code:
        op = ins.op
        if op == "label":
            holds.clear()
        elif op == "lw":
            key = None
            if ins.a == SP:
                key = ("sp", ins.c)
            elif ins.a == 0 and ins.c in immutable:
                key = ("k", ins.c)
            if key is not None and holds.get(ins.b) == key:
                changed = True
                continue
            holds.pop(ins.b, None)
            if key is not None:
                holds[ins.b] = key
        elif op == "sw":
            if ins.a == SP:
                key = ("sp", ins.c)
                for r in [r for r, k in holds.items() if k == key]:
                    del holds[r]
                holds[ins.b] = key
            elif not (ins.a == 0 and isinstance(ins.c, str)):
                # a store through a pointer may hit the frame
                for r in [r for r, k in holds.items() if k[0] == "sp"]:
                    del holds[r]
        elif op in ("add", "nor"):
            holds.pop(ins.c, None)
            if ins.c == SP:
                holds.clear()
        elif op == "jalr":
            holds.clear()
        out.append(ins)
    return out, changed


def optimize(code, immutable=frozenset()):
    for _ in range(8):
        changed = _thread_jumps(code)
        code, c1 = _drop_jump_to_next(code)
        code, c2 = _drop_unreachable(code)
        code, c3 = _forward_loads(code, immutable)
        code, c4 = _drop_unused_labels(code)
        if not (changed or c1 or c2 or c3 or c4):
            break
    return code
