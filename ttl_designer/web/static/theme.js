// Se carga en <head> sin defer para aplicar el tema guardado antes de pintar.
(function () {
  var root = document.documentElement;
  root.classList.remove("no-js");
  try {
    var saved = localStorage.getItem("ttl-theme");
    if (saved === "light" || saved === "dark") root.dataset.theme = saved;
  } catch (e) { /* almacenamiento no disponible: se sigue al sistema */ }
})();
