from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException

from ..logic.build import build_netlist
from ..logic.minimize import minimize_equations
from ..logic.parser import ParseError, parse_equations
from ..logic.qm import Implicant
from ..models.catalog import Catalog, load_catalog
from ..sim.functional import check_equivalence
from ..techmap.cells import MapOptions
from ..techmap.mapper import Candidate, map_design
from ..techmap.strategies import STRATEGIES
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CandidateOut,
    ImplicantOut,
    MapRequest,
    MapResponse,
    MinimizationOut,
)

router = APIRouter(prefix="/api")


def _imp(imp: Implicant, variables: list[str]) -> ImplicantOut:
    n = len(variables)
    return ImplicantOut(
        pattern=imp.pattern(n), term=str(imp.to_expr(variables)), minterms=imp.minterms(n)
    )


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest) -> AnalyzeResponse:
    try:
        equations = parse_equations(req.equations)
        mini = minimize_equations(equations, req.dont_cares)
    except (ParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    inputs = mini.inputs
    report = [
        MinimizationOut(
            output=o.name,
            original=str(o.original),
            minterms=o.minterms,
            dont_cares=o.dont_cares,
            prime_implicants=[_imp(p, inputs) for p in o.result.trace.prime_implicants],
            essential=[_imp(p, inputs) for p in o.result.trace.essential],
            method=o.result.trace.method,
            minimized=str(o.minimized),
        )
        for o in mini.outputs
    ]

    netlist = build_netlist(mini.equations)
    equivalent = not check_equivalence(netlist, equations, req.dont_cares)

    rows = [ins + outs for ins, outs in mini.table.rows()]
    return AnalyzeResponse(
        inputs=inputs,
        outputs=mini.table.outputs,
        truth_table=rows,
        minimization=report,
        netlist=netlist,
        logic_depth=netlist.depth(),
        equivalent=equivalent,
    )


@lru_cache(maxsize=1)
def _catalog() -> Catalog:
    return load_catalog()


def _candidate_out(c: Candidate) -> CandidateOut:
    d = c.design
    return CandidateOut(
        source=c.source,
        strategy=c.strategy,
        ic_count=d.ic_count if d else None,
        depth=d.netlist.depth() if d else None,
        gate_count=len(d.netlist.gates) if d else None,
        parts=d.parts() if d else {},
        absorbed=len(c.absorbed),
        equivalent=c.equivalent,
        error=c.error,
    )


@router.post("/map", response_model=MapResponse)
def map_circuit(req: MapRequest) -> MapResponse:
    """Mapea a chips 74LS: todas las estrategias, elige por número de ICs (§COSTO-IC)."""
    strategies = tuple(req.strategies) if req.strategies else STRATEGIES
    unknown = sorted(set(strategies) - set(STRATEGIES))
    if unknown:
        raise HTTPException(422, f"estrategias desconocidas: {unknown}; válidas: {STRATEGIES}")
    try:
        catalog = _catalog()
    except FileNotFoundError as exc:
        raise HTTPException(503, "catálogo de chips no disponible") from exc
    options = MapOptions(
        strategies=strategies,
        allow_open_collector=req.allow_open_collector,
        allow_schmitt=req.allow_schmitt,
        excluded_parts=frozenset(req.excluded_parts),
    )
    try:
        equations = parse_equations(req.equations)
        report = map_design(equations, catalog, req.dont_cares, options)
    except (ParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    sel = report.selected
    design = sel.design if sel else None
    return MapResponse(
        inputs=report.minimization.inputs,
        outputs=report.minimization.table.outputs,
        candidates=[_candidate_out(c) for c in report.candidates],
        selected=_candidate_out(sel) if sel else None,
        design=design,
        connections=design.connections() if design else {},
        warnings=report.warnings,
    )
