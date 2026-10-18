// Interfaz de TTL Designer (§FRONTEND). Sin dependencias además de htmx.
(function () {
  "use strict";
  var root = document.documentElement;
  var currentTab = "tab-resumen";

  // --- tema -----------------------------------------------------------------
  function effectiveTheme() {
    if (root.dataset.theme) return root.dataset.theme;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function paintThemeButton() {
    var label = document.getElementById("theme-label");
    if (label) label.textContent = effectiveTheme() === "dark" ? "Tema oscuro" : "Tema claro";
  }
  function setupTheme() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.hidden = false;
    paintThemeButton();
    btn.addEventListener("click", function () {
      var next = effectiveTheme() === "dark" ? "light" : "dark";
      root.dataset.theme = next;
      try { localStorage.setItem("ttl-theme", next); } catch (e) { /* sin persistencia */ }
      paintThemeButton();
    });
  }

  // --- pestañas (patrón ARIA: flechas, Inicio, Fin) -------------------------
  function setupTabs(scope) {
    var list = scope.querySelector("[data-tabs]");
    if (!list) return;
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    function select(tab, focus) {
      tabs.forEach(function (t) {
        var on = t === tab;
        t.setAttribute("aria-selected", on ? "true" : "false");
        t.tabIndex = on ? 0 : -1;
        var panel = document.getElementById(t.getAttribute("aria-controls"));
        if (panel) panel.hidden = !on;
      });
      currentTab = tab.id;
      if (focus) tab.focus();
    }
    tabs.forEach(function (t, i) {
      t.addEventListener("click", function () { select(t, false); });
      t.addEventListener("keydown", function (ev) {
        var j = null;
        if (ev.key === "ArrowRight") j = (i + 1) % tabs.length;
        else if (ev.key === "ArrowLeft") j = (i - 1 + tabs.length) % tabs.length;
        else if (ev.key === "Home") j = 0;
        else if (ev.key === "End") j = tabs.length - 1;
        if (j !== null) { ev.preventDefault(); select(tabs[j], true); }
      });
    });
    var keep = document.getElementById(currentTab);
    select(keep && tabs.indexOf(keep) >= 0 ? keep : tabs[0], false);
  }

  // --- ajustar / tamaño real en los diagramas ------------------------------
  function setupFit(scope) {
    scope.querySelectorAll("[data-fit]").forEach(function (btn) {
      var fig = document.getElementById(btn.getAttribute("data-fit"));
      if (!fig) return;
      btn.hidden = false;
      btn.addEventListener("click", function () {
        var fit = fig.classList.toggle("fit");
        btn.textContent = fit ? "100 %" : "Ajustar al ancho";
      });
    });
  }

  // --- copiar enlace y Ctrl+Enter --------------------------------------------
  function setupForm() {
    var form = document.getElementById("spec");
    var eq = document.getElementById("eq");
    if (form && eq) {
      eq.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
          ev.preventDefault();
          form.requestSubmit();
        }
      });
    }
    var copy = document.getElementById("copy-link");
    if (copy && navigator.clipboard) {
      copy.hidden = false;
      var label = copy.querySelector("span");
      copy.addEventListener("click", function () {
        navigator.clipboard.writeText(window.location.href).then(function () {
          label.textContent = "Enlace copiado";
          setTimeout(function () { label.textContent = "Copiar enlace"; }, 2000);
        });
      });
    }
  }

  // Al cargar un ejemplo, el editor refleja sus ecuaciones.
  function syncEditorFromUrl() {
    var eq = document.getElementById("eq");
    if (!eq) return;
    var p = new URLSearchParams(window.location.search);
    if (p.has("eq") && eq.value !== p.get("eq")) eq.value = p.get("eq");
  }

  document.addEventListener("DOMContentLoaded", function () {
    setupTheme();
    setupForm();
    setupTabs(document);
    setupFit(document);
  });
  document.body.addEventListener("htmx:afterSwap", function (ev) {
    if (ev.detail && ev.detail.target && ev.detail.target.id === "results") {
      setupTabs(ev.detail.target);
      setupFit(ev.detail.target);
      // el error llega fuera de banda: reflejarlo en el editor para lectores de pantalla
      var eq = document.getElementById("eq");
      var hasError = !!document.querySelector("#eq-error .alert");
      if (eq) {
        if (hasError && document.querySelector("#eq-error .caret")) eq.setAttribute("aria-invalid", "true");
        else eq.removeAttribute("aria-invalid");
      }
    }
  });
  // htmx actualiza la URL después del swap; un ejemplo cargado llega al editor aquí.
  document.body.addEventListener("htmx:pushedIntoHistory", syncEditorFromUrl);
})();
