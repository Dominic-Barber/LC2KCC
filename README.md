# lc2kcc

A C compiler that targets the **EECS 370 LC-2K ISA**: 8 opcodes, 8
registers, 16-bit offsets, 65,536 words of memory. Output follows the
layout conventions in `../programs/_LC2K_Format.txt`. The first real
target is [CoreMark](third_party/coremark), run unmodified and validated
against its own built-in CRC checks.

Status: **hello world**. `examples/hello.c` compiles, assembles, runs, and
stores 42 in the `Result` output word. The supported C subset is only
`return <integer constant expression>;`. Anything else fails with a
`CompileError` that names the construct.

## Quick start

Requires Python ≥ 3.11, `pycparser`, and `gcc` (used only as the C
preprocessor).

```sh
make test       # unit tests
make hello      # C -> .as -> lint -> .mc -> simulate
make coremark-size   # native x86-32 size of CoreMark with our port
PYTHONPATH=src python3 -m lc2kcc --help
```

| Command | What it does |
|---|---|
| `lc2kcc cc foo.c -o foo.as` | compile C to LC-2K assembly, plus a `foo.map` label→C-name map |
| `lc2kcc as foo.as -o foo.mc` | assemble to machine code (one 8-digit hex word per line) |
| `lc2kcc sim foo.mc` | simulate and print registers and instruction count |
| `lc2kcc run foo.c` | all of the above, then print `Result` |
| `lc2kcc lint foo.as` | check layout conventions |

## Layout

```
src/lc2kcc/
  frontend.py   gcc -E (-nostdinc -undef -D__LC2K__) + pycparser -> AST
  consteval.py  integer constant folding (32-bit C semantics)
  codegen.py    AST -> Program; also emits the startup code (crt0)
  asmwriter.py  Program model; data-section ordering; tab layout
  labels.py     6-char label rules and C-name mangling
  abi.py        register conventions
  isa.py        opcodes, encoding, field ranges
  assembler.py  strict 370-spec assembler (b/jump, range checks)
  simulator.py  reference simulator
  lint.py       layout-convention checker
  include/      freestanding headers (stddef.h, stdint.h, limits.h)
ports/coremark/ LC-2K port of CoreMark (core_portme.h/.c)
third_party/    vendored CoreMark, unmodified
examples/       sample C programs
tests/          unittest suites
```

The repo's `programs/lc2k-assembler.exe` targets the extended 470 ISA
(16 registers, `addi`/`nand`, 20-bit offsets). `assembler.py` and
`simulator.py` implement the strict 370 spec instead, so nothing that
only the extended ISA allows can slip through.

## Design decisions

**Language: Python + pycparser.** At CoreMark's scale (about 2K lines of C),
compile speed doesn't matter, and pycparser provides a complete C99
parser. All the effort goes into semantics and code generation. gcc
does preprocessing only, with the host's headers hidden.

**Memory model: "sparse ILP32".** `sizeof` follows ordinary 32-bit C
(`char` 1, `short` 2, `int`/`long`/pointers 4, `long long` 8), and
pointers are byte addresses. Because each byte address is also a word
address, a scalar lives whole in the word at its own address, and the
words after it are padding. Consequences:

- Every load and store is one `lw`/`sw`, with no shifting. That matters
  because LC-2K has no shift instruction.
- Struct layout, `sizeof`, and pointer arithmetic match x86-32, so
  CoreMark's `check_data_types()` and its known CRCs work unchanged. A
  model with one word per `char` would fail them: `core_list_join.c`
  hard-codes `16 + sizeof(...)`.
- Stores of `char`/`short` mask or sign-extend to 8 or 16 bits.
- Costs: memory use is 4× for `int`s, and reading the individual bytes
  of an `int` through a `char*` (type punning) doesn't work. CoreMark
  never does this. `memcpy` and `memset(0)` copy and clear padding words
  too, so they stay correct.

**Registers** (`abi.py`, provisional): r0 = 0 and is never written; r1 =
return value; r2–r4 = temporaries; r5 = stack pointer (grows upward from
`Stack`); r6 = scratch; r7 = return address. Calls are `lw 0 6 Pfunc` /
`jalr 6 7`, and returns are `jalr 7 6`. Returns don't use `jump 7`
because that writes r0.

**Labels**: globals get a capitalized label (`main` → `Main`), with
`Gxxx` as a fallback when the name doesn't fit 6 characters or is
already taken. Constants are `k<n>`/`n<n>`, and function-pointer cells
are `P<name>`. The `k`, `n`, `G`, and `P` prefixes are reserved. The
convention file also allows global labels to start with `_`, but the
spec and the assembler reject `_`, so lc2kcc never uses it.

**Output**: LC-2K has no I/O. A program's observable results are memory
words marked `OUTPUT:` in the data section: `Result` for main's return
value, and, in the CoreMark port, `ee_outbuf`, which receives the raw
`ee_printf` format strings.

## CoreMark

The native x86-32 `-Os` build of CoreMark plus our port is 1,945
instructions and 8 KB of code, with no libc dependencies. At an
estimated 3–5× LC-2K expansion, that's about 6–10K words, well under the
65,536-word limit. The port fakes a 10-second run so CoreMark's timing
check doesn't count as an error. Real performance is the simulator's
instruction count. Use `ITERATIONS=1` while developing.

## Roadmap

1. **Expressions & locals**: stack frames, a simple register allocator,
   `+ - & | ^ ~` (AND/OR/XOR built from `nor`), comparisons
   (subtract + sign-bit test), `if`/`while`/`for`/`switch`.
2. **Calls**: arguments on the stack, callee-saved registers, recursion,
   function pointers.
3. **Types**: type checker; `char`/`short` masking and sign extension;
   `unsigned`; pointers and arrays; structs and unions; globals and
   static data with initializers; string literals.
4. **Runtime library** (hand-written LC-2K): multiply, divide/mod,
   shifts (left = repeated `add`; right = bit-test loop), `memcpy`,
   `memset`, varargs.
5. **CoreMark**: compile all five `core_*.c` files plus the port, link
   them into one image, and get `Correct operation validated.` in
   `ee_outbuf`. Check the CRCs against the x86-32 reference build.
6. **Then**: a register allocator and peephole pass to bring down
   instruction count, and differential testing (csmith or c-torture)
   against gcc.
