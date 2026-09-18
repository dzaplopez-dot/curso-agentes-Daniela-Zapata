"""Ruta A Taskmaster: filtra restaurant-table-1/2, muestra reproducible, extrae con anotaciones. No modifica el original."""
import json, csv, argparse, random
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
ORIG = BASE / "datos" / "original" / "self-dialogs.json"
OUT_DIR = BASE / "datos" / "procesado"
OUT_DIR.mkdir(parents=True, exist_ok=True)

BASE_NAMES = {
    "restaurante": "restaurant_reservation.name.restaurant",
    "zona": "restaurant_reservation.location.restaurant",
    "fecha_hora": "restaurant_reservation.time.reservation",
    "personas": "restaurant_reservation.num.guests",
    "seating": "restaurant_reservation.type.seating",
}

def collect(c):
    """Junta textos por campo base (incluye variantes .accept/.reject) y set de annotation names."""
    vals = {k: [] for k in BASE_NAMES}
    names = set()
    for u in c.get("utterances", []):
        for s in u.get("segments", []) or []:
            txt = (s.get("text") or "").strip()
            for a in s.get("annotations", []) or []:
                n = a.get("name", "")
                names.add(n)
                for campo, base in BASE_NAMES.items():
                    if n == base or n == base + ".accept" or n == base + ".reject":
                        if txt and txt not in vals[campo]:
                            vals[campo].append(txt)
    return vals, names

def estado(names):
    if "restaurant_reservation.reservation.accept" in names:
        return "aceptado"
    if any(n.endswith(".reject") for n in names):
        return "rechazado"
    return "pendiente"

def main(n=200, seed=7):
    data = json.loads(ORIG.read_text(encoding="utf-8"))
    convs = data if isinstance(data, list) else data.get("conversations", [])
    universo = [c for c in convs if c.get("instruction_id") in ("restaurant-table-1", "restaurant-table-2")]
    rnd = random.Random(seed)
    muestra = rnd.sample(universo, min(n, len(universo)))
    rows, pendientes = [], []
    for c in muestra:
        cid = c.get("conversation_id", "sin-id")
        vals, names = collect(c)
        row = {"conversation_id": cid}
        for campo in BASE_NAMES:
            v = vals[campo]
            if campo == "personas" and v:
                try:
                    row[campo] = int("".join(filter(str.isdigit, v[0])) or 0) or v[0]
                except Exception:
                    row[campo] = v[0]
            else:
                row[campo] = " | ".join(v[:3]) if v else "pendiente"
            if row[campo] == "pendiente":
                pendientes.append([cid, campo, "sin anotación explícita"])
        row["estado"] = estado(names)
        if row["estado"] == "pendiente":
            pendientes.append([cid, "estado", "sin reservation.accept ni reject"])
        rows.append(row)
    with open(OUT_DIR / "muestra.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["conversation_id", "instruction_id"])
        for c in muestra:
            w.writerow([c.get("conversation_id"), c.get("instruction_id")])
    with open(OUT_DIR / "datos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["conversation_id"] + list(BASE_NAMES) + ["estado"])
        w.writeheader()
        w.writerows(rows)
    with open(OUT_DIR / "pendientes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["conversation_id", "campo", "motivo"])
        w.writerows(pendientes)
    print(f"universo: {len(universo)}, muestra: {len(muestra)}, filas: {len(rows)}, pendientes-reg: {len(pendientes)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()
    main(a.n, a.seed)
