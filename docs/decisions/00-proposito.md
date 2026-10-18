# 00 — Para qué existe la herramienta

- **Sección**: §PROPOSITO
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: —
- **Tests**: —

---

## Contexto

Diseñar un circuito combinacional con lógica TTL discreta implica una cadena de pasos que
normalmente se hace a mano y por separado: tabla de verdad, mapa de Karnaugh, conversión a
las compuertas disponibles, reparto de compuertas en chips, asignación de pines, revisión de
fan-out y armado de la lista de materiales. Cada paso es mecánico, pero un error en
cualquiera (un pin mal leído, una compuerta de más) solo aparece al montar el circuito.

## Decisión

La herramienta automatiza la cadena completa, de la especificación al circuito montable, y
**explica cada paso**. Lo que entrega: netlist verificado, esquemático lógico y vista de
chips en SVG, BOM exportable (con desacople y pull-ups) y documentación por etapa
generada de forma determinista a partir de la traza de cada transformación.

Alcance del MVP: solo combinacional, entrada por expresión booleana, familia 74LS.

## Consecuencias

- La explicación es un producto, no un añadido: cada módulo de transformación registra qué
  hizo y por qué (ver `QMTrace` en `qm.py`).
- La exactitud de los datos físicos (pinout, retardos, corrientes) es crítica, porque el
  usuario arma el circuito con ellos; de ahí §CATALOGO.

## Alternativas descartadas

- **Simulador gráfico de propósito general** (tipo Logisim): ya existen y no resuelven el
  paso a chips reales ni el BOM.
- **Narrativa generada por LLM como fuente de la explicación**: no es reproducible ni
  verificable. Se admite a futuro solo como capa de redacción sobre la traza determinista.
