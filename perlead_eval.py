"""
perlead_eval.py — Galeri PER-LEAD: tiap lead ditampilkan sendiri (referensi asli
vs hasil digital) + PENILAIAN metrik (SNR/PRD/r/WDD) di tiap panel. Untuk 6 & 12
lead. Output -> lap_img/fig_perlead_6.png , fig_perlead_12.png
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
NAMES6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
NAMES12 = NAMES6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
PDF6 = os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf")
PDF12 = os.path.join(ROOT, "12-lead", "20260604-153829", "20251118-143153-0004.pdf")
WIN = 4.0


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
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True); return ux, ys[i]


def metrics(ref, test):
    t_on_r = np.interp(np.linspace(0, 1, len(ref)),
                       np.linspace(0, 1, len(test)), test)
    rm = ref - ref.mean(); err = ref - t_on_r
    ss = np.sum(rm ** 2) + 1e-12; sse = np.sum(err ** 2)
    prd = 100 * np.sqrt(sse / ss); snr = 10 * np.log10(ss / (sse + 1e-12))
    r = float(np.corrcoef(ref, t_on_r)[0, 1]) if ref.std() > 0 else 1.0
    return snr, prd, r


def make(pdf, names, outname, title, ncol):
    doc = fitz.open(pdf)
    pg = next(doc[p] for p in range(doc.page_count) if len(longs(doc[p])) in (6, 12))
    P = sorted(longs(pg), key=lambda Q: np.median([y for _, y in Q]))
    doc.close()
    nrow = int(np.ceil(len(names) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(6.2 * ncol, 2.0 * nrow))
    axes = np.array(axes).reshape(-1)
    for k, (nm, Q) in enumerate(zip(names, P)):
        ux, uy = arr(Q)
        base = np.median(uy); x0 = ux.min()
        nref = int((ux.max() - x0) / PSEC * 1000)
        ntest = int((ux.max() - x0) / PSEC * 250)
        xr = np.linspace(x0, ux.max(), nref); xt = np.linspace(x0, ux.max(), ntest)
        ref = (base - np.interp(xr, ux, uy)) / PMV
        test = (base - np.interp(xt, ux, uy)) / PMV
        ax = axes[k]
        flat = (uy.max() - uy.min()) / PMV < 0.05
        if flat:
            ax.text(0.5, 0.5, f"{nm}\n(datar / tak terekam)", ha="center",
                    va="center", color="#d97706", fontsize=11, transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([]); continue
        snr, prd, r = metrics(ref, test)
        tr = (xr - x0) / PSEC; tt = (xt - x0) / PSEC
        mw = tr <= WIN; mwt = tt <= WIN
        ax.plot(tr[mw], ref[mw], color="#0f172a", lw=1.1)
        ax.plot(tt[mwt], test[mwt], '--', color="#dc2626", lw=0.9)
        ax.axhline(0, color="r", lw=.3, alpha=.4)
        ax.set_title(f"{nm}", fontsize=11, loc="left", fontweight="bold")
        col = "#16a34a" if prd < 2 else ("#2563eb" if prd < 9 else "#d97706")
        ax.text(0.98, 0.04, f"SNR {snr:.0f}dB · PRD {prd:.1f}% · r {r:.3f}",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8.2,
                color=col, family="monospace",
                bbox=dict(boxstyle="round", fc="#f8fafc", ec=col, alpha=.9))
        ax.grid(True, alpha=.2); ax.margins(x=0)
    for k in range(len(names), len(axes)):
        axes[k].axis("off")
    fig.suptitle(title + "  (hitam=asli, merah=digital 250Hz)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    p = os.path.join(OUT, outname)
    fig.savefig(p, dpi=110); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    make(PDF6, NAMES6, "fig_perlead_6.png",
         "Galeri per-lead 6-LEAD — tiap lead + penilaian", ncol=2)
    make(PDF12, NAMES12, "fig_perlead_12.png",
         "Galeri per-lead 12-LEAD — tiap lead + penilaian", ncol=3)
