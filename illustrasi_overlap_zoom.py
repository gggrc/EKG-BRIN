"""
illustrasi_overlap_zoom.py — Zoom satu peristiwa persilangan V2/V3 dengan anotasi:
kolom-x tempat tinta V2 & V3 bertumpuk (sumber kebingungan metode piksel) +
kedalaman penetrasi S-wave V2 ke lajur V3. Output -> lap_img/fig_overlap_zoom.png
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


def arr(P):
    xs = np.array([x for x, _ in P]); ys = np.array([y for _, y in P])
    o = np.argsort(xs); return xs[o], ys[o]


def main():
    doc = fitz.open(PDF)
    pg = next(doc[p] for p in range(doc.page_count) if len(longs(doc[p])) == 12)
    P = sorted(longs(pg), key=lambda Q: np.median([y for _, y in Q]))
    x2, y2 = arr(P[7]); x3, y3 = arr(P[8])
    b2, b3 = np.median(y2), np.median(y3)
    x0 = min(x2.min(), x3.min())
    doc.close()

    # cari S-wave pertama (y2 maksimum) -> zoom ±0.22s di sekitarnya
    iS = int(np.argmax(y2))
    xc = x2[iS]
    lo, hi = xc - 0.12 * PSEC, xc + 0.22 * PSEC
    m2 = (x2 >= lo) & (x2 <= hi); m3 = (x3 >= lo) & (x3 <= hi)
    t2 = (x2[m2] - x0) / PSEC; t3 = (x3[m3] - x0) / PSEC
    tc = (xc - x0) / PSEC

    fig, ax = plt.subplots(figsize=(11, 5.4))
    ax.axhspan(b3 - 0.9 * PMV, b3 + 0.9 * PMV, color="#fde68a", alpha=.55,
               label="lajur normal V3 (±0.9 mV)")
    ax.axhline(b3, color="#ea580c", lw=.8, ls=":", alpha=.8)
    ax.plot(t2, y2[m2], color="#1d4ed8", lw=1.6, label="V2 (path vektor)")
    ax.plot(t3, y3[m3], color="#ea580c", lw=1.6, label="V3 (path vektor)")

    # kolom persilangan
    ax.axvline(tc, color="#7c3aed", lw=1.2, ls="--", alpha=.8)
    ax.annotate("kolom-x ini:\ntinta V2 & V3 BERTUMPUK\n(metode piksel bingung\nmilik lead mana)",
                xy=(tc, b3), xytext=(tc + 0.04, b3 - 1.1 * PMV),
                fontsize=9, color="#6d28d9",
                arrowprops=dict(arrowstyle="->", color="#6d28d9"))
    # penetrasi
    yb = y2[m2].max()
    ax.annotate("", xy=(tc, yb), xytext=(tc, b3),
                arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=1.6))
    ax.text(tc - 0.085, (yb + b3) / 2,
            "S-wave V2 menembus\n7.55 mm (0.75 mV)\nMELEWATI baseline V3",
            fontsize=9, color="#b91c1c", ha="right", va="center")

    ax.invert_yaxis()
    ax.set_title("Zoom satu persilangan: S-wave V2 menukik menembus lajur V3",
                 fontsize=12)
    ax.set_xlabel("detik"); ax.set_ylabel("y (point) — posisi di kertas")
    ax.legend(loc="upper right", fontsize=8.5); ax.grid(True, alpha=.25)
    fig.tight_layout()
    p = os.path.join(OUT, "fig_overlap_zoom.png")
    fig.savefig(p, dpi=120); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    main()
