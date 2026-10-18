"""Modelo de vista: del estado de la URL al contexto de las plantillas (§FRONTEND).

Todo se calcula con las mismas funciones que la API; aquí solo se ordena para
mostrar. Los tres ejes de §EJES llegan por separado a la plantilla.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from markupsafe import Markup

from ..bom import Bom, build_bom
from ..drc import DrcReport, Severity, run_drc
from ..logic.parser import ParseError, parse_equations
from ..models.catalog import Catalog
from ..render.chips import render_chips_svg
from ..render.schematic import render_schematic_svg
from ..techmap.mapper import MapReport, map_design
from .state import STRATEGY_LABELS, StateError, UiState

MAX_TRUTH_ROWS = 64

SEVERITY_ORDER = [
    (Severity.ERROR, "Errores", "err"),
    (Severity.WARNING, "Advertencias", "warn"),
    (Severity.NOT_EVALUABLE, "No evaluables", "ne"),
    (Severity.INFO, "Informativos", "info"),
]


@dataclass
class InputError:
    message: str
    line: str | None = None  # línea del texto donde está el error
    caret: int | None = None  # columna dentro de esa línea
    hint: str | None = None


@dataclass
class View:
    state: UiState
    query: str
    error: InputError | None = None
    report: MapReport | None = None
    drc: DrcReport | None = None
    bom: Bom | None = None
    data: dict[str, Any] = field(default_factory=dict)

    @property
    def has_result(self) -> bool:
        return self.report is not None and self.report.selected is not None


def build_view(state: UiState, catalog: Catalog) -> View:
    view = View(state=state, query=state.query())
    if not state.equations.strip():
        return view
    try:
        equations = parse_equations(state.equations)
    except ParseError as exc:
        view.error = _parse_error(exc)
        return view
    try:
        dont_cares = state.parsed_dont_cares()
        report = map_design(equations, catalog, dont_cares, state.map_options())
    except StateError as exc:
        view.error = InputError(str(exc))
        return view
    except ValueError as exc:  # límites de QM, salidas inexistentes, etc.
        view.error = InputError(str(exc))
        return view

    view.report = report
    sel = report.selected
    if sel is None or sel.design is None:
        view.error = InputError("ningún candidato es realizable con las celdas permitidas")
        return view
    design = sel.design
    view.drc = run_drc(design, catalog, state.bom_options())
    view.bom = build_bom(design, catalog, state.bom_options())
    mini = report.minimization
    title = ", ".join(mini.table.outputs)

    rows = mini.table.rows()
    view.data = {
        "title": title,
        "selected": sel,
        "strategy_label": STRATEGY_LABELS.get(sel.strategy, sel.strategy),
        "equivalent": sel.equivalent,  # verificado en map_design contra la especificación
        "n_rows": len(rows),
        "inputs": mini.inputs,
        "outputs": mini.table.outputs,
        "truth_rows": rows[:MAX_TRUTH_ROWS],
        "truth_truncated": len(rows) > MAX_TRUTH_ROWS,
        "minimization": [
            {
                "name": o.name,
                "original": str(o.original),
                "minterms": o.minterms,
                "dont_cares": o.dont_cares,
                "method": _method_label(o.result.trace.method),
                "primes": [str(p.to_expr(mini.inputs)) for p in o.result.trace.prime_implicants],
                "essential": [str(p.to_expr(mini.inputs)) for p in o.result.trace.essential],
                "minimized": str(o.minimized),
            }
            for o in mini.outputs
        ],
        "candidates": [
            {
                "source": c.source,
                "strategy": STRATEGY_LABELS.get(c.strategy, c.strategy),
                "ok": c.ok,
                "error": c.error,
                "ics": c.design.ic_count if c.design else None,
                "depth": c.design.netlist.depth() if c.design else None,
                "gates": len(c.design.netlist.gates) if c.design else None,
                "parts": c.design.parts() if c.design else {},
                "absorbed": len(c.absorbed),
                "selected": c is sel,
            }
            for c in report.candidates
        ],
        "chips": [
            {
                "ref": c.ref,
                "part": c.part,
                "kind": f"{catalog.chip(c.part).gates_per_package}×"
                f"{catalog.chip(c.part).function.value}{catalog.chip(c.part).inputs_per_gate}",
                "used": len(c.used_slots),
                "total": len(c.used_slots) + len(c.free_slots),
                "cap": view.bom.decoupling.get(c.ref, ""),
            }
            for c in design.chips
        ],
        "drc_groups": [
            {
                "title": label,
                "css": css,
                "findings": [f for f in view.drc.findings if f.severity is sev],
            }
            for sev, label, css in SEVERITY_ORDER
            if any(f.severity is sev for f in view.drc.findings)
        ],
        "drc_counts": {sev.value: view.drc.count(sev) for sev, _, _ in SEVERITY_ORDER},
        "schematic_svg": Markup(render_schematic_svg(design, view.bom, title)),
        "chips_svg": Markup(render_chips_svg(design, catalog, view.bom, title)),
    }
    return view


def _method_label(method: str) -> str:
    return {
        "trivial": "trivial",
        "essential": "solo esenciales",
        "petrick": "Petrick",
        "greedy": "cobertura voraz",
    }.get(method, method)


def _parse_error(exc: ParseError) -> InputError:
    """Ubica el error en su línea y columna, y sugiere la causa más común."""
    text, pos = exc.text, exc.pos
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    line = text[start : end if end != -1 else len(text)]
    message = str(exc).rsplit(" (posición", 1)[0]
    message = message[:1].upper() + message[1:]
    hint = None
    if "')'" in message:
        depth, opened = 0, None
        for i, ch in enumerate(text[:pos]):
            if ch == "(":
                depth += 1
                opened = i
            elif ch == ")":
                depth -= 1
        if depth > 0 and opened is not None:
            col = opened - (text.rfind("\n", 0, opened) + 1)
            hint = f"Falta cerrar el paréntesis abierto en la columna {col + 1}."
    return InputError(message=message, line=line, caret=pos - start, hint=hint)
