import unittest
from pathlib import Path

from lc2kcc import lint
from lc2kcc.assembler import assemble
from lc2kcc.cli import compile_c
from lc2kcc.codegen import compile_ast
from lc2kcc.frontend import CompileError, parse
from lc2kcc.simulator import run

ROOT = Path(__file__).resolve().parents[1]


def compile_source(source: str) -> str:
    program, _ = compile_ast(parse(source))
    return program.render()


def run_asm(asm: str) -> int:
    assembled = assemble(asm)
    state = run(assembled.words)
    return state.mem[assembled.symbols["Result"]]


class HelloTest(unittest.TestCase):
    def test_hello_example(self):
        asm, symbol_map = compile_c(ROOT / "examples" / "hello.c")
        self.assertEqual(run_asm(asm), 42)
        self.assertEqual(lint.check(asm), [])
        self.assertIn("Main\tfunc main", symbol_map)

    def test_return_values(self):
        cases = {
            "int main(void) { return 0; }": 0,
            "int main(void) { }": 0,
            "int main(void) { return -1; }": -1,
            "int main(void) { return 0x7fffffff + 1; }": -(2**31),
            "int main(void) { return -7 / 2; }": -3,
            "int main(void) { return 1 << 4 | 3; }": 19,
            "int main(void) { return 'A'; }": 65,
        }
        for source, expected in cases.items():
            with self.subTest(source):
                self.assertEqual(run_asm(compile_source(source)), expected)

    def test_data_section_order(self):
        asm = compile_source("int f(void) { return -3; } int g(void) { return 9; } int h(void) { return -1; } int main(void) { return 2; }")
        consts = [line.split()[0] for line in asm.splitlines() if line[:1] in "kn"]
        self.assertEqual(consts, ["k2", "k9", "n1", "n3"])
        self.assertEqual(asm.splitlines()[-1].split()[0], "Stack")

    def test_name_collisions_get_unique_labels(self):
        asm = compile_source("int stack(void) { return 1; } int verylongname(void) { return 2; } int main(void) { return 0; }")
        labels = [line.split()[0] for line in asm.splitlines() if not line.startswith("\t")]
        self.assertEqual(len(labels), len(set(labels)))
        assemble(asm)

    def test_unsupported_constructs_fail_loudly(self):
        for source in ("int main(void) { int x = 1; return x; }", "int g; int main(void) { return 0; }", "int f(void) { return 1; }"):
            with self.subTest(source), self.assertRaises(CompileError):
                compile_source(source)


class LintTest(unittest.TestCase):
    def test_flags_bad_layout(self):
        self.assertEqual(lint.check("\t\thalt\n"), [])
        self.assertTrue(lint.check("\thalt\n"))  # opcode at column 4
        self.assertTrue(lint.check("\t\thalt \n"))  # trailing whitespace
        self.assertTrue(lint.check("\t\thalt"))  # no final newline
        self.assertTrue(lint.check("\t\tlw  0 1 2\n"))  # two spaces between operands
        self.assertTrue(lint.check("\t\thalt\tcomment\n"))  # comment at column 16


if __name__ == "__main__":
    unittest.main()
