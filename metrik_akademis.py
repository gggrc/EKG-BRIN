"""
metrik_akademis.py — Metrik BAKU literatur untuk menilai kesetiaan
PDF(asli) -> digital. Referensi = trace vektor asli (ground truth); uji =
sinyal digital hasil pipeline (resample fs Hz). Dihitung per lead + agregat:

  SNR (dB)  : Signal-to-Noise Ratio. Metrik skor PhysioNet/CinC Challenge 2024
              (digitalisasi citra EKG). SNR = 10*log10( Σ(r-mean)^2 / Σ(r-s)^2 ).
  PRD (%)   : Percentage RMS Difference (mean-removed = PRDN). Metrik klasik
              kompresi/rekonstruksi EKG. PRDN = 100*sqrt(Σ(r-s)^2/Σ(r-mean)^2).
  r (Pearson): korelasi bentuk gelombang.
  RMSE / maxAE (mV) : galat absolut.

Ambang kualitas PRD (Zigel, Cohen & Katz, IEEE TBME 2000; skala MOS):
  PRD < 2%  : "very good"      2-9% : "good"      >9% : turun.
Diagnostik (WDD) dianggap aman secara klinis bila < 4%.

Pakai: python metrik_akademis.py <pdf> [fs]
"""
import os
import sys

import numpy as np
import fitz

PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT


def long_paths(page, min_seg=500):
    out = []
    for dr in page.get_drawings():
        pts = []
        for it in dr['items']:
            if it[0] == 'l':
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
        if len(pts) > min_seg:
            out.append(pts)
    return out


def metrics(r, s):
    """r=referensi (asli), s=uji (digital). Keduanya array mV sejajar."""
    r = np.asarray(r, float); s = np.asarray(s, float)
    rm = r - r.mean()
    err = r - s
    sse = float(np.sum(err ** 2))
    ss = float(np.sum(rm ** 2)) + 1e-12
    prd = 100.0 * np.sqrt(sse / ss)                  # PRDN (%)
    snr = 10.0 * np.log10(ss / (sse + 1e-12))        # dB
    rmse = float(np.sqrt(np.mean(err ** 2)))
    maxae = float(np.max(np.abs(err)))
    rr = float(np.corrcoef(r, s)[0, 1]) if r.std() > 0 and s.std() > 0 else 1.0
    return snr, prd, rr, rmse, maxae


def quality(prd):
    if prd < 2:
        return "very good"
    if prd < 9:
        return "good"
    return "perlu ditinjau"


def run(pdf_path, fs=250):
    doc = fitz.open(pdf_path)
    page = next((doc[p] for p in range(doc.page_count)
                 if len(long_paths(doc[p])) in (6, 12)), None)
    if page is None:
        print("Bukan PDF vektor 6/12-lead."); return
    paths = long_paths(page)
    paths.sort(key=lambda P: np.median([y for _, y in P]))
    names6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
    names = (names6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']) if len(paths) == 12 else names6

    print(f"\n{os.path.basename(pdf_path)}  ({len(paths)} lead, fs={fs}Hz)")
    print(f"{'lead':>5} | {'SNR(dB)':>8} | {'PRD(%)':>7} | {'r':>7} | "
          f"{'RMSE_mV':>8} | {'maxAE_mV':>8} | mutu")
    print("-" * 72)
    allr, alls = [], []
    agg = []
    for nm, P in zip(names, paths):
        xs = np.array([x for x, _ in P], float)
        ys = np.array([y for _, y in P], float)
        o = np.argsort(xs, kind="stable"); xs, ys = xs[o], ys[o]
        ux, idx = np.unique(xs, return_index=True); uy = ys[idx]
        x_lo, x_hi = ux.min(), ux.max()
        n = int(round((x_hi - x_lo) / PSEC * fs))
        xg = np.linspace(x_lo, x_hi, n)
        yg = np.interp(xg, ux, uy)               # digital (resample)
        y_render = np.interp(ux, xg, yg)         # render balik di titik asli
        r = (uy.mean() - uy) / PMV               # mV asli (ref)
        s = (uy.mean() - y_render) / PMV         # mV digital (uji)
        snr, prd, rr, rmse, maxae = metrics(r, s)
        agg.append((snr, prd, rr, rmse, maxae))
        allr.append(r); alls.append(s)
        print(f"{nm:>5} | {snr:8.2f} | {prd:7.3f} | {rr:7.5f} | "
              f"{rmse:8.5f} | {maxae:8.4f} | {quality(prd)}")
    A = np.array(agg)
    print("-" * 72)
    print(f"{'RATA2':>5} | {A[:,0].mean():8.2f} | {A[:,1].mean():7.3f} | "
          f"{A[:,2].mean():7.5f} | {A[:,3].mean():8.5f} | {A[:,4].mean():8.4f} | "
          f"{quality(A[:,1].mean())}")
    # gabungan semua lead (global)
    R = np.concatenate(allr); S = np.concatenate(alls)
    gsnr, gprd, grr, grmse, gmax = metrics(R, S)
    print(f"\nGLOBAL (semua lead digabung):")
    print(f"  SNR={gsnr:.2f} dB | PRD={gprd:.3f}% ({quality(gprd)}) | "
          f"r={grr:.6f} | RMSE={grmse:.5f} mV | maxAE={gmax:.4f} mV")
    doc.close()


if __name__ == "__main__":
    pdf = sys.argv[1]
    fs = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    run(pdf, fs)
