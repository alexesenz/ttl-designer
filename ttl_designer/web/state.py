"""Estado de la interfaz en la URL (§FRONTEND): query string ↔ solicitud de mapeo.

El diseño completo viaja en la URL, así que se comparte copiando el enlace y no
hace falta base de datos. Este módulo solo traduce; el cálculo vive en el núcleo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlencode

from ..bom import BomOptions
from ..techmap.cells import MapOptions
from ..techmap.strategies import STRATEGIES

STRATEGY_LABELS = {
    "mixta": "mixta",
    "nand": "solo NAND",
    "nor": "solo NOR",
    "nand+xor": "NAND + XOR",
    "nor+xor": "NOR + XOR",
}
PACKAGES = ("DIP-14", "SOIC-14")
MAX_EQUATIONS_CHARS = 4000

_RANGE = re.compile(r"^\s*(\d+)\s*(?:-\s*(\d+))?\s*$")


class StateError(ValueError):
    """Un campo de la URL no se puede interpretar."""


@dataclass
class UiState:
    equations: str = ""
    dont_cares: str = ""  # "S: 1, 3, 10-15" una salida por línea
    strategies: list[str] = field(default_factory=lambda: list(STRATEGIES))
    package: str = "DIP-14"
    allow_open_collector: bool = False
    allow_schmitt: bool = False
    excluded: str = ""

    @classmethod
    def from_query(cls, q: dict[str, list[str]]) -> UiState:
        def one(key: str, default: str = "") -> str:
            vals = q.get(key)
            return vals[-1] if vals else default

        st = cls(
            equations=one("eq")[:MAX_EQUATIONS_CHARS],
            dont_cares=one("dc")[:MAX_EQUATIONS_CHARS],
            package=one("pkg", "DIP-14"),
            allow_open_collector=one("oc") == "1",
            allow_schmitt=one("st") == "1",
            excluded=one("ex")[:200],
        )
        # El formulario manda solo las estrategias marcadas; "f" indica que vino de él,
        # así que sin ninguna "s" el usuario las desmarcó todas.
        if "s" in q or "f" in q:
            st.strategies = [s for s in q.get("s", []) if s in STRATEGIES]
        if st.package not in PACKAGES:
            st.package = "DIP-14"
        return st

    def query(self) -> str:
        """Query string canónica para el enlace compartible y las descargas."""
        pairs: list[tuple[str, str]] = [("eq", self.equations)]
        if self.dont_cares.strip():
            pairs.append(("dc", self.dont_cares))
        if self.strategies != list(STRATEGIES):
            pairs += [("s", s) for s in self.strategies]
        if self.package != "DIP-14":
            pairs.append(("pkg", self.package))
        if self.allow_open_collector:
            pairs.append(("oc", "1"))
        if self.allow_schmitt:
            pairs.append(("st", "1"))
        if self.excluded.strip():
            pairs.append(("ex", self.excluded))
        return urlencode(pairs)

    def map_options(self) -> MapOptions:
        if not self.strategies:
            raise StateError("marca al menos una estrategia")
        excluded = frozenset(p.strip().upper() for p in self.excluded.split(",") if p.strip())
        return MapOptions(
            strategies=tuple(self.strategies),
            allow_open_collector=self.allow_open_collector,
            allow_schmitt=self.allow_schmitt,
            excluded_parts=frozenset(p if p.startswith("74") else f"74{p}" for p in excluded),
        )

    def bom_options(self) -> BomOptions:
        return BomOptions(package=self.package)

    def parsed_dont_cares(self) -> dict[str, list[int]]:
        """``S: 1, 3, 10-15`` por línea (o separadas por ``;``) → {"S": [1, 3, 10, …]}."""
        out: dict[str, list[int]] = {}
        for raw in re.split(r"[;\n]", self.dont_cares):
            line = raw.strip()
            if not line:
                continue
            if ":" not in line:
                raise StateError(f"don't-cares: falta ':' en «{line}» (formato: S: 1, 3, 10-15)")
            name, values = (x.strip() for x in line.split(":", 1))
            rows: list[int] = []
            for part in values.split(","):
                if not part.strip():
                    continue
                m = _RANGE.match(part)
                if not m:
                    raise StateError(f"don't-cares de {name}: «{part.strip()}» no es un índice")
                lo = int(m.group(1))
                hi = int(m.group(2)) if m.group(2) else lo
                if hi < lo or hi - lo > 65536:
                    raise StateError(f"don't-cares de {name}: rango inválido «{part.strip()}»")
                rows.extend(range(lo, hi + 1))
            out[name] = sorted(set(out.get(name, []) + rows))
        return out


EXAMPLES: list[tuple[str, str]] = [
    ("Sumador completo", "S = A ^ B ^ Ci\nCo = A B + Ci (A ^ B)"),
    ("Mux 4:1", "Y = S1' S0' D0 + S1' S0 D1 + S1 S0' D2 + S1 S0 D3"),
    ("Mayoría de 3", "M = A B + A C + B C"),
    ("Paridad de 4 bits", "P = A ^ B ^ C ^ D"),
    (
        "Comparador de 2 bits",
        "GT = A1 B1' + A0 B0' (A1 ^ B1)'\nEQ = (A1 ^ B1)' (A0 ^ B0)'\n"
        "LT = A1' B1 + A0' B0 (A1 ^ B1)'",
    ),
]


def example_links() -> list[tuple[str, str]]:
    return [(label, urlencode([("eq", eq)])) for label, eq in EXAMPLES]
