"""Chequeo eléctrico (DRC) del diseño físico (§DRC).

Es el segundo eje de §EJES: independiente de la corrección lógica y de los
huecos del BOM. Cada regla compara contra límites del catálogo; si falta un
dato, el resultado es ``no_evaluable`` y nunca un valor supuesto (§CATALOGO).
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from .bom import BomOptions
from .electrical import (
    group_pullups,
    input_load,
    max_inputs_per_pullup,
    pin_sort_key,
    pullup_pins,
)
from .models.catalog import Catalog, OutputType
from .models.netlist import CONSTANT_NETS
from .models.physical import PhysicalDesign


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "advertencia"
    INFO = "info"
    NOT_EVALUABLE = "no_evaluable"


class Finding(BaseModel):
    rule: str
    severity: Severity
    target: str
    message: str


class NetLoad(BaseModel):
    net: str
    driver: str  # "U1.3" o "externa"
    load_pins: list[str]
    iil_total_mA: float | None
    iih_total_uA: float | None
    iol_limit_mA: float | None
    ioh_limit_mA: float | None


class PowerBudget(BaseModel):
    icc_max_mA: float  # suma de los chips con dato
    power_max_mW: float | None  # con Vcc máx
    per_chip_mA: dict[str, float | None]
    complete: bool  # False si algún chip no tiene ICC verificado


class DrcReport(BaseModel):
    ok: bool  # sin errores; no_evaluable no cuenta como error ni como éxito
    findings: list[Finding] = Field(default_factory=list)
    loads: list[NetLoad] = Field(default_factory=list)
    power: PowerBudget

    def count(self, severity: Severity) -> int:
        return sum(f.severity is severity for f in self.findings)


def run_drc(
    design: PhysicalDesign, catalog: Catalog, options: BomOptions | None = None
) -> DrcReport:
    options = options or BomOptions()
    findings: list[Finding] = []
    fam = catalog.family_defaults
    chips = {c.ref: catalog.chip(c.part) for c in design.chips}
    gates = {g.id: g for g in design.netlist.gates}

    # --- conectividad: cada red con sus drivers y sus cargas -----------------
    drivers: dict[str, list[str]] = {}
    loads: dict[str, list[str]] = {}
    for p in design.placements:
        g = gates[p.gate_id]
        drivers.setdefault(g.output, []).append(f"{p.ref}.{p.output_pin}")
        for net, pin in zip(g.inputs, p.input_pins, strict=True):
            if net not in CONSTANT_NETS:
                loads.setdefault(net, []).append(f"{p.ref}.{pin}")
    for name in design.netlist.inputs:
        drivers.setdefault(name, []).append("externa")

    # --- entradas flotantes --------------------------------------------------
    tied = {(t.ref, t.pin) for t in design.ties}
    connected = {(p.ref, pin) for p in design.placements for pin in p.input_pins}
    for c in design.chips:
        for slot in chips[c.ref].gates:
            for pin in slot.inputs:
                if (c.ref, pin) not in tied and (c.ref, pin) not in connected:
                    findings.append(
                        Finding(
                            rule="entrada_flotante",
                            severity=Severity.ERROR,
                            target=f"{c.ref}.{pin}",
                            message="entrada sin conexión ni nivel fijo",
                        )
                    )

    # --- salidas en conflicto ------------------------------------------------
    for net, ds in drivers.items():
        if len(ds) > 1:
            all_oc = all(
                d != "externa" and chips[d.split(".")[0]].output_type is OutputType.OPEN_COLLECTOR
                for d in ds
            )
            if not all_oc:
                findings.append(
                    Finding(
                        rule="salidas_en_conflicto",
                        severity=Severity.ERROR,
                        target=net,
                        message=f"varios drivers: {', '.join(ds)}",
                    )
                )

    # --- fan-out por red -----------------------------------------------------
    iol = abs(fam.iol_max_mA) if fam.iol_max_mA is not None else None
    ioh = abs(fam.ioh_max_mA) if fam.ioh_max_mA is not None else None
    net_loads: list[NetLoad] = []
    nonstandard: set[str] = set()
    for net, pins in sorted(loads.items()):
        pins = sorted(pins, key=pin_sort_key)
        il = [input_load(chips[p.split(".")[0]], catalog) for p in pins]
        iil_tot = (
            round(sum(x.iil_mA for x in il if x.iil_mA is not None), 4)
            if all(x.iil_mA is not None for x in il)
            else None
        )
        iih_vals = [x.iih_uA for x in il]
        iih_tot = (
            round(sum(v for v in iih_vals if v is not None), 4) if None not in iih_vals else None
        )
        for load_pin, x in zip(pins, il, strict=True):
            if not x.standard:
                nonstandard.add(chips[load_pin.split(".")[0]].part)
        driver = drivers.get(net, ["?"])[0]
        external = driver == "externa"
        oc = not external and chips[driver.split(".")[0]].output_type is OutputType.OPEN_COLLECTOR
        nl = NetLoad(
            net=net,
            driver=driver,
            load_pins=pins,
            iil_total_mA=iil_tot,
            iih_total_uA=iih_tot,
            iol_limit_mA=None if external else iol,
            ioh_limit_mA=None if external or oc else ioh,
        )
        net_loads.append(nl)
        if external:
            findings.append(
                Finding(
                    rule="entrada_externa",
                    severity=Severity.INFO,
                    target=net,
                    message=f"{len(pins)} entradas LS; el driver externo debe absorber "
                    f"{_fmt(iil_tot, 'mA')} en bajo y entregar {_fmt(iih_tot, 'µA')} en alto",
                )
            )
            continue
        findings += _fanout_findings(nl, oc)

    for part in sorted(nonstandard):
        findings.append(
            Finding(
                rule="carga_no_estandar",
                severity=Severity.WARNING,
                target=part,
                message="sus entradas no son una carga LS estándar (IIL distinto de la "
                "familia) y el catálogo no tiene IIH por chip: el fan-out en alto queda "
                "no evaluable",
            )
        )

    # --- grupos de pull-up ---------------------------------------------------
    per_group = max_inputs_per_pullup(catalog, options.pullup_ohm)
    for i, grp in enumerate(group_pullups(pullup_pins(design), per_group), 1):
        if fam.vcc_min_V is None or fam.vih_min_V is None or fam.iih_max_uA is None:
            findings.append(
                Finding(
                    rule="pullup",
                    severity=Severity.NOT_EVALUABLE,
                    target=f"R{i}",
                    message="faltan Vcc mín, VIH mín o IIH",
                )
            )
            continue
        v = fam.vcc_min_V - len(grp) * fam.iih_max_uA * 1e-6 * options.pullup_ohm
        if v < fam.vih_min_V:
            findings.append(
                Finding(
                    rule="pullup",
                    severity=Severity.ERROR,
                    target=f"R{i}",
                    message=f"{len(grp)} entradas bajan el nivel a {v:.2f} V "
                    f"< VIH mín {fam.vih_min_V} V",
                )
            )

    # --- entradas y salidas primarias ----------------------------------------
    used = set(loads) | {o.net for o in design.netlist.outputs}
    for name in design.netlist.inputs:
        if name not in used:
            findings.append(
                Finding(
                    rule="entrada_sin_uso",
                    severity=Severity.INFO,
                    target=name,
                    message="la entrada no afecta ninguna salida",
                )
            )
    for o in design.netlist.outputs:
        if o.net in CONSTANT_NETS:
            level = "Vcc (por resistencia)" if o.net == "$1" else "GND"
            findings.append(
                Finding(
                    rule="salida_constante",
                    severity=Severity.INFO,
                    target=o.name,
                    message=f"salida fija: conectar a {level}",
                )
            )

    # --- consumo -------------------------------------------------------------
    per_chip: dict[str, float | None] = {}
    for c in design.chips:
        e = chips[c.ref].electrical
        vals = [e.icch_max_mA, e.iccl_max_mA]
        per_chip[c.ref] = None if None in vals else max(v for v in vals if v is not None)
    known = [v for v in per_chip.values() if v is not None]
    complete = len(known) == len(per_chip)
    icc = sum(known)
    power = PowerBudget(
        icc_max_mA=round(icc, 3),
        power_max_mW=round(icc * fam.vcc_max_V, 3) if fam.vcc_max_V is not None else None,
        per_chip_mA=per_chip,
        complete=complete,
    )
    if not complete:
        missing = [f"{r} ({chips[r].part})" for r, v in per_chip.items() if v is None]
        findings.append(
            Finding(
                rule="consumo",
                severity=Severity.NOT_EVALUABLE,
                target=", ".join(missing),
                message=f"sin ICC verificado; el total de {icc:.1f} mA excluye estos chips",
            )
        )

    ok = not any(f.severity is Severity.ERROR for f in findings)
    return DrcReport(ok=ok, findings=findings, loads=net_loads, power=power)


def _fanout_findings(nl: NetLoad, open_collector: bool) -> list[Finding]:
    out: list[Finding] = []
    pins = len(nl.load_pins)
    if nl.iil_total_mA is None or nl.iol_limit_mA is None:
        out.append(
            Finding(
                rule="fanout_bajo",
                severity=Severity.NOT_EVALUABLE,
                target=nl.net,
                message="falta IIL o IOL en el catálogo",
            )
        )
    elif nl.iil_total_mA > nl.iol_limit_mA:
        out.append(
            Finding(
                rule="fanout_bajo",
                severity=Severity.ERROR,
                target=nl.net,
                message=f"{nl.driver} debe absorber {nl.iil_total_mA:.2f} mA de "
                f"{pins} entradas; IOL máx {nl.iol_limit_mA} mA",
            )
        )
    if open_collector:
        out.append(
            Finding(
                rule="fanout_alto",
                severity=Severity.NOT_EVALUABLE,
                target=nl.net,
                message="salida de colector abierto: el nivel alto depende del pull-up",
            )
        )
    elif nl.iih_total_uA is None or nl.ioh_limit_mA is None:
        out.append(
            Finding(
                rule="fanout_alto",
                severity=Severity.NOT_EVALUABLE,
                target=nl.net,
                message="falta IIH o IOH para alguna de las cargas",
            )
        )
    elif nl.iih_total_uA / 1000 > nl.ioh_limit_mA:
        out.append(
            Finding(
                rule="fanout_alto",
                severity=Severity.ERROR,
                target=nl.net,
                message=f"{nl.driver} debe entregar {nl.iih_total_uA:.0f} µA a "
                f"{pins} entradas; IOH máx {nl.ioh_limit_mA} mA",
            )
        )
    return out


def _fmt(v: float | None, unit: str) -> str:
    return f"{v:g} {unit}" if v is not None else f"? {unit}"
