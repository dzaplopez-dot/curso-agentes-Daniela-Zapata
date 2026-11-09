'use strict';
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="practica-token"]').content;
const money = n => new Intl.NumberFormat('es-CO',{style:'currency',currency:'COP',maximumFractionDigits:0}).format(n);
const dateTime = s => new Date(s).toLocaleString('es-CO');
function el(tag,text,cls) { const n=document.createElement(tag); if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n; }
function error(e) { $('global-error').textContent=e.message||String(e);$('global-error').hidden=false; }
function clearError() { $('global-error').hidden=true; }
async function api(url,options={}) {
  const response=await fetch(url,{...options,headers:{'X-Practica-Token':token,...options.headers}});
  const data=await response.json();
  if(!response.ok)throw new Error(data.error||'No se pudo completar la solicitud.');
  return data;
}
async function task(action) {clearError();try {await action();}catch(e){error(e);}}
async function busy(button,action) {const original=button.textContent;button.disabled=true;button.textContent='Un momento…';try{await action();}finally{button.disabled=false;button.textContent=original;}}
const headings={mesa:['Cada soporte, en su lugar.','Consulta tus ventas y prepara el siguiente paso.','Mesa de trabajo'],ventas:['Las ventas, a la vista.','Busca y revisa el detalle comercial antes de asociar.','Ventas'],catalogo:['El catálogo de La Esquina.','Una fuente de productos y precios para construir tus ventas.','Catálogo'],practica:['Observa. Consulta. Decide.','Doce soportes para practicar distintos recorridos.','Soportes de práctica']};
function page(name) {
 if(!headings[name])name='mesa';
 document.querySelectorAll('.page').forEach(n=>n.hidden=n.id!=='page-'+name);
 document.querySelectorAll('.nav').forEach(n=>{n.classList.toggle('selected',n.dataset.page===name);if(n.dataset.page===name)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});
 const [title,subtitle,crumb]=headings[name];$('page-title').textContent=title;$('page-subtitle').textContent=subtitle;$('breadcrumb').textContent=crumb;
 location.hash=name;clearError();
 if(name==='ventas')task(loadSales);if(name==='catalogo')task(loadProducts);if(name==='practica')task(loadSamples);
}
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.page)));
document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>page(b.dataset.go)));
window.addEventListener('hashchange',()=>{const name=location.hash.slice(1);if(headings[name]&&!$('page-'+name).hidden)return;page(name);});
async function summary(){const d=await api('/api/resumen');['productos','ventas','archivos'].forEach(k=>$('stat-'+k).textContent=new Intl.NumberFormat('es-CO').format(d[k]));}
function message(role,text){const n=el('div',undefined,'message'+(role==='usuario'?' user':''));n.append(el('span',role==='usuario'?'TÚ':'CHAT DE PRÁCTICA','author'),document.createTextNode(text));$('messages').append(n);$('messages').scrollTop=$('messages').scrollHeight;}
async function chatHistory(){const rows=await api('/api/chat');$('messages').replaceChildren();if(!rows.length)message('asistente','Hola. Esta es tu mesa de trabajo. Carga un soporte para conservar su evidencia o escribe «ventas» para consultar SQLite. El reconocimiento y las operaciones comerciales se construyen en clase.');rows.forEach(r=>message(r.rol,r.texto));}
let sending=false;
async function sendChat(text){if(sending||!text.trim())return;sending=true;try{await busy($('send-chat'),async()=>{await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:text})});$('chat-input').value='';await chatHistory();});}finally{sending=false;}}
$('chat-form').addEventListener('submit',e=>{e.preventDefault();task(()=>sendChat($('chat-input').value));});
$('chat-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$('chat-form').requestSubmit();}});
document.querySelectorAll('[data-command]').forEach(b=>b.addEventListener('click',()=>task(()=>sendChat(b.dataset.command))));
let archivoActual=null;
function preview(file){archivoActual=$('preview-image').src?file:null;$('preview-empty').hidden=true;$('preview').hidden=false;$('preview-image').src='/archivos/'+file.id;$('original-link').href='/archivos/'+file.id;$('file-detail').replaceChildren(el('strong',file.nombre_original),el('div',file.id),el('div','Pendiente de reconocimiento · '+dateTime(file.cargado_en)));$('reconocer-panel').hidden=false;$('ficha-extraccion').hidden=true;$('ficha-error').hidden=true;$('reconocer-status').textContent='';$('registrar-status').textContent='';}
async function upload(file){
 if(file.size>8*1024*1024)throw new Error('La imagen supera 8 MB.');
 const form=new FormData();form.append('archivo',file,file.name);
 const data=await api('/api/archivos',{method:'POST',body:form});
 preview(data.archivo);$('upload-status').textContent=data.duplicado?'Este mismo archivo ya estaba cargado. Conservamos su ID.':'Imagen conservada en tu equipo. Pendiente de reconocimiento y revisión.';
 await Promise.all([loadFiles(),summary()]);
}
$('upload-form').addEventListener('submit',e=>{e.preventDefault();task(()=>busy($('upload-button'),async()=>{const f=$('upload-input').files[0];if(!f)throw new Error('Selecciona una imagen.');await upload(f);$('upload-input').value='';}));});
async function loadFiles(){const rows=await api('/api/archivos');$('file-list').replaceChildren();if(!rows.length){$('file-list').append(el('p','Aún no has cargado archivos. Elige una imagen o usa un soporte de práctica.','hint'));return;}for(const r of rows){const row=el('div',undefined,'file-row'),info=el('div');info.append(el('strong',r.nombre_original),el('small',r.id+' · Pendiente de reconocimiento'),el('small',dateTime(r.cargado_en)));const b=el('button','Ver soporte','secondary');b.addEventListener('click',()=>{preview(r);page('mesa');$('preview').scrollIntoView({block:'center'});});row.append(info,b);$('file-list').append(row);}}
$('refresh-files').addEventListener('click',()=>task(()=>busy($('refresh-files'),loadFiles)));
function openDialog(title,content){$('dialog-title').textContent=title;$('dialog-content').replaceChildren(content);$('detail-dialog').showModal();}
$('close-dialog').addEventListener('click',()=>$('detail-dialog').close());
function enlarge(src,title){const img=el('img',undefined,'zoom-image');img.src=src;img.alt=title;openDialog(title,img);}
$('enlarge').addEventListener('click',()=>enlarge($('preview-image').src,'Soporte original'));
function table(headers,rows){const t=el('table'),head=el('thead'),hr=el('tr'),body=el('tbody');headers.forEach(h=>{const n=el('th',h);n.scope='col';hr.append(n);});head.append(hr);rows.forEach(cells=>{const r=el('tr');cells.forEach(c=>{const td=el('td');if(c instanceof Node)td.append(c);else td.textContent=c;r.append(td);});body.append(r);});t.append(head,body);return t;}
async function loadSales(){const params=new URLSearchParams({q:$('sales-q').value,importe:$('sales-amount').value,fecha:$('sales-date').value});const rows=await api('/api/ventas?'+params);$('sales-count').textContent=rows.length+' ventas encontradas'+(rows.length?'':'. Prueba otros criterios: no encontrar un total exacto no demuestra que falte la venta.');$('sales-table').replaceChildren(table(['Venta','Fecha comercial','Cliente','Total COP','Detalle'],rows.map(v=>{const b=el('button','Abrir','table-action');b.setAttribute('aria-label','Abrir venta '+v.id);b.addEventListener('click',()=>task(()=>saleDetail(v.id)));return [v.id,v.fecha_comercial,v.cliente||'Sin cliente',el('span',money(v.total),'number'),b];})));}
$('sales-form').addEventListener('submit',e=>{e.preventDefault();task(()=>busy(e.submitter,loadSales));});
$('clear-sales').addEventListener('click',()=>{$('sales-form').reset();task(loadSales);});
async function saleDetail(id){const v=await api('/api/ventas/'+id),content=el('div'),meta=el('div',undefined,'detail-meta');for(const [label,value]of [['Fecha comercial',v.fecha_comercial],['Cliente',v.cliente||'Sin cliente'],['Factura externa',v.factura_externa||'No informada'],['Origen','Venta ficticia de práctica']]){const n=el('div');n.append(el('span',label),document.createTextNode(value));meta.append(n);}content.append(meta);const wrap=el('div',undefined,'table-wrap');wrap.append(table(['Producto','Cantidad','Precio COP','Subtotal COP'],v.lineas.map(l=>[l.producto_codigo+' · '+l.nombre,l.cantidad,money(l.precio_unitario),money(l.subtotal)])));content.append(wrap,el('p','Total '+money(v.total)+' COP','total'),el('p','Sin pagos asociados. La revisión de una imagen no verifica el abono bancario.','info'));openDialog('Venta '+id,content);}
let productsPage=1;
async function loadProducts(){const data=await api('/api/productos?'+new URLSearchParams({q:$('products-q').value,pagina:productsPage}));$('products-count').textContent=data.total+' productos encontrados';$('products-page').textContent='Página '+productsPage+' de '+Math.max(1,Math.ceil(data.total/30));$('previous-products').disabled=productsPage<=1;$('next-products').disabled=productsPage*30>=data.total;$('products-table').replaceChildren(table(['Código','Producto','Categoría','Unidad','Precio COP'],data.resultados.map(p=>[p.codigo,p.nombre,p.categoria,p.unidad,el('span',money(p.precio_venta),'number')])));}
$('products-form').addEventListener('submit',e=>{e.preventDefault();productsPage=1;task(()=>busy(e.submitter,loadProducts));});
$('previous-products').addEventListener('click',()=>{if(productsPage>1){productsPage--;task(loadProducts);}});
$('next-products').addEventListener('click',()=>{productsPage++;task(loadProducts);});
let samplesLoaded=false;
async function loadSamples(){if(samplesLoaded)return;const rows=await api('/api/casos');$('sample-list').replaceChildren();for(const r of rows){const card=el('article',undefined,'sample-card'),img=el('img');img.src=r.url;img.alt=r.nombre+' anonimizado';img.loading='lazy';const controls=el('div',undefined,'sample-buttons'),see=el('button','Ampliar','secondary'),use=el('button','Cargar a mi práctica','primary');see.addEventListener('click',()=>enlarge(r.url,r.nombre));use.addEventListener('click',()=>task(()=>busy(use,async()=>{const response=await fetch(r.url);if(!response.ok)throw new Error('No se pudo leer el soporte de práctica.');await upload(new File([await response.blob()],r.nombre,{type:'image/png'}));page('mesa');$('preview').scrollIntoView({block:'center'});})));controls.append(see,use);card.append(img,el('h3',r.nombre),controls);$('sample-list').append(card);}samplesLoaded=true;}

async function reconocer(){
  if(!archivoActual)throw new Error('No hay un soporte cargado.');
  $('btn-reconocer').disabled=true;$('btn-reconocer').textContent='Reconociendo…';
  try{
    const datos=await api('/api/extraer/'+archivoActual.id,{method:'POST'});
    $('reconocer-status').textContent='Extracción recibida. Revisa los campos antes de registrar.';
    $('ficha-extraccion').hidden=false;
    const e=datos.extraccion_original||{};
    $('form-ficha').querySelector('input[name="archivo_id"]').value=archivoActual.id;
    $('form-ficha').querySelector('input[name="revisado_humano"]').value='false';
    for(const campo of ['document_type','payment_brand_or_medium','currency_observed','operation_status_observed','amount_basis','total_amount','inferred_amount','stated_cash_amount','document_date','document_time','time_precision','merchant_or_store','notes']){
      const input=$('form-ficha').querySelector('[name="'+campo+'"]');
      if(input)input.value=e[campo]==null?'':e[campo];
    }
    const refs=e.references||{};
    $('referencias-lista').replaceChildren();
    for(const [clave,valor]of Object.entries(refs)){
      if(valor){
        const fila=el('div');fila.textContent=clave+': '+valor;$('referencias-lista').append(fila);
      }
    }
    $('advertencias-lista').replaceChildren();
    for(const a of (e.warnings||[])){
      const fila=el('div');fila.textContent=a;$('advertencias-lista').append(fila);
    }
    $('confianza-lista').replaceChildren();
    const conf=e.confidence||{};
    for(const [clave,valor]of Object.entries(conf)){
      if(valor!=null){
        const fila=el('div');fila.textContent=clave+': '+(Math.round(valor*100))+'%';$('confianza-lista').append(fila);
      }
    }
  }catch(err){
    $('ficha-error').textContent=err.message||String(err);$('ficha-error').hidden=false;
  }finally{$('btn-reconocer').disabled=false;$('btn-reconocer').textContent='Reconocer soporte con el modelo';}
}

async function registrarComprobante(){
  if(!archivoActual)throw new Error('No hay un soporte cargado.');
  const form=$('form-ficha');const e={};
  for(const campo of ['document_type','payment_brand_or_medium','currency_observed','operation_status_observed','amount_basis','total_amount','inferred_amount','stated_cash_amount','document_date','document_time','time_precision','merchant_or_store','notes']){
    const input=form.querySelector('[name="'+campo+'"]');
    e[campo]=input.value===''?null:input.value;
  }
  if(!confirm('¿Confirman que revisaron y corrigieron los datos del comprobante?'))return;
  const payload={archivo_id:archivoActual.id,revisado_humano:true,revisado_por:'operador',modelo:'gpt-5.6-luna',version_prompt:'v1',extraccion_original:e,notas_revision:'Revisado por el operador en la ficha de práctica.',correcciones:[]};
  $('btn-registrar').disabled=true;$('btn-registrar').textContent='Registrando…';
  try{
    const resultado=await api('/api/comprobantes',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    $('registrar-status').textContent='Comprobante registrado: '+resultado.id+'. Estado: '+resultado.estado;
    $('btn-registrar').disabled=true;
    comprobanteActual=archivoActual;
    $('asociar-panel').hidden=false;
    $('venta-faltante-panel').hidden=false;
    $('buscar-status').textContent='Comprobante listo. Elige naturaleza, importe y busca ventas candidatas.';
  }catch(err){
    $('ficha-error').textContent=err.message||String(err);$('ficha-error').hidden=false;
  }finally{$('btn-registrar').disabled=false;$('btn-registrar').textContent='Registrar comprobante tras revisión';}
}

let comprobanteActual=null;
let propuestaActual=null;
let ventaLines=[];
let propuestaVenta=null;

function preview(file){
  archivoActual=$('preview-image').src?file:null;
  $('preview-empty').hidden=true;$('preview').hidden=false;
  $('preview-image').src='/archivos/'+file.id;
  $('original-link').href='/archivos/'+file.id;
  $('file-detail').replaceChildren(el('strong',file.nombre_original),el('div',file.id),el('div','Pendiente de reconocimiento · '+dateTime(file.cargado_en)));
  $('reconocer-panel').hidden=false;$('ficha-extraccion').hidden=true;$('ficha-error').hidden=true;
  $('reconocer-status').textContent='';$('registrar-status').textContent='';
  $('asociar-panel').hidden=true;$('propuesta-panel').hidden=true;$('vinculo-panel').hidden=true;
  comprobanteActual=null;propuestaActual=null;
  ventaLines=[];propuestaVenta=null;
  $('venta-faltante-panel').hidden=true;$('vf-propuesta-panel').hidden=true;
  $('vf-fecha').value='';$('vf-cliente').value='';$('vf-factura').value='';
  $('vf-codigo').value='';$('vf-cantidad').value='';$('vf-precio').value='';
  vfError(null);renderVentaLineas();
}

async function buscarCandidatos(){
  if(!archivoActual)throw new Error('No hay un soporte cargado.');
  const naturaleza=$('asoc-naturaleza').value;
  const importe=$('asoc-importe').value;
  if(!importe)throw new Error('Ingresa un importe aplicado para buscar candidatos.');
  const params=new URLSearchParams({importe});
  const rows=await api('/api/ventas?'+params);
  $('candidatos-lista').replaceChildren();
  if(!rows.length){
    $('buscar-status').textContent='No se encontraron ventas con ese importe exacto.';
    return;
  }
  $('buscar-status').textContent=rows.length+' candidato(s) encontrado(s). Selecciona uno:';
  for(const v of rows){
    const row=el('div',undefined,'candidato-row');
    row.append(el('strong',v.id+' · '+v.fecha_comercial),el('span',' · Cliente: '+(v.cliente||'Sin cliente')),el('span',' · Total: '+money(v.total)));
    const sel=el('button','Seleccionar','secondary');
    sel.addEventListener('click',()=>{seleccionarCandidato(v);});
    row.append(sel);
    $('candidatos-lista').append(row);
  }
}

function seleccionarCandidato(venta){
  $('asoc-importe').disabled=true;
  $('btn-buscar-candidatos').disabled=true;
  propuestaActual={venta_id:venta.id,naturaleza:$('asoc-naturaleza').value,importe_aplicado:parseInt($('asoc-importe').value),archivo_id:archivoActual.id,motivo:$('asoc-motivo').value};
  $('candidatos-lista').replaceChildren(el('strong','Seleccionado: '+venta.id+' (total '+money(venta.total)+')'));
  prepararPropuesta();
}

async function prepararPropuesta(){
  if(!propuestaActual)throw new Error('No hay selección de candidato.');
  $('btn-aprobar').disabled=true;$('btn-ejecutar').disabled=true;
  $('propuesta-panel').hidden=true;$('vinculo-panel').hidden=true;
  try{
    const p=await api('/api/propuestas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(propuestaActual)});
    propuestaActual=p;
    $('propuesta-detalle').replaceChildren(
      el('strong','ID: '+p.id+' · Versión: '+p.version+' · Estado: '+p.estado),
      el('div','Naturaleza: '+p.naturaleza+' · Importe: '+money(p.importe_aplicado)),
      el('div','Comprobante: '+p.archivo_id+' · Venta: '+p.venta_id)
    );
    $('propuesta-panel').hidden=false;
    $('btn-aprobar').disabled=false;
    $('btn-ejecutar').disabled=true;
    $('buscar-status').textContent='Propuesta preparada (pendiente). Revisa y aprueba en el servidor.';
  }catch(err){
    $('ficha-error').textContent=err.message||String(err);$('ficha-error').hidden=false;
  }
}

async function aprobarPropuesta(){
  if(!propuestaActual)throw new Error('No hay una propuesta preparada.');
  if(!confirm('¿Apruebas esta propuesta? Esta acción es emitida por el servidor y no puede deshacerse.'))return;
  $('btn-aprobar').disabled=true;
  try{
    const aprobada=await api('/api/propuestas/'+propuestaActual.id+'/aprobar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({aprobado_por:'operador'})});
    propuestaActual=aprobada;
    $('propuesta-detalle').append(el('div','Aprobada: versión '+aprobada.version+' por '+aprobada.aprobado_por));
    $('btn-aprobar').disabled=true;
    $('btn-ejecutar').disabled=false;
    $('propuesta-status').textContent='Propuesta aprobada. Ahora puedes ejecutarla.';
  }catch(err){
    $('ficha-error').textContent=err.message||String(err);$('ficha-error').hidden=false;
    $('btn-aprobar').disabled=false;
  }
}

async function ejecutarPropuesta(){
  if(!propuestaActual || propuestaActual.estado!=='aprobada')throw new Error('La propuesta debe estar aprobada antes de ejecutar.');
  $('btn-ejecutar').disabled=true;
  try{
    const ejecucion=await api('/api/propuestas/ejecutar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
      propuesta_id:propuestaActual.id,
      version:propuestaActual.version,
      clave_idempotente:propuestaActual.clave_idempotente,
    })});
    $('propuesta-status').textContent='Ejecutada: operación '+ejecucion.operacion_id+(ejecucion.vinculo_id?' · vínculo '+ejecucion.vinculo_id:'');
    $('btn-ejecutar').disabled=true;
    if(ejecucion.vinculo_id){
      $('vinculo-panel').hidden=false;
      const v=await api('/api/vinculos/'+ejecucion.operacion_id);
      $('vinculo-detalle').replaceChildren(
        el('strong','Operación: '+v.operacion_id+' · Naturaleza: '+v.naturaleza),
        el('div','Venta: '+v.venta_id+' · Importe aplicado: '+money(v.importe_aplicado)),
        el('div','Estado financiero: '+v.estado_financiero)
      );
    }
  }catch(err){
    $('ficha-error').textContent=err.message||String(err);$('ficha-error').hidden=false;
    $('btn-ejecutar').disabled=false;
  }
}

function vfError(msg){const n=$('vf-error');if(msg===null){n.hidden=true;n.textContent='';}else{n.textContent=msg;n.hidden=false;}}

function renderVentaLineas(){
  const cont=$('vf-lineas');cont.replaceChildren();
  if(!ventaLines.length){cont.append(el('p','Aún no hay líneas confirmadas.','hint'));$('vf-total').textContent='Sin líneas confirmadas todavía.';return;}
  ventaLines.forEach((l,i)=>{
    const row=el('div',undefined,'candidato-row');
    const precio=l.precio_unitario==null?'catálogo':money(l.precio_unitario);
    row.append(el('strong',l.producto_codigo),el('span',' · Cantidad: '+l.cantidad),el('span',' · Precio: '+precio));
    const b=el('button','Quitar','secondary');b.type='button';
    b.addEventListener('click',()=>{ventaLines.splice(i,1);renderVentaLineas();});
    row.append(b);cont.append(row);
  });
  const total=ventaLines.reduce((s,l)=>s+Number(l.cantidad)*Number(l.precio_unitario||0),0);
  $('vf-total').textContent='Total estimado: '+money(total)+' (si omites el precio, el servidor usa el del catálogo).';
}

function addVentaLinea(){
  vfError(null);
  const codigo=$('vf-codigo').value.trim().toUpperCase();
  const cantidad=$('vf-cantidad').value;
  const precio=$('vf-precio').value;
  if(!codigo)throw new Error('Ingresa el código de producto.');
  if(!cantidad||Number(cantidad)<1)throw new Error('La cantidad debe ser un entero mayor que cero.');
  if(ventaLines.some(l=>l.producto_codigo===codigo))throw new Error('Ese producto ya está en las líneas.');
  ventaLines.push({producto_codigo:codigo,cantidad:parseInt(cantidad),precio_unitario:precio===''?null:parseInt(precio)});
  $('vf-codigo').value='';$('vf-cantidad').value='';$('vf-precio').value='';
  renderVentaLineas();
}

async function prepararVenta(){
  if(!archivoActual)throw new Error('No hay un soporte cargado.');
  vfError(null);
  $('vf-propuesta-panel').hidden=true;$('vinculo-panel').hidden=true;
  const payload={archivo_id:archivoActual.id,naturaleza:'cobro',fecha_comercial:$('vf-fecha').value||null,cliente:$('vf-cliente').value||null,factura_externa:$('vf-factura').value||null,lineas:ventaLines};
  if(propuestaVenta&&propuestaVenta.estado==='pendiente')payload.propuesta_id=propuestaVenta.id;
  $('btn-preparar-venta').disabled=true;
  try{
    const p=await api('/api/ventas/faltante',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    propuestaVenta=p;
    $('vf-propuesta-detalle').replaceChildren(
      el('strong','ID: '+p.id+' · Versión: '+p.version+' · Estado: '+p.estado),
      el('div','Fecha comercial: '+(p.fecha_comercial||'Falta')),
      el('div','Líneas: '+p.lineas.length+' · Total: '+money(p.total)),
      el('div',p.completo?'Propuesta completa.':'Borrador incompleto. Falta: '+p.faltantes.join(', '))
    );
    $('vf-propuesta-panel').hidden=false;
    $('btn-aprobar-venta').disabled=!p.completo;
    $('btn-ejecutar-venta').disabled=true;
    $('vf-status').textContent=p.completo?'Propuesta completa y pendiente. Revísala y apruébala.':'Borrador guardado. Agrega fecha y líneas para completarlo.';
  }catch(err){vfError(err.message||String(err));}
  finally{$('btn-preparar-venta').disabled=false;}
}

async function aprobarVenta(){
  if(!propuestaVenta)throw new Error('No hay una propuesta de venta.');
  if(!propuestaVenta.completo)throw new Error('Completa la fecha y las líneas antes de aprobar.');
  if(!confirm('¿Apruebas esta propuesta de venta? La aprobación la emite el servidor.'))return;
  $('btn-aprobar-venta').disabled=true;
  try{
    const a=await api('/api/propuestas/'+propuestaVenta.id+'/aprobar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({aprobado_por:'operador'})});
    propuestaVenta={...propuestaVenta,...a};
    $('vf-propuesta-detalle').append(el('div','Aprobada: versión '+a.version+' por '+a.aprobado_por));
    $('btn-ejecutar-venta').disabled=false;
    $('vf-status').textContent='Propuesta aprobada. Ahora crea la venta.';
  }catch(err){vfError(err.message||String(err));$('btn-aprobar-venta').disabled=false;}
}

async function ejecutarVenta(){
  if(!propuestaVenta||propuestaVenta.estado!=='aprobada')throw new Error('La propuesta debe estar aprobada antes de crear la venta.');
  $('btn-ejecutar-venta').disabled=true;
  try{
    const r=await api('/api/ventas/faltante/ejecutar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({propuesta_id:propuestaVenta.id,version:propuestaVenta.version,clave_idempotente:propuestaVenta.clave_idempotente})});
    $('vf-status').textContent='Venta creada: '+r.venta_id+' · Total '+money(r.total)+(r.idempotente?' (resultado existente, sin duplicar)':'')+(r.vinculo_id?' · vínculo '+r.vinculo_id:'');
    await Promise.all([summary(),loadFiles()]);
  }catch(err){vfError(err.message||String(err));$('btn-ejecutar-venta').disabled=false;}
}

$('btn-add-linea').addEventListener('click',()=>task(addVentaLinea));
$('btn-preparar-venta').addEventListener('click',()=>task(prepararVenta));
$('btn-aprobar-venta').addEventListener('click',()=>task(aprobarVenta));
$('btn-ejecutar-venta').addEventListener('click',()=>task(ejecutarVenta));
$('btn-buscar-candidatos').addEventListener('click',()=>task(buscarCandidatos));
$('btn-aprobar').addEventListener('click',()=>task(aprobarPropuesta));
$('btn-ejecutar').addEventListener('click',()=>task(ejecutarPropuesta));
$('btn-reconocer').addEventListener('click',()=>task(reconocer));
$('btn-registrar').addEventListener('click',()=>task(registrarComprobante));

task(async()=>{await Promise.all([summary(),chatHistory(),loadFiles()]);const files=await api('/api/archivos');if(files.length)preview(files[0]);page(location.hash.slice(1)||'mesa');});
