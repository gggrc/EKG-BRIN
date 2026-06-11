"""
plot_perlead.py — Tampilkan tiap lead SECARA TERPISAH (per-lead) dari file
*_signals.json hasil ekstraksi. Buat 2 keluaran:
  1) <id>_perlead_grid.png  : 12 panel (1 lead per panel), grid 6x2
  2) <id>_perlead/<LEAD>.csv : 1 CSV per lead (kolom: t_sec, mV)
  3) <id>_perlead/<LEAD>.png : 1 gambar per lead (zoom satu lead)

Pakai:
  python plot_perlead.py <path_signals.json>
"""
import os
import sys
import json
import csv

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LEAD_ORDER = ["I", "II", "III", "aVR", "aVL", "aVF",
              "V1", "V2", "V3", "V4", "V5", "V6"]


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    meta = data.get("meta", {})
    leads = data["leads"]
    fs = float(meta.get("fs", 250))
    rid = os.path.splitext(os.path.basename(path))[0].replace("_signals", "")
    outdir = os.path.join(os.path.dirname(path), rid + "_perlead")
    os.makedirs(outdir, exist_ok=True)

    names = [n for n in LEAD_ORDER if n in leads] + \
            [n for n in leads if n not in LEAD_ORDER]

    # ---- 1) grid 6x2 ----
    fig, axes = plt.subplots(6, 2, figsize=(14, 16), sharex=False)
    axes = axes.ravel()
    for k, nm in enumerate(names):
        y = np.asarray(leads[nm], dtype=float)
        t = np.arange(len(y)) / fs
        ax = axes[k]
        ax.plot(t, y, lw=0.7, color="k")
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_title(f"{nm}  ({len(y)} sampel, "
                     f"{y.min():.2f}..{y.max():.2f} mV)", fontsize=9)
        ax.set_ylabel("mV", fontsize=8)
        ax.grid(True, alpha=0.25)
        if k >= len(names) - 2:
            ax.set_xlabel("detik", fontsize=8)
    for k in range(len(names), len(axes)):
        axes[k].axis("off")
    fig.suptitle(f"{rid} — PER-LEAD (12 lead terpisah)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    grid_path = os.path.join(os.path.dirname(path), rid + "_perlead_grid.png")
    fig.savefig(grid_path, dpi=110)
    plt.close(fig)

    # ---- 2) + 3) per lead: CSV + PNG ----
    for nm in names:
        y = np.asarray(leads[nm], dtype=float)
        t = np.arange(len(y)) / fs
        # CSV
        with open(os.path.join(outdir, f"{nm}.csv"), "w", newline="",
                  encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t_sec", "mV"])
            for ti, yi in zip(t, y):
                w.writerow([f"{ti:.4f}", f"{yi:.4f}"])
        # PNG zoom
        fig, ax = plt.subplots(figsize=(12, 2.6))
        ax.plot(t, y, lw=0.8, color="k")
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_title(f"{rid} — Lead {nm}", fontsize=10)
        ax.set_xlabel("detik"); ax.set_ylabel("mV")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(os.path.join(outdir, f"{nm}.png"), dpi=110)
        plt.close(fig)

    print("grid :", grid_path)
    print("perlead dir:", outdir)
    print("lead :", ", ".join(names))


if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else \
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "export_test", "20251118-143153-0004_signals.json")
    main(p)
