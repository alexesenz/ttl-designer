"""Rutas de la interfaz web (§FRONTEND): página completa o fragmento para htmx."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..models.catalog import Catalog, load_catalog
from .state import PACKAGES, STRATEGY_LABELS, UiState, example_links
from .view import View, build_view

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=HERE / "templates")
router = APIRouter()

# Sin scripts en línea ni orígenes externos; los SVG incrustados traen <style>.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; "
    "form-action 'self'"
)


@lru_cache(maxsize=1)
def _catalog() -> Catalog:
    return load_catalog()


def _view(request: Request) -> View:
    q: dict[str, list[str]] = {}
    for k, v in request.query_params.multi_items():
        q.setdefault(k, []).append(v)
    try:
        catalog = _catalog()
    except FileNotFoundError as exc:
        raise HTTPException(503, "catálogo de chips no disponible") from exc
    return build_view(UiState.from_query(q), catalog)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def index(request: Request) -> Response:
    view = _view(request)
    ctx = {
        "v": view,
        "strategy_labels": STRATEGY_LABELS,
        "packages": PACKAGES,
        "examples": example_links(),
    }
    # htmx pide solo los resultados, más el error del editor fuera de banda
    partial = bool(request.headers.get("HX-Request"))
    ctx["oob"] = partial
    name = "partials/results.html" if partial else "index.html"
    resp = templates.TemplateResponse(request, name, ctx)
    resp.headers["Content-Security-Policy"] = CSP
    resp.headers["X-Content-Type-Options"] = "nosniff"
    if partial:
        # Query canónica (solo campos distintos del defecto). El cliente la agrega a su
        # propia ruta (§FRONTEND): htmx resuelve las URL de historial contra la raíz y
        # perdería la subruta cuando un proxy monta la app en /algo/.
        resp.headers["X-TTL-Query"] = view.query if view.state.equations.strip() else ""
    return resp


def _download(request: Request) -> View:
    view = _view(request)
    if not view.has_result or view.bom is None:
        raise HTTPException(
            422, view.error.message if view.error else "no hay diseño que descargar"
        )
    return view


def _attachment(body: str, media: str, filename: str) -> Response:
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(content=body, media_type=media, headers=headers)


@router.get("/descargas/esquematico.svg", include_in_schema=False)
def download_schematic(request: Request) -> Response:
    v = _download(request)
    return _attachment(str(v.data["schematic_svg"]), "image/svg+xml", "esquematico.svg")


@router.get("/descargas/chips.svg", include_in_schema=False)
def download_chips(request: Request) -> Response:
    v = _download(request)
    return _attachment(str(v.data["chips_svg"]), "image/svg+xml", "chips.svg")


@router.get("/descargas/bom.csv", include_in_schema=False)
def download_bom_csv(request: Request) -> Response:
    v = _download(request)
    assert v.bom is not None
    return _attachment(v.bom.to_csv(), "text/csv; charset=utf-8", "bom.csv")


@router.get("/descargas/bom.json", include_in_schema=False)
def download_bom_json(request: Request) -> Response:
    v = _download(request)
    assert v.bom is not None
    return _attachment(v.bom.model_dump_json(indent=2), "application/json", "bom.json")
