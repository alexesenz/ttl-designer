# Registro de decisiones — índice

Cada archivo documenta una decisión de diseño: el contexto que la motivó, lo que se decidió,
sus consecuencias y las alternativas descartadas. Se leen bajo demanda, cuando se va a tocar
un módulo que cita la sección o cuando algo parece "raro" y hay que saber por qué es así.

Convenciones:

- Nombre `NN-tema-en-minusculas.md`, numeración consecutiva; los números no se reutilizan.
- Cabecera obligatoria: **Sección** (`§id` único que el código puede citar), **Estado**
  (`vigente`, `propuesta` o `reemplazada por NN`), **Fecha**, **Módulos**, **Tests**.
- Cuerpo con `## Contexto`, `## Decisión`, `## Consecuencias` y `## Alternativas descartadas`.
- Una decisión reemplazada no se borra: cambia su estado y apunta a la que la sustituye.

`tests/test_docs_layout.py` verifica que esta tabla liste todos los archivos, que cada
cabecera esté completa, que los módulos y tests citados existan y que cada `§id` usado en
el código resuelva aquí.

| archivo | sección | tema |
|---|---|---|
| [`00-proposito.md`](00-proposito.md) | §PROPOSITO | Para qué existe la herramienta y qué no pretende ser |
| [`01-netlist-fuente-de-verdad.md`](01-netlist-fuente-de-verdad.md) | §NETLIST | El netlist lógico como única fuente de verdad |
| [`02-costo-en-ics.md`](02-costo-en-ics.md) | §COSTO-IC | El mapeo tecnológico minimiza chips, no compuertas |
| [`03-convenciones-de-entrada.md`](03-convenciones-de-entrada.md) | §CONVENCIONES | Orden de variables, MSB y sintaxis de expresiones |
| [`04-catalogo-y-fuentes.md`](04-catalogo-y-fuentes.md) | §CATALOGO | Catálogo 74LS: fuentes oficiales, null antes que suponer |
| [`05-ejes-de-reporte.md`](05-ejes-de-reporte.md) | §EJES | Corrección lógica, DRC eléctrico y BOM como ejes separados |
| [`06-despliegue.md`](06-despliegue.md) | §DESPLIEGUE | Despliegue en Raspberry Pi: puerto 8040, red local y Tailscale |
| [`07-mapeo-y-empaquetado.md`](07-mapeo-y-empaquetado.md) | §MAPEO | Mapeo tecnológico y empaquetado en chips 74LS |
