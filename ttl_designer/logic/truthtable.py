"""Tablas de verdad y conversión expresión ↔ minterms.

Convención de bits: la primera variable es el bit más significativo del índice
de fila, como en la notación habitual Σm(...) (§CONVENCIONES).
"""

from __future__ import annotations

from dataclasses import dataclass

from .ast import Expr

MAX_VARIABLES = 16


def input_vectors(n: int) -> tuple[list[int], int]:
    """Vectores bit-paralelos de cada variable para las 2**n filas.

    El bit ``r`` del vector de la variable ``i`` vale el bit ``n-1-i`` de ``r``.
    """
    if n > MAX_VARIABLES:
        raise ValueError(f"máximo {MAX_VARIABLES} variables, se recibieron {n}")
    rows = 1 << n
    mask = (1 << rows) - 1
    vectors = []
    for i in range(n):
        half = 1 << (n - 1 - i)
        period = half << 1
        # bloque de `half` ceros seguido de `half` unos, repetido rows/period veces
        block = ((1 << half) - 1) << half
        vectors.append(block * (mask // ((1 << period) - 1)))
    return vectors, mask


def ones(vector: int) -> list[int]:
    """Índices de los bits en 1 (filas donde la función vale 1)."""
    return [r for r, c in enumerate(reversed(bin(vector)[2:])) if c == "1"]


def minterms(expr: Expr, variables: list[str]) -> list[int]:
    missing = set(expr.variables()) - set(variables)
    if missing:
        raise ValueError(f"variables no declaradas: {', '.join(sorted(missing))}")
    vectors, mask = input_vectors(len(variables))
    return ones(expr.eval(dict(zip(variables, vectors, strict=True)), mask))


@dataclass
class TruthTable:
    inputs: list[str]
    outputs: list[str]
    # columnas de salida como vectores bit-paralelos, una por salida
    columns: dict[str, int]

    @property
    def n_rows(self) -> int:
        return 1 << len(self.inputs)

    def rows(self) -> list[tuple[list[int], list[int]]]:
        n = len(self.inputs)
        out = []
        for r in range(self.n_rows):
            ins = [(r >> (n - 1 - i)) & 1 for i in range(n)]
            outs = [(self.columns[o] >> r) & 1 for o in self.outputs]
            out.append((ins, outs))
        return out

    def minterms(self, output: str) -> list[int]:
        return ones(self.columns[output])


def collect_inputs(equations: list[tuple[str, Expr]]) -> list[str]:
    """Variables de entrada en orden alfabético, excluyendo nombres de salida."""
    outputs = {n for n, _ in equations}
    names = {v for _, e in equations for v in e.variables()}
    feedback = names & outputs
    if feedback:
        raise ValueError(
            "una salida no puede usarse como entrada en un circuito combinacional: "
            + ", ".join(sorted(feedback))
        )
    return sorted(names)


def truth_table(equations: list[tuple[str, Expr]], inputs: list[str] | None = None) -> TruthTable:
    inputs = inputs if inputs is not None else collect_inputs(equations)
    vectors, mask = input_vectors(len(inputs))
    env = dict(zip(inputs, vectors, strict=True))
    columns = {name: expr.eval(env, mask) for name, expr in equations}
    return TruthTable(inputs, [n for n, _ in equations], columns)
