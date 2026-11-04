"""Hand-written LC-2K runtime helpers.

The ISA has no multiply, no shifts, and no compare; the compiler calls
these routines for the cases it cannot expand inline.

Helper calling convention (not the C ABI):
  arguments r1, r2; result r1
  the caller loads the helper's address cell into r6 and does `jalr 6 4`
  helpers may clobber r2, r3, r4, r6 (r4 = link); r5 (SP) and r7 are kept
  the caller treats every temporary register as clobbered
"""

from .asmwriter import Line

HELPERS = ("Mul", "Shl", "Shru", "Shrs", "Lts", "Ltu")


def emit_helpers(comp, needed: set[str]):
    p = comp.program
    m = comp.mangler
    out = p.text

    def ins(op, *args, label=None, comment=None):
        out.append(Line(op, args, label, comment))

    def lab(prefix):
        return m.fresh(prefix, "")

    c = p.const
    hsave = hneg = None

    def scratch():
        nonlocal hsave, hneg
        if hsave is None:
            hsave = m.fresh("h", "helper link save")
            hneg = m.fresh("h", "helper sign flag")
            p.data.append(Line(".fill", (0,), hsave))
            p.data.append(Line(".fill", (0,), hneg))

    names = comp.helper_labels
    # Mul, Shru and Shrs share one accumulate loop; emit them together if any is needed.
    shift_family = needed & {"Mul", "Shru", "Shrs"}
    if shift_family:
        scratch()
        loop, skip, done, zero, ret = lab("h"), lab("h"), lab("h"), lab("h"), lab("h")
        ret_label = lab("h")
        if "Mul" in shift_family:
            ins("sw", 0, 0, hneg, label=names["Mul"], comment="r1 = r1 * r2")
            ins("sw", 0, 4, hsave)
            ins("nor", 2, 2, 3, comment="r3 = ~multiplier: bits left to consume")
            ins("lw", 0, 6, c(-1))
            ins("beq", 3, 6, zero)
            ins("add", 0, 0, 2, comment="acc = 0")
            ins("lw", 0, 4, c(-2), comment="r4 = ~mask, mask = 1")
            ins("beq", 0, 0, loop)
        if "Shru" in shift_family or "Shrs" in shift_family:
            setup = lab("h")
            ins("sw", 0, 0, hneg, label=names["Shru"], comment="r1 = r1 >> n (logical), r2 = 1 << n")
            ins("sw", 0, 4, hsave, label=setup)
            ins("nor", 2, 2, 4, comment="r4 = ~mask")
            ins("lw", 0, 6, c(1))
            ins("add", 4, 6, 6, comment="r6 = -mask")
            ins("nor", 1, 1, 2)
            ins("nor", 6, 6, 6)
            ins("nor", 2, 6, 2, comment="r2 = x with the bits below n cleared")
            ins("nor", 2, 2, 3, comment="r3 = ~r2: bits left to consume")
            ins("lw", 0, 6, c(-1))
            ins("beq", 3, 6, zero)
            ins("add", 0, 0, 2, comment="acc = 0")
            ins("lw", 0, 1, c(1), comment="weight = 1")
            ins("beq", 0, 0, loop)
            if "Shrs" in shift_family:
                sneg = lab("h")
                ins("lw", 0, 3, c(0x7FFFFFFF), label=names["Shrs"], comment="r1 = r1 >> n (arithmetic), r2 = 1 << n")
                ins("nor", 1, 3, 3, comment="r3 == 0 iff x < 0")
                ins("beq", 3, 0, sneg)
                ins("beq", 0, 0, names["Shru"])
                ins("nor", 1, 1, 1, label=sneg, comment="x < 0: shift ~x, then negate")
                ins("lw", 0, 6, c(1))
                ins("sw", 0, 6, hneg)
                ins("beq", 0, 0, setup)
        # shared loop: r1 = weight/multiplicand, r2 = acc, r3 = ~bits left, r4 = ~mask
        ins("nor", 3, 4, 6, label=loop, comment="mask & bits")
        ins("beq", 6, 0, skip)
        ins("add", 2, 1, 2, comment="acc += weight")
        ins("nor", 4, 4, 6)
        ins("add", 3, 6, 3, comment="clear the consumed bit")
        ins("lw", 0, 6, c(-1))
        ins("beq", 3, 6, done)
        ins("add", 1, 1, 1, label=skip, comment="weight <<= 1")
        ins("add", 4, 4, 4)
        ins("lw", 0, 6, c(1))
        ins("add", 4, 6, 4, comment="~mask = ~(mask << 1)")
        ins("beq", 0, 0, loop)
        ins("add", 0, 0, 2, label=zero)
        ins("add", 2, 0, 1, label=done)
        ins("lw", 0, 4, hsave)
        ins("lw", 0, 6, hneg)
        ins("beq", 6, 0, ret_label)
        ins("nor", 1, 1, 1)
        ins("jalr", 4, 6, label=ret_label, comment="return")

    if "Shl" in needed:
        loop, done = lab("h"), lab("h")
        ins("beq", 2, 0, done, label=names["Shl"], comment="r1 = r1 << r2")
        ins("add", 1, 1, 1, label=loop)
        ins("lw", 0, 6, c(-1))
        ins("add", 2, 6, 2)
        ins("beq", 2, 0, done)
        ins("beq", 0, 0, loop)
        ins("jalr", 4, 6, label=done, comment="return")

    if "Lts" in needed or "Ltu" in needed:
        same, true, false = lab("h"), lab("h"), lab("h")
        if "Ltu" in needed:
            ins("lw", 0, 3, c(-(2**31)), label=names["Ltu"], comment="r1 = r1 < r2 (unsigned)")
            ins("add", 1, 3, 1, comment="flip sign bits, then compare signed")
            ins("add", 2, 3, 2)
        if "Lts" in needed or "Ltu" in needed:
            ins("lw", 0, 3, c(0x7FFFFFFF), label=names["Lts"], comment="r1 = r1 < r2 (signed)")
            ins("nor", 1, 3, 6, comment="r6 == 0 iff a < 0")
            ins("nor", 2, 3, 3, comment="r3 == 0 iff b < 0")
            ins("beq", 6, 3, same)
            ins("beq", 6, 0, true, comment="signs differ: a < b iff a < 0")
            ins("add", 0, 0, 1, label=false)
            ins("jalr", 4, 6, comment="return")
            ins("lw", 0, 1, c(1), label=true)
            ins("jalr", 4, 6, comment="return")
            ins("nor", 2, 2, 2, label=same, comment="same sign: a - b cannot overflow")
            ins("add", 1, 2, 1)
            ins("lw", 0, 6, c(1))
            ins("add", 1, 6, 1)
            ins("lw", 0, 3, c(0x7FFFFFFF))
            ins("nor", 1, 3, 1, comment="r1 == 0 iff a - b < 0")
            ins("beq", 1, 0, true)
            ins("beq", 0, 0, false)
