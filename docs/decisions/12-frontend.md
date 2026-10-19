# 12 — Interfaz web: Jinja2 + htmx, estado en la URL, sin compilación

- **Sección**: §FRONTEND
- **Estado**: vigente
- **Fecha**: 2026-10-18
- **Módulos**: `ttl_designer/web/routes.py`, `ttl_designer/web/state.py`, `ttl_designer/web/view.py`, `ttl_designer/render/theme.py`
- **Tests**: `tests/test_web.py`

---

## Contexto

La herramienta tenía API y vistas SVG, pero ninguna interfaz. Corre en una Raspberry Pi
en la red local y por Tailscale, sin autenticación, y el repo es público. El cálculo ya
vive en el servidor y los diagramas se generan en él (§SVG, §ESQUEMATICO).

## Decisión

- **Stack**: plantillas Jinja2 (autoescape) servidas por el mismo FastAPI, con **htmx
  2.0.4 vendorizado** en `web/static/vendor/` (licencia 0BSD). Sin Node, sin paso de
  compilación y sin CDN.
- **Sin lógica en el navegador**: las rutas de interfaz llaman a las mismas funciones que la
  API (`map_design`, `run_drc`, `build_bom`, los render). `web/view.py` solo ordena para
  mostrar; los tres ejes de §EJES llegan por separado a la plantilla.
- **Estado en la URL** (decisión por defecto, el usuario no eligió otra): ecuaciones,
  don't-cares y opciones van en la query string; el enlace es el diseño. Sin base de datos
  ni cuentas. El servidor manda la query canónica (solo campos que difieren del defecto);
  ver Consecuencias.
- **Cálculo explícito** con botón o Ctrl+Enter. No se recalcula al teclear, porque la
  minimización puede tardar segundos cerca de los límites.
- **Mejora progresiva**: el formulario es un `GET` normal. Con htmx se actualiza solo
  `#results`, y el error del editor llega **fuera de banda** (`hx-swap-oob`). Sin
  JavaScript, la página completa funciona y las pestañas se muestran apiladas.
- **Pestañas** con el patrón ARIA (flechas, Inicio, Fin). La pestaña elegida se conserva al
  recalcular.
- **Seguridad**:
  - CSP en las páginas de la interfaz: `script-src 'self'` sin scripts en línea. Se
    permiten estilos en línea porque los SVG incrustados traen `<style>`.
  - htmx con `allowEval` y `allowScriptTags` apagados y `selfRequestsOnly`.
  - `nosniff`.
  - La API (`/docs`) queda sin CSP porque Swagger carga recursos externos.
- **SVG incrustables**: los estilos de los SVG cuelgan de una clase en su raíz
  (`.ttl-chips`, `.ttl-schematic`) y no de `:root`, para no pisar los tokens de la página
  (`render/theme.py`). Siguen `prefers-color-scheme` salvo que la página fije
  `data-theme`, así el interruptor manual de tema también los cambia.
- **Visual**:
  - Tokens en variables CSS: tema claro, oscuro por sistema y oscuro o claro manual,
    recordado en `localStorage` con try/catch.
  - Fuentes del sistema, monoespaciada para lo técnico.
  - Color reservado para significado, siempre acompañado de ícono o texto.
- **Mensajes de error del parser**: se muestran con la línea, un caret en la columna y una
  pista para el paréntesis sin cerrar.

## Consecuencias

- **Rutas relativas, historial propio.** Todas las URL internas (estáticos, formulario,
  ejemplos, descargas) son relativas, para que la interfaz funcione igual en la raíz que
  detrás de un proxy que la monta en una subruta (`tailscale serve --set-path /ttl`, que
  quita el prefijo antes de llegar a la app). No se usa `hx-push-url`: htmx 2 normaliza esas
  URL contra la raíz y pierde la subruta. El servidor manda la query canónica en
  `X-TTL-Query` y `app.js` la agrega a `location.pathname`; atrás/adelante recarga la URL.
  La única condición es entrar a la subruta con la barra final (`/ttl/`).
- El indicador "Calculando…" está oculto por atributo `hidden` y solo `app.js` lo muestra,
  así no queda visible si faltaran el CSS o el JavaScript.

- Verificado en Chromium con Playwright: flujo completo, teclado en pestañas, error por
  htmx con `aria-invalid`, ejemplos, tema manual, teléfono sin scroll horizontal.
  **axe-core 4.10 sin violaciones WCAG 2 A/AA** en las cinco vistas auditadas. Esa
  auditoría no corre en CI (necesita navegador); los tests de `tests/test_web.py` sí.
- La tabla de verdad se muestra hasta 64 filas; con más entradas se avisa.
- Una URL muy larga (BCD a 7 segmentos con mintérminos completos) sigue funcionando, pero
  no es bonita; un futuro formato compacto quedaría como otra decisión.

## Alternativas descartadas

- **SPA (React/Vue)**: paso de compilación y modelos duplicados en TypeScript sin
  beneficio a esta escala.
- **Proyectos guardados en el servidor**: base de datos y la pregunta de quién ve qué sin
  autenticación.
- **Cargar htmx desde CDN**: dependencia externa en una Pi que puede quedar sin internet.
