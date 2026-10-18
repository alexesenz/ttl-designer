import csv
import io

from ttl_designer.bom import BomOptions, GapKind, LineKind, build_bom
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.techmap.cells import MapOptions
from ttl_designer.techmap.mapper import map_design

CATALOG = load_catalog()
FULL_ADDER = "S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)"


def design_for(text: str, **opts):
    report = map_design(parse_equations(text), CATALOG, options=MapOptions(**opts))
    assert report.selected is not None
    return report.selected.design


def lines(bom, kind):
    return [ln for ln in bom.lines if ln.kind is kind]


def test_full_adder_bom():
    bom = build_bom(design_for(FULL_ADDER), CATALOG)
    ics = lines(bom, LineKind.IC)
    assert [(ln.refs, ln.value, ln.manufacturer_pn) for ln in ics] == [
        (["U1"], "74LS00", "SN74LS00N"),
        (["U2"], "74LS86", "SN74LS86AN"),
    ]
    assert all(ln.datasheet and ln.datasheet.startswith("https://") for ln in ics)
    caps = lines(bom, LineKind.CAPACITOR)
    assert caps[0].refs == ["C1", "C2"] and caps[0].value == "100 nF"
    assert caps[0].notes == ["C1: U1 pin 14–7", "C2: U2 pin 14–7"]
    assert caps[1].refs == ["C3"] and caps[1].value == "10 µF"
    (pullup,) = lines(bom, LineKind.RESISTOR)
    assert pullup.refs == ["R1"] and pullup.value == "1 kΩ"
    assert bom.gnd_pins == ["U2.9", "U2.10", "U2.12", "U2.13"]


def test_catalog_gaps_are_reported_not_hidden():
    bom = build_bom(design_for(FULL_ADDER), CATALOG)
    by_target = {(g.target, g.kind) for g in bom.gaps}
    assert ("74LS86", GapKind.UNVERIFIED) in by_target


def test_single_source_part_is_flagged():
    bom = build_bom(design_for("Y = A B C D", strategies=("mixta",)), CATALOG)
    assert any(ln.value == "74LS21" for ln in bom.lines)
    assert ("74LS21", GapKind.SINGLE_SOURCE) in {(g.target, g.kind) for g in bom.gaps}


def test_package_option_changes_part_numbers_and_passives():
    opts = BomOptions(package="SOIC-14", bulk_uF=None)
    bom = build_bom(design_for(FULL_ADDER), CATALOG, opts)
    ics = lines(bom, LineKind.IC)
    assert ics[0].manufacturer_pn == "SN74LS00DR"
    assert all(ln.package == "SMD 0805" for ln in bom.lines if ln.kind is not LineKind.IC)
    assert len(lines(bom, LineKind.CAPACITOR)) == 1  # sin bulk


def test_obsolete_part_preferred_last():
    bom = build_bom(design_for("Y = (A + B)'"), CATALOG, BomOptions(package="SOIC-14"))
    (ic,) = lines(bom, LineKind.IC)
    assert ic.manufacturer_pn == "SN74LS02DR"  # SN74LS02D está obsoleto


def test_missing_package_is_a_gap():
    bom = build_bom(design_for("Y = (A B)'"), CATALOG, BomOptions(package="TSSOP-14"))
    (ic,) = lines(bom, LineKind.IC)
    assert ic.manufacturer_pn is None
    assert ("74LS00", GapKind.NO_ORDERABLE) in {(g.target, g.kind) for g in bom.gaps}


def test_open_collector_pullups_are_unsized_gaps():
    bom = build_bom(design_for("Y = (A ^ B)'", allow_open_collector=True), CATALOG)
    oc = [ln for ln in lines(bom, LineKind.RESISTOR) if ln.value is None]
    assert oc and "colector abierto" in oc[0].description
    assert any(g.kind is GapKind.UNSIZED for g in bom.gaps)


def test_pullup_groups_follow_computed_limit():
    # 200 kΩ: cada entrada baja 4 V, el límite calculado es 1 entrada por resistencia
    bom = build_bom(design_for("Y = A B C D E"), CATALOG, BomOptions(pullup_ohm=200_000))
    (r,) = lines(bom, LineKind.RESISTOR)
    assert r.qty == len(r.notes) > 1
    assert all(note.count(".") == 1 for note in r.notes)


def test_no_chips_no_passives():
    bom = build_bom(design_for("Y = A; Z = 1"), CATALOG)
    assert bom.lines == []


def test_csv_export():
    bom = build_bom(design_for(FULL_ADDER), CATALOG)
    rows = list(csv.reader(io.StringIO(bom.to_csv())))
    assert rows[0][:4] == ["Referencias", "Cantidad", "Tipo", "Valor"]
    assert rows[1][:4] == ["U1", "1", "ic", "74LS00"]
    assert len(rows) == 1 + len(bom.lines)
