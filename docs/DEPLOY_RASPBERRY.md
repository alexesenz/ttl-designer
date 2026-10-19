# Despliegue en la Raspberry Pi

Procedimiento para dejar ttl-designer corriendo como servicio permanente en la Raspberry
Pi. Está escrito para que lo ejecute Claude Code en la propia Pi, o una persona. El porqué
del puerto y de la exposición en red está en `docs/decisions/06-despliegue.md`
(§DESPLIEGUE).

| parámetro | valor |
|---|---|
| servicio systemd | `ttl-designer.service` |
| puerto | **8040** (8000 y 8020 quedan libres para otros servicios) |
| interfaz | `0.0.0.0`: red local y Tailscale |
| proceso | `uvicorn ttl_designer.app:app --workers 1`, sin `--reload` |
| usuario | el usuario normal que clonó el repo (nunca root) |

## Requisitos

- Raspberry Pi OS de 64 bits (Bookworm o posterior), con Python ≥ 3.11. En 32 bits,
  `pydantic-core` puede no tener rueda precompilada y exigir compilar con Rust.
- `git`, `curl` y `python3-venv` (`sudo apt install -y git curl python3-venv`).
- Tailscale instalado y con sesión iniciada (`tailscale status` responde) si se quiere el
  acceso remoto. No es requisito para la red local.

## Primera instalación

```bash
git clone https://github.com/alexesenz/ttl-designer.git ~/ttl-designer
cd ~/ttl-designer
deploy/install.sh
```

`install.sh` es idempotente. Hace lo siguiente:

1. Comprueba Python ≥ 3.11 y que el puerto 8040 esté libre.
2. Crea `.venv` e instala el paquete.
3. Genera la unidad systemd con el usuario y la ruta reales, la instala, la habilita al
   arranque y la reinicia.
4. Espera a que `/health` responda e imprime las URLs de red local y de Tailscale.

Si el puerto 8040 está ocupado por otro proceso, el script aborta y muestra cuál es. No hay
que matar ese proceso: se debe preguntar al usuario antes de tocar otro servicio.

## Verificación

```bash
systemctl status ttl-designer --no-pager
ss -ltnp 'sport = :8040'                     # debe mostrar 0.0.0.0:8040
curl -s http://127.0.0.1:8040/health          # {"status":"ok","version":...,"commit":...}
curl -s http://$(tailscale ip -4):8040/health # por la interfaz de Tailscale
```

El `commit` de `/health` debe coincidir con `git rev-parse --short HEAD`. Si no coincide,
el servicio no se reinició después de actualizar.

Desde otro equipo: la interfaz en `http://<ip-lan-de-la-pi>:8040/` en la red local, o
`http://<nombre-tailscale>:8040/` desde cualquier dispositivo de la tailnet; la API en `/docs`.

## HTTPS por Tailscale (`tailscale serve`)

`tailscale serve` publica el servicio con HTTPS solo dentro de la tailnet (no es Funnel), con
un nombre `https://<equipo>.<tailnet>.ts.net`. La interfaz usa rutas relativas, así que
funciona tanto en la raíz del nombre como en una subruta:

```bash
tailscale serve status                                    # qué está publicado y dónde
tailscale serve --bg http://127.0.0.1:8040                # en la raíz, si no hay otro servicio ahí
tailscale serve --bg --set-path /ttl http://127.0.0.1:8040   # en una subruta, si la raíz está ocupada
```

Con subruta, entra **con la barra final**: `https://<equipo>.<tailnet>.ts.net/ttl/`. Sin la
barra (`…/ttl`), el navegador resuelve las rutas relativas contra la raíz y la página sale
sin estilos. Confirma la sintaxis exacta con `tailscale serve --help`, porque cambia entre
versiones del cliente.

## Actualizar

```bash
cd ~/ttl-designer
git pull --ff-only
deploy/install.sh        # reinstala dependencias y reinicia
```

Basta con `sudo systemctl restart ttl-designer` si solo cambió código Python y no cambió
`pyproject.toml`. Después de reiniciar, confirma el commit en `/health`.

## Operación

| acción | comando |
|---|---|
| logs en vivo | `journalctl -u ttl-designer -f` |
| últimos errores | `journalctl -u ttl-designer -n 100 --no-pager` |
| reiniciar | `sudo systemctl restart ttl-designer` |
| detener | `sudo systemctl stop ttl-designer` |
| deshabilitar al arranque | `sudo systemctl disable ttl-designer` |

Reglas:

- El servicio se maneja solo con `systemctl`. Nunca se usan `pkill`, `kill` ni `nohup`
  sobre uvicorn, porque systemd lo volvería a levantar o quedarían dos instancias peleando
  por el puerto.
- No se edita `/etc/systemd/system/ttl-designer.service` a mano. Se cambia la plantilla
  `deploy/ttl-designer.service` y se vuelve a correr `install.sh`.
- No se usa `--reload` en el servicio: es para desarrollo y vigila el disco en una SD.

## Firewall

Si `ufw` está activo (`sudo ufw status`), se abre el puerto solo para la red local y para
Tailscale, nunca de forma global:

```bash
ip -4 route | awk '/proto kernel/ && !/tailscale/ {print $1}'   # subred local, p. ej. 192.168.1.0/24
sudo ufw allow from 192.168.1.0/24 to any port 8040 proto tcp  # sustituir por la subred real
sudo ufw allow in on tailscale0 to any port 8040 proto tcp
```

Sin `ufw` activo no hay nada que hacer: `0.0.0.0` ya escucha en la LAN y en `tailscale0`.

## Seguridad

La aplicación **no tiene autenticación**. La exposición está acotada por la red:

- No se abre el puerto en el router ni se hace port-forwarding.
- No se usa `tailscale funnel` (publicaría el servicio en internet). `tailscale serve` es
  aceptable, porque queda dentro de la tailnet.
- Si se necesita restringir quién de la tailnet accede, se usan las ACL de Tailscale.

## Problemas frecuentes

| síntoma | causa probable | revisión |
|---|---|---|
| `install.sh` dice que el puerto está en uso | otro servicio en 8040 | `ss -ltnp 'sport = :8040'`; preguntar antes de tocarlo |
| el servicio reinicia en bucle | dependencia faltante o error al importar | `journalctl -u ttl-designer -n 50` |
| la página sale sin estilos y "Calculando…" no avanza | se abrió una subruta de `tailscale serve` sin la barra final, o el servicio corre una versión anterior a las rutas relativas | entra a `…/ttl/`; `git pull --ff-only && deploy/install.sh` |
| responde en 127.0.0.1 pero no desde la LAN | ufw o escucha en 127.0.0.1 | `ss -ltnp` debe mostrar `0.0.0.0:8040`; reglas de ufw |
| no responde por Tailscale | Tailscale caído o sin sesión | `tailscale status`; `sudo systemctl status tailscaled` |
| `/health` muestra un commit viejo | no se reinició tras `git pull` | `sudo systemctl restart ttl-designer` |
