"""Circuitos dorados: el resultado de su mapeo está fijado en mapping_baseline.json."""

from __future__ import annotations

from ttl_designer.techmap.mapper import MapReport


def _sum_of_minterms(name: str, variables: list[str], minterms: list[int]) -> str:
    """``name = Σm(...)`` escrita como SOP de mintérminos completos (§CONVENCIONES)."""
    n = len(variables)
    terms = []
    for m in minterms:
        lits = [v if (m >> (n - 1 - i)) & 1 else f"{v}'" for i, v in enumerate(variables)]
        terms.append(" ".join(lits))
    return f"{name} = " + " + ".join(terms)


# BCD a 7 segmentos (cátodo común, segmento activo en alto); A es el MSB.
_SEGMENTS = {
    "a": [0, 2, 3, 5, 6, 7, 8, 9],
    "b": [0, 1, 2, 3, 4, 7, 8, 9],
    "c": [0, 1, 3, 4, 5, 6, 7, 8, 9],
    "d": [0, 2, 3, 5, 6, 8, 9],
    "e": [0, 2, 6, 8],
    "f": [0, 4, 5, 6, 8, 9],
    "g": [2, 3, 4, 5, 6, 8, 9],
}
_BCD_VARS = ["A", "B", "C", "D"]

CIRCUITS: dict[str, tuple[str, dict[str, list[int]]]] = {
    "sumador_completo": ("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)", {}),
    "comparador_2bits": (
        "GT = A1 B1' + A0 B0' (A1 ^ B1)'\n"
        "EQ = (A1 ^ B1)' (A0 ^ B0)'\n"
        "LT = A1' B1 + A0' B0 (A1 ^ B1)'",
        {},
    ),
    "mux_4a1": ("Y = S1' S0' D0 + S1' S0 D1 + S1 S0' D2 + S1 S0 D3", {}),
    "paridad_4bits": ("P = A ^ B ^ C ^ D", {}),
    "mayoria_3": ("M = A B + A C + B C", {}),
    "bcd_7seg": (
        "\n".join(_sum_of_minterms(s, _BCD_VARS, ms) for s, ms in _SEGMENTS.items()),
        {s: list(range(10, 16)) for s in _SEGMENTS},
    ),
}


def summarize(report: MapReport) -> dict[str, object]:
    sel = report.selected
    assert sel is not None and sel.design is not None
    d = sel.design
    return {
        "source": sel.source,
        "strategy": sel.strategy,
        "ic_count": d.ic_count,
        "depth": d.netlist.depth(),
        "gate_count": len(d.netlist.gates),
        "parts": d.parts(),
    }
