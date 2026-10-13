"""Asistente local de terminal: interpreta la solicitud, valida con Python/SQLite.

Límite obligatorio: consulta y propone. Nunca modifica existencias,
no registra compras, no inventa datos ausentes.
"""

from __future__ import annotations

import re
import sys

from . import herramientas as H

PATRON_CODIGO = re.compile(r"\b([A-Z]{3}-\d{4})\b", re.IGNORECASE)

PALABRAS_ESCRITURA = [
    "cambia", "cambie", "modifica", "modifique", "actualiza", "actualice",
    "registra", "registre", "compra", "compre", "vende", "venda",
    "ajusta", "ajuste", "suma", "sumale", "resta", "restale",
    "borra", "borre", "elimina", "elimine", "descuenta", "descuente",
    "agrega", "agregue", "quita", "quite", "pon ", "ponle",
    "incrementa", "decrementa", "setea",
]

MENSAJE_RECHAZO = (
    "No puedo modificar el inventario. Solo consulto existencias, "
    "vencimientos y propongo reposición. La base no fue alterada. "
    "(Fuente: ninguna escritura ejecutada)"
)


def es_escritura_no_autorizada(texto: str) -> bool:
    t = f" {(texto or '').lower()} "
    return any(p in t for p in PALABRAS_ESCRITURA)


def responder(solicitud: str) -> str:
    """Interpreta una solicitud y devuelve la respuesta (puro, testeable)."""
    texto = (solicitud or "").strip()
    if not texto:
        return "Escribe un código (ej. FER-0001), un nombre, 'bajo mínimo', 'vencidos' o 'ayuda'."

    if es_escritura_no_autorizada(texto):
        return f"RECHAZADO: {MENSAJE_RECHAZO}"

    t = texto.lower()
    codigos = [c.upper() for c in PATRON_CODIGO.findall(texto)]

    # 1. Vencimientos
    if "vencid" in t or "vence" in t or "por vencer" in t or t.strip() == "vencidos":
        if codigos:
            v = H.vencimiento_por_producto(codigos[0])
            if v is None:
                return f"El código {codigos[0]} no existe en productos. No invento información. (Fuente: productos)"
            lineas = [
                f"{v['codigo']} · {v['nombre']}",
                f"Disponible: {v['stock_disponible']} | Vencido (separado, no disponible): {v['stock_vencido']}",
            ]
            for l in v["lotes_vencidos"][:5]:
                lineas.append(f"  - VENCIDO {l['lote']} stock={l['stock']} fv={l['fecha_vencimiento']} (fila {l['fila_origen']})")
            for l in v["lotes_disponibles"][:5]:
                lineas.append(f"  - disponible {l['lote']} stock={l['stock']} fv={l.get('fecha_vencimiento')} (fila {l['fila_origen']})")
            lineas.append(f"Fuente: {v['fuente']}")
            return "\n".join(lineas)
        vencidos = H.consultar_vencimientos(solo_vencidos=True, limite=10)
        total = len(H.consultar_vencimientos(solo_vencidos=True, limite=10000))
        lineas = [f"Lotes vencidos: {total} (muestro 10, separados del disponible):"]
        for v in vencidos:
            lineas.append(f"  - {v['producto_codigo']} {v['lote']} stock={v['stock']} fv={v['fecha_vencimiento']} (fila {v['fila_origen']})")
        lineas.append("Fuente: inventario.fecha_vencimiento < hoy")
        return "\n".join(lineas)

    # 2. Bajo mínimo / reposición general
    if "bajo" in t and "min" in t or "reposici" in t or "reponer" in t or "faltante" in t:
        if codigos:
            p = H.proponer_reposicion(codigos[0])
            if isinstance(p, dict) and p.get("existe") is False:
                return f"El código {codigos[0]} no existe en productos. No invento información. (Fuente: productos)"
            estado = "NECESITA reposición" if p["necesita_reposicion"] else "OK (no necesita)"
            return (
                f"{p['codigo']} · {p.get('nombre','')}: "
                f"stock={p['stock_total']} mínimo={p['stock_minimo']} -> "
                f"sugerido={p['cantidad_sugerida']} [{estado}]\n"
                f"Regla: {p['regla']}\nFuente: {p['fuente']}"
            )
        bajos = H.productos_bajo_minimo(limite=10)
        total = len(H.productos_bajo_minimo(limite=10000))
        lineas = [f"Productos bajo el mínimo: {total} (muestro 10, propuesta reproducible):"]
        for b in bajos:
            lineas.append(f"  - {b['producto_codigo']} stock={b['stock_total']} min={b['stock_minimo']} sugerido={b['faltante']}")
        lineas.append("Regla: cantidad = max(0, stock_minimo - stock_total)")
        lineas.append("Fuente: inventario")
        return "\n".join(lineas)

    # 3. Código exacto -> producto + existencias
    if codigos:
        codigo = codigos[0]
        prod = H.obtener_producto(codigo)
        if prod is None:
            return f"El código {codigo} no existe en productos. No invento información. (Fuente: productos)"
        ex = H.consultar_existencias(codigo)
        estado = "BAJO MÍNIMO" if ex["bajo_minimo"] else "OK"
        lineas = [
            f"{prod['codigo']} · {prod['nombre']} ({prod['categoria']})",
            f"Proveedor: {prod['proveedor']} ({prod['proveedor_id']}) | Unidad: {prod.get('unidad')} | "
            f"Costo={prod['precio_costo']} Venta={prod['precio_venta']}",
            f"Stock total={ex['stock_total']} Mínimo={ex['stock_minimo']} Estado={estado}",
        ]
        for m in ex["movimientos"][:5]:
            lineas.append(
                f"  - {m['lote']} ubic={m.get('ubicacion')} stock={m['stock']} "
                f"fv={m.get('fecha_vencimiento')} estado={m.get('estado')} (fila {m['fila_origen']})"
            )
        lineas.append("Fuente: productos + proveedores + inventario")
        return "\n".join(lineas)

    # 4. Ayuda
    if t in ("ayuda", "help", "?") or "ayuda" in t:
        return (
            "Comandos:\n"
            "  FER-0001 -> ficha + stock por lote\n"
            "  busca martillo -> candidatos (si hay varios, pide precisión)\n"
            "  bajo minimo -> lista + propuesta de reposición\n"
            "  vencidos -> lotes vencidos separados del disponible\n"
            "  reponer ABA-0220 -> propuesta para un código\n"
            "  salir -> termina\n"
            "Límite: no modifico existencias ni registro compras."
        )

    # 5. Búsqueda por nombre (ambigüedad)
    nombre = re.sub(r"^(busca|buscar|encuentra|muestra)\s+", "", texto, flags=re.IGNORECASE).strip()
    resultados = H.buscar_productos(nombre, limite=10)
    if not resultados:
        return f"Sin coincidencias para '{nombre}' en productos. No invento información. (Fuente: productos)"
    if len(resultados) == 1:
        return responder(resultados[0]["codigo"])
    lineas = [f"Encontré {len(resultados)} coincidencias para '{nombre}', precisa el código:"]
    for r in resultados[:10]:
        lineas.append(f"  - {r['codigo']} · {r['nombre']} ({r['categoria']})")
    lineas.append("Fuente: productos.nombre LIKE")
    return "\n".join(lineas)


def bucle() -> None:
    print("ASISTENTE DE INVENTARIO (solo consulta, no modifica)")
    print("Escribe 'ayuda' para ver comandos, 'salir' para terminar.")
    while True:
        try:
            pedido = input("inventario> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSesión terminada. Base intacta.")
            break
        if pedido.lower() in ("salir", "exit", "quit"):
            print("Sesión terminada. Base intacta.")
            break
        print(responder(pedido))
        print("-" * 60)


def main() -> None:
    print("ASISTENTE DE INVENTARIO")
    print("Base del proyecto instalada correctamente.")
    print("Ejemplos: FER-0001 | busca martillo | bajo minimo | vencidos | ayuda")
    # Solo entra al bucle si hay terminal interactiva (pytest no se bloquea).
    if sys.stdin.isatty():
        bucle()


if __name__ == "__main__":
    main()
