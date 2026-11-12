"""Load per-category inputs from the UAV Industry Benchmark workbook."""
from __future__ import annotations

from pathlib import Path
from statistics import median

import openpyxl

from .model import UAV, budget_from_endurance, M_REF

DEFAULT_XLSX = Path(__file__).resolve().parents[1] / "data" / "UAV_Industry_Benchmark_v2.xlsx"
CATEGORIES = {
    "Delivery": "Delivery / Logistics", "SAR": "Disaster Relief & SAR", "Agricultural": "Agricultural",
    "Surveillance": "Surveillance & Security", "Mapping": "Mapping & Surveying", "Inspection": "Industrial Inspection",
}
HEADER_ROW, FIRST, LAST = 5, 6, 15


def load_rows(xlsx: Path = DEFAULT_XLSX) -> dict[str, list[dict]]:
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    out = {}
    for sheet in CATEGORIES:
        ws = wb[sheet]
        hdr = [c.value for c in ws[HEADER_ROW]]
        rows = []
        for cells in ws.iter_rows(min_row=FIRST, max_row=LAST):
            if not cells[0].value:
                continue
            row = {h: c.value for h, c in zip(hdr, cells)}
            # the sheet shows the word "link"; the real URL is stored as the cell's hyperlink target
            for h, c in zip(hdr, cells):
                if c.hyperlink is not None and c.hyperlink.target:
                    row[h] = c.hyperlink.target
            rows.append(row)
        out[sheet] = rows
    return out


def _med(rows, key, default):
    vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
    return median(vals) if vals else default


def category_uav(rows: list[dict], lam0: float = 0.01, k: float = 2.0, eta: float = 0.8) -> tuple[UAV, dict]:
    """Representative free-flight multirotor for a category (medians over multirotor rows)."""
    mr = [r for r in rows if r.get("Airframe") == "Multirotor"]
    m = _med(mr, "MTOW / TOW (kg)", M_REF)
    vmax = _med(mr, "Max speed (m/s)", 20.0)
    endu = _med(mr, "Max flight time (min)", 30.0)
    rob = _med(rows, "Robustness score (/100)", 50.0)
    uav = UAV(mass_kg=m, v_max=vmax, battery_kJ=budget_from_endurance(m, endu, eta),
              lam0=lam0 * (1.5 - rob / 100), k=k)
    return uav, dict(n_companies=len(rows), n_multirotor=len(mr), mass_kg=m, v_max=vmax, endurance_min=endu, robustness=rob)
