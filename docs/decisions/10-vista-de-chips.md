# 10 — Vista de chips en SVG: etiquetas de red por pin y tabla de conexiones

- **Sección**: §SVG
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/render/chips.py`
- **Tests**: `tests/test_render_chips.py`

---

## Contexto

La primera salida gráfica debe servir para montar el circuito en protoboard. Dibujar
cables entre chips exige un ruteador y produce cruces que se leen peor que una lista,
sobre todo con más de tres chips. Lo que la persona que monta necesita es saber, pin por
pin, a qué va cada patita.

## Decisión

- Cada chip se dibuja como un DIP en **vista superior** (pin 1 arriba a la izquierda,
  muesca arriba), con el número de pin dentro del cuerpo y una **etiqueta** fuera:
  - nombre de la red (entradas y salidas primarias con su nombre; internas como `n3`);
  - `VCC` / `GND` en los pines de alimentación;
  - `↑R1` en las entradas que van a pull-up, con la referencia real del BOM;
  - `GND` en las entradas a tierra, `libre` en salidas sin usar, `NC` donde corresponda.
- No se dibujan cables. Debajo va una **tabla de conexiones** (red → origen → destinos),
  la lista de **niveles fijos** (cada pull-up con sus pines, pines a GND) y las salidas
  que no necesitan chip.
- Bajo cada chip se indica su capacitor de desacople, tomado de la asignación del BOM.
- El color de una red ayuda a seguirla entre chips, pero **nunca es la única señal**: el
  nombre siempre está escrito. La paleta tiene variante para tema oscuro
  (`prefers-color-scheme`).
- Todo sale de `PhysicalDesign` y de las asignaciones estructuradas del BOM
  (`pin_resistor`, `decoupling`). El SVG no calcula nada propio (§NETLIST).
- Cada etiqueta lleva `data-pin` y, si es una red, `data-net`, para pruebas y para
  interacción futura.

## Consecuencias

- La vista es exacta por construcción. Los tests verifican que cada pin de cada chip
  tenga etiqueta y que cada conexión de `connections()` aparezca en el pin correcto.
- Para ver la lógica (qué compuerta alimenta a cuál) hará falta el esquemático lógico,
  que es otra vista con otro problema de layout.
- Con muchos chips la tabla crece en vertical; no hay paginación.

## Alternativas descartadas

- **Cables ortogonales entre chips**: es la imagen "de libro", pero sin un buen ruteador
  produce cruces ilegibles y no aporta información que la tabla no tenga.
- **Vista de protoboard con posiciones físicas**: depende del tamaño de protoboard de cada
  persona; queda para después si hace falta.
