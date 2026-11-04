"""CoreMark, unmodified, with the lc2kcc port: it must validate itself."""

import unittest

from lc2kcc.cli import read_cstring

from support import ROOT, run_files

CM = ROOT / "third_party" / "coremark"
PORT = ROOT / "ports" / "coremark"
SOURCES = [CM / f for f in ("core_list_join.c", "core_main.c", "core_matrix.c", "core_state.c", "core_util.c")] + [PORT / "core_portme.c"]


class CoreMarkTest(unittest.TestCase):
    def test_validates(self):
        from lc2kcc.cli import compile_files

        asm, symbol_map = compile_files(SOURCES, [str(CM), str(PORT)], ['FLAGS_STR="lc2kcc"'])
        label = next(l.split("\t")[0] for l in symbol_map.splitlines() if l.endswith("\tee_outbuf"))
        from lc2kcc.cli import execute

        assembled, mem, steps = execute(asm, False, 50_000_000)
        out = read_cstring(mem, assembled.symbols[label])
        self.assertIn("Correct operation validated.", out)
        for line in ("seedcrc          : 0xe9f5", "[0]crclist       : 0xe714", "[0]crcmatrix     : 0x1fd7", "[0]crcstate      : 0x8e3a", "[0]crcfinal      : 0xe714"):
            self.assertIn(line, out)
        self.assertLess(len(assembled.words), 32768)


if __name__ == "__main__":
    unittest.main()
