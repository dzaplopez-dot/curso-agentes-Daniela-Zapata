from collections import Counter
from datetime import datetime
from pathlib import Path

from . import config, repository
from .texto import formatear_precio

ESTILO = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body { margin: 0; font-family: "Segoe UI", system-ui, sans-serif; background: #f6f4ef; color: #1d1d1b; }
header { background: #111; color: #f7e7a1; padding: 28px 32px; }
header h1 { margin: 0; font-size: 24px; letter-spacing: .08em; text-transform: uppercase; }
header p { margin: 6px 0 0; color: #cfc8b4; font-size: 14px; }
main { padding: 24px 32px 48px; display: grid; gap: 24px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }
.kpi { background: #fff; border: 1px solid #e3ded2; border-radius: 12px; padding: 16px; }
.kpi span { display: block; font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: #7a7568; }
.kpi strong { display: block; margin-top: 6px; font-size: 26px; }
section { background: #fff; border: 1px solid #e3ded2; border-radius: 12px; padding: 18px 20px; }
section h2 { margin: 0 0 12px; font-size: 15px; text-transform: uppercase; letter-spacing: .06em; color: #4b463b; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #7a7568; border-bottom: 1px solid #e3ded2; padding: 8px 6px; }
td { padding: 8px 6px; border-bottom: 1px solid #f0ece3; }
tr:last-child td { border-bottom: none; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
.INV { background: #fbe9c9; color: #8a5a00; }
.ok { background: #dff0d8; color: #2f5c22; }
.borrador { background: #fdf3d0; color: #7a5b00; }
.confirmado { background: #dff0d8; color: #2f5c22; }
.cancelado { background: #eeeae0; color: #6f6a5e; }
.bajo { color: #a33; font-weight: 600; }
footer { padding: 0 32px 32px; font-size: 12px; color: #8a8477; }
"""


def _tabla(columnas, filas, clase_estado=True):
    encabezado = "".join(f"<th>{c}</th>" for c in columnas)
    cuerpo = []
    for fila in filas:
        celdas = []
        for valor in fila:
            if clase_estado and valor in ("borrador", "confirmado", "cancelado"):
                celdas.append(f"<td><span class='tag {valor}'>{valor}</span></td>")
            else:
                celdas.append(f"<td>{valor}</td>")
        cuerpo.append("<tr>" + "".join(celdas) + "</tr>")
    return (
        f"<table><thead><tr>{encabezado}</tr></thead>"
        f"<tbody>{''.join(cuerpo)}</tbody></table>"
    )


def generar(destino=None):
    destino = Path(destino or config.RAIZ_ENTREGABLE / "evidencias" / "panel.html")
    destino.parent.mkdir(parents=True, exist_ok=True)

    perfumes = repository.listar_todo()
    todos = repository.pedidos()
    confirmados = [p for p in todos if p["estado"] == "confirmado"]
    unidades = sum(int(p["cantidad"]) for p in confirmados)
    ingresos = sum(float(p["precio"]) * int(p["cantidad"]) for p in confirmados)
    bajo = repository.stock_bajo()
    inventario = sum(int(p["stock"]) for p in perfumes)

    familias = Counter()
    casas = Counter()
    for p in confirmados:
        familias[p["familia_base"]] += int(p["cantidad"])
        casas[p["casa"]] += int(p["cantidad"])

    filas_pedidos = [
        (
            f"#{p['id']}",
            p["creado_en"],
            p["codigo"],
            f"{p['inspirado_en']} ({p['casa']})",
            p["cantidad"],
            formatear_precio(float(p["precio"]) * int(p["cantidad"])),
            p["estado"],
        )
        for p in todos[:15]
    ]

    filas_bajo = [
        (f["codigo"], f"{f['inspirado_en']} ({f['casa']})", f"<span class='bajo'>{f['stock']}</span>")
        for f in bajo[:15]
    ]

    filas_familias = [(k, v) for k, v in familias.most_common(7)] or [("—", 0)]
    filas_casas = [(k, v) for k, v in casas.most_common(7)] or [("—", 0)]

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Panel EFY · pedidos y stock</title>
<style>{ESTILO}</style>
</head>
<body>
<header>
  <h1>EFY Perfumería · Panel</h1>
  <p>Pedidos, stock e indicadores del bot · generado {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
</header>
<main>
  <div class="kpis">
    <div class="kpi"><span>Referencias</span><strong>{len(perfumes)}</strong></div>
    <div class="kpi"><span>Unidades en stock</span><strong>{inventario}</strong></div>
    <div class="kpi"><span>Pedidos confirmados</span><strong>{len(confirmados)}</strong></div>
    <div class="kpi"><span>Unidades vendidas</span><strong>{unidades}</strong></div>
    <div class="kpi"><span>Ingresos confirmados</span><strong>{formatear_precio(ingresos)}</strong></div>
    <div class="kpi"><span>Refs. con stock bajo</span><strong>{len(bajo)}</strong></div>
  </div>

  <section>
    <h2>Últimos pedidos</h2>
    {_tabla(("Pedido", "Fecha", "Código", "Perfume", "Cant.", "Total", "Estado"), filas_pedidos)}
  </section>

  <section>
    <h2>Stock bajo (menos de {config.STOCK_BAJO + 1} unidades)</h2>
    {_tabla(("Código", "Perfume", "Stock"), filas_bajo)}
  </section>

  <section>
    <h2>Familias más vendidas (unidades)</h2>
    {_tabla(("Familia", "Unidades"), filas_familias, clase_estado=False)}
  </section>

  <section>
    <h2>Casas más pedidas (unidades)</h2>
    {_tabla(("Casa", "Unidades"), filas_casas, clase_estado=False)}
  </section>
</main>
<footer>
  Datos de demostración. El stock parte de {config.STOCK_INICIAL} unidades por referencia y
  se descuenta solo al confirmar un pedido. Precio único {formatear_precio(config.PRECIO_DEFECTO)} · 100 ml.
  Backend: {config.BACKEND}.
</footer>
</body>
</html>
"""
    destino.write_text(html, encoding="utf-8")
    return destino


if __name__ == "__main__":
    print(generar())
