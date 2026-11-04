# lc2kcc

A C compiler for the **EECS 370 LC-2K ISA** (8 opcodes, 8 registers, 16-bit
offsets, 65,536 words of memory). It is written in Python with
[pycparser](https://github.com/eliben/pycparser) and compiles
[CoreMark](third_party/coremark), unmodified, to a 9,850-word program that
validates itself (`Correct operation validated.`) on the bundled simulator,
with the same CRCs as the x86-32 build.

```
C source --gcc -E--> pycparser AST --> typed code generator --> .as --> assembler --> .mc
                                       (+ hand-written runtime)
```

## Quick start

Requires Python >= 3.11, `pycparser`, and `gcc` (used only as the C
preprocessor, with the host's headers hidden).

```sh
make test            # unit tests, the gcc-checked program corpus, and CoreMark
make hello           # C -> .as -> lint -> .mc -> simulate
make coremark        # compile CoreMark, assemble, run, print its report
make coremark-native # the same sources built for x86-32, for comparison
make fuzz            # differential fuzzing against gcc -m32
PYTHONPATH=src python3 -m lc2kcc --help
```

| Command | What it does |
|---|---|
| `lc2kcc cc a.c b.c -o out.as` | compile and link C files to LC-2K assembly, plus `out.map` (label -> C name) |
| `lc2kcc as foo.as -o foo.mc` | assemble with the strict 370 assembler (one 8-digit hex word per line) |
| `lc2kcc sim foo.mc` | simulate with the strict 370 simulator |
| `lc2kcc run a.c b.c [--fast] [--dump NAME]` | compile, assemble, run, print `Result` (and a C string global); `--fast` uses `lc2k-sim.exe` |
| `lc2kcc lint foo.as` | check the layout conventions |

`cc` accepts `-I dir` and `-D name[=value]`. The output of `cc` is always run
through the strict assembler and the layout lint before it is written, so a
file that is produced is a file that assembles.

## The target

The LC-2K has no immediates, shifts, compare, multiply, or I/O. Everything
else is built from `add`, `nor`, `lw`, `sw`, `beq` and `jalr`.

**Memory model: "sparse ILP32".** `sizeof` and struct layout are those of
ordinary 32-bit C (`char` 1, `short` 2, `int`/`long`/pointers 4), and a
pointer is a byte address that is also a word address. A scalar lives whole
in the word at its own address; the words after it are padding that is never
read. So:

- every load and store is one `lw`/`sw`, with no shifting or masking,
- `sizeof`, `offsetof` and pointer arithmetic match x86-32, so CoreMark's
  `check_data_types()` and its `16 + sizeof(...)` arithmetic work unchanged,
- `char`/`short` stores truncate or sign-extend to 8/16 bits, so a loaded
  value is already normalized,
- the costs: an `int` uses 4 words, and the bytes of an `int` can't be read
  through a `char *` (type punning; CoreMark never does this).

**ISA conventions.** The program starts at address 0 (the startup code),
register 0 is the constant zero and the generated code never writes it, and
the last word of the image is `Stack`, where the stack pointer starts. Since
code occupies address 0, no C object has address 0, so `NULL` never aliases
data. `lw`/`sw`/`beq` offsets are 16 bits, so every label the code loads, stores or
branches to must be below address 32,768; the compiler checks this by
assembling its own output.

**Registers.**

| reg | use |
|---|---|
| r0 | zero, never written |
| r1-r4 | expression temporaries; spilled to the frame under pressure; r1 = return value |
| r5 | stack pointer (the stack grows upward from `Stack`, past the end of the image) |
| r6 | scratch: constants, call targets |
| r7 | return address |

**Calls.** Arguments are stored in the callee's frame (word per scalar,
`sizeof` words per struct), the caller bumps r5 by its frame size, jumps with
`jalr`, and restores r5. Frame slot 0 holds the saved r7 (non-leaf functions
only), slots 1..n the parameters, then locals and spill slots. Variadic
functions work (`<stdarg.h>` is word-per-argument). Structs pass and return
by value (the callee gets a hidden result pointer).

**Constants.** Every constant is a `.fill` word loaded with `lw 0 r k<n>`;
addresses of globals are `.fill` cells. Any global word can carry a label, so
`g.field`, `arr[3]` and `arr[i]` are one `lw` (the register holds the index,
the label is the offset).

**Runtime** (`src/lc2kcc/runtime.py`, hand-written assembly, emitted only if
used): multiply (with a 16x16 lookup table fast path), shifts (the shift
count is passed as `1 << n`), signed/unsigned compare. Division and `%` are
in C (`src/lc2kcc/runtime/rt.c`), and so are 64-bit operations
(`runtime/ll.c`) and a small libc (`runtime/libc.c`: string, stdlib, ctype and
a `printf` family that writes to the `__stdout` buffer), all compiled with the
program. The shift and
multiply loops are bit-serial.

**Output layout** (follows `../programs/_LC2K_Format.txt`, checked by
`lint`): code first, then function-pointer cells, `Result`
(`OUTPUT: main's return value`), constants (positive ascending, then negative
descending), other single data, arrays (the CoreMark `ee_outbuf` is marked
`OUTPUT:`), and finally `Stack`. Labels are at most 6 characters; functions and
non-static data are capitalized, everything else is lowercase. Opcodes sit at
the 3rd tab stop, comments at the 7th, and each statement's first instruction
is annotated with its C source line.

**The program's output.** A program's result is `main`'s return value, stored
by the startup code in `Result`. CoreMark's port (`ports/coremark/`) also
formats its report into `ee_outbuf`, which `lc2kcc run --dump ee_outbuf` prints.

## C support

Supported: all integer types (`char`, `short`, `int`, `long`, `long long`,
signed/unsigned; 64-bit operations call the runtime's `__ll_*` routines), pointers, arrays (multi-dimensional, incomplete), structs,
unions (including anonymous members), enums, typedefs, function pointers,
`static`/`extern`/`const`/`volatile`, string literals, initializers
(positional, designated, nested, compound literals), every operator,
`if`/`while`/`do`/`for`/`switch`/`goto`, variadic functions, struct
assignment and by-value arguments/results, multiple translation units, and
`static` locals. Functions and data that `main` can't reach are not emitted.

Not supported, with a `CompileError` rather than wrong code: floating point,
bit-fields, variable-length arrays, K&R function
definitions, inline assembly.

## Verification

- `tests/test_assembler.py`: the spec example assembles to the exact machine
  code published in the 370 spec; error cases from section 3.3.
- `tests/test_programs.py`: 29 programs in `tests/programs/`, each returning a
  checksum compared with what gcc -m32 computes (`// expect: N`, stamped by
  `tools/expect.py`).
- `tests/test_coremark.py`: CoreMark validates and prints the published CRCs.
- `tools/fuzz.py`: random programs (expression mode, statement mode over
  arrays, structs and pointers, and a 64-bit mode) compared against gcc -m32. Running it with
  `LC2KCC_TEMPS=123` or `12` shrinks the temporary-register pool to stress
  the spill logic.
- Programs also run on the bundled `lc2k-assembler.exe` and `lc2k-sim.exe`,
  which implement the extended 470 encoding of the same assembly language,
  as an independent check (`lc2kcc run --fast`).

CoreMark, one iteration (`ITERATIONS=1`): 9,850 words, about 3.9 million
instructions; `tools/profile.py` reports where they go. The port fakes a
10-second run so CoreMark does not reject it as too short; real performance
is the simulator's instruction count.

## Layout

```
src/lc2kcc/
  frontend.py   gcc -E (-nostdinc -undef -D__LC2K__) + pycparser -> AST
  cty.py        C types: sizes, alignment, struct layout, conversions
  compiler.py   translation units, symbols, type building, global data, linking
  funcgen.py    per-function code generation (expressions, statements, calls)
  peephole.py   jump threading, dead code, redundant-load removal
  runtime.py    hand-written runtime helpers; runtime/*.c: division, 64-bit, libc
  asmwriter.py  Program model; data-section ordering; tab layout
  labels.py     6-char label rules and C-name abbreviation
  isa.py        opcodes, encoding, field ranges
  assembler.py  strict 370-spec assembler (b/jump, range checks)
  simulator.py  strict 370 reference simulator
  lint.py       layout-convention checker
  cli.py        command line
  include/      freestanding headers (stddef.h, stdint.h, limits.h, stdarg.h)
ports/coremark/ LC-2K port of CoreMark (core_portme.h/.c)
third_party/    vendored CoreMark, unmodified
examples/       sample C programs
tests/          unittest suites and the gcc-checked program corpus
tools/          fuzz.py, expect.py, profile.py
```

The repo's `lc2k-assembler.exe` and `lc2k-sim.exe` target the extended 470 ISA
(16 registers, `addi`/`nand`, 20-bit offsets, a different encoding).
`assembler.py` and `simulator.py` implement the strict 370 spec instead, so
nothing that only the extended ISA allows can slip through.
