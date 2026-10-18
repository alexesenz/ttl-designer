# 09 — Chequeo eléctrico (DRC): límites del catálogo, no evaluable antes que suponer

- **Sección**: §DRC
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/drc.py`, `ttl_designer/electrical.py`
- **Tests**: `tests/test_drc.py`

---

## Contexto

Un circuito puede ser lógicamente correcto y fallar en la protoboard: una salida con
demasiadas cargas, una entrada flotante, una fuente que no alcanza. El catálogo no trae
`fanout_ls_loads` (quedó en `null` porque ninguna fuente leída lo afirma), pero sí trae
IOL, IOH, IIL e IIH verificados para la familia.

## Decisión

Reglas, cada una con severidad `error`, `advertencia`, `info` o `no_evaluable`:

- **`fanout_bajo`**: Σ|IIL| de las cargas ≤ |IOL| del driver. **`fanout_alto`**: ΣIIH ≤
  |IOH|. El fan-out se **calcula** con corrientes del catálogo; no se usa el "20" de
  memoria.
- **Carga no estándar**: si un chip declara un IIL distinto del de familia (74LS86, -0.8 mA),
  su IIH no está en el esquema. El fan-out en alto de las redes que lo alimentan queda
  `no_evaluable`; no se escala IIH por proporción.
- **IIL nulo en el chip** significa "igual a la familia" (`CATALOG_CONTRACT.md`) y se usa
  el de familia.
- **Colector abierto**: el nivel alto depende del pull-up → `fanout_alto` no evaluable.
- **`entrada_flotante`**: toda entrada de todo chip debe estar conectada o fija. Verifica
  el empaquetado en vez de confiar en él.
- **`salidas_en_conflicto`**: más de un driver en una red, salvo que todos sean de colector
  abierto.
- **`pullup`**: el nivel con n entradas en un pull-up compartido debe quedar ≥ VIH mín.
- **`entrada_externa`** (info): carga que cada entrada primaria impone a quien la maneje.
- **`entrada_sin_uso`** y **`salida_constante`** (info).
- **`consumo`**: Σ max(ICCH, ICCL) por chip y potencia con Vcc máx. Si un chip no tiene
  ICC verificado, el total lo excluye y se declara `no_evaluable` con el chip señalado.

`ok` significa **sin errores**. Los `no_evaluable` no cuentan como error ni como éxito, y
se muestran aparte (§EJES).

## Consecuencias

- Un diseño con el 74LS86 siempre tendrá hallazgos `no_evaluable` mientras el catálogo no
  tenga su ICC ni el IIH por chip. Es la consecuencia buscada de §CATALOGO.
- El margen de ruido (VOH/VOL contra VIH/VIL) no se evalúa: con salidas LS manejando
  entradas LS se cumple por especificación de familia, y la excepción conocida (VOH 2.4 V
  del 74LS14) no tiene campo en el esquema.
- El análisis de tiempos (ruta crítica con tpd) no es parte del DRC; va con la simulación
  temporal.

## Alternativas descartadas

- **Usar fan-out = 10 o 20 "cargas LS"**: es el número que todos recuerdan, pero ninguna
  fuente leída lo afirma y oculta el caso de cargas no estándar.
- **Mezclar DRC y huecos del BOM en un solo estado**: viola §EJES.
