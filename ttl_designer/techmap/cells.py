"""Biblioteca de celdas: qué compuertas físicas hay disponibles y en qué chip.

Una celda es el par (función, número de entradas). Para cada celda se elige un
único chip del catálogo; colector abierto y Schmitt solo entran si se piden
explícitamente (§MAPEO).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models.catalog import Catalog, Chip, OutputType
from ..models.netlist import CONST0, CONST1, GateKind

Cell = tuple[GateKind, int]

# Valor de entrada que no altera la función: es el que recibe una entrada sobrante.
NEUTRAL: dict[GateKind, str] = {
    GateKind.AND: CONST1,
    GateKind.NAND: CONST1,
    GateKind.OR: CONST0,
    GateKind.NOR: CONST0,
    GateKind.XOR: CONST0,
    GateKind.XNOR: CONST0,
}


@dataclass(frozen=True)
class MapOptions:
    strategies: tuple[str, ...] = ("mixta", "nand", "nor", "nand+xor", "nor+xor")
    allow_open_collector: bool = False
    allow_schmitt: bool = False
    excluded_parts: frozenset[str] = field(default_factory=frozenset)


class CellLibrary:
    def __init__(self, catalog: Catalog, options: MapOptions):
        self.catalog = catalog
        self._by_cell: dict[Cell, Chip] = {}
        candidates = sorted(catalog.chips, key=lambda c: (_rank(c), c.part))
        for chip in candidates:
            if chip.part in options.excluded_parts:
                continue
            if chip.output_type is OutputType.OPEN_COLLECTOR and not options.allow_open_collector:
                continue
            if chip.schmitt_trigger and not options.allow_schmitt:
                continue
            cell = (GateKind(chip.function.value), chip.inputs_per_gate)
            self._by_cell.setdefault(cell, chip)

    def chip_for(self, cell: Cell) -> Chip | None:
        return self._by_cell.get(cell)

    def has(self, kind: GateKind, n: int) -> bool:
        return (kind, n) in self._by_cell

    def arities(self, kind: GateKind) -> list[int]:
        return sorted(n for k, n in self._by_cell if k is kind)

    def fit(self, kind: GateKind, n: int) -> int | None:
        """Menor número de entradas disponible ≥ n para esa función, o None."""
        sizes = [s for s in self.arities(kind) if s >= n]
        if not sizes:
            return None
        if kind.unary:
            return sizes[0] if n == 1 else None
        return sizes[0]

    def max_arity(self, kind: GateKind) -> int:
        sizes = self.arities(kind)
        return sizes[-1] if sizes else 0

    def chip(self, part: str) -> Chip:
        return self.catalog.chip(part)


def _rank(chip: Chip) -> int:
    """Preferencia entre chips de la misma celda: estándar antes que OC o Schmitt."""
    return (chip.output_type is OutputType.OPEN_COLLECTOR) * 2 + chip.schmitt_trigger
