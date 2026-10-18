"""CSS de los SVG con alcance propio, para usarlos sueltos o dentro de la interfaz.

Las variables y reglas cuelgan de una clase en el ``<svg>`` raíz, no de ``:root``,
para no pisar los tokens de la página que los incrusta. El tema oscuro sigue a
``prefers-color-scheme`` salvo que la página fije ``data-theme`` en ``<html>``.
"""

from __future__ import annotations


def scoped_style(scope: str, light: str, dark: str, rules: str) -> str:
    """``rules`` usa ``&`` como marcador del alcance (``& text { … }``)."""
    s = f".{scope}"
    return (
        f"{s} {{ {light} }}\n"
        f"@media (prefers-color-scheme: dark) {{\n"
        f'  {s}:root, :root:not([data-theme="light"]) {s} {{ {dark} }}\n'
        f"}}\n"
        f'[data-theme="dark"] {s} {{ {dark} }}\n' + rules.replace("&", s)
    )
