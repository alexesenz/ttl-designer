"""Esquemático lógico en SVG: compuertas ANSI en columnas por nivel (§ESQUEMATICO).

Layout estilo Sugiyama, simplificado:

1. Capas: entradas en la columna 0, cada compuerta en su nivel lógico, salidas
   en la última columna. Una red que salta columnas recibe un nodo ficticio en
   cada columna intermedia, por donde pasa en línea recta.
2. Orden dentro de cada columna por baricentro (barridos ida y vuelta).
3. Posición vertical: cada nodo se alinea con sus predecesores sin solaparse.
4. Ruteo ortogonal por canales entre columnas: cada red que cruza un canal
   tiene su propio carril vertical; los carriles se ordenan para que un tramo
   horizontal nunca se monte sobre el de otra red.

Se dibuja el netlist mapeado (las celdas reales, con su ubicación U1A), no el
lógico, para que el esquemático coincida con los chips y el BOM (§NETLIST).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from xml.sax.saxutils import escape

from ..bom import Bom
from ..models.netlist import CONST1, CONSTANT_NETS, Gate, GateKind
from ..models.physical import PhysicalDesign
from .chips import FONT, PALETTE, net_names
from .theme import scoped_style

PIN_SP = 16  # separación entre entradas de una compuerta
PAD = 8
GW = 48  # ancho del cuerpo de la compuerta
NOT_W = 30
BUBBLE = 4
STUB_IN = 40  # espacio a la izquierda del cuerpo (cabe la etiqueta de un nivel fijo)
STUB_OUT = 20
GATE_COL_W = STUB_IN + GW + 2 * BUBBLE + STUB_OUT
IO_COL_W = 84
TERM_H = 24
DUMMY_H = 12
GAP = 14
TRACK_SP = 10
MIN_CHANNEL = 24
MARGIN = 24
TOP = 44
SWEEPS = 4

STYLE = scoped_style(
    "ttl-schematic",
    (
        "--bg:#ffffff; --fg:#1f2328; --muted:#6e7781; --gate:#ffffff; --stroke:#24292f; "
        "--wire:#57606a; --vcc:#cf222e; --gnd:#57606a; --n0:#0b63c4; --n1:#c2410c; "
        "--n2:#047857; --n3:#a21caf; --n4:#9a6700; --n5:#0e7490; --n6:#9f1239; "
        "--n7:#4d7c0f;"
    ),
    (
        "--bg:#0d1117; --fg:#e6edf3; --muted:#8b949e; --gate:#161b22; --stroke:#c9d1d9; "
        "--wire:#8b949e; --vcc:#ff7b72; --gnd:#8b949e; --n0:#79c0ff; --n1:#ffa657; "
        "--n2:#56d364; --n3:#e2a5f8; --n4:#e3b341; --n5:#76e3ea; --n6:#ff9bce; "
        "--n7:#a5d6a7;"
    ),
    """
& text { fill: var(--fg); font-family: __FONT__; font-size: 12px; }
& .h { font-weight: 700; font-size: 14px; }
& .slot { fill: var(--muted); font-size: 10px; }
& .gate { fill: var(--gate); stroke: var(--stroke); stroke-width: 1.6; }
& .gate-line { fill: none; stroke: var(--stroke); stroke-width: 1.6; }
& .wire { stroke-width: 1.6; fill: none; stroke-linecap: round; }
& .dot { stroke: none; }
& .term { fill: var(--gate); stroke: var(--stroke); stroke-width: 1.4; }
& .io { font-weight: 700; }
& .vcc { fill: var(--vcc); font-size: 10px; font-weight: 700; }
& .gnd { fill: var(--gnd); font-size: 10px; font-weight: 700; }
& .tie { stroke: var(--wire); stroke-width: 1.4; }
& .pinpt { fill: none; stroke: none; }
""".replace("__FONT__", FONT)
    + "\n".join(
        f"& .n{i} {{ stroke: var(--n{i}); }} & .t{i} {{ fill: var(--n{i}); }}"
        for i in range(PALETTE)
    ),
)


@dataclass
class Node:
    key: str
    kind: str  # "in" | "gate" | "dummy" | "out"
    col: int
    net: str | None = None  # in/dummy/out: la red que llevan
    gate: Gate | None = None
    label: str = ""
    height: int = 0
    top: int = 0
    order: float = 0.0
    preds: list[str] = field(default_factory=list)

    def in_y(self, i: int) -> int:
        """y de la entrada i (compuertas) o del pin único (resto)."""
        if self.kind == "gate":
            assert self.gate is not None
            n = len(self.gate.inputs)
            span = max(n, 2) * PIN_SP
            first = self.top + PAD + (span - n * PIN_SP) // 2 + PIN_SP // 2
            return first + i * PIN_SP
        return self.top + self.height // 2

    @property
    def out_y(self) -> int:
        return self.top + self.height // 2


@dataclass
class Segment:
    x1: int
    y1: int
    x2: int
    y2: int
    gate: str | None = None  # stub que toca una compuerta (para pruebas de colisión)


def render_schematic_svg(design: PhysicalDesign, bom: Bom, title: str = "") -> str:
    nl = design.netlist
    names = net_names(design)
    slot_of = {p.gate_id: f"{p.ref}{p.slot}" for p in design.placements}
    levels = nl.levels()
    last_gate_col = max(levels.values(), default=0)
    out_col = last_gate_col + 1

    nodes: dict[str, Node] = {}
    driver_node: dict[str, str] = {}
    for name in nl.inputs:
        k = f"in:{name}"
        nodes[k] = Node(k, "in", 0, net=name, label=name, height=TERM_H)
        driver_node[name] = k
    for g in nl.gates:
        k = f"gate:{g.id}"
        n = len(g.inputs)
        nodes[k] = Node(
            k,
            "gate",
            levels[g.id],
            gate=g,
            label=slot_of.get(g.id, g.id),
            height=max(n, 2) * PIN_SP + 2 * PAD,
        )
        driver_node[g.output] = k
    for o in nl.outputs:
        k = f"out:{o.name}"
        nodes[k] = Node(k, "out", out_col, net=o.net, label=o.name, height=TERM_H)

    # sumideros: (nodo, índice de entrada) por red; las constantes no se rutean
    sinks: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for g in nl.gates:
        for i, net in enumerate(g.inputs):
            if net not in CONSTANT_NETS:
                sinks[net].append((f"gate:{g.id}", i))
    for o in nl.outputs:
        if o.net not in CONSTANT_NETS:
            sinks[o.net].append((f"out:{o.name}", 0))

    # cadena por red: nodo que la lleva en cada columna (fuente, ficticios)
    chain: dict[str, dict[int, str]] = {}
    for net, sk in sinks.items():
        src = driver_node[net]
        c0 = nodes[src].col
        cmax = max(nodes[s].col for s, _ in sk)
        chain[net] = {c0: src}
        for c in range(c0 + 1, cmax):
            k = f"dummy:{net}:{c}"
            nodes[k] = Node(k, "dummy", c, net=net, height=DUMMY_H, preds=[chain[net][c - 1]])
            chain[net][c] = k
    for net, sk in sinks.items():
        for s, _ in sk:
            pred = chain[net][nodes[s].col - 1]
            if pred not in nodes[s].preds:
                nodes[s].preds.append(pred)

    columns: list[list[Node]] = [[] for _ in range(out_col + 1)]
    for nd in nodes.values():
        columns[nd.col].append(nd)
    _order_columns(columns, nodes)
    _place_vertically(columns, nodes)

    # --- canales -------------------------------------------------------------
    channels: list[dict[str, tuple[list[int], list[int]]]] = []
    for c in range(out_col):
        ch: dict[str, tuple[list[int], list[int]]] = {}
        for net, per_col in chain.items():
            if c not in per_col:
                continue
            left = [nodes[per_col[c]].out_y]
            right = [nodes[s].in_y(i) for s, i in sinks[net] if nodes[s].col == c + 1]
            if c + 1 in per_col and nodes[per_col[c + 1]].kind == "dummy":
                right.append(nodes[per_col[c + 1]].in_y(0))
            if right:
                ch[net] = (left, right)
        channels.append(ch)
    tracks = [_assign_tracks(ch) for ch in channels]

    # --- coordenadas x -------------------------------------------------------
    col_x: list[int] = []
    col_w: list[int] = []
    x = MARGIN
    for c in range(out_col + 1):
        w = IO_COL_W if c in (0, out_col) else GATE_COL_W
        col_x.append(x)
        col_w.append(w)
        if c < out_col:
            x += w + max(MIN_CHANNEL, (len(tracks[c]) + 1) * TRACK_SP)
    width = x + col_w[-1] + MARGIN
    height = max((nd.top + nd.height for nd in nodes.values()), default=TOP) + MARGIN + 20

    color = {net: f"{i % PALETTE}" for i, net in enumerate(sorted(chain))}
    wires: dict[str, list[Segment]] = defaultdict(list)
    dots: dict[str, list[tuple[int, int]]] = defaultdict(list)
    pinpts: list[tuple[str, str, int, int]] = []  # (net, rol, x, y)
    body: list[str] = []

    for nd in nodes.values():
        x0, w = col_x[nd.col], col_w[nd.col]
        if nd.kind == "dummy":
            assert nd.net is not None
            wires[nd.net].append(Segment(x0, nd.out_y, x0 + w, nd.out_y))
        elif nd.kind == "in":
            assert nd.net is not None
            body.append(_input_terminal(nd, x0, w))
            if nd.net in chain:
                wires[nd.net].append(Segment(x0 + w - 24, nd.out_y, x0 + w, nd.out_y))
                pinpts.append((nd.net, "src", x0 + w - 24, nd.out_y))
        elif nd.kind == "out":
            assert nd.net is not None
            body.append(_output_terminal(nd, x0, w))
            if nd.net in CONSTANT_NETS:
                body.append(_tie(x0 + 20, nd.out_y, nd.net == CONST1, bom, None, right=True))
            else:
                wires[nd.net].append(Segment(x0, nd.out_y, x0 + 20, nd.out_y))
                pinpts.append((nd.net, "sink", x0 + 20, nd.out_y))
        else:
            assert nd.gate is not None
            svg, segs, pts = _gate(nd, x0, w, design, bom)
            body.append(svg)
            for net, seg in segs:
                wires[net].append(seg)
            pinpts += pts

    for c, ch in enumerate(channels):
        xl, xr = col_x[c] + col_w[c], col_x[c + 1]
        for net, (left, right) in ch.items():
            ys = left + right
            if net not in tracks[c]:  # recta: mismo y a ambos lados
                wires[net].append(Segment(xl, left[0], xr, left[0]))
                continue
            xt = xl + (tracks[c][net] + 1) * TRACK_SP
            for y in left:
                wires[net].append(Segment(xl, y, xt, y))
            for y in right:
                wires[net].append(Segment(xt, y, xr, y))
            lo, hi = min(ys), max(ys)
            if hi > lo:
                wires[net].append(Segment(xt, lo, xt, hi))
            for y in set(ys):
                arms = (y in left) + (y in right) + (y > lo) + (y < hi)
                if arms >= 3:
                    dots[net].append((xt, y))

    out: list[str] = [
        f'<text x="{MARGIN}" y="{MARGIN + 6}" class="h">'
        f"{escape(title or 'Esquemático lógico')}</text>"
    ]
    for net in sorted(wires, key=lambda n: names.get(n, n)):
        cls = color.get(net, "0")
        out.append(
            f'<g class="net" data-net="{escape(net)}"><title>{escape(names.get(net, net))}</title>'
        )
        for seg in wires[net]:
            gate_attr = f' data-gate="{seg.gate}"' if seg.gate else ""
            out.append(
                f'<line x1="{seg.x1}" y1="{seg.y1}" x2="{seg.x2}" y2="{seg.y2}" '
                f'class="wire n{cls}"{gate_attr}/>'
            )
        for dx, dy in dots[net]:
            out.append(f'<circle cx="{dx}" cy="{dy}" r="3" class="dot t{cls}"/>')
        out.append("</g>")
    out += body
    for net, role, px, py in pinpts:
        out.append(
            f'<circle class="pinpt" data-net="{escape(net)}" data-role="{role}" '
            f'cx="{px}" cy="{py}" r="0"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" class="ttl-schematic" '
        f'width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">'
        f"<title>{escape(title or 'Esquemático lógico')}</title>"
        f"<style>{STYLE}</style>"
        f'<rect width="100%" height="100%" style="fill:var(--bg)"/>' + "".join(out) + "</svg>"
    )


# --- orden y posición ---------------------------------------------------------


def _order_columns(columns: list[list[Node]], nodes: dict[str, Node]) -> None:
    succs: dict[str, list[str]] = defaultdict(list)
    for nd in nodes.values():
        for p in nd.preds:
            succs[p].append(nd.key)
    for col in columns:
        col.sort(key=_initial_key)
        for i, nd in enumerate(col):
            nd.order = i

    def sweep(cols: list[list[Node]], neigh: dict[str, list[str]]) -> None:
        for col in cols:
            for nd in col:
                ns = neigh.get(nd.key, [])
                if ns:
                    nd.order = sum(nodes[k].order for k in ns) / len(ns)
            col.sort(key=lambda n: (n.order, _initial_key(n)))
            for i, nd in enumerate(col):
                nd.order = i

    preds = {k: nd.preds for k, nd in nodes.items()}
    for _ in range(SWEEPS):
        sweep(columns[1:], preds)
        sweep(list(reversed(columns[:-1])), succs)
    sweep(columns[1:], preds)


def _initial_key(nd: Node) -> tuple[int, str]:
    rank = {"in": 0, "gate": 1, "dummy": 2, "out": 3}[nd.kind]
    return rank, nd.label or nd.key


def _place_vertically(columns: list[list[Node]], nodes: dict[str, Node]) -> None:
    for c, col in enumerate(columns):
        bottom = TOP - GAP
        for nd in col:
            desired = bottom + GAP
            if c > 0 and nd.preds:
                anchors = [nodes[p].out_y for p in nd.preds]
                target = sum(anchors) // len(anchors)
                desired = max(desired, target - nd.height // 2)
            nd.top = desired
            bottom = nd.top + nd.height


def _assign_tracks(ch: dict[str, tuple[list[int], list[int]]]) -> dict[str, int]:
    """Carril por red; las redes rectas (un solo y a ambos lados) no usan carril.

    Restricción: si la red A sale por la izquierda a la altura y y la red B entra por
    la derecha a la misma altura, el carril de A debe quedar a la izquierda del de B;
    si no, sus tramos horizontales se montarían.
    """
    routed = [n for n, (lf, rt) in ch.items() if not (len(rt) == 1 and lf[0] == rt[0])]
    after: dict[str, set[str]] = {n: set() for n in routed}
    for a in routed:
        for b in routed:
            if a != b and set(ch[a][0]) & set(ch[b][1]):
                after[b].add(a)  # a antes que b
    order: list[str] = []
    pending = sorted(routed, key=lambda n: (min(ch[n][0] + ch[n][1]), n))
    while pending:
        ready = [n for n in pending if after[n] <= set(order)] or pending[:1]
        order.append(ready[0])
        pending.remove(ready[0])
    return {n: i for i, n in enumerate(order)}


# --- símbolos -----------------------------------------------------------------


def _input_terminal(nd: Node, x0: int, w: int) -> str:
    y, r = nd.out_y, x0 + w - 24
    return (
        f'<g data-io="in" data-name="{escape(nd.label)}">'
        f'<path d="M {r - 22} {y - 9} H {r - 6} L {r} {y} L {r - 6} {y + 9} H {r - 22} Z" '
        f'class="term"/>'
        f'<text x="{r - 26}" y="{y + 4}" text-anchor="end" class="io">{escape(nd.label)}'
        "</text></g>"
    )


def _output_terminal(nd: Node, x0: int, w: int) -> str:
    y, lx = nd.out_y, x0 + 20
    return (
        f'<g data-io="out" data-name="{escape(nd.label)}">'
        f'<path d="M {lx} {y - 9} H {lx + 16} L {lx + 22} {y} L {lx + 16} {y + 9} H {lx} Z" '
        f'class="term"/>'
        f'<text x="{lx + 28}" y="{y + 4}" class="io">{escape(nd.label)}</text></g>'
    )


def _tie(x: int, y: int, high: bool, bom: Bom, pin: str | None, right: bool = False) -> str:
    """Nivel fijo: ↑Rn (pull-up con su referencia del BOM) o GND."""
    if high:
        r = bom.pin_resistor.get(pin, "") if pin else ""
        text, cls = f"↑{r}" if r else "VCC", "vcc"
    else:
        text, cls = "GND", "gnd"
    anchor = "start" if right else "end"
    tx = x + 6 if right else x - 4
    return (
        f'<line x1="{x - (0 if right else 10)}" y1="{y}" x2="{x + (10 if right else 0)}" '
        f'y2="{y}" class="tie"/>'
        f'<text x="{tx + (10 if right else 0)}" y="{y + 3}" text-anchor="{anchor}" '
        f'class="{cls}">{escape(text)}</text>'
    )


def _gate(
    nd: Node, x0: int, w: int, design: PhysicalDesign, bom: Bom
) -> tuple[str, list[tuple[str, Segment]], list[tuple[str, str, int, int]]]:
    g = nd.gate
    assert g is not None
    kind = g.kind
    bw = NOT_W if kind in (GateKind.NOT, GateKind.BUF) else GW
    bx = x0 + STUB_IN
    by = nd.top + PAD // 2
    bh = nd.height - PAD
    inverted = kind in (GateKind.NAND, GateKind.NOR, GateKind.XNOR, GateKind.NOT)
    out_x = bx + bw + (2 * BUBBLE if inverted else 0)

    shape = _shape(kind, bx, by, bw, bh)
    xor_pad = 6 if kind in (GateKind.XOR, GateKind.XNOR) else 0
    bbox = f"{bx - xor_pad} {by} {out_x - bx + xor_pad} {bh}"
    parts = [
        f'<g data-gate="{g.id}" data-slot="{escape(nd.label)}" data-kind="{kind.value}" '
        f'data-bbox="{bbox}"><title>{escape(nd.label)}: {kind.value}</title>{shape}'
    ]
    if inverted:
        parts.append(
            f'<circle cx="{bx + bw + BUBBLE}" cy="{by + bh // 2}" r="{BUBBLE}" class="gate"/>'
        )
    parts.append(
        f'<text x="{bx + bw // 2}" y="{by - 3}" text-anchor="middle" class="slot">'
        f"{escape(nd.label)}</text>"
    )

    placement = next((p for p in design.placements if p.gate_id == g.id), None)
    segs: list[tuple[str, Segment]] = []
    pts: list[tuple[str, str, int, int]] = []
    for i, net in enumerate(g.inputs):
        y = nd.in_y(i)
        xe = bx + _back_offset(kind, by, bh, bw, y)
        if net in CONSTANT_NETS:
            pin = f"{placement.ref}.{placement.input_pins[i]}" if placement else None
            parts.append(f'<line x1="{bx - 12}" y1="{y}" x2="{xe}" y2="{y}" class="tie"/>')
            parts.append(_tie(bx - 12, y, net == CONST1, bom, pin))
            continue
        segs.append((net, Segment(x0, y, xe, y, gate=g.id)))
        pts.append((net, "sink", xe, y))
    oy = nd.out_y
    segs.append((g.output, Segment(out_x, oy, x0 + w, oy, gate=g.id)))
    pts.append((g.output, "src", out_x, oy))
    parts.append("</g>")
    return "".join(parts), segs, pts


def _back_offset(kind: GateKind, by: int, bh: int, bw: int, y: int) -> int:
    """x relativa donde una entrada toca el cuerpo (curva trasera en OR/XOR)."""
    if kind in (GateKind.OR, GateKind.NOR, GateKind.XOR, GateKind.XNOR):
        t = (y - by) / bh
        off = round(2 * t * (1 - t) * bw * 0.25)
        # en XOR/XNOR la entrada toca la curva extra, 6 px más atrás
        return off - 6 if kind in (GateKind.XOR, GateKind.XNOR) else off
    return 0


def _shape(kind: GateKind, x: int, y: int, w: int, h: int) -> str:
    if kind in (GateKind.NOT, GateKind.BUF):
        return f'<path d="M {x} {y} L {x + w} {y + h / 2} L {x} {y + h} Z" class="gate"/>'
    if kind in (GateKind.AND, GateKind.NAND):
        rx = min(h / 2, w * 0.6)
        return (
            f'<path d="M {x} {y} H {x + w - rx} A {rx} {h / 2} 0 0 1 {x + w - rx} {y + h} '
            f'H {x} Z" class="gate"/>'
        )
    back = w * 0.25
    path = (
        f"M {x} {y} Q {x + w * 0.6} {y} {x + w} {y + h / 2} "
        f"Q {x + w * 0.6} {y + h} {x} {y + h} Q {x + back} {y + h / 2} {x} {y} Z"
    )
    out = f'<path d="{path}" class="gate"/>'
    if kind in (GateKind.XOR, GateKind.XNOR):
        out = (
            f'<path d="M {x - 6} {y} Q {x - 6 + back} {y + h / 2} {x - 6} {y + h}" '
            f'class="gate-line"/>' + out
        )
    return out
