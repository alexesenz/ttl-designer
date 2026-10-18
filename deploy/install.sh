#!/usr/bin/env bash
# Instala o actualiza ttl-designer como servicio systemd en la Raspberry Pi.
# Uso (como el usuario normal, no root; pide sudo solo para systemd):
#   deploy/install.sh
# Idempotente: crea .venv si falta, reinstala el paquete, reescribe la unidad y reinicia.
set -euo pipefail

SERVICE=ttl-designer
PORT=8040
REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="$(id -un)"

if [ "$(id -u)" -eq 0 ]; then
  echo "error: ejecútalo como el usuario que será dueño del servicio, no como root" >&2
  exit 1
fi

python3 - <<'PY' || { echo "error: se requiere Python >= 3.11" >&2; exit 1; }
import sys
sys.exit(0 if sys.version_info >= (3, 11) else 1)
PY

# El puerto debe estar libre, salvo que lo ocupe este mismo servicio.
if ! systemctl is-active --quiet "$SERVICE" && ss -ltnH "sport = :$PORT" | grep -q .; then
  echo "error: el puerto $PORT ya está en uso por otro proceso:" >&2
  ss -ltnp "sport = :$PORT" >&2 || true
  exit 1
fi

echo "==> entorno virtual e instalación del paquete"
[ -d "$REPO/.venv" ] || python3 -m venv "$REPO/.venv"
"$REPO/.venv/bin/pip" install -q --upgrade pip
"$REPO/.venv/bin/pip" install -q -e "$REPO"

echo "==> unidad systemd"
UNIT_TMP="$(mktemp)"
trap 'rm -f "$UNIT_TMP"' EXIT
sed -e "s|__USER__|$RUN_USER|g" -e "s|__REPO__|$REPO|g" \
  "$REPO/deploy/$SERVICE.service" > "$UNIT_TMP"
sudo install -m 644 "$UNIT_TMP" "/etc/systemd/system/$SERVICE.service"
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE" >/dev/null
sudo systemctl restart "$SERVICE"

echo "==> verificando /health"
for _ in $(seq 1 20); do
  if body="$(curl -fsS "http://127.0.0.1:$PORT/health" 2>/dev/null)"; then
    echo "    $body"
    break
  fi
  sleep 1
done
if [ -z "${body:-}" ]; then
  echo "error: el servicio no respondió en 20 s; revisa: journalctl -u $SERVICE -n 50" >&2
  exit 1
fi

echo "==> direcciones de acceso"
for ip in $(hostname -I); do
  case "$ip" in
    100.*) ;;          # la de Tailscale se lista abajo
    *:*) ;;            # se omite IPv6
    *) echo "    red local: http://$ip:$PORT" ;;
  esac
done
if command -v tailscale >/dev/null 2>&1; then
  ts_ip="$(tailscale ip -4 2>/dev/null | head -n1 || true)"
  [ -n "$ts_ip" ] && echo "    tailscale: http://$ts_ip:$PORT"
  ts_name="$(tailscale status --json 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))' \
    2>/dev/null || true)"
  [ -n "$ts_name" ] && echo "    tailscale: http://$ts_name:$PORT"
else
  echo "    (tailscale no está instalado en este equipo)"
fi

if command -v ufw >/dev/null 2>&1 && sudo ufw status | grep -q "Status: active"; then
  if ! sudo ufw status | grep -q "$PORT"; then
    echo "aviso: ufw está activo y no tiene regla para $PORT; ver docs/DEPLOY_RASPBERRY.md"
  fi
fi
