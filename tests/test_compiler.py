import unittest

from lc2kcc import lint
from lc2kcc.assembler import assemble
from lc2kcc.cli import compile_files
from lc2kcc.frontend import CompileError

from lc2kcc.cli import read_cstring

from support import ROOT, result_of, run_files, run_source


class HelloTest(unittest.TestCase):
    def test_hello_example(self):
        result, _, asm, _, _ = run_files([ROOT / "examples" / "hello.c"])
        self.assertEqual(result, 42)
        self.assertEqual(lint.check(asm), [])
        _, symbol_map = compile_files([ROOT / "examples" / "hello.c"])
        self.assertIn("Main\tfunc main", symbol_map)


class SemanticsTest(unittest.TestCase):
    """Small programs with hand-computed answers (the corpus in tests/programs
    is checked against gcc)."""

    def test_return_values(self):
        cases = {
            "int main(void) { return 0; }": 0,
            "int main(void) { }": 0,
            "int main(void) { return -1; }": -1,
            "int main(void) { return 0x7fffffff + 1; }": -(2**31),
            "int main(void) { return -7 / 2; }": -3,
            "int main(void) { return -7 % 3; }": -1,
            "int main(void) { return 1 << 4 | 3; }": 19,
            "int main(void) { return 'A'; }": 65,
            "int main(void) { return (unsigned char)300; }": 44,
            "int main(void) { return (signed char)200; }": -56,
            "int main(void) { return (short)70000; }": 4464,
            "int main(void) { return 6 * 7; }": 42,
            "int main(int argc, char **argv) { return argc + (argv == 0); }": 1,
            "int main(void) { int x = -2147483648; return x == (-2147483647 - 1); }": 1,
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(result_of(source), expected)

    def test_runtime_arithmetic(self):
        source = """
        int g(int a, int b) { return a * b; }
        int main(void) {
            volatile int x = 1234, y = -37;
            unsigned u = 4000000000u;
            return g(x, y) + x / y + x % y + (int)(u / 1000u) + (y >> 2) + (int)(u >> 28);
        }"""
        x, y, u = 1234, -37, 4000000000
        q = int(x / y)
        expected = x * y + q + (x - q * y) + u // 1000 + (y >> 2) + (u >> 28)
        self.assertEqual(result_of(source), expected)

    def test_struct_and_pointer_layout_matches_ilp32(self):
        source = """
        struct S { char a; short b; int c; char d; };
        union U { char c; int i; };
        int main(void) {
            struct S s;
            return sizeof(struct S) * 1000 + sizeof(union U) * 100
                 + (int)((char *)&s.c - (char *)&s) * 10 + (int)((char *)&s.b - (char *)&s);
        }"""
        self.assertEqual(result_of(source), 12 * 1000 + 4 * 100 + 4 * 10 + 2)

    def test_stack_frames_are_independent_for_recursion(self):
        source = """
        int sum(int n) { int local = n; return n == 0 ? 0 : local + sum(n - 1); }
        int main(void) { return sum(100); }"""
        self.assertEqual(result_of(source), 5050)

    def test_variadic_arguments(self):
        source = """
        #include <stdarg.h>
        int sum(int n, ...) { va_list ap; int s = 0; va_start(ap, n); while (n--) s += va_arg(ap, int); va_end(ap); return s; }
        int main(void) { return sum(4, 10, 20, 30, 40); }"""
        self.assertEqual(result_of(source), 100)


class LibraryTest(unittest.TestCase):
    def test_printf_and_string_library(self):
        source = r"""
        #include <stdio.h>
        #include <string.h>
        #include <stdlib.h>
        #include <ctype.h>
        static int cmp(const void *a, const void *b) { return *(const int *)a - *(const int *)b; }
        int main(void) {
            int v[6] = { 5, 3, 9, -1, 7, 2 };
            char buf[40];
            int i;
            qsort(v, 6, sizeof v[0], cmp);
            for (i = 0; i < 6; i++) printf("%d,", v[i]);
            sprintf(buf, "%s|%05d|%x|%c|%-3d|%3d|", "ab", 42, 255, 'z', 7, -8);
            puts(buf);
            printf("%u %d%%\n", 4000000000u, (int)strlen(buf));
            return atoi("-12") + toupper('a');
        }"""
        result, _, asm, assembled, mem = run_source(source)
        self.assertEqual(result, -12 + 65)
        out = read_cstring(mem, assembled.symbols["Stdout"])
        self.assertEqual(out, "-1,2,3,5,7,9,ab|00042|ff|z|7  | -8|\n4000000000 22%\n")

    def test_program_may_replace_a_library_function(self):
        source = """
        #include <string.h>
        size_t strlen(const char *s) { return 99; }
        int main(void) { return (int)strlen("abc"); }"""
        self.assertEqual(result_of(source), 99)


class LinkTest(unittest.TestCase):
    def test_multiple_translation_units(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.c"), Path(d, "b.c")
            a.write_text("int shared = 5; static int hidden = 1; int bump(int);\nint main(void) { return bump(10) + hidden + shared; }\n")
            b.write_text("extern int shared; static int hidden = 100; int bump(int x) { return x + hidden + shared++; }\n")
            result, _, _, _, _ = run_files([a, b])
        self.assertEqual(result, 10 + 100 + 5 + 1 + 6)


class DiagnosticsTest(unittest.TestCase):
    def test_unsupported_constructs_fail_loudly(self):
        cases = {
            "float": "int main(void) { float f = 1.0f; return 0; }",
            "double": "double d; int main(void) { return 0; }",
            "long long": "int main(void) { long long x = 1; return 0; }",
            "bit-field": "struct B { int a : 3; }; int main(void) { return 0; }",
            "undeclared": "int main(void) { return x; }",
            "undefined function": "int f(void); int main(void) { return f(); }",
            "no main": "int f(void) { return 1; }",
            "non-constant initializer": "int f(void); int g = 1 + f(); int main(void) { return g; }",
        }
        for name, source in cases.items():
            with self.subTest(name), self.assertRaises(CompileError):
                run_source(source)


class OutputFormatTest(unittest.TestCase):
    SOURCE = """
    int table[3] = { 1, 2, 3 };
    static int hidden = 7;
    int f(int x) { return x * 100 + hidden + table[1]; }
    int main(void) { return f(table[2]); }
    """

    def test_layout_and_label_conventions(self):
        _, _, asm, assembled, _ = run_source(self.SOURCE)
        self.assertEqual(lint.check(asm), [])
        assemble(asm)  # strict assembler accepts it
        lines = asm.splitlines()
        labels = [l.split("\t")[0] for l in lines if l[:1] not in ("\t", "")]
        self.assertEqual(len(labels), len(set(labels)), "duplicate labels")
        self.assertTrue(all(len(l) <= 6 and l.isalnum() and l[0].isalpha() for l in labels))
        # the first instruction is at address 0 and the stack label closes the image
        self.assertEqual(assembled.words[0] >> 22 & 7, 2, "starts with the lw that loads the stack pointer")
        self.assertEqual(lines[-1].split("\t")[0], "Stack")
        # global (non-static) data and functions are capitalized, statics are lowercase
        self.assertIn("Main", labels)
        self.assertIn("Table", labels)
        self.assertTrue(any(l == "hidden" for l in labels))

    def test_data_section_order(self):
        _, _, asm, _, _ = run_source("int f(void) { return -3; } int g(void) { return 9; } int h(void) { return -1; } int main(void) { return f() + g() + h() + 2; }")
        consts = [line.split()[0] for line in asm.splitlines() if line[:1] in "kn" and line.split()[1] == ".fill"]
        positive = [c for c in consts if c[0] == "k"]
        negative = [c for c in consts if c[0] == "n"]
        self.assertEqual(consts, positive + negative)
        values = [int(c[1:]) for c in positive]
        self.assertEqual(values, sorted(values))
        values = [int(c[1:]) for c in negative]
        self.assertEqual(values, sorted(values))

    def test_r0_is_never_written(self):
        _, _, asm, _, _ = run_source(self.SOURCE)
        for line in asm.splitlines():
            parts = line.split()
            if len(parts) > 1 and not line[0].isspace():
                parts = parts[1:]
            if not parts:
                continue
            op = parts[0]
            if op in ("add", "nor"):
                self.assertNotEqual(parts[3], "0", line)
            elif op == "lw":
                self.assertNotEqual(parts[2], "0", line)
            elif op == "jalr":
                self.assertNotEqual(parts[2], "0", line)


if __name__ == "__main__":
    unittest.main()
