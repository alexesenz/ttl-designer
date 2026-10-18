# 05 — Corrección lógica, DRC eléctrico y BOM como ejes separados

- **Sección**: §EJES
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/sim/functional.py`, `ttl_designer/api/routes.py`
- **Tests**: `tests/test_netlist_sim.py`, `tests/test_api.py`

---

## Contexto

Un circuito puede ser lógicamente correcto y aun así no funcionar físicamente (fan-out
excedido, entrada flotante). También puede funcionar y tener un BOM incompleto (una pieza
sin parte comercial resuelta). Si estos problemas se agregan en un único indicador de
"salud", un número verde puede esconder un fallo de otro tipo.

## Decisión

Tres ejes independientes. Cada uno se reporta por separado y ninguno se deriva de otro:

1. **Corrección lógica**: el netlist implementa la especificación en todas las filas,
   salvo los don't-cares (`check_equivalence`, campo `equivalent` de la API).
2. **DRC eléctrico** (pendiente): fan-out, entradas flotantes, salidas en corto, lazos,
   presupuesto de corriente. Cada hallazgo identifica la compuerta o red y el límite del
   catálogo que excede; si el límite es `null`, el hallazgo es "no evaluable".
3. **Huecos del BOM** (pendiente): componentes sin número de parte comercial, datos sin
   verificar heredados del catálogo y decisiones de política aplicadas (pull-ups, desacople).

## Consecuencias

- La API y la documentación muestran los tres ejes por separado.
- Un circuito correcto con DRC en rojo se entrega igual, con el problema declarado; no se
  "corrige" en silencio.

## Alternativas descartadas

- **Un puntaje único de calidad**: es fácil de mostrar, pero vuelve invisible el tipo de
  falla.
