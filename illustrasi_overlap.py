"""
illustrasi_overlap.py — Tunjukkan KENAPA tumpang tindih (overlap) bisa ditangani.
Contoh nyata: 12-lead 0004, V2 (gelombang-S dalam) menyilang ke lajur V3.

Kiri  : posisi di HALAMAN (koordinat-y PDF) — tinta V2 & V3 bersilang.
Kanan : hasil ekstraksi — tiap lead path vektor TERPISAH -> sinyal bersih,
        tak tercampur. Output -> lap_img/fig_overlap.png
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
WIN = 2.5


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


def lead(P, x0, xmax):
    xs = np.array([x for x, _ in P]); ys = np.array([y for _, y in P])
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True); uy = ys[i]
    m = (ux >= x0) & (ux <= xmax)
    return ux[m], uy[m]


def main():
    doc = fitz.open(PDF)
    pg = next(doc[p] for p in range(doc.page_count) if len(longs(doc[p])) == 12)
    P = sorted(longs(pg), key=lambda Q: np.median([y for _, y in Q]))
    V2, V3 = P[7], P[8]
    x0 = min(min(x for x, _ in V2), min(x for x, _ in V3))
    xmax = x0 + WIN * PSEC
    x2, y2 = lead(V2, x0, xmax)
    x3, y3 = lead(V3, x0, xmax)
    b2, b3 = np.median(y2), np.median(y3)
    t2 = (x2 - x0) / PSEC; t3 = (x3 - x0) / PSEC
    doc.close()

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(14, 5.2))

    # ---- KIRI: posisi di halaman (y PDF, terbalik) ----
    # lajur nominal tiap lead (median ± ~1.8mV)
    axL.axhspan(b3 - 1.0*PMV, b3 + 1.0*PMV, color="#fde68a", alpha=.5,
                label="lajur V3")
    axL.plot(t2, y2, color="#1d4ed8", lw=1.1, label="V2 (path vektor)")
    axL.plot(t3, y3, color="#ea580c", lw=1.1, label="V3 (path vektor)")
    # tandai S-wave V2 yang menukik ke lajur V3
    iS = int(np.argmax(y2))
    axL.annotate("S-wave V2 menukik\nMASUK lajur V3",
                 xy=(t2[iS], y2[iS]), xytext=(t2[iS] + 0.25, y2[iS] - 8),
                 fontsize=9, color="#b91c1c",
                 arrowprops=dict(arrowstyle="->", color="#b91c1c"))
    axL.invert_yaxis()
    axL.set_title("DI HALAMAN: tinta V2 & V3 BERSILANG", fontsize=11)
    axL.set_xlabel("detik"); axL.set_ylabel("y (point) — posisi di kertas")
    axL.legend(loc="lower right", fontsize=8); axL.grid(True, alpha=.25)

    # ---- KANAN: hasil ekstraksi (mV, terpisah, di-offset utk jelas) ----
    mv2 = (b2 - y2) / PMV
    mv3 = (b3 - y3) / PMV
    axR.plot(t2, mv2 + 2.2, color="#1d4ed8", lw=1.0)
    axR.plot(t3, mv3 - 2.2, color="#ea580c", lw=1.0)
    axR.text(0.02, 2.2 + 1.4, "V2 (bersih)", color="#1d4ed8", fontsize=10)
    axR.text(0.02, -2.2 + 1.4, "V3 (bersih)", color="#ea580c", fontsize=10)
    axR.axhline(2.2, color="#1d4ed8", lw=.4, alpha=.4)
    axR.axhline(-2.2, color="#ea580c", lw=.4, alpha=.4)
    axR.set_title("HASIL: tiap lead TERPISAH, tak tercampur", fontsize=11)
    axR.set_xlabel("detik"); axR.set_ylabel("mV (di-offset agar jelas)")
    axR.grid(True, alpha=.25); axR.set_yticks([])

    fig.suptitle("Kenapa tumpang tindih bisa ditangani: tiap lead = PATH VEKTOR "
                 "tersendiri (daftar koordinat berbeda)", fontsize=12.5)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, "fig_overlap.png")
    fig.savefig(p, dpi=120); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    main()
