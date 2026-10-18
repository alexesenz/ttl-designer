from ttl_designer.bom import BomOptions
from ttl_designer.drc import Severity, run_drc
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.techmap.cells import MapOptions
from ttl_designer.techmap.mapper import map_design

CATALOG = load_catalog()


def design_for(text: str, **opts):
    report = map_design(parse_equations(text), CATALOG, options=MapOptions(**opts))
    assert report.selected is not None
    return report.selected.design


def rules(report, severity=None):
    return {
        (f.rule, f.target) for f in report.findings if severity is None or f.severity is severity
    }


def test_clean_nand_design_passes():
    r = run_drc(design_for("Y = A B' + A C + B C'"), CATALOG)
    assert r.ok
    assert r.count(Severity.ERROR) == 0
    assert r.power.complete and r.power.icc_max_mA == 4.4
    assert r.power.power_max_mW == round(4.4 * 5.25, 3)


def test_fanout_violation_detected():
    # A' alimenta 28 compuertas (7 de 2 entradas y 21 de 3): 28 × 0.4 mA > IOL 8 mA
    eqs = [f"Y{i} = A' B{i}" for i in range(7)]
    eqs += [f"Z{i}{j} = A' B{i} B{j}" for i in range(7) for j in range(i + 1, 7)]
    text = "\n".join(eqs)
    r = run_drc(design_for(text), CATALOG)
    assert not r.ok
    low = [f for f in r.findings if f.rule == "fanout_bajo" and f.severity is Severity.ERROR]
    assert len(low) == 1
    load = next(nl for nl in r.loads if nl.net == low[0].target)
    assert len(load.load_pins) == 28 and load.iil_total_mA == 11.2


def test_external_inputs_report_their_load():
    r = run_drc(design_for("Y = (A B)'"), CATALOG)
    ext = [f for f in r.findings if f.rule == "entrada_externa"]
    assert {f.target for f in ext} == {"A", "B"}
    assert all(f.severity is Severity.INFO for f in ext)


def test_nonstandard_load_makes_high_fanout_not_evaluable():
    r = run_drc(design_for("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"), CATALOG)
    assert r.ok  # no_evaluable no es error
    assert ("carga_no_estandar", "74LS86") in rules(r, Severity.WARNING)
    assert any(f.rule == "fanout_alto" for f in r.findings if f.severity is Severity.NOT_EVALUABLE)


def test_power_excludes_chips_without_verified_icc():
    r = run_drc(design_for("P = A ^ B ^ C ^ D"), CATALOG)
    assert not r.power.complete
    assert r.power.per_chip_mA == {"U1": None}
    assert any(f.rule == "consumo" and f.severity is Severity.NOT_EVALUABLE for f in r.findings)


def test_floating_input_detected():
    design = design_for("Y = (A + B)'", strategies=("nor",))
    broken = design.model_copy(update={"ties": design.ties[1:]})
    r = run_drc(broken, CATALOG)
    assert not r.ok
    assert any(f.rule == "entrada_flotante" for f in r.findings)


def test_shared_pullup_too_weak_is_an_error():
    r = run_drc(design_for("Y = A B C D E"), CATALOG, BomOptions(pullup_ohm=200_000))
    assert any(f.rule == "pullup" and f.severity is Severity.ERROR for f in r.findings)


def test_open_collector_high_fanout_not_evaluable():
    design = design_for("Y = (A ^ B)' C", allow_open_collector=True, strategies=("mixta",))
    r = run_drc(design, CATALOG)
    oc_nets = [f for f in r.findings if f.rule == "fanout_alto" and "colector abierto" in f.message]
    assert oc_nets


def test_constant_output_and_unused_input_are_info():
    r = run_drc(design_for("Y = A A' + B; Z = 1; W = C C'"), CATALOG)
    found = rules(r, Severity.INFO)
    assert ("salida_constante", "Z") in found
    assert ("entrada_sin_uso", "A") in found and ("entrada_sin_uso", "C") in found
    assert ("entrada_sin_uso", "B") not in found
