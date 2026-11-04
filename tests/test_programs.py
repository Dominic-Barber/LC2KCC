"""Every tests/programs/*.c returns a checksum; `// expect: N` on line 1 is
what gcc -m32 produced (see tools/expect.py)."""

import re
import unittest

from support import ROOT, run_files

PROGRAMS = sorted((ROOT / "tests" / "programs").glob("*.c"))


class ProgramsTest(unittest.TestCase):
    def test_corpus_matches_gcc(self):
        self.assertGreater(len(PROGRAMS), 10)
        for path in PROGRAMS:
            with self.subTest(path.name):
                expected = int(re.match(r"// expect: (-?\d+)", path.read_text()).group(1))
                result, steps, _, assembled, _ = run_files([path])
                self.assertEqual(result, expected)
                self.assertLess(len(assembled.words), 32768)


if __name__ == "__main__":
    unittest.main()
