# ttl-designer — manual de operación

Herramienta para diseñar circuitos combinacionales con compuertas TTL 74LS: parte de
expresiones booleanas, minimiza, mapea a chips reales, simula y entrega esquemático SVG,
BOM y documentación por etapa. FastAPI + Python, licencia MIT, repo público.

```
expresión ──► AST ──► Quine-McCluskey ──► netlist lógico ──► mapeo 74LS ──► empaquetado
                                               │                                 │
                                               └── simulación / equivalencia ◄───┘ ──► SVG, BOM, docs
```

**Dónde está escrito cada cosa.** Este archivo es solo el manual de operación: cómo se
trabaja y qué reglas no se rompen. El *porqué* de cada decisión vive en `docs/decisions/`
(un archivo por tema, índice en su `README.md`) y se lee bajo demanda. Las especificaciones
vivas están en la raíz (`CATALOG_CONTRACT.md`). El trabajo pendiente vive en GitHub Issues.
`tests/test_docs_layout.py` limita el tamaño de este archivo y verifica que cada `§id` citado
en el código resuelva en una decisión.

## Comandos

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pre-commit install                       # ruff + mypy + pytest en cada commit
.venv/bin/pytest -q
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy
.venv/bin/uvicorn ttl_designer.app:app --reload    # http://127.0.0.1:8000/docs
```

## Mapa de módulos

```
ttl_designer/logic/parser.py      texto → AST; errores con posición
ttl_designer/logic/ast.py         AST con evaluación bit-paralela
ttl_designer/logic/truthtable.py  vectores de entrada, minterms, tablas de verdad (§CONVENCIONES)
ttl_designer/logic/qm.py          Quine-McCluskey + Petrick, traza por etapa
ttl_designer/logic/build.py       ecuaciones → netlist con hashing estructural
ttl_designer/models/netlist.py    netlist lógico validado (§NETLIST)
ttl_designer/models/catalog.py    esquema del catálogo 74LS (§CATALOGO)
ttl_designer/sim/functional.py    simulación sin retardo, check_equivalence (§EJES)
ttl_designer/api/                 rutas FastAPI y esquemas de request/response
library/                          ttl_ls_catalog.json (datos, no código)
```

## Invariantes

- **El netlist es la fuente única de verdad** (§NETLIST). SVG, BOM, simulación y
  documentación se derivan de él; ninguna salida guarda estado propio que pueda divergir.
- **Equivalencia como puerta de aceptación.** Toda transformación del netlist (minimizar,
  mapear, empaquetar) debe pasar `check_equivalence` contra la especificación, en los tests
  y en la API. Un cambio que la rompa no entra.
- **No suponer** (§CATALOGO). Un dato eléctrico o de pinout sin fuente oficial queda en `null`
  y se declara en `unverified`. Nunca se rellena con un valor "típico" de memoria.
- **La ambigüedad se resuelve en nada.** Si dos fuentes no concuerdan y no hay criterio
  escrito, el campo queda vacío y la discrepancia se declara; no se elige "la más cercana".
- **Ejes independientes** (§EJES): corrección lógica, DRC eléctrico y huecos del BOM se
  reportan por separado y nunca se mezclan en un solo indicador.
- **Fallar en voz alta.** Los modelos de entrada son estrictos (`extra="forbid"`, validación
  estructural). Un dato malformado produce un error con contexto, no un resultado plausible.
- **Límites explícitos.** Lo que crece exponencialmente con la entrada tiene tope
  (`MAX_VARIABLES`, `PETRICK_LIMIT`) y la API responde 422 al excederlo. Una ruta nueva cuyo
  costo crezca con la entrada más allá de eso nace como job asíncrono, no se adapta después.
- **Convenciones fijas** (§CONVENCIONES): primera variable = MSB del índice Σm; variables en
  orden alfabético; los identificadores pueden tener varios caracteres.
- **Costo de mapeo = número de ICs** (§COSTO-IC), no número de compuertas.

## Repo público

- No se versionan PDFs de datasheets: el catálogo guarda valores con URL y revisión.
- Ningún secreto en el repo; credenciales futuras (p. ej. API de LLM) solo por variable de
  entorno, documentada en el README.
- No se copia texto ni código de proyectos con licencia incompatible con MIT, aunque se
  adopten sus ideas.

## Flujo de trabajo

- Una rama por cambio, creada desde `origin/main`; todo entra a `main` por PR. Preguntar antes
  de hacer merge. Informar siempre en qué rama se trabaja.
- El mensaje de commit lleva la narrativa completa: qué cambió, por qué, cómo se validó y qué
  tests lo fijan. Si hubo una decisión, se agrega o amplía un archivo en `docs/decisions/`.
  Este archivo solo cambia si cambia la forma de operar.
- Documentación en español neutro.
