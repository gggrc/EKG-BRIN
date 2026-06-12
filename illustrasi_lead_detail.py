"""
illustrasi_lead_detail.py — Satu lead (V2) dari AWAL sampai AKHIR, dengan tiap
ANGKA pada tabel §5.8 ditandai POSISINYA di gambar:
  Tahap A : koordinat PDF mentah — titik-1, median_y(baseline), y_min/y_max, amplitudo, segmen
  Tahap B : setelah konversi mV — baseline→0, R-peak & S-wave dalam mV
Output -> lap_img/fig_lead_detail.png
"""
import os
import numpy as np
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "C:/BRINDATA/EKG-BRIN"
OUT = os.path.join(ROOT, "lap_img")
PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT
PDF = os.path.join(ROOT, "12-lead", "20260604-153829", "20251118-143153-0004.pdf")


def longs(pg, ms=500):
    r = []
    for d in pg.get_drawings():
        pts = []
        for it in d['items']:
            if it[0] == 'l':
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
        if len(pts) > ms:
            r.append(pts)
    return r


def main():
    doc = fitz.open(PDF)
    pg = next(doc[p] for p in range(doc.page_count) if len(longs(doc[p])) == 12)
    P = sorted(longs(pg), key=lambda Q: np.median([y for _, y in Q]))
    V2 = P[7]
    xs = np.array([x for x, _ in V2]); ys = np.array([y for _, y in V2])
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True); uy = ys[i]
    doc.close()

    base = float(np.median(uy))
    x0 = ux.min()
    # window cukup lebar agar titik-1, R-peak global, & S-wave global semua tampak
    # -> angka y_min/y_max/amplitudo PERSIS sama dgn tabel §5.8
    xmax = x0 + 4.3 * PSEC
    m = ux <= xmax
    xw, yw = ux[m], uy[m]
    t = (xw - x0) / PSEC
    # R/S = ekstrem GLOBAL pada window (agar cocok angka tabel §5.8)
    iR = int(np.argmin(yw))   # R-peak (y terkecil)
    iS = int(np.argmax(yw))   # S-wave (y terbesar)
    ymin, ymax = yw[iR], yw[iS]

    ann = dict(fontsize=9.5, fontweight="bold",
               bbox=dict(boxstyle="round", fc="white", ec="#cbd5e1", alpha=.95))
    arA = lambda c: dict(arrowstyle="->", color=c, lw=1.3)

    fig, (axA, axB) = plt.subplots(2, 1, figsize=(13, 10))

    # ===== TAHAP A: koordinat PDF mentah =====
    axA.plot(t, yw, '-', color="#94a3b8", lw=0.8, zorder=1)
    axA.plot(t, yw, '.', color="#1d4ed8", ms=2.5, zorder=2)
    # beri ruang ekstra atas-bawah (sumbu terbalik nanti)
    pad = 0.18 * (yw.max() - yw.min())
    axA.set_ylim(yw.max() + pad, yw.min() - pad)   # (bawah, atas) krn terbalik
    # baseline (median_y)
    axA.axhline(base, color="#16a34a", lw=1.4, ls="--")
    axA.annotate(f"median_y = {base:.1f} pt (BASELINE)", xy=(1.55, base),
                 xytext=(0.62, 0.52), textcoords="axes fraction", color="#16a34a",
                 va="center", arrowprops=arA("#16a34a"), **ann)
    # titik-1
    axA.plot([t[0]], [yw[0]], 'o', color="#dc2626", ms=11, mec="k", zorder=5)
    axA.annotate(f"titik-1: (x={xw[0]:.2f}, y={yw[0]:.2f})", xy=(t[0], yw[0]),
                 xytext=(0.02, 0.30), textcoords="axes fraction", color="#dc2626",
                 arrowprops=arA("#dc2626"), **ann)
    # y_min (R-peak)
    axA.plot([t[iR]], [ymin], 'v', color="#7c3aed", ms=11, zorder=5)
    axA.annotate(f"y_min = {ymin:.1f} pt (R-peak)", xy=(t[iR], ymin),
                 xytext=(0.30, 0.92), textcoords="axes fraction", color="#7c3aed",
                 arrowprops=arA("#7c3aed"), **ann)
    # y_max (S-wave)
    axA.plot([t[iS]], [ymax], '^', color="#b91c1c", ms=11, zorder=5)
    axA.annotate(f"y_max = {ymax:.1f} pt (S-wave terdalam)", xy=(t[iS], ymax),
                 xytext=(0.30, 0.08), textcoords="axes fraction", color="#b91c1c",
                 arrowprops=arA("#b91c1c"), **ann)
    # amplitudo bracket di beat pertama
    xb = t[iS] + 0.32
    axA.annotate("", xy=(xb, ymin), xytext=(xb, ymax),
                 arrowprops=dict(arrowstyle="<->", color="#0f766e", lw=1.8))
    axA.annotate(f"y_range = {ymax-ymin:.1f} pt = {(ymax-ymin)/PMV:.3f} mV (amplitudo)",
                 xy=(xb, (ymin + ymax) / 2), xytext=(0.60, 0.30),
                 textcoords="axes fraction", color="#0f766e",
                 arrowprops=arA("#0f766e"), **ann)
    axA.text(0.99, 0.95, f"jumlah titik = {len(V2)}", transform=axA.transAxes,
             ha="right", va="top", fontsize=9.5, color="#334155",
             bbox=dict(boxstyle="round", fc="#f1f5f9", ec="#cbd5e1"))
    axA.set_title("TAHAP A — koordinat PDF MENTAH (Lead V2). Tiap angka tabel §5.8 "
                  "ditandai posisinya.", fontsize=11.5, pad=10)
    axA.set_ylabel("y (point) — posisi di kertas\n[y ke bawah]"); axA.grid(True, alpha=.25)

    # ===== TAHAP B: konversi ke mV =====
    mv = (base - yw) / PMV
    axB.plot(t, mv, '-', color="#1d4ed8", lw=1.1)
    axB.set_ylim(mv.min() - 0.7, mv.max() + 0.7)
    axB.axhline(0, color="#16a34a", lw=1.2, ls="--")
    axB.annotate("0 mV (baseline)", xy=(1.55, 0), xytext=(0.62, 0.62),
                 textcoords="axes fraction", color="#16a34a", va="center",
                 arrowprops=arA("#16a34a"), **ann)
    mvR = (base - ymin) / PMV; mvS = (base - ymax) / PMV
    axB.plot([t[iR]], [mvR], 'v', color="#7c3aed", ms=11)
    axB.annotate(f"R-peak = {mvR:+.2f} mV", xy=(t[iR], mvR), xytext=(0.30, 0.88),
                 textcoords="axes fraction", color="#7c3aed",
                 arrowprops=arA("#7c3aed"), **ann)
    axB.plot([t[iS]], [mvS], '^', color="#b91c1c", ms=11)
    axB.annotate(f"S-wave = {mvS:+.2f} mV", xy=(t[iS], mvS), xytext=(0.30, 0.10),
                 textcoords="axes fraction", color="#b91c1c",
                 arrowprops=arA("#b91c1c"), **ann)
    axB.text(0.99, 0.06, f"mV = (median_y − y) / {PMV:.3f}\n"
             f"titik-1: ({base:.1f} − {yw[0]:.2f})/{PMV:.3f} = {(base-yw[0])/PMV:+.4f} mV",
             transform=axB.transAxes, ha="right", va="bottom", fontsize=9.5,
             family="monospace", color="#0f172a",
             bbox=dict(boxstyle="round", fc="#eff6ff", ec="#bfdbfe"))
    axB.set_title("TAHAP B — setelah konversi mV (sumbu dibalik & diskalakan). "
                  "Baseline → 0; R & S dalam mV.", fontsize=11.5, pad=10)
    axB.set_xlabel("detik"); axB.set_ylabel("mV"); axB.grid(True, alpha=.25)

    fig.suptitle("Satu lead (V2) dari awal → akhir: di mana tiap angka tabel berada",
                 fontsize=13, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.96], h_pad=2.5)
    p = os.path.join(OUT, "fig_lead_detail.png")
    fig.savefig(p, dpi=120); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    main()
