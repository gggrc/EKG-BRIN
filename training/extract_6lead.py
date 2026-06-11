"""
extract_6lead.py — Ekstraksi VEKTOR eksak untuk PDF Kardia/AliveCor 6-lead
(Lead I, II, III, aVR, aVL, aVF). Trace tersimpan sbg polyline vektor di
halaman 1 (6 path panjang). Kalibrasi: 25mm/s, 10mm/mV; 1mm = 72/25.4 pt.

Keluaran:
  <id>_6l_signals.json   : {meta, leads{I..aVF}}
  <id>_6l_perlead_grid.png
  <id>_6l_perlead/<LEAD>.csv + .png
Pakai: python extract_6lead.py <pdf> [fs]
"""
import os
import sys
import json
import csv

import numpy as np
import fitz
from scipy.signal import butter, filtfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PT_PER_MM = 72.0 / 25.4
PMV_PT = 10.0 * PT_PER_MM        # 10 mm/mV -> pt/mV
PSEC_PT = 25.0 * PT_PER_MM       # 25 mm/s  -> pt/sec
LEAD6 = ["I", "II", "III", "aVR", "aVL", "aVF"]
HP_FC = 0.5                      # Hz: highpass baseline-wander removal (std AHA)


def highpass(x, fs, fc=HP_FC):
    """Buang drift < fc Hz (baseline wander). Linear & zero-phase (filtfilt)
    -> bentuk P-QRS-T tak terdistorsi, relasi antar-lead tetap terjaga."""
    if len(x) < 27:
        return x
    b, a = butter(2, fc / (fs / 2.0), btype="high")
    return filtfilt(b, a, x)


def _polyline(items):
    """Kumpulkan (x,y) terurut dari item garis 'l'."""
    xs, ys = [], []
    for it in items:
        if it[0] == "l":
            p0, p1 = it[1], it[2]
            xs.append(p0.x); ys.append(p0.y)
            xs.append(p1.x); ys.append(p1.y)
    return np.asarray(xs), np.asarray(ys)


def _page_leads(traces, fs):
    """Dari 6 path 1 halaman -> dict {lead: mv_array} + durasi halaman."""
    polys = []
    for d in traces:
        xs, ys = _polyline(d["items"])
        polys.append((float(np.median(ys)), xs, ys))
    polys.sort(key=lambda t: t[0])          # atas->bawah = I..aVF
    x_lo = min(float(xs.min()) for _, xs, _ in polys)
    x_hi = max(float(xs.max()) for _, xs, _ in polys)
    n = max(1, int((x_hi - x_lo) / PSEC_PT * fs))
    tgrid = np.linspace(x_lo, x_hi, n)
    out = {}
    for k, (med_y, xs, ys) in enumerate(polys):
        order = np.argsort(xs, kind="stable")
        xx, yy = xs[order], ys[order]
        ux, idx = np.unique(xx, return_index=True)
        yi = np.interp(tgrid, ux, yy[idx])
        out[LEAD6[k]] = (med_y - yi) / PMV_PT       # mV (baseline mentah)
    return out, n


def extract_6lead(pdf_path, fs=250, hp=True):
    """Sambung SEMUA halaman trace (rekaman 30s terpotong per halaman) ->
    sinyal penuh per lead. Halaman diurutkan sesuai urutan dokumen.
    hp=True -> highpass 0.5Hz (buang baseline wander, std AHA)."""
    doc = fitz.open(pdf_path)
    page_segs = []                          # (pno, {lead:mv}, n)
    for pno in range(doc.page_count):
        dr = doc[pno].get_drawings()
        longs = [d for d in dr
                 if sum(1 for it in d["items"] if it[0] == "l") > 1000]
        if len(longs) == 6:
            seg, n = _page_leads(longs, fs)
            page_segs.append((pno, seg, n))
    doc.close()
    if not page_segs:
        return None

    # sambung per lead sesuai urutan halaman
    leads = {nm: [] for nm in LEAD6}
    for _, seg, _ in page_segs:
        for nm in LEAD6:
            leads[nm].append(seg[nm])
    for nm in LEAD6:
        sig = np.concatenate(leads[nm])
        if hp:
            sig = highpass(sig, fs)         # buang baseline wander < 0.5Hz
        sig = sig - np.median(sig)          # koreksi baseline global
        leads[nm] = sig.astype(float).tolist()

    n_total = len(leads["I"])
    pages = [p for p, _, _ in page_segs]
    meta = {"fs": fs, "source": "kardia_6lead_vector_multipage",
            "pt_per_mv": PMV_PT, "pt_per_sec": PSEC_PT,
            "pages_joined": pages, "n_samples": n_total,
            "duration_sec": round(n_total / fs, 2),
            "highpass_hz": HP_FC if hp else None}
    return {"meta": meta, "leads": leads}


def plot_perlead(out, pdf_path):
    leads = out["leads"]; fs = out["meta"]["fs"]
    rid = os.path.splitext(os.path.basename(pdf_path))[0]
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_test")
    os.makedirs(base, exist_ok=True)
    outdir = os.path.join(base, rid + "_6l_perlead")
    os.makedirs(outdir, exist_ok=True)

    # JSON
    json.dump(out, open(os.path.join(base, rid + "_6l_signals.json"), "w"),
              ensure_ascii=False)

    names = [n for n in LEAD6 if n in leads]
    fig, axes = plt.subplots(6, 1, figsize=(13, 12))
    for ax, nm in zip(axes, names):
        y = np.asarray(leads[nm]); t = np.arange(len(y)) / fs
        ax.plot(t, y, lw=0.7, color="k")
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_title(f"{nm}  ({len(y)} sampel, {y.min():.2f}..{y.max():.2f} mV)",
                     fontsize=9)
        ax.set_ylabel("mV", fontsize=8); ax.grid(True, alpha=0.25)
    axes[-1].set_xlabel("detik")
    fig.suptitle(f"{rid} — 6-LEAD (vektor eksak)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    grid = os.path.join(base, rid + "_6l_perlead_grid.png")
    fig.savefig(grid, dpi=110); plt.close(fig)

    for nm in names:
        y = np.asarray(leads[nm]); t = np.arange(len(y)) / fs
        with open(os.path.join(outdir, f"{nm}.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(["t_sec", "mV"])
            for ti, yi in zip(t, y):
                w.writerow([f"{ti:.4f}", f"{yi:.4f}"])
        fig, ax = plt.subplots(figsize=(12, 2.4))
        ax.plot(t, y, lw=0.8, color="k"); ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_title(f"{rid} — Lead {nm}"); ax.set_xlabel("detik"); ax.set_ylabel("mV")
        ax.grid(True, alpha=0.3); fig.tight_layout()
        fig.savefig(os.path.join(outdir, f"{nm}.png"), dpi=110); plt.close(fig)
    print("grid:", grid)
    return grid


if __name__ == "__main__":
    pdf = sys.argv[1]
    fs = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    out = extract_6lead(pdf, fs)
    if out is None:
        print("BUKAN format 6-lead vektor:", pdf); sys.exit(1)
    print("OK 6-lead vektor:", out["meta"])
    plot_perlead(out, pdf)
