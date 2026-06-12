"""
illustrasi_overlap_bukti.py — BUKTI ANGKA 'kepemilikan terkode':
di kolom-x persilangan, tampilkan titik-titik MENTAH V2 & V3 sebagai dua deret
dot terpisah + kotak daftar koordinat masing-masing. Output -> lap_img/fig_overlap_bukti.png
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


def arr(Q):
    xs = np.array([x for x, _ in Q]); ys = np.array([y for _, y in Q])
    o = np.argsort(xs); return xs[o], ys[o]


def main():
    doc = fitz.open(PDF)
    pg = next(doc[p] for p in range(doc.page_count) if len(longs(doc[p])) == 12)
    P = sorted(longs(pg), key=lambda Q: np.median([y for _, y in Q]))
    x2, y2 = arr(P[7]); x3, y3 = arr(P[8])
    b2, b3 = np.median(y2), np.median(y3)
    iS = int(np.argmax(y2)); xc = x2[iS]
    doc.close()

    lo, hi = xc - 0.06 * PSEC, xc + 0.06 * PSEC
    m2 = (x2 >= lo) & (x2 <= hi); m3 = (x3 >= lo) & (x3 <= hi)

    fig, ax = plt.subplots(figsize=(12, 6.6))
    ax.axhspan(b3 - 0.9 * PMV, b3 + 0.9 * PMV, color="#fde68a", alpha=.45)
    ax.plot(x2[m2], y2[m2], '-o', color="#1d4ed8", ms=5, lw=1, label="titik V2 (daftar V2)")
    ax.plot(x3[m3], y3[m3], '-o', color="#ea580c", ms=5, lw=1, label="titik V3 (daftar V3)")
    # garis kolom xc + dua titik kunci
    ax.axvline(xc, color="#7c3aed", ls="--", lw=1)
    j = int(np.argmin(np.abs(x3 - xc)))
    ax.plot([xc], [y2[iS]], 'o', color="#1d4ed8", ms=11, mec="k", zorder=5)
    ax.plot([xc], [y3[j]], 'o', color="#ea580c", ms=11, mec="k", zorder=5)
    ax.annotate(f"V2: (x={xc:.2f}, y={y2[iS]:.2f})  →  {(b2-y2[iS])/PMV:+.2f} mV",
                xy=(xc, y2[iS]), xytext=(xc + 1.2, y2[iS] - 6), fontsize=10,
                color="#1d4ed8", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#1d4ed8"))
    ax.annotate(f"V3: (x={xc:.2f}, y={y3[j]:.2f})  →  {(b3-y3[j])/PMV:+.2f} mV",
                xy=(xc, y3[j]), xytext=(xc + 1.2, y3[j] + 7), fontsize=10,
                color="#ea580c", fontweight="bold",
                arrowprops=dict(arrowstyle="->", color="#ea580c"))
    # tanda jarak di kertas
    ax.annotate("", xy=(xc - 0.4, y2[iS]), xytext=(xc - 0.4, y3[j]),
                arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.3))
    ax.text(xc - 0.7, (y2[iS] + y3[j]) / 2,
            f"di kertas cuma\n{abs(y3[j]-y2[iS]):.0f} pt (~{abs(y3[j]-y2[iS])/PT:.2f} mm)\nterpisah",
            fontsize=8.5, color="#b91c1c", ha="right", va="center")
    ax.invert_yaxis()
    ax.set_title("BUKTI: di kolom-x sama, V2 & V3 simpan titiknya MASING-MASING "
                 "(dua daftar berbeda)", fontsize=12)
    ax.set_xlabel("x (point)"); ax.set_ylabel("y (point) — posisi di kertas")
    ax.legend(loc="upper left", fontsize=9); ax.grid(True, alpha=.25)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_overlap_bukti.png")
    fig.savefig(p, dpi=120); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    main()
