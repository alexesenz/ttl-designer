# 13 — PROPUESTA: banco de prueba con Raspberry Pi Pico 2 y MicroPython

- **Sección**: §BANCO-PICO
- **Estado**: propuesta
- **Fecha**: 2026-10-19
- **Módulos**: —
- **Tests**: —

---

## Contexto

La herramienta verifica la equivalencia en software (`check_equivalence`), pero el circuito
que se monta en la protoboard puede fallar por causas que el software no ve: un cable en
el pin equivocado, un chip dañado, una entrada sin conectar. Una Raspberry Pi Pico 2
(RP2350) con MicroPython puede manejar las entradas del circuito por GPIO y leer sus
salidas, así que puede llevar la puerta de aceptación al hardware.

Es solo una idea registrada: **no se implementa todavía**. Las cifras de la placa que
aparecen abajo no se han contrastado con el datasheet oficial y están marcadas como tal
(§CATALOGO).

## Decisión

**Uso principal: probador del circuito montado.** El generador produciría un único
`main.py` para la Pico 2 que:

- recorre la tabla de verdad completa, aplicando cada combinación de entradas por GPIO;
- espera un tiempo de asentamiento y lee las salidas;
- compara contra la tabla esperada, con los don't-cares enmascarados;
- reporta por serial (REPL o Thonny) las filas que no coinciden, con su índice Σm, las
  entradas aplicadas y las salidas esperada y leída.

**Uso secundario: emulador.** Un modo del mismo `main.py` que implementa las funciones en
software, para probar la lógica antes de tener los chips. No reproduce retardos ni cargas.

**Fuera de alcance de la primera versión:** medir retardos con PIO. Con el reloj del
RP2350 la resolución quedaría en el orden de los tpd de la familia LS (9–15 ns), al borde
del ruido de medición.

**Generación desde la fuente única** (§NETLIST):

- El `main.py` se genera de la especificación y del diseño físico. Contiene el mapa GPIO ↔
  red (entradas y salidas primarias) y la tabla esperada empaquetada en bits, por salida.
- No hay lógica escrita a mano por circuito.

**Interfaz** (§FRONTEND):

- Una pestaña "Banco de prueba" con el diagrama de conexión Pico 2 ↔ adaptador de niveles ↔
  circuito.
- La asignación de GPIO, editable y guardada en la URL.
- La descarga de `main.py`.

**Niveles eléctricos.** La Pico 2 trabaja a 3.3 V y el circuito a 5 V:

- *Pico → entradas TTL*: 3.3 V supera el VIH mínimo de 2.0 V del catálogo; no hace falta
  adaptación.
- *Salidas TTL → Pico*: el catálogo garantiza VOH mínimo, no máximo. Hay información de que
  los GPIO del RP2350 toleran 5 V con condiciones (alimentación presente, pines no
  analógicos). **FUENTE NO VERIFICADA**: hasta confirmarlo en el datasheet del RP2350, la
  propuesta asume un adaptador de niveles (buffer de entradas tolerantes a 5 V alimentado a
  3.3 V, o divisor resistivo por línea).
- El adaptador iría en un BOM aparte, "banco de prueba", con sus datos en el catálogo y su
  fuente citada, igual que los 74LS. No se mezcla con el BOM del circuito (§EJES).

**Límites explícitos:**

- Entradas + salidas ≤ GPIO disponibles en el cabezal de la Pico 2 (del orden de 26;
  **FUENTE NO VERIFICADA**). Si no alcanzan, la interfaz lo dice en lugar de generar.
- La tabla esperada de 16 entradas ocupa 8 KB por salida, lo que cabe con holgura en la RAM
  del RP2350 (**cifra de RAM sin verificar**).
- Una prueba exhaustiva de 2^16 combinaciones con un asentamiento del orden de decenas de
  microsegundos tarda segundos.

**Verificación sin hardware:**

- El `main.py` generado se ejecutaría en CPython con un módulo `machine` falso que simula el
  circuito a partir del netlist.
- Los tests comprobarían que pasa con el circuito correcto y que detecta fallas inyectadas:
  una salida invertida, dos cables cruzados, una entrada flotante.
- Así el CI no necesita la placa.

## Consecuencias

Si se aprueba:

- Hay que agregar al catálogo la Pico 2 y el adaptador de niveles con fuentes oficiales,
  incluidos el límite de tolerancia a 5 V, el número de GPIO y la RAM.
- La decisión pasaría a `vigente` con su módulo (p. ej. `ttl_designer/export/pico.py`) y sus
  tests. El índice se actualizaría.
- Decisiones abiertas para entonces:
  - modo emulador sí o no;
  - tipo de adaptador;
  - reporte solo serial o también LEDs de pasa/falla.

## Alternativas descartadas

- **Raspberry Pi con Linux (4/5) como probador**: corre Python completo, pero tiene más
  latencia no determinista en GPIO y es excesiva para esta tarea. La Pico es más barata,
  arranca al instante y sus tiempos son predecibles.
- **Solo emulador**: no prueba lo que la herramienta realmente entrega, que es el circuito
  físico con chips reales.
- **Arduino/C++**: viable, pero MicroPython permite generar y leer el código en el mismo
  lenguaje del proyecto y modificarlo sin compilar.
