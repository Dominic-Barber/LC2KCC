"""Reference LC-2K simulator (strict spec semantics)."""

from dataclasses import dataclass

from . import isa


class SimError(Exception):
    pass


@dataclass
class State:
    pc: int
    regs: list[int]
    mem: list[int]
    steps: int = 0
    halted: bool = False


def run(words: list[int], max_steps: int = 50_000_000) -> State:
    if len(words) > isa.MEM_WORDS:
        raise SimError(f"image of {len(words)} words exceeds memory")
    state = State(pc=0, regs=[0] * isa.NUM_REGS, mem=list(words) + [0] * (isa.MEM_WORDS - len(words)))
    regs, mem = state.regs, state.mem

    def address(base: int, offset: int) -> int:
        addr = regs[base] + offset
        if not 0 <= addr < isa.MEM_WORDS:
            raise SimError(f"pc {state.pc}: memory address {addr} out of range")
        return addr

    while state.steps < max_steps:
        pc = state.pc
        if not 0 <= pc < isa.MEM_WORDS:
            raise SimError(f"pc {pc} out of range")
        op, a, b, dest, offset = isa.decode(mem[pc])
        state.steps += 1
        state.pc = pc + 1
        if op == "add":
            regs[dest] = isa.to_signed32(regs[a] + regs[b])
        elif op == "nor":
            regs[dest] = isa.to_signed32(~(regs[a] | regs[b]))
        elif op == "lw":
            regs[b] = mem[address(a, offset)]
        elif op == "sw":
            mem[address(a, offset)] = regs[b]
        elif op == "beq":
            if regs[a] == regs[b]:
                state.pc = pc + 1 + offset
        elif op == "jalr":
            regs[b] = pc + 1
            state.pc = regs[a]
        elif op == "halt":
            state.halted = True
            return state
    raise SimError(f"no halt after {max_steps} instructions")
