"""
roundtrip_error.py — Ukur error round-trip: PDF asli -> sinyal digital ->
render balik ke posisi PDF -> bandingkan dgn trace asli.

Sumber error SATU-SATUNYA pada jalur vektor = RESAMPLING (trace asli punya
titik tak-seragam; kita resample ke grid seragam fs Hz). Saat digambar ulang
ke PDF, beda antara trace asli vs trace hasil-resample = error round-trip.

Lapor per lead: RMSE & max dalam mV, dan % terhadap amplitudo (rentang) lead.
Pakai: python roundtrip_error.py <pdf> [fs]
"""
import os
import sys

import numpy as np
import fitz

PT = 72.0 / 25.4
PMV = 10.0 * PT          # pt per mV
PSEC = 25.0 * PT         # pt per detik


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


def roundtrip(pdf_path, fs=250):
    doc = fitz.open(pdf_path)
    # halaman trace pertama
    page = next((doc[p] for p in range(doc.page_count)
                 if len(long_paths(doc[p])) in (6, 12)), None)
    if page is None:
        print("Bukan PDF vektor 6/12-lead."); return
    paths = long_paths(page)
    paths.sort(key=lambda P: np.median([y for _, y in P]))
    names6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
    names12 = names6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
    names = names12 if len(paths) == 12 else names6

    print(f"{os.path.basename(pdf_path)}  ({len(paths)} lead, fs={fs}Hz)")
    print(f"{'lead':>5} | {'RMSE_mV':>8} | {'max_mV':>7} | {'rentang_mV':>10} | {'%error':>7}")
    print("-" * 52)
    rmses = []
    for nm, P in zip(names, paths):
        xs = np.array([x for x, _ in P], float)
        ys = np.array([y for _, y in P], float)
        o = np.argsort(xs, kind="stable"); xs, ys = xs[o], ys[o]
        ux, idx = np.unique(xs, return_index=True); uy = ys[idx]
        x_lo, x_hi = ux.min(), ux.max()

        # ---- jalur kita: resample ke grid seragam fs ----
        n = int(round((x_hi - x_lo) / PSEC * fs))
        xg = np.linspace(x_lo, x_hi, n)
        yg = np.interp(xg, ux, uy)            # trace digital (seragam)

        # ---- render balik ke PDF = gambar yg seragam; bandingkan ke ASLI ----
        # di tiap titik asli, posisi hasil-render (interp dari grid seragam)
        y_render = np.interp(ux, xg, yg)
        resid_mv = (uy - y_render) / PMV      # selisih posisi -> mV

        rng = (uy.max() - uy.min()) / PMV
        rmse = float(np.sqrt(np.mean(resid_mv ** 2)))
        mx = float(np.max(np.abs(resid_mv)))
        pct = 100.0 * rmse / rng if rng > 1e-6 else 0.0
        rmses.append(rmse)
        print(f"{nm:>5} | {rmse:8.5f} | {mx:7.4f} | {rng:10.3f} | {pct:6.3f}%")
    doc.close()
    print("-" * 52)
    print(f"Rata-rata RMSE = {np.mean(rmses):.5f} mV  "
          f"(1 piksel grid 254dpi ~ 0.025 mV sbg pembanding)")


if __name__ == "__main__":
    pdf = sys.argv[1]
    fs = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    roundtrip(pdf, fs)
