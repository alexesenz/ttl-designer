# 06 — Despliegue en Raspberry Pi: puerto 8040, red local y Tailscale

- **Sección**: §DESPLIEGUE
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `deploy/ttl-designer.service`, `deploy/install.sh`, `ttl_designer/app.py`
- **Tests**: `tests/test_deploy.py`, `tests/test_api.py`

---

## Contexto

La herramienta corre de forma permanente en una Raspberry Pi que ya aloja otros servicios:
el 8000 es el puerto por defecto de uvicorn y el 8020 lo usa otro servicio. Debe ser
accesible desde la red local y, fuera de casa, por Tailscale. La administra Claude Code en
la propia Pi, así que el procedimiento tiene que ser repetible y verificable sin
interpretación.

## Decisión

- **Puerto 8040**, fijo en la plantilla de la unidad y en `install.sh`. Evita el 8000 (por
  defecto de uvicorn, propenso a choques con cualquier `uvicorn` de desarrollo) y el 8020.
- **Escucha en `0.0.0.0`**: una sola interfaz lógica que cubre la LAN y `tailscale0`, sin
  depender de que Tailscale esté arriba cuando arranca el servicio.
- **systemd** con `Restart=on-failure`, habilitado al arranque, usuario sin privilegios y
  `--workers 1`, sin `--reload`.
- **Instalación por script idempotente** (`deploy/install.sh`). Genera la unidad desde una
  plantilla versionada, verifica `/health` e imprime las URLs. La copia instalada no se edita.
- **`/health` informa versión y commit**, para confirmar que un reinicio tomó el código nuevo.
- **Sin autenticación en la aplicación**; el límite de exposición es la red. No se hace
  port-forwarding ni se usa `tailscale funnel`. Si ufw está activo, se abre solo para la
  subred local y para `tailscale0`.

## Consecuencias

- Cambiar el puerto exige tocar la plantilla y `install.sh` a la vez;
  `tests/test_deploy.py` verifica que coincidan y que la unidad no use `--reload` ni
  escuche solo en localhost.
- Exponer la herramienta a internet requeriría primero una decisión nueva que agregue
  autenticación.
- Con un solo worker, las operaciones largas bloquean a otros usuarios. Es aceptable para
  uso personal; si deja de serlo, rige el invariante de "nace como job".

## Alternativas descartadas

- **Escuchar solo en la IP de Tailscale**: deja fuera la red local y falla si el servicio
  arranca antes que Tailscale.
- **Contenedor Docker**: añade una capa de operación sin beneficio para un único servicio
  Python en una Pi.
- **`tailscale serve` como único acceso**: válido, pero no cubre la red local sin Tailscale
  en cada cliente. Queda como opción adicional.
