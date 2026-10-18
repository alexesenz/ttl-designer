from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..logic.build import build_netlist
from ..logic.parser import ParseError, parse_equations
from ..logic.qm import Implicant, minimize
from ..logic.truthtable import collect_inputs, truth_table
from ..sim.functional import check_equivalence
from .schemas import AnalyzeRequest, AnalyzeResponse, ImplicantOut, MinimizationOut

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
        inputs = collect_inputs(equations)
        table = truth_table(equations, inputs)
    except (ParseError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    unknown = set(req.dont_cares) - set(table.outputs)
    if unknown:
        raise HTTPException(422, f"don't-cares para salidas inexistentes: {sorted(unknown)}")

    minimized = []
    report = []
    for name, expr in equations:
        dcs = set(req.dont_cares.get(name, []))
        ms = [m for m in table.minterms(name) if m not in dcs]
        try:
            res = minimize(len(inputs), ms, sorted(dcs))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        min_expr = res.to_expr(inputs)
        minimized.append((name, min_expr))
        t = res.trace
        report.append(
            MinimizationOut(
                output=name,
                original=str(expr),
                minterms=ms,
                dont_cares=sorted(dcs),
                prime_implicants=[_imp(p, inputs) for p in t.prime_implicants],
                essential=[_imp(p, inputs) for p in t.essential],
                method=t.method,
                minimized=str(min_expr),
            )
        )

    netlist = build_netlist(minimized)
    equivalent = not check_equivalence(netlist, equations, req.dont_cares)

    rows = [ins + outs for ins, outs in table.rows()]
    return AnalyzeResponse(
        inputs=inputs,
        outputs=table.outputs,
        truth_table=rows,
        minimization=report,
        netlist=netlist,
        logic_depth=netlist.depth(),
        equivalent=equivalent,
    )
