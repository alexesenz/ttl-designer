"""Coherencia entre la documentación y el código.

CLAUDE.md se carga completo en cada sesión de agente, así que tiene techo de tamaño: la
narrativa va a docs/decisions/ y a los mensajes de commit. Las decisiones tienen un formato
fijo y un índice; cada §id citado en el código debe resolver en una decisión, y cada
módulo o test que una decisión cita debe existir.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DECISIONS = REPO / "docs" / "decisions"

CLAUDE_MD_MAX_BYTES = 12_000

HEADER_FIELDS = ("Sección", "Estado", "Fecha", "Módulos", "Tests")
BODY_SECTIONS = ("## Contexto", "## Decisión", "## Consecuencias", "## Alternativas descartadas")
VALID_STATES = re.compile(r"^(vigente|propuesta|reemplazada por \d{2})$")

SECTION_ID = re.compile(r"§[A-Z][A-Z0-9-]*")
DECISION_FILE = re.compile(r"^\d{2}-[a-z0-9-]+\.md$")


def decision_files() -> list[Path]:
    return sorted(p for p in DECISIONS.glob("*.md") if p.name != "README.md")


def header(path: Path) -> dict[str, str]:
    fields = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^- \*\*(.+?)\*\*: (.*)$", line)
        if m:
            fields[m.group(1)] = m.group(2).strip()
        if line.strip() == "---":
            break
    return fields


def declared_sections() -> dict[str, str]:
    out: dict[str, str] = {}
    for p in decision_files():
        sec = header(p).get("Sección", "")
        out[sec] = p.name
    return out


def test_claude_md_fits_context() -> None:
    size = (REPO / "CLAUDE.md").stat().st_size
    assert size <= CLAUDE_MD_MAX_BYTES, (
        f"CLAUDE.md pesa {size} B (máximo {CLAUDE_MD_MAX_BYTES}); "
        "mueve la narrativa a docs/decisions/"
    )


@pytest.mark.parametrize("path", decision_files(), ids=lambda p: p.name)
def test_decision_format(path: Path) -> None:
    assert DECISION_FILE.match(path.name), "nombre NN-tema.md en minúsculas"
    fields = header(path)
    missing = [f for f in HEADER_FIELDS if f not in fields]
    assert not missing, f"faltan campos de cabecera: {missing}"
    assert SECTION_ID.fullmatch(fields["Sección"]), fields["Sección"]
    assert VALID_STATES.match(fields["Estado"]), fields["Estado"]
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields["Fecha"]), fields["Fecha"]
    text = path.read_text(encoding="utf-8")
    absent = [s for s in BODY_SECTIONS if s not in text]
    assert not absent, f"faltan secciones: {absent}"


@pytest.mark.parametrize("path", decision_files(), ids=lambda p: p.name)
def test_decision_references_exist(path: Path) -> None:
    fields = header(path)
    for key in ("Módulos", "Tests"):
        for ref in re.findall(r"`([^`]+)`", fields[key]):
            assert (REPO / ref).exists(), f"{key}: {ref} no existe"


def test_section_ids_unique() -> None:
    secs = [header(p).get("Sección") for p in decision_files()]
    dup = {s for s in secs if secs.count(s) > 1}
    assert not dup, f"secciones repetidas: {dup}"


def test_index_lists_every_decision() -> None:
    index = (DECISIONS / "README.md").read_text(encoding="utf-8")
    linked = set(re.findall(r"\]\(([^)]+\.md)\)", index))
    files = {p.name for p in decision_files()}
    assert files - linked == set(), f"sin entrada en el índice: {sorted(files - linked)}"
    assert linked - files == set(), f"el índice apunta a inexistentes: {sorted(linked - files)}"
    sections = declared_sections()
    for sec, name in sections.items():
        assert f"[`{name}`]({name}) | {sec} |" in index, f"índice desalineado para {name}"


def test_section_ids_cited_in_code_resolve() -> None:
    declared = set(declared_sections())
    sources = [
        *REPO.glob("ttl_designer/**/*.py"),
        *REPO.glob("tests/*.py"),
        REPO / "CLAUDE.md",
        REPO / "CATALOG_CONTRACT.md",
    ]
    unresolved: dict[str, list[str]] = {}
    for p in sources:
        for sec in SECTION_ID.findall(p.read_text(encoding="utf-8")):
            if sec not in declared:
                unresolved.setdefault(sec, []).append(str(p.relative_to(REPO)))
    assert not unresolved, f"§ sin decisión que los declare: {unresolved}"
