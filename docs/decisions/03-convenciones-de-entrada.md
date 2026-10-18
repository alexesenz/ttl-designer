# 03 — Orden de variables, MSB y sintaxis de expresiones

- **Sección**: §CONVENCIONES
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/logic/parser.py`, `ttl_designer/logic/truthtable.py`, `ttl_designer/logic/qm.py`
- **Tests**: `tests/test_parser.py`, `tests/test_truthtable.py`

---

## Contexto

Una misma función tiene distintos índices Σm según el orden de las variables y qué bit se
considera el más significativo. Sin una convención fija, la tabla de verdad, los minterms
de la API y los don't-cares que manda el usuario no concuerdan.

## Decisión

- **Orden de variables**: alfabético entre las variables de entrada. Las salidas no pueden
  usarse como entradas (sería realimentación, fuera del alcance combinacional).
- **MSB**: la primera variable es el bit más significativo del índice de fila. Con `A, B, C`,
  la fila 4 es `A=1, B=0, C=0`.
- **Sintaxis**: NOT (`'` `!` `~` `¬`) > AND (`·` `*` `&` `∧` o yuxtaposición) > XOR (`^` `⊕`)
  > OR (`+` `|` `∨`).
- **Identificadores** de varios caracteres: `AB` es una variable; el producto se escribe
  `A B`, `A·B` o `A*B`. Esto permite nombres significativos (`sel0`, `Cin`).
- **Varias salidas** separadas por `;` o salto de línea, con la forma `Nombre = expresión`.

## Consecuencias

- Los don't-cares de la API se expresan con esta misma convención de índices.
- La impresión de expresiones (`Expr.to_str`) usa `·`, `+` y `⊕`, y el resultado se puede
  volver a parsear (verificado por test de ida y vuelta).

## Alternativas descartadas

- **Variables de un solo carácter con AND implícito por yuxtaposición** (`AB` = `A·B`): es la
  convención de libro de texto, pero impide nombres de señal reales y vuelve ambiguas
  entradas como `Cin`.
- **Orden por primera aparición**: hace que el índice Σm dependa de cómo se escribió la
  expresión, no de la función.
