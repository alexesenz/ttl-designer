# 02 — El mapeo tecnológico minimiza chips, no compuertas

- **Sección**: §COSTO-IC
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: —
- **Tests**: —

---

## Contexto

La minimización clásica (Quine-McCluskey, Karnaugh) reduce términos y literales. En lógica
discreta eso no equivale a reducir el hardware: las compuertas vienen empaquetadas (un 7400
trae 4 NAND de 2 entradas, un 7404 trae 6 inversores). Por ejemplo, una función que en forma
mixta usa una AND, una OR y una NOT ocupa tres chips distintos, mientras que su equivalente
NAND-NAND puede caber completa en un solo 7400.

## Decisión

La función de costo del mapeo tecnológico y del empaquetado es, en orden lexicográfico:

1. número de ICs;
2. profundidad lógica (retardo en el peor caso);
3. número de compuertas.

Se ofrecen estrategias seleccionables (mixta, solo NAND, solo NOR, mínimo de ICs) y la
herramienta muestra la comparación entre ellas, porque esa comparación es material didáctico.

## Consecuencias

- El resultado de QM es un punto de partida, no el circuito final.
- El mapeo necesita el catálogo (compuertas por encapsulado y fan-in disponible): §CATALOGO.
- Las compuertas que sobran en un chip se reportan como libres, y sus entradas reciben el
  tratamiento de entradas no usadas en el BOM.

Estado de implementación: decisión tomada; el mapeo está pendiente de que exista el catálogo.

## Alternativas descartadas

- **Minimizar compuertas o literales**: optimiza una métrica que no corresponde al costo
  real del montaje.
- **Usar siempre NAND-NAND**: suele ganar, pero no siempre. Con XOR o inversores sueltos una
  solución mixta puede ocupar menos chips.
