# Contribuir

## Entorno

```bash
python -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/pre-commit install
```

Los hooks usan las herramientas del entorno activo: activa `.venv` (`source .venv/bin/activate`)
antes de hacer commit. El hook de pre-commit corre `ruff check`, `ruff format --check`, `mypy` (modo estricto) y
`pytest`. El CI corre lo mismo en Python 3.11, 3.12 y 3.13; un PR en rojo no se integra.

## Cambios

- Una rama por cambio, creada desde `main`; todo entra por pull request.
- El mensaje de commit cuenta la historia completa: qué cambió, por qué, cómo se validó y
  qué tests lo fijan. La primera línea, en imperativo y de menos de 72 caracteres.
- Si el cambio implica una decisión de diseño, agrega o amplía un archivo en
  `docs/decisions/` (formato en su `README.md`) y cita su `§id` desde el código afectado.
- Toda transformación nueva del netlist debe tener un test de equivalencia contra la
  especificación (ver `check_equivalence`).
- Cambios al catálogo: cita la fuente oficial de cada valor y actualiza `library/SOURCES.md`.
  Ver `CATALOG_CONTRACT.md`.

## Qué no se acepta

- PDFs de datasheets u otro material con derechos de terceros.
- Credenciales o secretos de cualquier tipo.
- Código o texto copiado de proyectos con licencia incompatible con MIT.
- Valores del catálogo sin fuente, o tests desactivados para dejar el CI en verde.

## Idioma

Documentación, mensajes de error y commits en español neutro. Los identificadores de
código pueden seguir la convención técnica en inglés cuando sea el término estándar
(`netlist`, `fanout`).

## Licencia

Al contribuir aceptas que tu aporte se distribuya bajo la licencia MIT del proyecto.
