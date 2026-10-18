"""Lista de materiales derivada del diseño físico (§BOM).

El BOM no guarda estado propio: se recalcula del netlist físico y del catálogo
(§NETLIST). Lo que no se puede resolver con datos verificados va a ``gaps``, el
tercer eje de §EJES, y nunca se rellena con un valor supuesto.
"""

from __future__ import annotations

import csv
import io
from enum import StrEnum

from pydantic import BaseModel, Field

from .electrical import group_pullups, max_inputs_per_pullup, pullup_pins
from .models.catalog import Catalog, Chip, Lifecycle
from .models.physical import PhysicalDesign, TieReason, TieTarget

PREFERRED_MANUFACTURER = "Texas Instruments"


class BomOptions(BaseModel):
    package: str = "DIP-14"
    pullup_ohm: float = Field(default=1000, gt=0)
    decoupling_nF: float = Field(default=100, gt=0)
    bulk_uF: float | None = Field(default=10, gt=0)


class LineKind(StrEnum):
    IC = "ic"
    CAPACITOR = "capacitor"
    RESISTOR = "resistencia"


class BomLine(BaseModel):
    refs: list[str]
    qty: int
    kind: LineKind
    value: str | None
    description: str
    package: str | None = None
    manufacturer: str | None = None
    manufacturer_pn: str | None = None
    datasheet: str | None = None
    notes: list[str] = Field(default_factory=list)


class GapKind(StrEnum):
    NO_ORDERABLE = "sin_parte_comercial"
    LIFECYCLE = "ciclo_de_vida"
    SINGLE_SOURCE = "fuente_unica"
    UNVERIFIED = "datos_sin_verificar"
    UNSIZED = "valor_sin_dimensionar"


class BomGap(BaseModel):
    target: str
    kind: GapKind
    message: str


class Bom(BaseModel):
    options: BomOptions
    lines: list[BomLine]
    gaps: list[BomGap]
    gnd_pins: list[str]  # se cablean a GND; no llevan componente

    def to_csv(self) -> str:
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(
            [
                "Referencias",
                "Cantidad",
                "Tipo",
                "Valor",
                "Descripción",
                "Encapsulado",
                "Fabricante",
                "Número de parte",
                "Datasheet",
                "Notas",
            ]
        )
        for ln in self.lines:
            w.writerow(
                [
                    " ".join(ln.refs),
                    ln.qty,
                    ln.kind.value,
                    ln.value or "",
                    ln.description,
                    ln.package or "",
                    ln.manufacturer or "",
                    ln.manufacturer_pn or "",
                    ln.datasheet or "",
                    "; ".join(ln.notes),
                ]
            )
        return buf.getvalue()


def build_bom(design: PhysicalDesign, catalog: Catalog, options: BomOptions | None = None) -> Bom:
    options = options or BomOptions()
    lines: list[BomLine] = []
    gaps: list[BomGap] = []

    by_part: dict[str, list[str]] = {}
    for c in design.chips:
        by_part.setdefault(c.part, []).append(c.ref)
    for part, refs in by_part.items():
        line, line_gaps = _ic_line(catalog.chip(part), refs, options.package)
        lines.append(line)
        gaps += line_gaps

    smd = not options.package.startswith("DIP")
    passive_pkg = "SMD 0805" if smd else "THT"

    if design.chips:
        caps = [f"C{i}" for i in range(1, len(design.chips) + 1)]
        lines.append(
            BomLine(
                refs=caps,
                qty=len(caps),
                kind=LineKind.CAPACITOR,
                value=f"{options.decoupling_nF:g} nF",
                description="Capacitor cerámico de desacople, ≥16 V, junto al pin Vcc de cada IC",
                package=passive_pkg,
                notes=[
                    f"{cap}: {c.ref} pin {c.vcc_pin}–{c.gnd_pin}"
                    for cap, c in zip(caps, design.chips, strict=True)
                ],
            )
        )
        if options.bulk_uF is not None:
            ref = f"C{len(caps) + 1}"
            lines.append(
                BomLine(
                    refs=[ref],
                    qty=1,
                    kind=LineKind.CAPACITOR,
                    value=f"{options.bulk_uF:g} µF",
                    description="Capacitor electrolítico de entrada de alimentación, ≥16 V",
                    package=passive_pkg,
                    notes=[f"{ref}: entre Vcc y GND en la entrada de la placa"],
                )
            )

    r_n = 0
    per_group = max_inputs_per_pullup(catalog, options.pullup_ohm)
    groups = group_pullups(pullup_pins(design), per_group)
    if groups:
        refs = [f"R{r_n + i}" for i in range(1, len(groups) + 1)]
        r_n += len(groups)
        lines.append(
            BomLine(
                refs=refs,
                qty=len(refs),
                kind=LineKind.RESISTOR,
                value=_ohm(options.pullup_ohm),
                description="Pull-up a Vcc de entradas fijas en alto (§MAPEO)",
                package=passive_pkg,
                notes=[f"{r}: {', '.join(g)}" for r, g in zip(refs, groups, strict=True)],
            )
        )
        if per_group is None:
            gaps.append(
                BomGap(
                    target=refs[0],
                    kind=GapKind.UNSIZED,
                    message="no se pudo calcular cuántas entradas sostiene un "
                    "pull-up: faltan Vcc mín, VIH mín o IIH en el catálogo",
                )
            )

    oc_outputs = [f"{t.ref}.{t.pin}" for t in design.ties if t.reason is TieReason.OPEN_COLLECTOR]
    if oc_outputs:
        refs = [f"R{r_n + i}" for i in range(1, len(oc_outputs) + 1)]
        lines.append(
            BomLine(
                refs=refs,
                qty=len(refs),
                kind=LineKind.RESISTOR,
                value=None,
                description="Pull-up de salida de colector abierto",
                package=passive_pkg,
                notes=[f"{r}: {p}" for r, p in zip(refs, oc_outputs, strict=True)],
            )
        )
        gaps.append(
            BomGap(
                target=", ".join(refs),
                kind=GapKind.UNSIZED,
                message="valor sin dimensionar: el catálogo no tiene campo para la corriente de "
                "fuga en alto de las salidas de colector abierto (ver library/SOURCES.md)",
            )
        )

    gnd = sorted({f"{t.ref}.{t.pin}" for t in design.ties if t.to is TieTarget.GND})
    return Bom(options=options, lines=lines, gaps=gaps, gnd_pins=gnd)


def _ic_line(chip: Chip, refs: list[str], package: str) -> tuple[BomLine, list[BomGap]]:
    gaps: list[BomGap] = []
    candidates = [o for o in chip.orderable_parts if o.package == package]
    candidates.sort(
        key=lambda o: (
            o.lifecycle is not Lifecycle.ACTIVE,
            o.manufacturer != PREFERRED_MANUFACTURER,
            o.part_number,
        )
    )
    chosen = candidates[0] if candidates else None
    if chosen is None:
        gaps.append(
            BomGap(
                target=chip.part,
                kind=GapKind.NO_ORDERABLE,
                message=f"el catálogo no tiene parte comercial en {package}",
            )
        )
    elif chosen.lifecycle is not Lifecycle.ACTIVE:
        gaps.append(
            BomGap(
                target=chip.part,
                kind=GapKind.LIFECYCLE,
                message=f"{chosen.part_number}: ciclo de vida '{chosen.lifecycle}'; "
                "confirmar disponibilidad",
            )
        )
    if len({d.manufacturer for d in chip.datasheets}) < 2:
        gaps.append(
            BomGap(
                target=chip.part,
                kind=GapKind.SINGLE_SOURCE,
                message="datos contrastados con un solo fabricante",
            )
        )
    if chip.unverified:
        gaps.append(
            BomGap(
                target=chip.part,
                kind=GapKind.UNVERIFIED,
                message=f"{len(chip.unverified)} campos sin verificar: "
                + ", ".join(chip.unverified),
            )
        )
    datasheet = next(
        (d.url for d in chip.datasheets if chosen and d.manufacturer == chosen.manufacturer),
        chip.datasheets[0].url if chip.datasheets else None,
    )
    line = BomLine(
        refs=refs,
        qty=len(refs),
        kind=LineKind.IC,
        value=chip.part,
        description=chip.description,
        package=package,
        manufacturer=chosen.manufacturer if chosen else None,
        manufacturer_pn=chosen.part_number if chosen else None,
        datasheet=datasheet,
    )
    return line, gaps


def _ohm(r: float) -> str:
    if r >= 1e6:
        return f"{r / 1e6:g} MΩ"
    if r >= 1e3:
        return f"{r / 1e3:g} kΩ"
    return f"{r:g} Ω"
