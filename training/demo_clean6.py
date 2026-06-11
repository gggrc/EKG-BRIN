"""Demo: baseline-wander removal (highpass 0.5Hz) utk 6-lead Kardia.
Tampilkan sebelum vs sesudah pada lead II (yang paling goyang di awal)."""
import sys, json
import numpy as np
from scipy.signal import butter, filtfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def highpass(x, fs=250, fc=0.5):
    b, a = butter(2, fc / (fs / 2), btype="high")
    return filtfilt(b, a, x)

p = sys.argv[1]
d = json.load(open(p)); fs = d["meta"]["fs"]
fig, axes = plt.subplots(2, 1, figsize=(13, 5), sharex=True)
for ax, (title, fn) in zip(axes, [("ASLI (raw)", lambda y: y),
                                   ("Setelah highpass 0.5Hz", highpass)]):
    for nm, col in [("II", "k")]:
        y = np.asarray(d["leads"][nm]); t = np.arange(len(y)) / fs
        ax.plot(t, fn(y), lw=0.6, color=col)
    ax.axhline(0, color="r", lw=0.4, alpha=0.5)
    ax.set_title(f"Lead II — {title}"); ax.set_ylabel("mV"); ax.grid(True, alpha=0.3)
axes[-1].set_xlabel("detik")
fig.tight_layout()
out = p.replace("_6l_signals.json", "_clean_compare.png")
fig.savefig(out, dpi=110); print(out)
