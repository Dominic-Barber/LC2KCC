"""AST -> LC-2K assembly.

Current subset: functions whose bodies are `return <integer constant
expression>;` (or empty, for main). Everything else raises CompileError
naming the construct, so unsupported input fails loudly instead of
miscompiling.
"""

from pycparser import c_ast

from . import abi
from .asmwriter import Line, Program
from .consteval import fold
from .frontend import CompileError
from .labels import Mangler

RUNTIME_LABELS = ("Stack", "Result")


class CodeGen:
    def __init__(self):
        self.program = Program()
        self.mangler = Mangler(reserved=RUNTIME_LABELS)
        self.functions: dict[str, str] = {}

    def compile(self, ast: c_ast.FileAST) -> Program:
        for ext in ast.ext:
            if isinstance(ext, c_ast.FuncDef):
                name = ext.decl.name
                self.functions[name] = self.mangler.global_label(("func", name), name)
            elif not self._is_declaration_only(ext):
                raise CompileError(f"not supported yet: top-level {type(ext).__name__}", ext)
        if "main" not in self.functions:
            raise CompileError("no main function")
        self._emit_crt0()
        for ext in ast.ext:
            if isinstance(ext, c_ast.FuncDef):
                self._function(ext)
        return self.program

    @staticmethod
    def _is_declaration_only(ext: c_ast.Node) -> bool:
        if isinstance(ext, c_ast.Typedef):
            return True
        return isinstance(ext, c_ast.Decl) and isinstance(ext.type, c_ast.FuncDecl)

    def _emit_crt0(self):
        p = self.program
        main_ptr = self.mangler.global_label(("funcptr", "main"), "main", prefix="P")
        p.emit("lw", abi.ZERO, abi.SP, "spinit", comment="initialize stack pointer")
        p.emit("lw", abi.ZERO, abi.AT, main_ptr, comment="load address of main")
        p.emit("jalr", abi.AT, abi.RA, comment="call main")
        p.emit("sw", abi.ZERO, abi.RV, "Result", comment="record main's return value")
        p.emit("halt")
        p.func_ptrs.append(Line(".fill", (self.functions["main"],), main_ptr))
        p.io.append(Line(".fill", (0,), "Result", "OUTPUT: main's return value"))
        p.data.append(Line(".fill", (p.stack_label,), "spinit"))

    def _function(self, func: c_ast.FuncDef):
        label = self.functions[func.decl.name]
        items = func.body.block_items or []
        for stmt in items:
            if not isinstance(stmt, c_ast.Return):
                raise CompileError(f"not supported yet: {type(stmt).__name__} statement", stmt)
        if items:
            value = fold(items[0].expr) if items[0].expr else 0
        elif func.decl.name == "main":
            value = 0  # C99: falling off main returns 0
        else:
            raise CompileError("not supported yet: function without return", func)
        self._load_const(abi.RV, value, label)
        self._return()

    def _load_const(self, reg: int, value: int, label: str | None = None):
        if value == 0:
            self.program.emit("add", abi.ZERO, abi.ZERO, reg, label=label, comment="r = 0")
        else:
            self.program.emit("lw", abi.ZERO, reg, self.program.const(value), label=label, comment=f"r = {value}")

    def _return(self):
        self.program.emit("jalr", abi.RA, abi.AT, comment="return")


def compile_ast(ast: c_ast.FileAST) -> tuple[Program, Mangler]:
    gen = CodeGen()
    return gen.compile(ast), gen.mangler
