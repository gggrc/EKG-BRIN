"""
plot_hasil.py — Render gambar dari JSON hasil run_any.py (skema universal v2).
Buat grid semua lead (6 atau 12) per record. Output PNG di folder yang sama.

Pakai:
  python plot_hasil.py                  # semua *.json di ./hasil
  python plot_hasil.py hasil/xxx.json   # satu file
"""
import os
import sys
import glob
import json

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
LEAD_ORDER = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
              'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


def plot_one(path):
    d = json.load(open(path, encoding="utf-8"))
    rec = d.get("recording", {})
    fs = int(rec.get("sampling_rate_hz") or d.get("sampling_rate") or 250)
    L = {k: np.asarray(v["signal"], float) for k, v in d["leads"].items()}
    names = [n for n in LEAD_ORDER if n in L] + [n for n in L if n not in LEAD_ORDER]
    nrow = len(names)
    ai = d.get("ai_screening", {})
    title = (f"{d.get('source_file','')}  |  {rec.get('num_leads','?')} lead, "
             f"{rec.get('duration_sec','?')}s @ {fs}Hz  |  "
             f"AI: {ai.get('top_label','-')}")

    fig, axes = plt.subplots(nrow, 1, figsize=(14, 1.5 * nrow + 1), sharex=True)
    if nrow == 1:
        axes = [axes]
    for ax, nm in zip(axes, names):
        y = L[nm]; t = np.arange(len(y)) / fs
        ax.plot(t, y, lw=0.6, color="k")
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_ylabel(nm, fontsize=9, rotation=0, ha="right", va="center")
        ax.grid(True, alpha=0.25)
        ax.margins(x=0)
    axes[-1].set_xlabel("detik")
    fig.suptitle(title, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    out = os.path.splitext(path)[0] + "_plot.png"
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print("->", out)
    return out


def main():
    args = sys.argv[1:]
    if args:
        files = args
    else:
        files = sorted(glob.glob(os.path.join(HERE, "hasil", "*.json")))
    for p in files:
        try:
            plot_one(p)
        except Exception as e:
            print("! gagal", p, type(e).__name__, e)


if __name__ == "__main__":
    main()
