"""Interfaz web (§FRONTEND): páginas, fragmentos htmx, estado en la URL y descargas."""

import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode

import pytest
from fastapi.testclient import TestClient

from ttl_designer.app import app
from ttl_designer.web.state import StateError, UiState

client = TestClient(app)
FULL_ADDER = "S = A ^ B ^ Ci\nCo = A B + Ci (A ^ B)"


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if "id" in a:
            self.ids.append(a["id"])


def parse(html):
    c = Collector()
    c.feed(html)
    return c


def test_empty_page_has_form_examples_and_security_headers():
    r = client.get("/")
    assert r.status_code == 200
    assert "default-src 'self'" in r.headers["content-security-policy"]
    assert "script-src 'self'" in r.headers["content-security-policy"]
    doc = parse(r.text)
    form = next(a for t, a in doc.tags if t == "form")
    assert form["id"] == "spec" and form["method"] == "get" and form["hx-get"] == "/"
    assert "Sin resultados todavía" in r.text
    assert r.text.count("data-example") == 5


def test_no_inline_scripts_and_assets_are_local():
    r = client.get("/", params={"eq": FULL_ADDER})
    doc = parse(r.text)
    scripts = [a for t, a in doc.tags if t == "script"]
    assert scripts and all(a.get("src", "").startswith("/static/") for a in scripts)
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", r.text)
    assert not any(a.get("href", "").startswith("http") for t, a in doc.tags if t == "link")
    for path in (
        "/static/app.css",
        "/static/app.js",
        "/static/theme.js",
        "/static/vendor/htmx-2.0.4.min.js",
        "/static/favicon.svg",
    ):
        assert client.get(path).status_code == 200, path


def test_full_result_page():
    r = client.get("/", params={"eq": FULL_ADDER})
    assert r.status_code == 200
    doc = parse(r.text)
    for panel in ("resumen", "logica", "candidatos", "esquematico", "chips", "bom", "drc"):
        assert f"panel-{panel}" in doc.ids and f"tab-{panel}" in doc.ids
    assert len(set(doc.ids)) == len(doc.ids), "ids duplicados"
    assert 'class="ttl-schematic"' in r.text and 'class="ttl-chips"' in r.text
    assert "Equivalente" in r.text and "Sin errores" in r.text and "2 huecos" in r.text
    assert "SN74LS00N" in r.text and "SN74LS86AN" in r.text
    # tabla de verdad: 8 filas en Resumen y 8 en Lógica
    assert r.text.count('<td class="muted">7</td>') == 2


def test_three_axes_are_reported_separately():
    r = client.get("/", params={"eq": FULL_ADDER})
    for label in ("Corrección lógica", "DRC eléctrico", "Huecos del BOM"):
        assert label in r.text


def test_htmx_returns_fragment_with_oob_error_slot_and_canonical_url():
    r = client.get(
        "/",
        params={
            "eq": FULL_ADDER,
            "f": "1",
            "s": ["mixta", "nand", "nor", "nand+xor", "nor+xor"],
            "pkg": "DIP-14",
        },
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200
    assert "<html" not in r.text
    assert 'id="eq-error" hx-swap-oob="true"' in r.text
    pushed = r.headers["HX-Push-Url"]
    assert parse_qs(pushed.split("?", 1)[1]) == {"eq": [FULL_ADDER]}


def test_parse_error_shows_caret_and_hint():
    r = client.get("/", params={"eq": "Y = (A + B C'"})
    assert r.status_code == 200
    assert 'aria-invalid="true"' in r.text
    assert "Se esperaba &#39;)&#39;" in r.text
    assert "columna 14" in r.text
    assert "paréntesis abierto en la columna 5" in r.text
    assert "Corrige la especificación" in r.text


def test_multiline_error_points_to_its_line():
    r = client.get("/", params={"eq": "S = A ^ B\nCo = A $ B"})
    assert "Co = A $ B" in r.text and "columna 8" in r.text


def test_dont_cares_and_options_round_trip():
    q = {
        "eq": "Y = A B C + A' B' C'",
        "dc": "Y: 1, 3",
        "f": "1",
        "s": ["nand"],
        "pkg": "SOIC-14",
        "ex": "LS86",
    }
    r = client.get("/", params=q)
    assert r.status_code == 200
    assert "Equivalente" in r.text
    assert "SN74LS00DR" in r.text or "SN74LS10DR" in r.text  # números de parte SOIC
    assert "+ d(1, 3)" in r.text
    st = UiState.from_query({k: v if isinstance(v, list) else [v] for k, v in q.items()})
    assert st.strategies == ["nand"] and st.package == "SOIC-14"
    assert "74LS86" in st.map_options().excluded_parts
    assert parse_qs(st.query())["s"] == ["nand"]


def test_unchecking_all_strategies_is_an_error():
    r = client.get("/", params={"eq": "Y = A B", "f": "1"})
    assert "marca al menos una estrategia" in r.text


@pytest.mark.parametrize("bad", ["Y 1,2", "Y: a", "Y: 5-2"])
def test_bad_dont_cares(bad):
    with pytest.raises(StateError):
        UiState(dont_cares=bad).parsed_dont_cares()


def test_dont_care_ranges():
    assert UiState(dont_cares="S: 10-12, 15\nCo: 1").parsed_dont_cares() == {
        "S": [10, 11, 12, 15],
        "Co": [1],
    }


def test_limits_surface_as_message_not_500():
    names = " ".join(f"X{i}" for i in range(14))
    r = client.get("/", params={"eq": f"Y = A' B + {names}"})
    assert r.status_code == 200 and "cubos" in r.text


def test_downloads():
    qs = urlencode({"eq": FULL_ADDER})
    svg = client.get(f"/descargas/esquematico.svg?{qs}")
    assert svg.status_code == 200 and svg.text.startswith("<svg")
    assert "attachment" in svg.headers["content-disposition"]
    assert client.get(f"/descargas/chips.svg?{qs}").text.startswith("<svg")
    csv = client.get(f"/descargas/bom.csv?{qs}")
    assert csv.headers["content-type"].startswith("text/csv")
    assert csv.text.splitlines()[1].startswith("U1,1,ic,74LS00")
    assert client.get(f"/descargas/bom.json?{qs}").json()["lines"][0]["value"] == "74LS00"
    assert client.get("/descargas/bom.csv?eq=Y+%3D+%28").status_code == 422


def test_example_links_are_valid_designs():
    r = client.get("/")
    for href in re.findall(r'href="(/\?eq=[^"]+)"', r.text):
        page = client.get(href.replace("&amp;", "&"))
        assert page.status_code == 200 and "Equivalente" in page.text, href


def test_svgs_do_not_style_the_page_root():
    r = client.get("/", params={"eq": FULL_ADDER})
    for style in re.findall(r"<style>(.*?)</style>", r.text, re.S):
        assert not re.search(r"(^|[}\s]):root\s*\{", style), "un SVG redefine :root"


def test_vendored_htmx_matches_declared_checksum():
    import hashlib
    from pathlib import Path

    js = Path(__file__).parent.parent / "ttl_designer/web/static/vendor/htmx-2.0.4.min.js"
    notice = (Path(__file__).parent.parent / "THIRD_PARTY_NOTICES.md").read_text()
    assert hashlib.sha256(js.read_bytes()).hexdigest() in notice
