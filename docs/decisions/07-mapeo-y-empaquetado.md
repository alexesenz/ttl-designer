# 07 — Mapeo tecnológico y empaquetado en chips 74LS

- **Sección**: §MAPEO
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/techmap/cells.py`, `ttl_designer/techmap/builder.py`, `ttl_designer/techmap/strategies.py`, `ttl_designer/techmap/packing.py`, `ttl_designer/techmap/mapper.py`, `ttl_designer/models/physical.py`
- **Tests**: `tests/test_techmap.py`, `tests/test_golden.py`

---

## Contexto

§COSTO-IC fija qué se minimiza (ICs, luego profundidad, luego compuertas), pero no cómo se
llega al circuito. El netlist lógico tiene compuertas de cualquier fan-in y tipo. El
catálogo ofrece celdas concretas: NAND de 2, 3, 4 y 8 entradas; NOR de 2 y 3; AND de 2,
3 y 4; OR de 2; XOR de 2; NOT. Además hay que decidir qué hacer con las entradas sobrantes
y con las compuertas libres de cada chip. El óptimo global (mapeo más empaquetado) es un
problema combinatorio NP-difícil, así que hace falta una heurística con límites
declarados.

## Decisión

**Candidatos.** Se mapean dos fuentes, cada una con cinco estrategias, y se elige el mejor
candidato que pase `check_equivalence`:

- Fuentes: la forma **minimizada** (SOP de Quine-McCluskey) y la **original** escrita
  por el usuario. La original gana cuando la función tiene estructura XOR (la paridad de 4
  bits ocupa 1 chip escrita con XOR y 6 como SOP).
- Estrategias:
  - `mixta`: celdas directas, con fusión NOT(AND) → NAND y NOT(OR) → NOR cuando la
    compuerta interna no tiene otros consumidores.
  - `nand` y `nor`: universales.
  - `nand+xor` y `nor+xor`: universales, conservando las XOR como celda 7486. El
    sumador completo sale con 7486 + 7400 = 2 ICs.

**Pipeline por candidato.**

1. Descomposición a fan-in acotado (árboles balanceados).
2. Traducción a las primitivas de la estrategia, con cancelación de dobles negaciones,
   plegado de constantes y hashing estructural (`NetBuilder`).
3. Ajuste a celdas: cada compuerta se lleva al menor número de entradas disponible ≥ el
   suyo, rellenando con el valor neutro.
4. Absorción de compuertas sueltas.
5. Asignación a chips y pines.

**Entradas sobrantes** (decisión del usuario, 2026-10-18):

- En AND/NAND y en compuertas libres de inversores: **pull-up de 1 kΩ a Vcc**, compartible
  por varias entradas. Se declara en `ties` con `to = pullup`; el BOM lo materializa.
- En OR/NOR/XOR, el valor neutro es 0: **a GND directo**. Un pull-up daría la función
  equivocada.
- El inversor construido con NAND es `NAND(x, 1)` y no `NAND(x, x)`, para no duplicar la
  carga sobre `x`.

**Absorción.** Se intenta vaciar el último chip de cada tipo reubicando sus compuertas en
ranuras libres de otros chips ya presentes:

- un NOT en una NAND/NOR/XOR libre;
- una compuerta en otra de la misma función con más entradas.

Cada reubicación preserva la función y elimina un chip. Se itera hasta que ninguna mejora.

**Celdas permitidas** (decisión del usuario):

- Colector abierto y Schmitt quedan fuera por defecto; se habilitan con
  `allow_open_collector` / `allow_schmitt`. Una salida de colector abierto genera un
  `tie` de pull-up.
- El 74LS86 se usa aunque tenga campos sin verificar. Sus huecos se reportan en
  `warnings`, separados de la corrección lógica (§EJES).

**Asignación.** Las compuertas se ordenan por nivel lógico y número, y se llenan las
ranuras en el orden del catálogo. Las referencias U1, U2… se asignan por número de parte.
Las ranuras libres reciben sus entradas fijas (`compuerta_libre`) y sus salidas quedan
abiertas.

## Consecuencias

- El resultado es determinista y reproducible; los circuitos dorados de
  `tests/golden/mapping_baseline.json` lo fijan. Moverlos exige regenerar el baseline con
  `scripts/update_golden.py --reason` y explicar el cambio en el commit.
- La API devuelve todos los candidatos, no solo el elegido. La comparación entre
  estrategias es parte de la explicación (§PROPOSITO).
- La heurística no garantiza el óptimo global. Optimizaciones conocidas que no se hacen:
  - compartir términos entre estrategias distintas en un mismo diseño (híbridos
    arbitrarios);
  - reubicar una AND en una NAND libre más un inversor;
  - reordenar compuertas entre chips para acortar el cableado.
- El fan-out y el presupuesto de corriente no se evalúan aquí; pertenecen al DRC (§EJES).

## Alternativas descartadas

- **Mapeo por cobertura de árboles con biblioteca de patrones** (estilo DAGON/ABC):
  óptimo por árbol pero no por chips, que es la métrica que importa; añade complejidad sin
  atacar el costo real.
- **Programación entera para mapeo y empaquetado conjuntos**: daría el óptimo en
  circuitos chicos, pero con tiempos impredecibles y una dependencia de solver.
- **Unir entradas sobrantes a una entrada usada**: no necesita componentes, pero suma
  carga sobre la red que maneja esa entrada. El usuario eligió pull-up.
