import xml.etree.ElementTree as ET

from tests.golden.circuits import CIRCUITS
from ttl_designer.bom import build_bom
from ttl_designer.logic.parser import parse_equations
from ttl_designer.models.catalog import load_catalog
from ttl_designer.render.chips import net_names, render_chips_svg
from ttl_designer.techmap.mapper import map_design

CATALOG = load_catalog()
NS = {"s": "http://www.w3.org/2000/svg"}


def render(text: str, dont_cares=None, title: str = ""):
    design = map_design(parse_equations(text), CATALOG, dont_cares).selected.design
    bom = build_bom(design, CATALOG)
    root = ET.fromstring(render_chips_svg(design, CATALOG, bom, title))
    return design, bom, root


def pin_texts(root) -> dict[str, ET.Element]:
    return {
        t.get("data-pin"): t
        for t in root.iter("{http://www.w3.org/2000/svg}text")
        if t.get("data-pin")
    }


def test_every_pin_of_every_chip_is_labeled():
    for name, (text, dcs) in CIRCUITS.items():
        design, _, root = render(text, dcs)
        pins = pin_texts(root)
        for c in design.chips:
            n = CATALOG.chip(c.part).package_pins
            for p in range(1, n + 1):
                label = pins.get(f"{c.ref}.{p}")
                assert label is not None, (name, c.ref, p)
                assert label.text and label.text != "?", (name, c.ref, p)
        assert len(root.findall(".//s:g[@data-part]", NS)) == design.ic_count


def test_connections_appear_on_the_right_pins():
    design, _, root = render(CIRCUITS["bcd_7seg"][0], CIRCUITS["bcd_7seg"][1])
    pins = pin_texts(root)
    names = net_names(design)
    for net, pin_list in design.connections().items():
        for pin in pin_list:
            assert pins[pin].get("data-net") == net
            assert pins[pin].text == names[net]


def test_power_pullups_ground_and_free_slots():
    design, bom, root = render("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)")
    pins = pin_texts(root)
    assert pins["U1.14"].text == "VCC" and pins["U1.7"].text == "GND"
    for pin, r in bom.pin_resistor.items():
        assert pins[pin].text == f"↑{r}"
    for pin in bom.gnd_pins:
        assert pins[pin].text == "GND"
    assert pins["U1.11"].text == "libre"  # salida de la NAND sin usar


def test_nc_pins_and_decoupling_caption():
    design, bom, root = render("Y = A B C D E F G H", title="and8")
    pins = pin_texts(root)
    with_nc = [c for c in design.chips if CATALOG.chip(c.part).nc_pins]
    assert with_nc, "el caso debe usar un chip con pines NC (74LS20/21/30)"
    for c in with_nc:
        for p in CATALOG.chip(c.part).nc_pins:
            assert pins[f"{c.ref}.{p}"].text == "NC"
    texts = [t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text")]
    for chip_ref, cap in bom.decoupling.items():
        assert any(t.startswith(f"{cap} entre pin") for t in texts), chip_ref


def test_outputs_named_and_connection_table():
    design, _, root = render("S = A ^ B ^ Ci; Co = A B + Ci (A ^ B)")
    texts = [t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text")]
    assert "Conexiones" in texts and "Niveles fijos" in texts
    assert "→ salida S" in texts and "→ salida Co" in texts
    out_nets = {o.net for o in design.netlist.outputs}
    labelled = {t.get("data-net") for t in pin_texts(root).values()}
    assert out_nets <= labelled


def test_circuit_without_chips():
    _, _, root = render("Y = A; Z = 1")
    texts = " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))
    assert "no necesita chips" in texts
    assert "Y = entrada A" in texts and "Z = nivel alto fijo" in texts


def test_title_is_escaped():
    _, _, root = render("Y = (A B)'", title="<script>&")
    assert root.find("s:title", NS).text == "<script>&"


def test_dark_theme_is_declared():
    _, _, root = render("Y = (A B)'")
    style = root.find("s:style", NS).text
    assert "prefers-color-scheme: dark" in style
