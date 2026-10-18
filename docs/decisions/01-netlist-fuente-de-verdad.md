# 01 — El netlist lógico como única fuente de verdad

- **Sección**: §NETLIST
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/models/netlist.py`, `ttl_designer/logic/build.py`
- **Tests**: `tests/test_netlist_sim.py`

---

## Contexto

La herramienta produce varias salidas del mismo circuito: simulación, esquemático,
vista de chips, BOM y documentación. Si cada una construye su propio modelo, tarde o
temprano divergen; por ejemplo, un esquemático que muestra una compuerta que el BOM no
cuenta.

## Decisión

Toda salida se deriva de un único modelo: el netlist, formado por compuertas con id, tipo,
redes de entrada y una red de salida. Hay dos niveles del mismo modelo:

- **Netlist lógico**: compuertas abstractas de fan-in arbitrario, independiente de la
  tecnología. Lo producen `build.py` y el minimizador.
- **Netlist físico** (pendiente): el mismo grafo tras el mapeo y el empaquetado, con cada
  compuerta asignada a un chip y a sus pines.

El modelo se valida al construirse: cada red tiene un único driver, no hay redes sin driver,
se respeta la aridad de cada compuerta y no hay lazos combinacionales. Las constantes son
redes reservadas (`$0`, `$1`). `build.py` aplica hashing estructural para que una
subexpresión repetida se instancie una sola vez.

## Consecuencias

- Las salidas son funciones puras del netlist; no guardan estado propio.
- La verificación de equivalencia (`check_equivalence`) opera sobre el netlist, así que una
  sola puerta de aceptación cubre todas las transformaciones.
- Un netlist inválido no puede existir en memoria: falla al construirse.

## Alternativas descartadas

- **Usar el AST como modelo central**: un árbol no representa subexpresiones compartidas ni
  fan-out, que es justamente lo que importa al contar carga y chips.
- **Validar solo al final del pipeline**: los errores aparecerían lejos de su causa.
