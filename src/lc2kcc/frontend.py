"""C front end: preprocess with the host's gcc, parse with pycparser.

The preprocessor runs with -nostdinc -undef so only lc2kcc's own headers
(src/lc2kcc/include) and __LC2K__ are visible, never the host's libc.
"""

import os
import subprocess
from pathlib import Path

from pycparser import c_ast, c_parser

INCLUDE_DIR = Path(__file__).parent / "include"


class CompileError(Exception):
    def __init__(self, message: str, node: c_ast.Node | None = None):
        where = f"{node.coord}: " if node is not None and node.coord else ""
        super().__init__(where + message)


def preprocess(path: Path, include_dirs=(), defines=()) -> str:
    cpp = os.environ.get("LC2KCC_CPP", "gcc")
    cmd = [cpp, "-E", "-x", "c", "-std=c99", "-nostdinc", "-undef", "-D__LC2K__=1", "-I", str(INCLUDE_DIR)]
    cmd += [f"-I{d}" for d in include_dirs]
    cmd += [f"-D{d}" for d in defines]
    result = subprocess.run([*cmd, str(path)], capture_output=True, text=True)
    if result.returncode != 0:
        raise CompileError(f"preprocessing failed:\n{result.stderr}")
    return result.stdout


def parse(source: str, filename: str = "<input>") -> c_ast.FileAST:
    try:
        return c_parser.CParser().parse(source, filename=filename)
    except c_parser.ParseError as error:
        raise CompileError(str(error)) from None


def parse_file(path: Path, include_dirs=(), defines=()) -> c_ast.FileAST:
    return parse(preprocess(path, include_dirs, defines), str(path))
