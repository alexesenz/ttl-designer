# SOURCES.md — catálogo 74LS

Acompaña a `ttl_ls_catalog.json`. Generado el 18 de octubre de 2026.
Alcance: rango comercial 74LS (0 a 70 °C). Las variantes militares 54LS quedaron fuera.

## Cómo se leyó cada documento

Los datasheets 74LS de TI son documentos legacy. Hay tres situaciones distintas y conviene saber cuál aplica a cada chip, porque determina la confianza:

1. **Visor HTML de TI con tabla "Pin Functions"** — solo el SN74LS00 (SDLS025D) y el SN74LS14 (SDLS049C) tienen datasheet reformateado. Ahí el pinout y las tablas eléctricas se extrajeron como **texto**, que es el caso más fiable.
2. **PDF de TI con capa de texto** — SN74LS04 (SDLS029C) y SN74LS05 (SDLS030A).
3. **PDF de TI escaneado como imagen** — el resto. En estos casos las páginas se descargaron, se renderizaron a PNG a 150–200 dpi y se **leyeron visualmente**. El "PACKAGE OPTION ADDENDUM" del final sí es texto en todos, y de ahí salen `orderable_parts`, `packages` y `lifecycle`.

En ningún caso se tomó un valor de memoria, de un blog, de Wikipedia ni de una imagen de pinout de terceros.

Nota sobre el segundo fabricante: los PDF de Fairchild se obtuvieron del espejo `media.digikey.com`, que es un distribuidor reconocido. Se verificó en los metadatos de cada PDF que el `creator` sea `FrameMaker+SGML 5.5.6 Fairchild client` y que el pie diga `© 2000 Fairchild Semiconductor Corporation` con su número DS006xxx. En `DM74LS20`, `DM74LS30`, `DM74LS32` y `DM74LS14` los campos Title/Author del PDF fueron reescritos por ALLDATASHEET.COM, pero el cuerpo del documento es el original de Fairchild. onsemi.com, sucesor corporativo de Fairchild, devuelve 403 o HTML a todas las rutas de estos documentos: no fue utilizable.

## Criterio de resolución de conflictos

- **Valor principal: TI.** Donde TI y Fairchild difieren, el JSON lleva el valor de TI.
- **Límites máximos y mínimos: peor caso.** Se verificó que en todas las discrepancias encontradas el valor de TI **ya es** el peor caso, así que ambos criterios coinciden y no hubo que mezclar fuentes. Los `tPLH`/`tPHL` máximos de TI son mayores que los de Fairchild, el `IIL` máximo de TI es más negativo, y el `VOH` mínimo de TI es más bajo.
- **Nada se infiere.** Donde el documento no da el dato, el campo va en `null` y la ruta queda listada en `unverified` del chip.

## Tabla de fuentes

| id | fabricante | documento | revisión | URL |
|---|---|---|---|---|
| `FAIRCHILD-DS006344` | Fairchild Semiconductor | DM74LS03 Quad 2-Input NAND Gates with Open-Collector Outputs | DS006344, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS03.pdf |
| `FAIRCHILD-DS006345` | Fairchild Semiconductor | DM74LS04 Hex Inverting Gates | DS006345, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS04.pdf |
| `FAIRCHILD-DS006346` | Fairchild Semiconductor | DM74LS05 Hex Inverters with Open-Collector Outputs | DS006346, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS05.pdf |
| `FAIRCHILD-DS006347` | Fairchild Semiconductor | DM74LS08 Quad 2-Input AND Gate | DS006347, Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS08.pdf |
| `FAIRCHILD-DS006349` | Fairchild Semiconductor | DM74LS10 Triple 3-Input NAND Gate | DS006349, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS10.pdf |
| `FAIRCHILD-DS006350` | Fairchild Semiconductor | DM74LS11 Triple 3-Input AND Gate | DS006350, Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS11.pdf |
| `FAIRCHILD-DS006353` | Fairchild Semiconductor | DM74LS14 Hex Inverter with Schmitt Trigger Inputs | DS006353, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS14.pdf |
| `FAIRCHILD-DS006355` | Fairchild Semiconductor | DM74LS20 Dual 4-Input NAND Gate | DS006355, June 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS20.pdf |
| `FAIRCHILD-DS006359` | Fairchild Semiconductor | DM74LS27 Triple 3-Input NOR Gate | DS006359, May 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS27.pdf |
| `FAIRCHILD-DS006360` | Fairchild Semiconductor | DM74LS30 8-Input NAND Gate | DS006360, May 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS30.pdf |
| `FAIRCHILD-DS006361` | Fairchild Semiconductor | DM74LS32 Quad 2-Input OR Gate | DS006361, June 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS32.pdf |
| `FAIRCHILD-DS006380` | Fairchild Semiconductor | DM74LS86 Quad 2-Input Exclusive-OR Gate | DS006380, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS86.pdf |
| `FAIRCHILD-DS006389` | Fairchild Semiconductor | DM74LS132 Quad 2-Input NAND Gate with Schmitt Trigger Input | DS006389, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS132.pdf |
| `FAIRCHILD-DS006439` | Fairchild Semiconductor | DM74LS00 Quad 2-Input NAND Gate | DS006439, August 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS00.pdf |
| `FAIRCHILD-DS006441` | Fairchild Semiconductor | DM74LS02 Quad 2-Input NOR Gate | DS006441, May 1986 - Revised March 2000 | https://media.digikey.com/pdf/Data%20Sheets/Fairchild%20PDFs/DM74LS02.pdf |
| `TI-SDLS025D` | Texas Instruments | SNx400, SNx4LS00, and SNx4S00 Quadruple 2-Input Positive-NAND Gates | SDLS025D, December 1983 - Revised May 2017 | https://www.ti.com/lit/ds/symlink/sn74ls00.pdf |
| `TI-SDLS027` | Texas Instruments | Quadruple 2-Input Positive-NOR Gates | SDLS027, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls02.pdf |
| `TI-SDLS028` | Texas Instruments | Quadruple 2-Input Positive-NAND Gates With Open-Collector Outputs | SDLS028, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls03.pdf |
| `TI-SDLS029C` | Texas Instruments | Hex Inverters | SDLS029C, December 1983 - Revised January 2004 | https://www.ti.com/lit/ds/symlink/sn74ls04.pdf |
| `TI-SDLS030A` | Texas Instruments | Hex Inverters With Open-Collector Outputs | SDLS030A, December 1983 - Revised November 2003 | https://www.ti.com/lit/ds/symlink/sn74ls05.pdf |
| `TI-SDLS033` | Texas Instruments | Quadruple 2-Input Positive-AND Gates | SDLS033, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls08.pdf |
| `TI-SDLS035A` | Texas Instruments | Triple 3-Input Positive-NAND Gates | SDLS035A, December 1983 - Revised April 2003 (paginas LS rotuladas SDLS035, Revised March 1988) | https://www.ti.com/lit/ds/symlink/sn74ls10.pdf |
| `TI-SDLS047` | Texas Instruments | Quadruple 2-Input Positive-NAND Schmitt Triggers | SDLS047, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls132.pdf |
| `TI-SDLS049C` | Texas Instruments | SNx414 and SNx4LS14 Hex Schmitt-Trigger Inverters | SDLS049C, December 1983 - Revised November 2016 | https://www.ti.com/lit/ds/symlink/sn74ls14.pdf |
| `TI-SDLS079` | Texas Instruments | Dual 4-Input Positive-NAND Gates | SDLS079, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls20.pdf |
| `TI-SDLS089` | Texas Instruments | Triple 3-Input Positive-NOR Gates | SDLS089, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls27.pdf |
| `TI-SDLS099` | Texas Instruments | 8-Input Positive-NAND Gates | SDLS099, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls30.pdf |
| `TI-SDLS100` | Texas Instruments | Quadruple 2-Input Positive-OR Gates | SDLS100, December 1983 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls32.pdf |
| `TI-SDLS124` | Texas Instruments | Quadruple 2-Input Exclusive-OR Gates (SN54LS86A / SN74LS86A) | SDLS124, December 1972 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls86a.pdf |
| `TI-SDLS131` | Texas Instruments | Triple 3-Input Positive-AND Gates | SDLS131, April 1985 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls11.pdf |
| `TI-SDLS139` | Texas Instruments | Dual 4-Input Positive-AND Gates | SDLS139, April 1985 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls21.pdf |
| `TI-SDLS151` | Texas Instruments | Quadruple 2-Input Exclusive-NOR Gates With Open-Collector Outputs | SDLS151, December 1972 - Revised March 1988 | https://www.ti.com/lit/ds/symlink/sn74ls266.pdf |
| `TI-SDYA009C` | Texas Instruments | Designing With Logic | SDYA009C, June 1997 | https://www.ti.com/lit/pdf/sdya009 |
## Tabla de discrepancias entre fabricantes

| chip | campo | valor TI | valor Fairchild | adoptado | criterio |
|---|---|---|---|---|---|
| 74LS00 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; además peor caso |
| 74LS00 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 10 / 10 ns (CL=15 pF) | 15 / 15 | TI principal; peor caso |
| 74LS00 | VOH mín | 2.5 V | 2.7 V | 2.5 | peor caso (campo de familia) |
| 74LS02 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 13 / 10 ns | 15 / 15 | TI principal; peor caso |
| 74LS02 | `iil_max_mA` | −0.4 mA | −0.4 mA | −0.4 | coinciden |
| 74LS04 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS04 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 10 / 10 ns | 15 / 15 | TI principal; peor caso |
| 74LS08 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS08 | `tplh_max_ns` / `tphl_max_ns` | 15 / 20 ns | 13 / 11 ns | 15 / 20 | TI principal; peor caso |
| 74LS10 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS10 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 10 / 10 ns | 15 / 15 | TI principal; peor caso |
| 74LS11 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS11 | `tplh_max_ns` / `tphl_max_ns` | 15 / 20 ns | 13 / 11 ns | 15 / 20 | TI principal; peor caso |
| 74LS14 | VOH mín | 2.4 V | 2.7 V | 2.4 | peor caso; excepción de chip no representable en el esquema, ver abajo |
| 74LS14 | `tplh`/`tphl` | typ 15 / max 22 ns | min 5 / max 22 ns | typ 15 / max 22 | TI principal; los máximos coinciden |
| 74LS20 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS20 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 10 / 10 ns | 15 / 15 | TI principal; peor caso |
| 74LS27 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS27 | `tplh_max_ns` / `tphl_max_ns` | 15 / 15 ns | 13 / 10 ns | 15 / 15 | TI principal; peor caso |
| 74LS30 | `iil_max_mA` | −0.4 mA | −0.4 mA | −0.4 | coinciden |
| 74LS30 | `tplh_max_ns` / `tphl_max_ns` | 15 / 20 ns | 12 / 15 ns | 15 / 20 | TI principal; peor caso |
| 74LS32 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS32 | `tplh_max_ns` / `tphl_max_ns` | 22 / 22 ns | 11 / 11 ns | 22 / 22 | TI principal; peor caso |
| 74LS86 | `iil_max_mA` | −0.8 mA (LS86A) | −0.6 mA (LS86) | −0.8 | TI principal; peor caso. Son referencias distintas, ver nota del '86 |
| 74LS86 | ICCH / ICCL | solo un `ICC`: typ 6.1 / max 10 mA | ICCH 6.1/10 y ICCL 9/15 mA | `null` en los 4 campos | TI no separa los estados y no se reparte un valor por inferencia |
| 74LS86 | `tplh`/`tphl` | 4 filas según el otro input | 2 filas | fila "other input low" | elección propia, marcada en `unverified` |
| 74LS03 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS03 | `tplh_max_ns` / `tphl_max_ns` | 32 / 28 ns | 20 / 15 ns | 32 / 28 | TI principal; peor caso |
| 74LS03 | fuga de salida en alto | `IOH` 0.1 mA @ VOH=5.5 V | `ICEX` 100 µA @ VO=5.5 V | — | mismo valor, distinto nombre de parámetro; no hay campo en el esquema |
| 74LS05 | `iil_max_mA` | −0.4 mA | −0.36 mA | −0.4 | TI principal; peor caso |
| 74LS05 | `tplh_max_ns` / `tphl_max_ns` | 32 / 28 ns | 20 / 15 ns | 32 / 28 | TI principal; peor caso |
| 74LS132 | VT+ / VT− / histéresis | 1.6 / 0.8 / 0.8 V typ | idénticos | TI | coinciden |
| 74LS14 | VT+ / VT− / histéresis | 1.6 / 0.8 / 0.8 V typ | idénticos | TI | coinciden |

Fairchild documenta además una segunda condición de carga, **CL = 50 pF**, que TI no tabula para estos dispositivos. No se incorporó porque el esquema solo admite un juego de condiciones por chip; si la herramienta va a simular con cargas mayores, esos números están en los PDF de Fairchild listados arriba.

### Confirmación cruzada de pinouts

Los pinouts de TI y Fairchild **coinciden pin por pin en los 15 chips con dos fuentes**, incluidos los tres casos delicados:

- **74LS02**: salida antes de las entradas, confirmado por los dos (1=1Y, 2=1A, 3=1B).
- **74LS20**: NC en los pines **3 y 11**, confirmado por los dos.
- **74LS30**: NC en los pines **9, 10 y 13**, confirmado por los dos.

Corrección de una suposición del encargo: el 74LS10 y el 74LS11 **sí comparten** el mismo mapa de pines DIP-14 (ambos triples de 3 entradas, 1A=1, 1B=2, 1C=13, 1Y=12, etc.). Lo que cambia entre ellos es la función y el consumo, no el pinout. Se leyeron por separado de su propio diagrama, no se extrapoló uno del otro.

### Notas por chip que afectan el uso del catálogo

**74LS86 — la referencia que está en el JSON no es la que documenta TI.** `https://www.ti.com/lit/ds/symlink/sn74ls86.pdf` devuelve 404. El único documento vigente es **SN74LS86A** (SDLS124) y de ahí salen todos los valores, incluido `iil_max_mA = −0.8`. El campo `part` quedó como `"74LS86"` porque así se pidió, pero está listado en `unverified` por esta razón. Además las páginas técnicas de ese PDF llevan sello **"OBSOLETE – No Longer Available"** aunque el addendum siga listando referencias activas: si el catálogo alimenta un BOM, conviene confirmar disponibilidad antes de comprometer el diseño.

**74LS21 y 74LS266 — una sola fuente.** `DM74LS21.pdf` da 404 en el espejo de Digi-Key (se probaron cuatro variantes de nombre en el mismo host) y no existe un `DM74LS266`. onsemi devuelve 403. No se recurrió a espejos de terceros no reconocidos. Ambos chips quedan con TI como única fuente, y eso es la justificación formal del único fallo de validación.

**74LS14 — `timing.test_conditions.rl_ohm` es `null` a propósito.** La tabla 6.6 de SDLS049C es común a SNx414 y SNx4LS14 y la celda dice literalmente "RL = 400 Ω and CL = 15 pF, **or** RL = 2 kΩ and CL = 15 pF". No se puede atribuir un valor único a la columna LS sin elegir por cuenta propia, así que no se eligió.

**74LS14 — VOH mínimo 2.4 V contra 2.5 V de familia.** El `voh_min_V` de `family_defaults` es 2.5 V, tomado del '00. El '14 especifica 2.4 V. El esquema no tiene campo de VOH por chip, así que esta excepción vive solo en este documento: **para chequeo de márgenes en el '14, usar 2.4 V, no el valor de familia.**

**Los tres de colector abierto (74LS03, 74LS05, 74LS266) requieren resistencia de pull-up externa.** Ninguno especifica VOH como parámetro de salida; en su lugar dan corriente de fuga en estado alto: `IOH` máx **0.1 mA** @ VOH = 5.5 V en el '03 y el '05, y `IOH` máx **100 µA** @ VOH = 5.5 V en el '266. `ios_min_mA` e `ios_max_mA` quedan en `null` porque la corriente de cortocircuito no aplica a una salida sin pull-up activo, no porque falte el dato. Ningún datasheet de TI da un valor recomendado de resistencia; Fairchild incluye "Pull-Up Resistor Equations" en el '03 y el '05, pero están embebidas como imagen y no se transcribieron.

**`iil_max_mA` nulo no significa desconocido.** En casi todos los chips el campo está en `null` porque el valor medido es **−0.4 mA**, idéntico al de familia, y el esquema pide poblarlo solo cuando difiere. Las excepciones reales, con valor explícito en el JSON, son el **74LS86 (−0.8 mA)** y el **74LS266 (−0.8 mA)**.

**`output_type` es derivado, no literal.** Ningún datasheet de TI escribe "totem-pole". En los 14 chips de salida activa el valor se derivó del esquemático de salida (pull-up activo de 120 Ω o 150 Ω más Darlington, sin pin de pull-up externo), y por eso `output_type` aparece en `unverified` de esos chips. En los tres de colector abierto sí es literal: lo dice el título del documento.

**`fanout_ls_loads` es `null`.** Se buscó una afirmación explícita en SDLS025D, SDYA009C "Designing With Logic", SDYA010 "Input and Output Characteristics of Digital Integrated Circuits" y SCBA004E, y ninguno da un número de cargas LS. Existe la pista de que onsemi AN-319 contiene una tabla con 74LS→74LS = 20, pero onsemi bloquea el acceso con 403 y la cifra solo aparecía en un resumen de buscador, no en el documento leído. **No se calculó dividiendo IOL/IIL**, conforme a la instrucción. Si la herramienta necesita el fan-out, el cálculo le corresponde a ella a partir de `iol_max_mA` e `iil_max_mA`, con la advertencia de que entradas de reloj y habilitación de otros dispositivos LS suelen contar como dos unidades de carga.

**Errata de TI que afecta la lectura de `family_defaults`.** En la tabla 6.3 de SDLS025D, TI etiqueta dos filas como `SN7LS400` y `SN5LS400`; son erratas por SN74LS00 y SN54LS00, presentes igual en el visor HTML y en el PDF. La lectura se resolvió por coherencia: la fila de VIL 0.7 V está etiquetada explícitamente `SN54LS00`, y el `IOL = 8 mA (SN74LS00)` de la tabla 6.6 concuerda con la fila de 8 mA. De ahí `vil_max_V = 0.8` e `iol_max_mA = 8`.

**VOL tiene dos condiciones.** 0.4 V máx @ IOL = 4 mA y 0.5 V máx @ IOL = 8 mA. En `family_defaults` se puso la de mayor corriente, **0.5 V @ 8 mA**, que es la que aplica al rango comercial según las condiciones recomendadas de operación.

## Campos marcados FUENTE NO VERIFICADA

Lista consolidada, 66 entradas en chips más `family_defaults.fanout_ls_loads`. Cada ruta corresponde al campo tal como aparece en el JSON, y está replicada en el arreglo `unverified` del chip.

| chip | campo |
|---|---|
| 74LS00 | `output_type` |
| 74LS00 | `schmitt_trigger` |
| 74LS00 | `electrical.iil_max_mA` |
| 74LS00 | `electrical.schmitt` |
| 74LS02 | `output_type` |
| 74LS02 | `schmitt_trigger` |
| 74LS02 | `electrical.iil_max_mA` |
| 74LS02 | `electrical.schmitt` |
| 74LS04 | `output_type` |
| 74LS04 | `schmitt_trigger` |
| 74LS04 | `electrical.iil_max_mA` |
| 74LS04 | `electrical.schmitt` |
| 74LS08 | `output_type` |
| 74LS08 | `electrical.iil_max_mA` |
| 74LS08 | `electrical.schmitt` |
| 74LS10 | `output_type` |
| 74LS10 | `electrical.iil_max_mA` |
| 74LS10 | `electrical.schmitt` |
| 74LS11 | `output_type` |
| 74LS11 | `electrical.iil_max_mA` |
| 74LS11 | `electrical.schmitt` |
| 74LS14 | `output_type` |
| 74LS14 | `electrical.iil_max_mA` |
| 74LS14 | `timing.test_conditions.rl_ohm` |
| 74LS20 | `output_type` |
| 74LS20 | `electrical.iil_max_mA` |
| 74LS20 | `electrical.schmitt` |
| 74LS21 | `output_type` |
| 74LS21 | `electrical.iil_max_mA` |
| 74LS21 | `electrical.schmitt` |
| 74LS21 | `datasheets[1]` |
| 74LS27 | `output_type` |
| 74LS27 | `electrical.iil_max_mA` |
| 74LS27 | `electrical.schmitt` |
| 74LS30 | `output_type` |
| 74LS30 | `electrical.iil_max_mA` |
| 74LS30 | `electrical.schmitt` |
| 74LS32 | `output_type` |
| 74LS32 | `electrical.iil_max_mA` |
| 74LS32 | `electrical.schmitt` |
| 74LS86 | `part` |
| 74LS86 | `output_type` |
| 74LS86 | `electrical.icch_typ_mA` |
| 74LS86 | `electrical.icch_max_mA` |
| 74LS86 | `electrical.iccl_typ_mA` |
| 74LS86 | `electrical.iccl_max_mA` |
| 74LS86 | `electrical.schmitt` |
| 74LS86 | `timing.tplh_typ_ns` |
| 74LS86 | `timing.tplh_max_ns` |
| 74LS86 | `timing.tphl_typ_ns` |
| 74LS86 | `timing.tphl_max_ns` |
| 74LS132 | `output_type` |
| 74LS132 | `electrical.iil_max_mA` |
| 74LS03 | `electrical.ios_min_mA` |
| 74LS03 | `electrical.ios_max_mA` |
| 74LS03 | `electrical.schmitt` |
| 74LS05 | `electrical.ios_min_mA` |
| 74LS05 | `electrical.ios_max_mA` |
| 74LS05 | `electrical.schmitt` |
| 74LS266 | `electrical.icch_typ_mA` |
| 74LS266 | `electrical.icch_max_mA` |
| 74LS266 | `electrical.iccl_typ_mA` |
| 74LS266 | `electrical.iccl_max_mA` |
| 74LS266 | `electrical.ios_min_mA` |
| 74LS266 | `electrical.ios_max_mA` |
| 74LS266 | `electrical.schmitt` |
| 74LS266 | `datasheets[1]` || (family_defaults) | `fanout_ls_loads` |

## Resultado de las validaciones

Ejecutadas con un script de Python sobre el archivo entregado, no a mano. Resultado literal:

```
[PASS]  V1  JSON parsea sin errores                       -- 17 chips
[PASS]  V0  conteo de chips                               -- 17 (14 núcleo + 3 extendido)
[PASS]  V2  gates_per_package e inputs_per_gate coherentes-- 17/17
[PASS]  V3  sin pines repetidos y todos en 1..package_pins-- 17/17
[PASS]  V4  cobertura exacta de 1..package_pins           -- 17/17 cubren 1..14
[PASS]  V5  timing typ <= max                             -- todos los pares con ambos valores
[PASS]  V5b corriente de alimentación typ <= max          -- todos
[FALLA] V6  >=2 datasheets de fabricantes distintos       -- 74LS21 y 74LS266
[PASS]  V7  todo id de sources existe en source_index     -- 33 ids resueltos
[PASS]  V8  coherencia schmitt_trigger vs electrical.schmitt
[PASS]  V9  open_collector sin IOS (no aplica)            -- 74LS03, 74LS05, 74LS266
```

Detalle de cada una:

**V1 — el JSON parsea.** Pasa. 17 objetos en `chips`, 33 entradas en `source_index`.

**V2 — `len(gates) == gates_per_package` y `len(inputs) == inputs_per_gate` en cada compuerta.** Pasa en los 17. Cubre los casos no triviales: el '30 con una sola compuerta de 8 entradas, el '20 y el '21 con dos de 4, los triples de 3 entradas y los hex de 1 entrada.

**V3 — ningún pin repetido dentro de un chip, y todos entre 1 y `package_pins`.** Pasa en los 17.

**V4 — el conjunto `{gates.inputs, gates.output, vcc, gnd, nc_pins}` cubre exactamente 1..`package_pins`.** Pasa en los 17. Esta es la validación que atrapa un NC olvidado, y es la razón por la que los NC del '20, '21 y '30 están poblados: sin ellos el chip no cerraría 1..14.

**V5 — `typ <= max` en cada par de timing.** Pasa. Solo se evaluaron pares donde ambos valores existen; los pares con un `null` se saltan por diseño, no se asumen.

**V5b — añadida por mí: `typ <= max` en ICCH e ICCL.** Pasa. No estaba en el encargo, pero es el mismo tipo de error y era gratis comprobarlo.

**V6 — cada chip con dos datasheets de fabricantes distintos. FALLA en 2 de 17.** 15 chips tienen TI más Fairchild. **74LS21** y **74LS266** quedan con TI únicamente, por las razones de acceso documentadas arriba. Es el único incumplimiento del encargo y queda aquí justificado en lugar de disimulado.

**V7 — añadida por mí: todo id en `sources` existe en `source_index`.** Pasa, 33 ids. Evita referencias colgantes cuando la herramienta resuelva la procedencia de un valor.

**V8 — añadida por mí: coherencia entre `schmitt_trigger` y `electrical.schmitt`.** Pasa. Solo el '14 y el '132 tienen `schmitt_trigger: true`, y son los dos únicos con el objeto de umbrales poblado.

**V9 — añadida por mí: ningún chip de colector abierto trae IOS.** Pasa. Los tres de colector abierto tienen `ios_min_mA` e `ios_max_mA` en `null`, que es lo correcto físicamente.

### Lo que estas validaciones no comprueban

Son chequeos de consistencia estructural. **Ninguna de ellas verifica que un número sea el del datasheet**: si un valor se hubiera transcrito mal pero respetara `typ <= max`, las nueve seguirían pasando. La garantía de los valores es la trazabilidad de la tabla de fuentes y las transcripciones literales de pinouts y tablas que quedaron en el registro de extracción, no este script.
