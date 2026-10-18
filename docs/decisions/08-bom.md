# 08 — Lista de materiales: derivada, con políticas declaradas y huecos explícitos

- **Sección**: §BOM
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/bom.py`, `ttl_designer/electrical.py`
- **Tests**: `tests/test_bom.py`

---

## Contexto

El diseño físico (§MAPEO) dice qué chips hay y qué pines van fijos, pero un circuito
montable necesita además capacitores de desacople, resistencias de pull-up y números de
parte comprables. Parte de esto sale del catálogo (partes comerciales, ciclo de vida,
datasheets) y parte es política de diseño (valores de pasivos), que no debe disfrazarse
de dato de fabricante.

## Decisión

- El BOM se **recalcula** del netlist físico y del catálogo; no guarda estado (§NETLIST).
- **ICs**: una línea por número de parte, con todas sus referencias. Se elige la parte
  comercial del encapsulado pedido (DIP-14 por defecto), prefiriendo ciclo `active` y luego
  Texas Instruments (fuente primaria de §CATALOGO).
- **Desacople**: un capacitor cerámico de **100 nF por IC**, junto al pin Vcc. Fuente: la
  recomendación de TI (SDLS025D) transcrita en `family_defaults.decoupling_recommendation`
  (0.1 µF por pin de alimentación).
- **Bulk**: un electrolítico de **10 µF** en la entrada de alimentación. Es **política** de
  esta herramienta, no un dato de fabricante; es configurable y se puede desactivar.
- **Pull-ups** (§MAPEO): **1 kΩ**, compartidos. Cuántas entradas sostiene uno se **calcula**
  con datos verificados: `n ≤ (Vcc_min − VIH_min) / (IIH·R)`. Con los valores del catálogo
  (4.75 V, 2.0 V, 20 µA, 1 kΩ) da 137 entradas, así que en la práctica basta con uno.
- **Entradas a GND**: no llevan componente; se listan en `gnd_pins` para el cableado.
- **Salidas de colector abierto**: un pull-up por salida, **sin valor**. El catálogo no
  tiene campo para la corriente de fuga en alto, y dimensionarlo sin ese dato sería suponer.
- **Huecos** (`gaps`, tercer eje de §EJES): chip sin parte comercial en el encapsulado,
  ciclo de vida distinto de `active`, contraste con un solo fabricante, campos sin
  verificar, valores sin dimensionar. Pasan aquí los avisos que antes daba el mapeo, porque
  describen la compra y la confianza en los datos, no la lógica.
- **Exportación**: JSON (modelo completo) y CSV (una fila por línea).

## Consecuencias

- Un BOM con `gaps` es entregable, pero los huecos quedan visibles. No hay un indicador
  único de "BOM listo".
- Cambiar el encapsulado (`SOIC-14`) cambia los números de parte y los pasivos a SMD 0805,
  sin tocar el diseño.
- La lista de pines en cada pull-up y en cada capacitor es la base del cableado y del
  esquemático.

## Alternativas descartadas

- **Un pull-up por entrada**: es lo más simple de dibujar, pero multiplica componentes sin
  beneficio eléctrico para entradas LS.
- **Elegir siempre el número de parte más barato**: no hay precios verificados en el
  catálogo, y meterlos sería otra fuente que mantener.
