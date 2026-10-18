# 11 — Esquemático lógico: capas por nivel, ruteo por canales con carriles

- **Sección**: §ESQUEMATICO
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/render/schematic.py`
- **Tests**: `tests/test_render_schematic.py`

---

## Contexto

La vista de chips (§SVG) sirve para montar, pero no muestra la lógica: qué compuerta
alimenta a cuál. Un esquemático con cables necesita layout y ruteo. Python no tiene un
auto-ruteador ortogonal confiable, y depender de un motor JavaScript rompería la regla de
generar el SVG en el servidor.

## Decisión

- **Qué se dibuja**: el netlist **mapeado**, con las celdas reales (NAND, NOR, XOR…) y su
  ubicación `U1A`, para que coincida con la vista de chips y el BOM (§NETLIST). Las
  entradas fijas se muestran como `↑R1` / `GND` junto al pin, sin cable.
- **Símbolos** ANSI de forma distintiva: AND en D, OR curvo, XOR con curva extra,
  inversores con burbuja.
- **Layout** estilo Sugiyama simplificado:
  1. Columnas por nivel lógico: entradas a la izquierda, salidas a la derecha.
  2. Una red que salta columnas recibe un **nodo ficticio** en cada columna intermedia y
     la cruza en línea recta. Así ningún cable pasa por encima de una compuerta.
  3. Orden en cada columna por **baricentro**, con barridos de ida y vuelta.
  4. Posición vertical alineada con los predecesores, sin solapes.
- **Ruteo por canales**: entre dos columnas, cada red que cruza tiene su **carril
  vertical** propio. Una red con un solo punto a cada lado a la misma altura va recta,
  sin carril. Los carriles se ordenan con una restricción: si una red sale a la altura y
  y otra entra a esa misma altura, el carril de la primera va a la izquierda. Si no, sus
  tramos horizontales se montarían.
- **Puntos de unión** solo donde se encuentran tres o más tramos de la misma red.
- Cada cable, compuerta y terminal lleva atributos `data-*` (`data-net`, `data-gate`,
  `data-bbox`, `data-io`) y puntos de pin invisibles, para verificar la geometría en tests.

## Consecuencias

- Los tests verifican la geometría, no la apariencia, en los circuitos dorados y en 25
  circuitos aleatorios:
  - cada red conecta su origen con todos sus destinos;
  - ningún cable atraviesa una compuerta ajena;
  - no hay tramos colineales de redes distintas encimados.

  Se comprobó que los tres chequeos detectan una red partida, un tramo encimado y un cable
  dentro de una compuerta.
- Los cruces entre redes son inevitables y no se minimizan más allá del baricentro. Con
  circuitos de 20 o más compuertas el dibujo es denso pero correcto.
- Si un ciclo de restricciones entre carriles llegara a ocurrir, se rompe tomando el
  primero pendiente. No se ha visto en las pruebas, pero el test de encimado lo
  detectaría.

## Alternativas descartadas

- **ELK/Graphviz**: buen layout, pero agregan una dependencia nativa o JavaScript y su
  ruteo ortogonal no garantiza la ausencia de encimados que aquí se prueba.
- **Cables diagonales o curvos**: más fáciles de rutear, pero no es la convención de un
  esquemático digital y se leen peor.
