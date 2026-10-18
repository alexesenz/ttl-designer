"""Datos eléctricos derivados del catálogo, compartidos por el BOM y el DRC.

Solo se calcula a partir de valores verificados del catálogo. Si falta uno, el
resultado es ``None`` y quien lo consume lo declara como no evaluable (§CATALOGO).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import floor

from .models.catalog import Catalog, Chip
from .models.physical import PhysicalDesign, TieReason, TieTarget


@dataclass(frozen=True)
class InputLoad:
    """Carga que impone una entrada LS: |IIL| en bajo (mA) e IIH en alto (µA)."""

    iil_mA: float | None
    iih_uA: float | None
    standard: bool  # True si es la carga de familia; False si el chip declara otra


def input_load(chip: Chip, catalog: Catalog) -> InputLoad:
    fam = catalog.family_defaults
    fam_iil = abs(fam.iil_max_mA) if fam.iil_max_mA is not None else None
    if chip.electrical.iil_max_mA is None:
        # El contrato pide poblar el campo del chip solo si difiere de la familia.
        return InputLoad(fam_iil, fam.iih_max_uA, standard=True)
    iil = abs(chip.electrical.iil_max_mA)
    if fam_iil is not None and iil == fam_iil:
        return InputLoad(iil, fam.iih_max_uA, standard=True)
    # Entrada no estándar: el esquema no tiene IIH por chip y no se escala por inferencia.
    return InputLoad(iil, None, standard=False)


def max_inputs_per_pullup(catalog: Catalog, r_ohm: float) -> int | None:
    """Entradas que un pull-up de ``r_ohm`` sostiene sobre VIH mín con Vcc mín.

    Vcc_min − n·IIH·R ≥ VIH_min  →  n ≤ (Vcc_min − VIH_min) / (IIH·R)
    """
    fam = catalog.family_defaults
    if fam.vcc_min_V is None or fam.vih_min_V is None or not fam.iih_max_uA:
        return None
    n = floor((fam.vcc_min_V - fam.vih_min_V) / (fam.iih_max_uA * 1e-6 * r_ohm))
    return max(n, 1)


def pullup_pins(design: PhysicalDesign) -> list[str]:
    """Pines de entrada que van a nivel alto por resistencia (no salidas OC)."""
    pins = {
        f"{t.ref}.{t.pin}"
        for t in design.ties
        if t.to is TieTarget.PULLUP and t.reason is not TieReason.OPEN_COLLECTOR
    }
    return sorted(pins, key=pin_sort_key)


def pin_sort_key(pin: str) -> tuple[int, int]:
    ref, num = pin.split(".")
    return int(ref[1:]), int(num)


def group_pullups(pins: list[str], per_group: int | None) -> list[list[str]]:
    if not pins:
        return []
    if per_group is None:
        return [pins]
    return [pins[i : i + per_group] for i in range(0, len(pins), per_group)]
