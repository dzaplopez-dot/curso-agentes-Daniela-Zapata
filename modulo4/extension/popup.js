/* popup.js — UI mínima. Solo actúa tras clic. Sin red externa. Datos de página = no confiables. */
(function () {
  'use strict';
  var CABECERAS = ['proveedor', 'sku_proveedor', 'nombre', 'marca', 'precio_cop', 'inventario', 'activo', 'fuente_url', 'fecha_consulta', 'estado_revision', 'sku_pos', 'disponibilidad'];
  var CAB_EXC = ['sku_proveedor', 'nombre', 'fuente_url', 'tipo', 'campo_afectado', 'detalle'];

  var btnA = document.getElementById('btn-analizar');
  var btnD = document.getElementById('btn-descargar');
  var btnE = document.getElementById('btn-excepciones');
  var estado = document.getElementById('estado');
  var conteo = document.getElementById('conteo');
  var avisosWrap = document.getElementById('avisos-wrap');
  var avisosUl = document.getElementById('avisos');
  var previaWrap = document.getElementById('previa-wrap');
  var previaBody = document.getElementById('previa');
  var ultimo = null;

  function setEstado(m, c) { estado.textContent = m; estado.className = c || ''; }
  function celda(t) { var td = document.createElement('td'); td.textContent = t == null ? '' : String(t); return td; }
  function esc(v) { var s = String(v == null ? '' : v); if (/[",\n\r]/.test(s)) return '"' + s.replace(/"/g, '""') + '"'; return s; }

  function filaCatalogo(p, fecha) {
    return [esc(p.proveedor), esc(p.sku_proveedor), esc(p.nombre), esc(p.marca), esc(p.precio_cop), esc(p.inventario), esc(p.activo), esc(p.fuente_url), esc(p.fecha_consulta || fecha), esc(p.estado_revision), esc(p.sku_pos), esc(p.disponibilidad)].join(',');
  }
  function aCSV(r) {
    var L = [CABECERAS.join(',')];
    for (var i = 0; i < r.productos.length; i++) L.push(filaCatalogo(r.productos[i], r.fecha_consulta));
    return '﻿' + L.join('\r\n') + '\r\n';
  }
  function aExcepciones(r) {
    var L = [CAB_EXC.join(',')];
    for (var i = 0; i < r.productos.length; i++) {
      var p = r.productos[i];
      if (!p.sku_proveedor) L.push([esc(''), esc(p.nombre), esc(p.fuente_url), esc('faltante'), esc('sku_proveedor'), esc('Sin código visible en tarjeta; no inventar. Requiere revisión.')].join(','));
      if (!p.precio_cop) L.push([esc(p.sku_proveedor), esc(p.nombre), esc(p.fuente_url), esc('faltante'), esc('precio_cop'), esc('Sin precio visible; dejar vacío.')].join(','));
      // Sin tabla validada no hay sku_pos: todo va a excepción de equivalencia
      L.push([esc(p.sku_proveedor), esc(p.nombre), esc(p.fuente_url), esc('sin_equivalencia'), esc('sku_pos'), esc('Sin tabla de equivalencias validada; no asociar al POS.')].join(','));
    }
    return '﻿' + L.join('\r\n') + '\r\n';
  }
  function descargar(texto, nombre) {
    var blob = new Blob([texto], { type: 'text/csv;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    chrome.downloads.download({ url: url, filename: nombre, saveAs: true }, function () {
      setTimeout(function () { URL.revokeObjectURL(url); }, 30000);
    });
  }

  btnA.addEventListener('click', function () {
    ultimo = null; btnD.disabled = true; btnE.disabled = true; previaWrap.hidden = true; avisosWrap.hidden = true; conteo.hidden = true;
    setEstado('Analizando…');
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (!tabs || !tabs[0]) { setEstado('Sin pestaña activa.', 'error'); return; }
      var tab = tabs[0];
      if (!/^https:\/\/ferricentro\.com\//.test(tab.url || '')) { setEstado('Página no compatible. Abre https://ferricentro.com/. No se genera CSV.', 'error'); return; }
      chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['extractor.js'] }, function (res) {
        if (chrome.runtime.lastError) { setEstado('No se pudo inyectar: ' + chrome.runtime.lastError.message, 'error'); return; }
        var r = res && res[0] && res[0].result;
        if (!r) { setEstado('Sin resultado del extractor.', 'error'); return; }
        if (!r.ok) { setEstado(r.error || 'Error.', 'error'); return; }
        ultimo = r;
        setEstado('Listo. Revisa la previa y los avisos antes de descargar.', 'ok');
        conteo.hidden = false;
        conteo.textContent = 'Productos encontrados: ' + r.total_encontrados;
        avisosUl.textContent = '';
        (r.avisos || []).forEach(function (x) { var li = document.createElement('li'); li.textContent = String(x); avisosUl.appendChild(li); });
        avisosWrap.hidden = !(r.avisos && r.avisos.length);
        previaBody.textContent = '';
        r.productos.slice(0, 10).forEach(function (p, idx) {
          var tr = document.createElement('tr');
          tr.appendChild(celda(idx + 1)); tr.appendChild(celda(p.sku_proveedor || '—')); tr.appendChild(celda(p.nombre));
          tr.appendChild(celda(p.precio_cop || '—')); tr.appendChild(celda(p.estado_revision));
          previaBody.appendChild(tr);
        });
        previaWrap.hidden = false;
        btnD.disabled = false;
        btnE.disabled = false;
      });
    });
  });

  btnD.addEventListener('click', function () {
    if (!ultimo || !ultimo.ok || !ultimo.productos.length) { setEstado('Nada que descargar.', 'error'); return; }
    descargar(aCSV(ultimo), 'catalogo_proveedor.csv');
  });
  btnE.addEventListener('click', function () {
    if (!ultimo || !ultimo.ok || !ultimo.productos.length) { setEstado('Nada que descargar.', 'error'); return; }
    descargar(aExcepciones(ultimo), 'excepciones.csv');
  });
})();
