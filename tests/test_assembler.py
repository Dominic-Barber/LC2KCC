import unittest

from lc2kcc.assembler import AsmError, assemble, from_mc, to_mc
from lc2kcc.simulator import SimError, run

# The example program from the LC-2K spec (section 2.2.4).
SPEC = """\
        lw      0       1       five    load reg1 with 5 (symbolic address)
        lw      1       2       3       load reg2 with -1 (numeric address)
start   add     1       2       1       decrement reg1
        beq     0       1       2       goto end of program when reg1==0
        beq     0       0       start   go back to the beginning of the loop
        noop
done    halt                            end of program
five    .fill   5
neg1    .fill   -1
stAddr  .fill   start                   will contain the address of start (2)
"""

# Machine code for SPEC as published in the EECS 370 project 1 spec.
SPEC_MC = [8454151, 9043971, 655361, 16842754, 16842749, 29360128, 25165824, 5, -1, 2]


class AssemblerTest(unittest.TestCase):
    def test_spec_example(self):
        result = assemble(SPEC)
        self.assertEqual(result.words, SPEC_MC)
        self.assertEqual(result.symbols["start"], 2)
        self.assertEqual(result.symbols["stAddr"], 9)

    def test_mc_round_trip(self):
        self.assertEqual(from_mc(to_mc(SPEC_MC)), SPEC_MC)
        self.assertEqual(to_mc([-5]), "fffffffb\n")

    def test_pseudo_instructions(self):
        self.assertEqual(assemble("\tb\tx\nx\tjump\t7\n").words, assemble("\tbeq 0 0 x\nx\tjalr 7 0\n").words)

    def test_errors(self):
        cases = {
            "undefined label": "\tlw 0 1 nope\n",
            "duplicate label": "a\tnoop\na\tnoop\n",
            "invalid label": "toolong7\tnoop\n",
            "invalid label 2": "a_b\tnoop\n",
            "bad register": "\tadd 0 8 1\n",
            "offset range": "\tlw 0 1 32768\n",
            "fill range": "\t.fill 2147483648\n",
            "unknown opcode": "\tsub 0 0 0\n",
            "missing fields": "\tadd 0 1\n",
            "blank line": "\tnoop\n\n\thalt\n",
        }
        for name, text in cases.items():
            with self.subTest(name), self.assertRaises(AsmError):
                assemble(text)

    def test_program_too_big(self):
        with self.assertRaises(AsmError):
            assemble("\tnoop\n" * 65537)


class SimulatorTest(unittest.TestCase):
    def test_spec_example(self):
        state = run(SPEC_MC)
        self.assertTrue(state.halted)
        self.assertEqual(state.steps, 17)
        self.assertEqual(state.regs[1], 0)
        self.assertEqual(state.regs[2], -1)

    def test_jalr_same_register_falls_through(self):
        state = run(assemble("\tjalr 1 1\n\thalt\n").words)
        self.assertEqual(state.steps, 2)

    def test_memory_out_of_range(self):
        with self.assertRaises(SimError):
            run(assemble("\tlw 0 1 -1\n\thalt\n").words)

    def test_no_halt(self):
        with self.assertRaises(SimError):
            run(assemble("x\tbeq 0 0 x\n").words, max_steps=100)


if __name__ == "__main__":
    unittest.main()
