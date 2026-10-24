// Utilidades compartidas por las plantillas.
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function foto(ev) { return (ev.imagen && ev.imagen.ruta_abs) ? `url('${ev.imagen.ruta_abs}')` : "none"; }
function horaTxt(ev) {
  if (ev.todo_el_dia || !ev.hora_inicio) return "Todo el día";
  return ev.hora_fin ? `${ev.hora_inicio}–${ev.hora_fin}` : ev.hora_inicio;
}
function precioTxt(ev) { return ev.precio || "Consultar"; }
function fechaCorta(f) {
  const m = ["ene","feb","mar","abr","may","jun","jul","ago","sep","oct","nov","dic"];
  const d = new Date(f + "T12:00:00"); return `${d.getDate()} ${m[d.getMonth()]}`;
}
function listo() { // espera a que carguen las imágenes de fondo
  const urls = [...document.querySelectorAll("[style*='url(']")].map(e => (e.style.backgroundImage.match(/url\(["']?(.*?)["']?\)/) || [])[1]).filter(Boolean);
  return Promise.all(urls.map(u => new Promise(r => { const i = new Image(); i.onload = i.onerror = r; i.src = u; })));
}
