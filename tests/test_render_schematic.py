"""Pruebas geométricas del esquemático: conectividad, colisiones y tramos encimados."""

import random
import xml.etree.ElementTree as ET
from collections import defaultdict

import pytest

from tests.conftest import random_expr
from tests.golden.circuits import CIRCUITS
from ttl_designer.bom import build_bom
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.render.schematic import render_schematic_svg
from ttl_designer.techmap.cells import MapOptions
from ttl_designer.techmap.mapper import map_design

CATALOG = load_catalog()
SVG = "{http://www.w3.org/2000/svg}"


def render_eqs(eqs, dcs=None, title=""):
    design = map_design(eqs, CATALOG, dcs).selected.design
    root = ET.fromstring(render_schematic_svg(design, build_bom(design, CATALOG), title))
    return design, root


def render(text, dcs=None, title=""):
    return render_eqs(parse_equations(text), dcs, title)


def segments(root):
    out = defaultdict(list)
    for g in root.iter(f"{SVG}g"):
        net = g.get("data-net")
        if net is None:
            continue
        for ln in g.iter(f"{SVG}line"):
            seg = tuple(int(float(ln.get(k))) for k in ("x1", "y1", "x2", "y2"))
            out[net].append((seg, ln.get("data-gate")))
    return out


def pin_points(root):
    out = defaultdict(list)
    for c in root.iter(f"{SVG}circle"):
        if c.get("class") == "pinpt":
            out[c.get("data-net")].append((int(c.get("cx")), int(c.get("cy")), c.get("data-role")))
    return out


def on_segment(p, seg):
    (x, y), (x1, y1, x2, y2) = p, seg
    return (
        min(x1, x2) <= x <= max(x1, x2)
        and min(y1, y2) <= y <= max(y1, y2)
        and (x1 == x2 == x or y1 == y2 == y)
    )


def find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def check_geometry(root):
    segs = segments(root)
    pins = pin_points(root)
    # 1. cada red conecta su origen con todos sus destinos
    for net, plist in pins.items():
        lines = [s for s, _ in segs[net]]
        assert all(s[0] == s[2] or s[1] == s[3] for s in lines), net  # ortogonal
        parent = list(range(len(lines)))

        for i, a in enumerate(lines):
            for j, b in enumerate(lines):
                if (
                    i < j
                    and any(on_segment(p, b) for p in (a[:2], a[2:]))
                    or (i < j and any(on_segment(p, a) for p in (b[:2], b[2:])))
                ):
                    parent[find(parent, i)] = find(parent, j)
        comps = set()
        for x, y, _ in plist:
            owners = [i for i, s in enumerate(lines) if on_segment((x, y), s)]
            assert owners, f"pin de {net} en ({x},{y}) sin cable"
            comps.add(find(parent, owners[0]))
        assert len(comps) == 1, f"red {net} partida en {len(comps)} piezas"
        assert sum(r == "src" for _, _, r in plist) == 1, net

    # 2. ningún cable atraviesa el cuerpo de otra compuerta
    boxes = {}
    for g in root.iter(f"{SVG}g"):
        if g.get("data-gate"):
            boxes[g.get("data-gate")] = tuple(int(float(v)) for v in g.get("data-bbox").split())
    for net, lst in segs.items():
        for (x1, y1, x2, y2), own in lst:
            for gid, (bx, by, bw, bh) in boxes.items():
                if gid == own:
                    continue
                inside_y = by < y1 < by + bh if y1 == y2 else None
                inside_x = bx < x1 < bx + bw if x1 == x2 else None
                if y1 == y2 and inside_y:
                    assert max(x1, x2) <= bx or min(x1, x2) >= bx + bw, (net, gid)
                if x1 == x2 and inside_x:
                    assert max(y1, y2) <= by or min(y1, y2) >= by + bh, (net, gid)

    # 3. tramos colineales de redes distintas no se enciman
    flat = [(net, s) for net, lst in segs.items() for s, _ in lst]
    for i, (na, a) in enumerate(flat):
        for nb, b in flat[i + 1 :]:
            if na == nb:
                continue
            if a[1] == a[3] == b[1] == b[3]:
                lo = max(min(a[0], a[2]), min(b[0], b[2]))
                hi = min(max(a[0], a[2]), max(b[0], b[2]))
                assert hi <= lo, f"horizontales encimadas {na}/{nb} en y={a[1]}"
            if a[0] == a[2] == b[0] == b[2]:
                lo = max(min(a[1], a[3]), min(b[1], b[3]))
                hi = min(max(a[1], a[3]), max(b[1], b[3]))
                assert hi <= lo, f"verticales encimadas {na}/{nb} en x={a[0]}"


@pytest.mark.parametrize("name", sorted(CIRCUITS))
def test_golden_circuits_geometry(name):
    text, dcs = CIRCUITS[name]
    design, root = render(text, dcs)
    check_geometry(root)
    gates = {g.get("data-gate") for g in root.iter(f"{SVG}g") if g.get("data-gate")}
    assert gates == {g.id for g in design.netlist.gates}


def test_random_circuits_geometry():
    rng = random.Random(7)
    vs = ["A", "B", "C", "D", "E"]
    for _ in range(25):
        eqs = [("Y", random_expr(rng, vs)), ("Z", random_expr(rng, vs))]
        _, root = render_eqs(eqs)
        check_geometry(root)


def test_slots_and_kinds_match_physical_design():
    design, root = render("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)")
    slots = {p.gate_id: f"{p.ref}{p.slot}" for p in design.placements}
    kinds = {g.id: g.kind.value for g in design.netlist.gates}
    for g in root.iter(f"{SVG}g"):
        gid = g.get("data-gate")
        if gid:
            assert g.get("data-slot") == slots[gid]
            assert g.get("data-kind") == kinds[gid]


def test_terminals_for_every_input_and_output():
    design, root = render("Y = A B' + C; Z = A ^ C")
    ios = {(g.get("data-io"), g.get("data-name")) for g in root.iter(f"{SVG}g") if g.get("data-io")}
    assert ios == {("in", "A"), ("in", "B"), ("in", "C"), ("out", "Y"), ("out", "Z")}


def test_tied_inputs_show_pullup_reference():
    opts = MapOptions(strategies=("nand",))
    design = map_design(parse_equations("Y = A'"), CATALOG, options=opts).selected.design
    bom = build_bom(design, CATALOG)
    root = ET.fromstring(render_schematic_svg(design, bom))
    assert bom.pin_resistor  # NAND(A, 1): la segunda entrada va a pull-up
    texts = [t.text for t in root.iter(f"{SVG}text")]
    assert f"↑{next(iter(bom.pin_resistor.values()))}" in texts


def test_constant_and_direct_outputs():
    _, root = render("Y = A; Z = 0")
    check_geometry(root)
    texts = [t.text for t in root.iter(f"{SVG}text")]
    assert "GND" in texts  # Z fija a nivel bajo
    assert len(segments(root)["A"]) >= 1  # Y = A se cablea directo


def test_dark_theme_and_escaped_title():
    _, root = render("Y = (A B)'", title="<x>&")
    assert root.find(f"{SVG}title").text == "<x>&"
    assert "prefers-color-scheme: dark" in root.find(f"{SVG}style").text
