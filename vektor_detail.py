"""
vektor_detail.py — Bongkar PERHITUNGAN VEKTOR nyata dari PDF (6 & 12-lead):
berapa drawing, path trace, segmen, posisi-y, baseline, koordinat mentah, dan
konversi ke mV. Simpan ringkas ke vektor_detail.json + gambar layout path:
  fig_raw6.png  : 6 path 6-lead di koordinat PDF asli (layout halaman)
  fig_raw12.png : 12 path 12-lead di koordinat PDF asli
Output -> lap_img/ dan vektor_detail.json
"""
import os
import json
import numpy as np
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "C:/BRINDATA/EKG-BRIN"
OUT = os.path.join(ROOT, "lap_img")
os.makedirs(OUT, exist_ok=True)
PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT
NAMES6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
NAMES12 = NAMES6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
PDF6 = os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf")
PDF12 = os.path.join(ROOT, "12-lead", "20260604-153829", "20251118-143153-0004.pdf")


def paths_of(page, min_seg=500):
    out = []
    for d in page.get_drawings():
        pts = []
        for it in d['items']:
            if it[0] == 'l':
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
        if len(pts) > min_seg:
            out.append(pts)
    return out


def pts_arrays(P):
    xs = np.array([x for x, _ in P]); ys = np.array([y for _, y in P])
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True)
    return ux, ys[i]


def detail(pdf, names):
    doc = fitz.open(pdf)
    pages_info = []
    trace_pages = []
    for p in range(doc.page_count):
        dr = doc[p].get_drawings()
        lp = paths_of(doc[p])
        pages_info.append({"page": p, "n_drawings": len(dr), "n_trace_paths": len(lp)})
        if len(lp) in (6, 12):
            trace_pages.append(p)
    # halaman trace pertama -> rincian lead
    pg = doc[trace_pages[0]]
    P = sorted(paths_of(pg), key=lambda Q: np.median([y for _, y in Q]))
    leads = []
    for nm, p in zip(names, P):
        ux, uy = pts_arrays(p)
        base = float(np.median(uy))
        # 3 titik pertama + mV-nya
        sample = []
        for k in range(3):
            y = float(uy[k]); x = float(ux[k])
            sample.append({"x": round(x, 2), "y": round(y, 2),
                           "mv": round((base - y) / PMV, 4)})
        leads.append({
            "lead": nm, "n_segmen": int(len(p)),
            "median_y": round(base, 1),
            "x_range": [round(float(ux.min()), 1), round(float(ux.max()), 1)],
            "y_range": [round(float(uy.min()), 1), round(float(uy.max()), 1)],
            "amp_mV": round(float((uy.max() - uy.min()) / PMV), 3),
            "sample3": sample,
        })
    # untuk 6-lead: tabel sambung antar-halaman
    concat = []
    if len(names) == 6:
        for p in trace_pages:
            lp = paths_of(doc[p])
            allx = [x for Q in lp for x, _ in Q]
            dur = (max(allx) - min(allx)) / PSEC
            concat.append({"page": p, "x_range": [round(min(allx), 0), round(max(allx), 0)],
                           "dur_sec": round(dur, 2), "samples_250hz": int(round(dur * 250))})
    doc.close()
    return {"file": os.path.basename(pdf), "n_pages": len(pages_info),
            "pages": pages_info, "trace_pages": trace_pages,
            "leads": leads, "concat_pages": concat,
            "total_sec": round(sum(c["dur_sec"] for c in concat), 2) if concat else None}


def fig_layout(pdf, names, outname, title):
    doc = fitz.open(pdf)
    pg = next(doc[p] for p in range(doc.page_count) if len(paths_of(doc[p])) in (6, 12))
    P = sorted(paths_of(pg), key=lambda Q: np.median([y for _, y in Q]))
    cmap = plt.cm.tab20(np.linspace(0, 1, len(P)))
    fig, ax = plt.subplots(figsize=(12, 6.2 if len(P) == 12 else 4.2))
    x0 = min(min(x for x, _ in Q) for Q in P)
    xmax = x0 + 3.0 * PSEC
    for nm, Q, c in zip(names, P, cmap):
        ux, uy = pts_arrays(Q)
        m = ux <= xmax
        ax.plot(ux[m], uy[m], color=c, lw=0.9)
        ax.text(ux[m][0] - 4, np.median(uy), nm, ha="right", va="center",
                fontsize=9, color=c, fontweight="bold")
    ax.invert_yaxis()
    ax.set_title(title, fontsize=12)
    ax.set_xlabel("x (point)"); ax.set_ylabel("y (point) — posisi di halaman PDF")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    p = os.path.join(OUT, outname)
    fig.savefig(p, dpi=120); plt.close(fig); doc.close()
    return p


if __name__ == "__main__":
    out = {"6-lead": detail(PDF6, NAMES6), "12-lead": detail(PDF12, NAMES12),
           "konstanta": {"pt_per_mm": round(PT, 4), "pt_per_mV": round(PMV, 4),
                         "pt_per_sec": round(PSEC, 4)}}
    json.dump(out, open(os.path.join(ROOT, "vektor_detail.json"), "w"), indent=2)
    fig_layout(PDF6, NAMES6, "fig_raw6.png",
               "6 PATH VEKTOR 6-lead di koordinat PDF asli (3 dtk pertama, tiap warna = 1 lead)")
    fig_layout(PDF12, NAMES12, "fig_raw12.png",
               "12 PATH VEKTOR 12-lead di koordinat PDF asli (3 dtk pertama, tiap warna = 1 lead)")
    print("-> vektor_detail.json + fig_raw6/12.png")
