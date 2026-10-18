"""AST de expresiones booleanas.

La evaluación es bit-paralela: cada variable se asigna a un entero cuyos bits
representan todas las filas de la tabla de verdad a la vez. Con ``mask`` se
limita el ancho para que NOT no produzca enteros negativos.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import and_, or_, xor


class Expr:
    def variables(self) -> list[str]:
        """Variables en orden de primera aparición."""
        seen: dict[str, None] = {}
        self._collect(seen)
        return list(seen)

    def _collect(self, seen: dict[str, None]) -> None:
        raise NotImplementedError

    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        raise NotImplementedError

    def to_str(self) -> str:
        return _fmt(self, 0)

    def __str__(self) -> str:
        return self.to_str()


@dataclass(frozen=True)
class Const(Expr):
    value: bool

    def _collect(self, seen: dict[str, None]) -> None:
        pass

    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return mask if self.value else 0


@dataclass(frozen=True)
class Var(Expr):
    name: str

    def _collect(self, seen: dict[str, None]) -> None:
        seen.setdefault(self.name, None)

    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return env[self.name] & mask


@dataclass(frozen=True)
class Not(Expr):
    arg: Expr

    def _collect(self, seen: dict[str, None]) -> None:
        self.arg._collect(seen)

    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return ~self.arg.eval(env, mask) & mask


@dataclass(frozen=True)
class _NAry(Expr):
    args: tuple[Expr, ...]

    def _collect(self, seen: dict[str, None]) -> None:
        for a in self.args:
            a._collect(seen)


@dataclass(frozen=True)
class And(_NAry):
    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return reduce(and_, (a.eval(env, mask) for a in self.args), mask)


@dataclass(frozen=True)
class Or(_NAry):
    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return reduce(or_, (a.eval(env, mask) for a in self.args), 0)


@dataclass(frozen=True)
class Xor(_NAry):
    def eval(self, env: dict[str, int], mask: int = 1) -> int:
        return reduce(xor, (a.eval(env, mask) for a in self.args), 0)


def make_and(args: list[Expr]) -> Expr:
    return args[0] if len(args) == 1 else And(tuple(args))


def make_or(args: list[Expr]) -> Expr:
    return args[0] if len(args) == 1 else Or(tuple(args))


# Precedencia para imprimir: mayor número = liga más fuerte.
_PREC = {Or: 1, Xor: 2, And: 3}
_SYM = {Or: " + ", Xor: " ⊕ ", And: "·"}


def _fmt(e: Expr, parent_prec: int) -> str:
    if isinstance(e, Const):
        return "1" if e.value else "0"
    if isinstance(e, Var):
        return e.name
    if isinstance(e, Not):
        inner = e.arg
        if isinstance(inner, (Var, Const)):
            return _fmt(inner, 4) + "'"
        return "(" + _fmt(inner, 0) + ")'"
    prec = _PREC[type(e)]
    s = _SYM[type(e)].join(_fmt(a, prec) for a in e.args)
    return f"({s})" if prec <= parent_prec else s
