"""Esquema del catálogo de chips 74LS (library/ttl_ls_catalog.json).

Refleja el contrato entregado al agente que construye el catálogo; las
validaciones de pinout y de tiempos son las mismas que se le exigieron.
Política de fuentes y de datos faltantes: §CATALOGO; especificación: CATALOG_CONTRACT.md.
"""

from __future__ import annotations

import json
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GateFunction(StrEnum):
    NAND = "NAND"
    NOR = "NOR"
    AND = "AND"
    OR = "OR"
    NOT = "NOT"
    XOR = "XOR"
    XNOR = "XNOR"


class OutputType(StrEnum):
    TOTEM_POLE = "totem_pole"
    OPEN_COLLECTOR = "open_collector"


class Lifecycle(StrEnum):
    ACTIVE = "active"
    NRND = "nrnd"
    OBSOLETE = "obsolete"
    UNKNOWN = "unknown"


class FamilyDefaults(_Strict):
    vcc_min_V: float | None = None
    vcc_nom_V: float | None = None
    vcc_max_V: float | None = None
    vih_min_V: float | None = None
    vil_max_V: float | None = None
    voh_min_V: float | None = None
    voh_test_ioh_mA: float | None = None
    vol_max_V: float | None = None
    vol_test_iol_mA: float | None = None
    iih_max_uA: float | None = None
    iil_max_mA: float | None = None
    ioh_max_mA: float | None = None
    iol_max_mA: float | None = None
    fanout_ls_loads: int | None = None
    unused_input_recommendation: str | None = None
    decoupling_recommendation: str | None = None
    sources: list[str] = Field(default_factory=list)


class PowerPins(_Strict):
    vcc: int
    gnd: int


class GatePins(_Strict):
    id: str
    inputs: list[int]
    output: int


class Schmitt(_Strict):
    vt_pos_typ_V: float | None = None
    vt_neg_typ_V: float | None = None
    hysteresis_typ_V: float | None = None


class Electrical(_Strict):
    icch_typ_mA: float | None = None
    icch_max_mA: float | None = None
    iccl_typ_mA: float | None = None
    iccl_max_mA: float | None = None
    ios_min_mA: float | None = None
    ios_max_mA: float | None = None
    iil_max_mA: float | None = None
    schmitt: Schmitt | None = None


class TimingConditions(_Strict):
    cl_pF: float | None = None
    rl_ohm: float | None = None
    vcc_V: float | None = None
    temp_C: float | None = None


class Timing(_Strict):
    tplh_typ_ns: float | None = None
    tplh_max_ns: float | None = None
    tphl_typ_ns: float | None = None
    tphl_max_ns: float | None = None
    test_conditions: TimingConditions = Field(default_factory=TimingConditions)

    @model_validator(mode="after")
    def _typ_le_max(self) -> Timing:
        for edge in ("tplh", "tphl"):
            typ = getattr(self, f"{edge}_typ_ns")
            mx = getattr(self, f"{edge}_max_ns")
            if typ is not None and mx is not None and typ > mx:
                raise ValueError(f"{edge}: típico {typ} ns mayor que máximo {mx} ns")
        return self


class Package(_Strict):
    code: str
    suffix_ti: str | None = None


class OrderablePart(_Strict):
    manufacturer: str
    part_number: str
    package: str
    lifecycle: Lifecycle = Lifecycle.UNKNOWN


class Datasheet(_Strict):
    manufacturer: str
    url: str
    revision: str | None = None


class Chip(_Strict):
    part: str
    description: str
    function: GateFunction
    inputs_per_gate: int = Field(ge=1)
    gates_per_package: int = Field(ge=1)
    output_type: OutputType
    schmitt_trigger: bool = False
    package_pins: int = Field(ge=8)
    power_pins: PowerPins
    nc_pins: list[int] = Field(default_factory=list)
    gates: list[GatePins]
    electrical: Electrical = Field(default_factory=Electrical)
    timing: Timing = Field(default_factory=Timing)
    packages: list[Package] = Field(default_factory=list)
    orderable_parts: list[OrderablePart] = Field(default_factory=list)
    datasheets: list[Datasheet] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    unverified: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_pinout(self) -> Chip:
        p = self.part
        if len(self.gates) != self.gates_per_package:
            raise ValueError(
                f"{p}: {len(self.gates)} compuertas, se declararon {self.gates_per_package}"
            )
        if self.function is GateFunction.NOT and self.inputs_per_gate != 1:
            raise ValueError(f"{p}: un inversor tiene 1 entrada por compuerta")
        used: list[int] = [self.power_pins.vcc, self.power_pins.gnd, *self.nc_pins]
        for g in self.gates:
            if len(g.inputs) != self.inputs_per_gate:
                raise ValueError(
                    f"{p}/{g.id}: {len(g.inputs)} entradas, se esperaban {self.inputs_per_gate}"
                )
            used += [*g.inputs, g.output]
        dup = sorted({x for x in used if used.count(x) > 1})
        if dup:
            raise ValueError(f"{p}: pines repetidos {dup}")
        expected = set(range(1, self.package_pins + 1))
        if set(used) != expected:
            missing = sorted(expected - set(used))
            extra = sorted(set(used) - expected)
            raise ValueError(f"{p}: pinout incompleto; faltan {missing}, fuera de rango {extra}")
        return self


class Source(_Strict):
    title: str
    manufacturer: str | None = None
    url: str
    revision: str | None = None
    accessed: str | None = None


class Catalog(_Strict):
    schema_version: str
    family: str
    generated: str | None = None
    family_defaults: FamilyDefaults
    chips: list[Chip]
    source_index: dict[str, Source] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _check_refs(self) -> Catalog:
        parts = [c.part for c in self.chips]
        dup = sorted({x for x in parts if parts.count(x) > 1})
        if dup:
            raise ValueError(f"chips repetidos: {dup}")
        refs = set(self.family_defaults.sources)
        for c in self.chips:
            refs |= set(c.sources)
        unknown = sorted(refs - set(self.source_index))
        if unknown:
            raise ValueError(f"fuentes citadas sin entrada en source_index: {unknown}")
        return self

    def chip(self, part: str) -> Chip:
        for c in self.chips:
            if c.part == part:
                return c
        raise KeyError(part)


DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[2] / "library" / "ttl_ls_catalog.json"


def load_catalog(path: Path | str = DEFAULT_CATALOG_PATH) -> Catalog:
    with open(path, encoding="utf-8") as f:
        return Catalog.model_validate(json.load(f))
