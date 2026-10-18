"""Vista de chips en SVG: cada DIP con su pinout y el cableado pin a pin (§SVG).

Todo sale del diseño físico y del BOM (§NETLIST): ninguna conexión se dibuja que
no esté en ``PhysicalDesign.connections()`` o en las entradas fijas. La vista
usa etiquetas de red en cada pin en vez de cables dibujados, más una tabla de
conexiones; es lo que se sigue al montar en protoboard.
"""

from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from ..bom import Bom
from ..electrical import pin_sort_key
from ..logic.build import INTERNAL_NET_PREFIX
from ..models.catalog import Catalog, Chip
from ..models.netlist import CONSTANT_NETS
from ..models.physical import PhysicalDesign, TieTarget

# Geometría (px)
PITCH = 26
BODY_W = 116
STUB = 14
LABEL_W = 118
PAD_Y = 14
COLS = 3
GAP_X = 36
GAP_Y = 64
MARGIN = 24
ROW_H = 20
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

PALETTE = 8  # clases n0..n7; el color repite, el nombre identifica

STYLE = (
    """
:root { --bg:#ffffff; --fg:#1f2328; --muted:#6e7781; --body:#24292f; --bodytext:#f6f8fa;
  --pin:#8c959f; --rule:#d0d7de; --vcc:#cf222e; --gnd:#57606a; --free:#8c959f;
  --n0:#0b63c4; --n1:#c2410c; --n2:#047857; --n3:#a21caf; --n4:#9a6700; --n5:#0e7490;
  --n6:#9f1239; --n7:#4d7c0f; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --body:#30363d; --bodytext:#e6edf3;
    --pin:#6e7681; --rule:#30363d; --vcc:#ff7b72; --gnd:#8b949e; --free:#6e7681;
    --n0:#79c0ff; --n1:#ffa657; --n2:#56d364; --n3:#e2a5f8; --n4:#e3b341; --n5:#76e3ea;
    --n6:#ff9bce; --n7:#a5d6a7; }
}
svg { background: var(--bg); }
text { fill: var(--fg); font-family: __FONT__; font-size: 12px; }
.body { fill: var(--body); }
.bodytext { fill: var(--bodytext); }
.ref { font-weight: 700; font-size: 14px; }
.pinno { fill: var(--bodytext); font-size: 10px; opacity: .75; }
.stub { stroke: var(--pin); stroke-width: 3; }
.muted { fill: var(--muted); }
.vcc { fill: var(--vcc); font-weight: 700; }
.gnd { fill: var(--gnd); font-weight: 700; }
.free { fill: var(--free); font-style: italic; }
.rule { stroke: var(--rule); stroke-width: 1; }
.h { font-weight: 700; font-size: 14px; }
.io { font-weight: 700; }
""".replace("__FONT__", FONT)
    + "\n".join(f".n{i} {{ fill: var(--n{i}); }}" for i in range(PALETTE))
)


@dataclass(frozen=True)
class PinLabel:
    text: str
    css: str
    net: str | None = None


def net_names(design: PhysicalDesign) -> dict[str, str]:
    """Nombre visible de cada red: salida > entrada > interna sin prefijo."""
    names: dict[str, str] = {}
    for name in design.netlist.inputs:
        names[name] = name
    for o in design.netlist.outputs:
        if o.net not in CONSTANT_NETS:
            names[o.net] = o.name if o.net not in design.netlist.inputs else f"{o.net}={o.name}"
    for g in design.netlist.gates:
        if g.output not in names:
            names[g.output] = g.output.replace(INTERNAL_NET_PREFIX, "n", 1)
    return names


def _pin_labels(
    design: PhysicalDesign, catalog: Catalog, bom: Bom
) -> dict[str, dict[int, PinLabel]]:
    names = net_names(design)
    color = {net: f"n{i % PALETTE}" for i, net in enumerate(sorted(names, key=_net_order))}
    io_nets = set(design.netlist.inputs) | {o.net for o in design.netlist.outputs}
    gates = {g.id: g for g in design.netlist.gates}
    labels: dict[str, dict[int, PinLabel]] = {}

    for c in design.chips:
        chip = catalog.chip(c.part)
        lab: dict[int, PinLabel] = {
            chip.power_pins.vcc: PinLabel("VCC", "vcc"),
            chip.power_pins.gnd: PinLabel("GND", "gnd"),
        }
        for p in chip.nc_pins:
            lab[p] = PinLabel("NC", "muted")
        for slot in chip.gates:
            lab[slot.output] = PinLabel("libre", "free")
        labels[c.ref] = lab

    for t in design.ties:
        if t.to is TieTarget.GND:
            labels[t.ref][t.pin] = PinLabel("GND", "gnd")
        else:
            r = bom.pin_resistor.get(f"{t.ref}.{t.pin}", "R?")
            labels[t.ref][t.pin] = PinLabel(f"↑{r}", "vcc")

    for pl in design.placements:
        g = gates[pl.gate_id]
        for net, pin in zip(g.inputs, pl.input_pins, strict=True):
            if net not in CONSTANT_NETS:
                labels[pl.ref][pin] = _net_label(net, names, color, io_nets)
        out = _net_label(g.output, names, color, io_nets)
        resistor = bom.pin_resistor.get(f"{pl.ref}.{pl.output_pin}")
        if resistor:  # salida de colector abierto
            out = PinLabel(f"{out.text} ↑{resistor}", out.css, out.net)
        labels[pl.ref][pl.output_pin] = out
    return labels


def _net_label(
    net: str, names: dict[str, str], color: dict[str, str], io_nets: set[str]
) -> PinLabel:
    css = color[net] + (" io" if net in io_nets else "")
    return PinLabel(names[net], css, net)


def _net_order(net: str) -> tuple[int, str]:
    if net.startswith(INTERNAL_NET_PREFIX):
        return 1, f"{int(net[len(INTERNAL_NET_PREFIX) :]):06d}"
    return 0, net


def render_chips_svg(design: PhysicalDesign, catalog: Catalog, bom: Bom, title: str = "") -> str:
    labels = _pin_labels(design, catalog, bom)
    names = net_names(design)
    out: list[str] = []

    cell_w = 2 * LABEL_W + 2 * STUB + BODY_W
    n = len(design.chips)
    cols = max(1, min(COLS, n))
    rows = (n + cols - 1) // cols
    body_h = {c.ref: _body_height(catalog.chip(c.part)) for c in design.chips}
    row_h = max(body_h.values(), default=0) + GAP_Y
    width = 2 * MARGIN + cols * cell_w + (cols - 1) * GAP_X
    y = MARGIN + 30

    out.append(
        f'<text x="{MARGIN}" y="{MARGIN + 6}" class="h">{escape(title or "Vista de chips")}'
        f" — {n} IC{'s' if n != 1 else ''}</text>"
    )

    for i, c in enumerate(design.chips):
        col, row = i % cols, i // cols
        x0 = MARGIN + col * (cell_w + GAP_X)
        y0 = y + row * row_h
        out += _chip(c.ref, catalog.chip(c.part), labels[c.ref], x0, y0, bom.decoupling.get(c.ref))
    y += rows * row_h

    if not design.chips:
        out.append(
            f'<text x="{MARGIN}" y="{y}" class="muted">El circuito no necesita chips: '
            "las salidas son entradas directas o constantes.</text>"
        )
        y += ROW_H * 2

    table, y = _tables(design, bom, names, y, width)
    out += table
    height = y + MARGIN

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f"<title>{escape(title or 'Vista de chips')}</title>"
        f"<style>{STYLE}</style>"
        f'<rect width="100%" height="100%" style="fill:var(--bg)"/>' + "".join(out) + "</svg>"
    )


def _body_height(chip: Chip) -> int:
    return (chip.package_pins // 2) * PITCH + 2 * PAD_Y


def _chip(
    ref: str, chip: Chip, labels: dict[int, PinLabel], x0: int, y0: int, cap: str | None
) -> list[str]:
    half = chip.package_pins // 2
    bx = x0 + LABEL_W + STUB
    h = _body_height(chip)
    cx = bx + BODY_W / 2
    out = [
        f'<g id="{escape(ref)}" data-part="{escape(chip.part)}">',
        f'<rect x="{bx}" y="{y0}" width="{BODY_W}" height="{h}" rx="6" class="body"/>',
        f'<path d="M {cx - 9} {y0} a 9 9 0 0 0 18 0" style="fill:var(--bg)"/>',
        f'<text x="{cx}" y="{y0 + h / 2 - 6}" text-anchor="middle" class="bodytext ref">'
        f"{escape(ref)}</text>",
        f'<text x="{cx}" y="{y0 + h / 2 + 12}" text-anchor="middle" class="bodytext">'
        f"{escape(chip.part)}</text>",
        f'<text x="{cx}" y="{y0 + h / 2 + 28}" text-anchor="middle" class="pinno">'
        f"{chip.gates_per_package}×{chip.function.value}{chip.inputs_per_gate}</text>",
    ]
    for pin in range(1, chip.package_pins + 1):
        left = pin <= half
        row = pin - 1 if left else chip.package_pins - pin
        py = y0 + PAD_Y + row * PITCH + PITCH / 2
        lab = labels.get(pin, PinLabel("?", "muted"))
        net_attr = f' data-net="{escape(lab.net)}"' if lab.net else ""
        if left:
            sx, ex, tx, nx, anchor, nanchor = bx - STUB, bx, bx - STUB - 6, bx + 6, "end", "start"
        else:
            sx, ex = bx + BODY_W, bx + BODY_W + STUB
            tx, nx, anchor, nanchor = ex + 6, bx + BODY_W - 6, "start", "end"
        out += [
            f'<line x1="{sx}" y1="{py}" x2="{ex}" y2="{py}" class="stub"/>',
            f'<text x="{nx}" y="{py + 4}" text-anchor="{nanchor}" class="pinno">{pin}</text>',
            f'<text x="{tx}" y="{py + 4}" text-anchor="{anchor}" class="{lab.css}"'
            f' data-pin="{escape(ref)}.{pin}"{net_attr}>{escape(lab.text)}</text>',
        ]
    if cap:
        out.append(
            f'<text x="{cx}" y="{y0 + h + 18}" text-anchor="middle" class="muted">'
            f"{escape(cap)} entre pin {chip.power_pins.vcc} y {chip.power_pins.gnd}</text>"
        )
    out.append("</g>")
    return out


def _tables(
    design: PhysicalDesign, bom: Bom, names: dict[str, str], y: int, width: int
) -> tuple[list[str], int]:
    out = [
        f'<line x1="{MARGIN}" y1="{y - 24}" x2="{width - MARGIN}" y2="{y - 24}" class="rule"/>',
        f'<text x="{MARGIN}" y="{y}" class="h">Conexiones</text>',
    ]
    y += ROW_H + 4
    col2, col3 = MARGIN + 150, MARGIN + 290
    out += [
        f'<text x="{MARGIN}" y="{y}" class="muted">red</text>',
        f'<text x="{col2}" y="{y}" class="muted">origen</text>',
        f'<text x="{col3}" y="{y}" class="muted">destinos</text>',
    ]
    y += ROW_H

    drivers: dict[str, str] = {}
    gates = {g.id: g for g in design.netlist.gates}
    for pl in design.placements:
        drivers[gates[pl.gate_id].output] = f"{pl.ref}.{pl.output_pin}"
    outputs = {o.net: o.name for o in design.netlist.outputs}
    conns = design.connections()
    for net in sorted(conns, key=_net_order):
        src = drivers.get(net, "entrada")
        dests = sorted((p for p in conns[net] if p != src), key=pin_sort_key)
        if net in outputs:
            dests.append(f"→ salida {outputs[net]}")
        out += [
            f'<text x="{MARGIN}" y="{y}" class="io">{escape(names.get(net, net))}</text>',
            f'<text x="{col2}" y="{y}">{escape(src)}</text>',
            f'<text x="{col3}" y="{y}">{escape(", ".join(dests))}</text>',
        ]
        y += ROW_H

    by_r: dict[str, list[str]] = {}
    for pin, r in bom.pin_resistor.items():
        by_r.setdefault(r, []).append(pin)
    if by_r or bom.gnd_pins:
        y += 8
        out.append(f'<text x="{MARGIN}" y="{y}" class="h">Niveles fijos</text>')
        y += ROW_H + 4
        value = next((ln.value for ln in bom.lines if ln.refs and ln.refs[0] in by_r), None)
        for r in sorted(by_r, key=lambda s: int(s[1:])):
            pins = ", ".join(sorted(by_r[r], key=pin_sort_key))
            out += [
                f'<text x="{MARGIN}" y="{y}" class="vcc">↑{escape(r)}</text>',
                f'<text x="{col2}" y="{y}">{escape(value or "")} a VCC</text>',
                f'<text x="{col3}" y="{y}">{escape(pins)}</text>',
            ]
            y += ROW_H
        if bom.gnd_pins:
            out += [
                f'<text x="{MARGIN}" y="{y}" class="gnd">GND</text>',
                f'<text x="{col2}" y="{y}">directo</text>',
                f'<text x="{col3}" y="{y}">'
                f"{escape(', '.join(sorted(bom.gnd_pins, key=pin_sort_key)))}</text>",
            ]
            y += ROW_H

    const_out = [o for o in design.netlist.outputs if o.net in CONSTANT_NETS]
    direct = [o for o in design.netlist.outputs if o.net in design.netlist.inputs]
    if const_out or direct:
        y += 8
        out.append(f'<text x="{MARGIN}" y="{y}" class="h">Salidas sin chip</text>')
        y += ROW_H + 4
        for o in const_out:
            level = "nivel alto fijo (VCC)" if o.net == "$1" else "nivel bajo fijo (GND)"
            out.append(f'<text x="{MARGIN}" y="{y}">{escape(o.name)} = {level}</text>')
            y += ROW_H
        for o in direct:
            out.append(
                f'<text x="{MARGIN}" y="{y}">{escape(o.name)} = entrada {escape(o.net)}</text>'
            )
            y += ROW_H
    return out, y
