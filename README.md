# ttl-designer
Herramienta para la creación de circuitos usando compuertas básicas TTL

## Estado

Núcleo lógico (combinacional), independiente del catálogo de chips:

- `ttl_designer/logic/parser.py` — expresiones booleanas → AST (`Y = A B' + C`)
- `ttl_designer/logic/truthtable.py` — tablas de verdad bit-paralelas (hasta 16 entradas)
- `ttl_designer/logic/qm.py` — Quine-McCluskey + Petrick con traza por etapa
- `ttl_designer/logic/build.py` — ecuaciones → netlist lógico con hashing estructural
- `ttl_designer/models/netlist.py` — netlist validado (drivers únicos, sin lazos, niveles)
- `ttl_designer/sim/functional.py` — simulación sin retardo y verificación de equivalencia
- `ttl_designer/models/catalog.py` — esquema y validación de `library/ttl_ls_catalog.json`

## Sintaxis de expresiones

| Operación | Símbolos                         |
|-----------|----------------------------------|
| NOT       | `A'` `!A` `~A` `¬A`              |
| AND       | `A·B` `A*B` `A&B` `A B` `A(B+C)` |
| XOR       | `A^B` `A⊕B`                      |
| OR        | `A+B` `A|B`                      |

Precedencia: NOT > AND > XOR > OR. Los identificadores admiten varios caracteres
(`AB` es una variable). Varias salidas se separan con `;` o salto de línea.

## Desarrollo

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
.venv/bin/uvicorn ttl_designer.app:app --reload   # http://127.0.0.1:8000/docs
```
