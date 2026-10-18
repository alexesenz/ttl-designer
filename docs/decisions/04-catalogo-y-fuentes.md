# 04 — Catálogo 74LS: fuentes oficiales, null antes que suponer

- **Sección**: §CATALOGO
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/models/catalog.py`
- **Tests**: `tests/test_catalog.py`

---

## Contexto

Los datos de los chips (pinout, retardos, corrientes, fan-out) alimentan el empaquetado, la
simulación temporal, el DRC y el BOM. Un pin mal asignado produce un circuito que no
funciona al montarlo. Además, hay trampas conocidas: la disposición del 74LS02 tiene la
salida antes que las entradas, y la del 74LS11 y 74LS27 no sigue el patrón del 7400.
Extrapolar pinouts o rellenar valores de memoria es la forma de fallar más probable.

## Decisión

- El catálogo es **datos** (`library/ttl_ls_catalog.json`), no código. Su estructura está
  especificada en `CATALOG_CONTRACT.md`, y `models/catalog.py` la aplica estrictamente
  (`extra="forbid"`).
- **Fuentes**: solo datasheets oficiales de fabricante. Texas Instruments es la fuente
  primaria; cada chip se contrasta con al menos un segundo fabricante.
- **Discrepancias**: el valor típico se toma de TI. En los límites máximos y mínimos se
  usa el peor caso entre fabricantes. La discrepancia se declara en `SOURCES.md`.
- **Dato sin fuente**: `null` más una entrada en `unverified`. Nunca un valor "típico de la
  familia" escrito de memoria.
- **Validación estructural** en el modelo: número de compuertas igual al declarado,
  entradas por compuerta, pines sin repetir que cubren exactamente `1..N`, típico ≤ máximo
  y referencias de fuente resueltas en `source_index`.
- **Editar el catálogo es un acto deliberado**: un PR con la fuente citada. Ningún camino
  de ejecución escribe en él.
- **No se versionan los PDFs** de datasheets (redistribución): solo URL y revisión.

## Consecuencias

- El empaquetado puede confiar en el pinout sin revalidarlo.
- Un campo `null` debe manejarse río abajo: el DRC o la simulación temporal lo declaran
  como no evaluable, no lo sustituyen.
- El catálogo inicial se genera con un agente con búsqueda web siguiendo el contrato; su
  salida se acepta solo si `load_catalog()` la valida.

## Alternativas descartadas

- **Pinouts como constantes en el código**: mezcla datos con lógica y oculta la fuente.
- **Un YAML por chip**: más fácil de editar a mano, pero dificulta validar referencias
  cruzadas como `source_index` o chips duplicados.
