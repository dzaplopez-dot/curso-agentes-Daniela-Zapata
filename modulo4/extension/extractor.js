/* extractor.js — Ferricentro (Magento) a registro ERP revisable.
 * Se inyecta SOLO tras clic explícito. Sin red externa, sin clics, sin formularios.
 * Base observada (2026-09-26 de https://ferricentro.com/):
 *   tarjeta = imagen + línea "MARCA CÓDIGO" (ej. "YALE 10953/YMF") +
 *             [Título](https://ferricentro.com/<slug>) +
 *             "Precio normal $ X N% Precio especial $ Y" + [Ver Producto].
 * Discriminador de producto (sin inventar clases): <a> cuyo href es de UN solo
 * segmento (slug de producto). Las categorías son /productos/... (con ruta).
 * Todo el DOM es dato no confiable: solo se lee texto, jamás se ejecuta.
 * Contrato Módulo 4 (12 columnas): proveedor, sku_proveedor, nombre, marca,
 * precio_cop, inventario, activo, fuente_url, fecha_consulta, estado_revision,
 * sku_pos, disponibilidad. Vacío = no observado, nunca cero.
 */
(function () {
  'use strict';

  var PROVEEDOR = 'Ferricentro';
  var fuenteUrl = String(location.href || '');

  // Fecha con zona America/Bogota (UTC-5). Si toLocale falla, cae a ISO UTC.
  function fechaBogota() {
    try {
      var partes = new Date().toLocaleString('sv-SE', { timeZone: 'America/Bogota' });
      // sv-SE => "2026-09-26 12:34:56"
      return String(partes).replace(' ', 'T') + '-05:00';
    } catch (e) {
      return new Date().toISOString();
    }
  }
  var FECHA = fechaBogota();

  function texto(el) {
    try {
      var t = (typeof el.innerText === 'string') ? el.innerText : (el.textContent || '');
      return String(t).replace(/[ \t]+/g, ' ').replace(/\s+\n/g, '\n').trim();
    } catch (e) { return ''; }
  }
  function digitos(s) { return String(s || '').replace(/\D/g, ''); }

  if (!/^https:\/\/ferricentro\.com\//.test(fuenteUrl)) {
    return { ok: false, code: 'UNSUPPORTED_URL', error: 'Página no compatible. Abre https://ferricentro.com/ o una categoría /productos/... y reintenta.' };
  }

  var anclas;
  try { anclas = Array.prototype.slice.call(document.querySelectorAll('a[href]')); }
  catch (e) { return { ok: false, code: 'NO_DOM', error: 'No se pudo leer el DOM.' }; }

  function esSlugProducto(href) {
    var m = /^https:\/\/ferricentro\.com\/([a-z0-9\-]+)\/?(?:[?#]|$)/i.exec(href || '');
    if (!m) return false;
    var slug = m[1].toLowerCase();
    var noProducto = { productos: 1, combos: 1, ofertas: 1, 'precios-fugaces': 1, customer: 1, checkout: 1, catalogsearch: 1, contacto: 1 };
    if (noProducto[slug]) return false;
    if (slug.indexOf('experto') === 0) return false;
    if (slug.indexOf('esperto') === 0) return false;
    if (slug.indexOf('-ff-') === -1) return false;
    return slug.length >= 8;
  }

  var vistos = {};
  var productos = [];
  var avisos = [];
  var sinSku = 0, sinPrecio = 0;

  for (var i = 0; i < anclas.length; i++) {
    var a = anclas[i];
    var href = '';
    try { href = a.href || a.getAttribute('href') || ''; } catch (e) { continue; }
    if (!esSlugProducto(href)) continue;
    var urlLimpia = href.split('?')[0].split('#')[0].replace(/\/$/, '');
    if (vistos[urlLimpia]) continue;
    vistos[urlLimpia] = true;

    var cont = null;
    try { cont = (a.closest && a.closest('li')) || a.parentElement; } catch (e) { cont = a.parentElement; }
    var ctx = cont ? texto(cont) : texto(a);
    if (!ctx) continue;

    var nombre = texto(a);
    if (nombre.indexOf('{') !== -1 || nombre.indexOf('.product-image') !== -1) nombre = '';
    if (!nombre || nombre.length < 4 || nombre.indexOf('{') !== -1 || nombre.indexOf('.product-image') !== -1) {
      nombre = '';
      try {
        var cands = cont ? cont.querySelectorAll('a[href]') : [];
        for (var q = 0; q < cands.length; q++) {
          var ch = '';
          try { ch = cands[q].href || ''; } catch (e) { ch = ''; }
          if (ch.split('?')[0].split('#')[0].replace(/\/$/, '') !== urlLimpia) continue;
          var t1 = '', t2 = '';
          try { t1 = cands[q].getAttribute('title') || ''; t2 = texto(cands[q]); } catch (e) {}
          var cand = '';
          if (t1 && t1.indexOf('{') === -1 && t1.indexOf('.product-image') === -1) cand = t1.split('\n')[0].trim();
          else if (t2 && t2.indexOf('{') === -1 && t2.indexOf('.product-image') === -1) cand = t2.split('\n')[0].trim();
          else continue;
          if (cand.length > nombre.length) nombre = cand;
        }
      } catch (e) { /* conserva lo que haya */ }
    }
    nombre = String(nombre || '').split('\n')[0].trim().slice(0, 200);
    if (/^ver( producto)?$/i.test(nombre)) nombre = '';
    if (!nombre) continue;

    var marca = '', sku = '';
    var m = /(^|\n)\s*([A-ZÁÉÍÓÚÑ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ]+)?)\s+([A-Z0-9][A-Z0-9\/\-.]{3,})\s*(?:\n|$)/.exec(ctx);
    if (m) { marca = m[2].trim(); sku = m[3].trim(); }
    else {
      var m2 = /\b([A-Z]{2,})\s+(\d{4,}[A-Z0-9\/\-]*)/.exec(ctx);
      if (m2) { marca = m2[1]; sku = m2[2]; }
    }
    if (marca === 'VER' || !/\d/.test(sku)) { marca = ''; sku = ''; }
    if (!sku) sinSku++;

    var precio = '';
    var me = /precio especial\s*\$\s*([\d\.\,]+)/i.exec(ctx);
    if (me) precio = digitos(me[1]);
    else {
      var todos = [], re = /\$\s*([\d\.\,]+)/g, mm;
      while ((mm = re.exec(ctx)) !== null) { var d = digitos(mm[1]); if (d) todos.push(d); }
      if (todos.length) precio = todos[todos.length - 1];
    }
    if (!precio) sinPrecio++;

    var estado = (sku && precio) ? 'verificado' : 'requiere_revision';

    productos.push({
      proveedor: PROVEEDOR,
      sku_proveedor: sku,
      nombre: nombre,
      marca: marca,
      precio_cop: precio,
      inventario: '',
      activo: 'true',
      fuente_url: urlLimpia,
      fecha_consulta: FECHA,
      estado_revision: estado,
      sku_pos: '',
      disponibilidad: ''
    });
  }

  if (!productos.length) {
    return { ok: false, code: 'ZERO_RESULTS', error: 'Cero productos: no se halló ningún slug de producto. Haz scroll al portafolio (“Explora nuestro portafolio”) y reintenta.', fuente_url: fuenteUrl, fecha_consulta: FECHA };
  }

  avisos.push('Regla activo: publicado y visible en el listado = true (documentada y revisable).');
  avisos.push('Inventario: la tarjeta no publica unidades (“Añadir al carrito” no demuestra stock) → columna vacía, nunca cero.');
  avisos.push('sku_pos y disponibilidad: vacíos sin tabla de equivalencias validada; van a excepciones, no se inventan.');
  if (sinSku) avisos.push(sinSku + ' fila(s) sin sku visible: se exportan con sku_proveedor vacío y estado requiere_revision.');
  if (sinPrecio) avisos.push(sinPrecio + ' fila(s) sin precio visible: se exportan con precio_cop vacío.');

  var r = { ok: true, fuente_url: fuenteUrl, fecha_consulta: FECHA, total_encontrados: productos.length, avisos: avisos, productos: productos };
  try { window.__ferriUltimo = r; } catch (e) {}
  return r;
})();
