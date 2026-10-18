"""Orquestador del mapeo: candidatos por fuente × estrategia y selección (§COSTO-IC).

Cada candidato pasa la verificación de equivalencia contra la especificación;
uno que no la pasa se descarta y se reporta, nunca se elige (§EJES).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..logic.ast import Expr
from ..logic.build import build_netlist
from ..logic.minimize import Minimization, minimize_equations
from ..models.catalog import Catalog
from ..models.physical import PhysicalDesign
from ..sim.functional import check_equivalence
from .cells import CellLibrary, MapOptions
from .packing import Rehost, absorb_spares, pack
from .strategies import STRATEGIES, MappingError, map_netlist

SOURCES = ("minimizada", "original")


@dataclass
class Candidate:
    source: str
    strategy: str
    design: PhysicalDesign | None = None
    absorbed: list[Rehost] = field(default_factory=list)
    equivalent: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.design is not None and self.equivalent and self.error is None

    def cost(self) -> tuple[int, int, int, int, int]:
        """Orden lexicográfico de §COSTO-IC; desempate determinista por estrategia y fuente."""
        assert self.design is not None
        d = self.design
        return (
            d.ic_count,
            d.netlist.depth(),
            len(d.netlist.gates),
            _index(self.strategy),
            SOURCES.index(self.source),
        )


@dataclass
class MapReport:
    minimization: Minimization
    candidates: list[Candidate]
    selected: Candidate | None
    warnings: list[str]


def _index(strategy: str) -> int:
    return STRATEGIES.index(strategy) if strategy in STRATEGIES else len(STRATEGIES)


def map_design(
    equations: list[tuple[str, Expr]],
    catalog: Catalog,
    dont_cares: dict[str, list[int]] | None = None,
    options: MapOptions | None = None,
) -> MapReport:
    options = options or MapOptions()
    dont_cares = dont_cares or {}
    lib = CellLibrary(catalog, options)
    mini = minimize_equations(equations, dont_cares)
    sources = {
        "minimizada": build_netlist(mini.equations, inputs=mini.inputs),
        "original": build_netlist(equations, inputs=mini.inputs),
    }

    candidates: list[Candidate] = []
    for source, logic in sources.items():
        for strategy in options.strategies:
            cand = Candidate(source=source, strategy=strategy)
            try:
                mapped = map_netlist(logic, strategy, lib)
                mapped, cand.absorbed = absorb_spares(mapped, lib)
                cand.design = pack(mapped, lib)
            except MappingError as exc:
                cand.error = str(exc)
            else:
                cand.equivalent = not check_equivalence(mapped, equations, dont_cares)
                if not cand.equivalent:
                    cand.error = "el circuito mapeado no es equivalente a la especificación"
            candidates.append(cand)

    valid = [c for c in candidates if c.ok]
    selected = min(valid, key=Candidate.cost) if valid else None
    # Los datos sin verificar de los chips usados son huecos del BOM (§BOM), no del mapeo.
    warnings = [] if selected else ["ningún candidato es realizable"]
    return MapReport(mini, candidates, selected, warnings)
