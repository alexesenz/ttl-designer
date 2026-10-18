# Contrato del catálogo 74LS

Especificación de `library/ttl_ls_catalog.json`, el archivo del que la herramienta obtiene
pinouts y datos eléctricos de cada chip. La autoridad es `ttl_designer/models/catalog.py`:
si este documento y el modelo difieren, manda el modelo, y este documento debe corregirse.
El porqué de las reglas de fuentes está en `docs/decisions/04-catalogo-y-fuentes.md`
(§CATALOGO).

## Archivos

| archivo | contenido |
|---|---|
| `library/ttl_ls_catalog.json` | el catálogo; JSON válido, sin comentarios |
| `library/SOURCES.md` | fuentes, discrepancias entre fabricantes, campos sin verificar y resultado de las validaciones |

## Reglas de fuentes

- Solo datasheets oficiales de fabricante. TI es la fuente primaria; onsemi/Fairchild
  (DM74LS) y, como respaldo, Motorola/NXP/ST en sitios de fabricante o distribuidores.
- Nunca blogs, wikis, tutoriales ni imágenes de pinout de terceros.
- Cada chip se contrasta con al menos dos fabricantes. Si difieren: el típico se toma de TI,
  los límites máximos y mínimos del peor caso, y la discrepancia se registra en `SOURCES.md`.
- Dato sin fuente confiable → `null` y su ruta en `unverified`. No se infiere.
- Pinouts leídos del diagrama de conexiones de cada datasheet, chip por chip.
- Rango comercial 74LS (0 a 70 °C); se ignoran las variantes militares 54LS.
- Los PDFs no se versionan; se citan por URL y revisión.

## Chips

Núcleo: 74LS00, 74LS02, 74LS04, 74LS08, 74LS10, 74LS11, 74LS20, 74LS21, 74LS27, 74LS30,
74LS32, 74LS86, 74LS14, 74LS132. Extendidos, de colector abierto: 74LS03, 74LS05, 74LS266.

## Estructura

Las unidades van en el sufijo del nombre de cada campo: `_V`, `_mA`, `_uA`, `_ns`, `_pF`,
`_ohm`, `_C`. Todo campo numérico admite `null`.

### Raíz

| campo | tipo | notas |
|---|---|---|
| `schema_version` | str | `"1.0"` |
| `family` | str | `"74LS"` |
| `generated` | str \| null | fecha ISO |
| `family_defaults` | objeto | ver abajo |
| `chips` | lista | sin `part` repetidos |
| `source_index` | dict id → fuente | toda fuente citada debe existir aquí |

### `family_defaults`

`vcc_min_V`, `vcc_nom_V`, `vcc_max_V`, `vih_min_V`, `vil_max_V`, `voh_min_V`,
`voh_test_ioh_mA`, `vol_max_V`, `vol_test_iol_mA`, `iih_max_uA`, `iil_max_mA`,
`ioh_max_mA`, `iol_max_mA`, `fanout_ls_loads` (int), `unused_input_recommendation` (str),
`decoupling_recommendation` (str), `sources` (lista de ids).

### Chip

| campo | tipo | notas |
|---|---|---|
| `part` | str | `74LS00` |
| `description` | str | `Quad 2-input NAND` |
| `function` | enum | `NAND` `NOR` `AND` `OR` `NOT` `XOR` `XNOR` |
| `inputs_per_gate` | int ≥ 1 | 1 si `function` es `NOT` |
| `gates_per_package` | int ≥ 1 | debe coincidir con `len(gates)` |
| `output_type` | enum | `totem_pole` \| `open_collector` |
| `schmitt_trigger` | bool | |
| `package_pins` | int ≥ 8 | |
| `power_pins` | `{vcc, gnd}` | |
| `nc_pins` | lista int | pines sin conexión |
| `gates` | lista `{id, inputs[], output}` | números de pin reales |
| `electrical` | objeto | `icch_typ_mA`, `icch_max_mA`, `iccl_typ_mA`, `iccl_max_mA`, `ios_min_mA`, `ios_max_mA`, `iil_max_mA` (solo si difiere de la familia), `schmitt` (`vt_pos_typ_V`, `vt_neg_typ_V`, `hysteresis_typ_V`) o `null` |
| `timing` | objeto | `tplh_typ_ns`, `tplh_max_ns`, `tphl_typ_ns`, `tphl_max_ns`, `test_conditions` (`cl_pF`, `rl_ohm`, `vcc_V`, `temp_C`) |
| `packages` | lista `{code, suffix_ti}` | `DIP-14`/`N`, `SOIC-14`/`D` |
| `orderable_parts` | lista | `{manufacturer, part_number, package, lifecycle}`; `lifecycle` ∈ `active` `nrnd` `obsolete` `unknown` |
| `datasheets` | lista `{manufacturer, url, revision}` | |
| `sources` | lista de ids | |
| `unverified` | lista de str | rutas de campo sin fuente confiable |

### Fuente (`source_index[id]`)

`title`, `manufacturer`, `url`, `revision`, `accessed`.

## Validaciones (implementadas en el modelo)

- Ningún campo desconocido en ningún nivel.
- `len(gates) == gates_per_package` y cada compuerta tiene `inputs_per_gate` entradas.
- Ningún pin se repite dentro de un chip.
- `{entradas, salidas, vcc, gnd, nc_pins}` cubre exactamente `1..package_pins`.
- `typ ≤ max` en cada flanco de tiempo.
- Todo id en `sources` existe en `source_index`.

## Cómo se modifica

Editar el catálogo es un acto deliberado: un PR que cita la fuente de cada valor
modificado y actualiza `SOURCES.md`. Ningún camino de ejecución de la herramienta escribe
en el catálogo.
