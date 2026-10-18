"""Minimización por salida: ecuaciones → ecuaciones SOP mínimas con su traza QM."""

from __future__ import annotations

from dataclasses import dataclass

from .ast import Expr
from .qm import QMResult, minimize
from .truthtable import TruthTable, collect_inputs, truth_table


@dataclass
class MinimizedOutput:
    name: str
    original: Expr
    minimized: Expr
    minterms: list[int]
    dont_cares: list[int]
    result: QMResult


@dataclass
class Minimization:
    inputs: list[str]
    table: TruthTable
    outputs: list[MinimizedOutput]

    @property
    def equations(self) -> list[tuple[str, Expr]]:
        return [(o.name, o.minimized) for o in self.outputs]


def minimize_equations(
    equations: list[tuple[str, Expr]], dont_cares: dict[str, list[int]] | None = None
) -> Minimization:
    """Minimiza cada salida respetando sus don't-cares (índices Σm, §CONVENCIONES)."""
    dont_cares = dont_cares or {}
    inputs = collect_inputs(equations)
    table = truth_table(equations, inputs)
    unknown = set(dont_cares) - set(table.outputs)
    if unknown:
        raise ValueError(f"don't-cares para salidas inexistentes: {sorted(unknown)}")

    outputs = []
    for name, expr in equations:
        dcs = sorted(set(dont_cares.get(name, [])))
        dc_set = set(dcs)
        ms = [m for m in table.minterms(name) if m not in dc_set]
        res = minimize(len(inputs), ms, dcs)
        outputs.append(MinimizedOutput(name, expr, res.to_expr(inputs), ms, dcs, res))
    return Minimization(inputs, table, outputs)
