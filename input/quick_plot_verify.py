# quick_plot_verify.py
import wfdb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

record = wfdb.rdrecord('ptb-xl/records500/00000/00005_hr')
signal = record.p_signal

name_map = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF'}
lead_names = [name_map.get(n, n) for n in record.sig_name]

fs = record.fs
t = np.arange(signal.shape[0]) / fs

# skala amplitudo global untuk semua lead
max_abs = np.max(np.abs(signal))

fig, axes = plt.subplots(12, 1, figsize=(20, 20))

for i, lead in enumerate(lead_names):
    axes[i].plot(t, signal[:, i], 'b-', linewidth=0.6)

    axes[i].set_ylabel(
        lead,
        fontsize=8,
        rotation=0,
        labelpad=22
    )

    axes[i].set_xlim(0, 10)

    # semua lead pakai skala yang sama
    axes[i].set_ylim(-max_abs, max_abs)

    axes[i].grid(True, color='#ffaaaa', linewidth=0.3)
    axes[i].set_facecolor('#fff5f5')

plt.suptitle(
    'PTB-XL Record 00005 — Verifikasi Sinyal Nyata (12-Lead)',
    fontsize=11
)

plt.tight_layout()
plt.savefig(
    'verify_real_signal.png',
    dpi=120,
    bbox_inches='tight'
)
plt.close()

print("Saved: verify_real_signal.png")
print(f"Global Y range: {-max_abs:.3f} to {max_abs:.3f} mV")
print("Signal stats per lead:")

for i, lead in enumerate(lead_names):
    s = signal[:, i]
    print(
        f"  {lead:<5}: "
        f"min={s.min():.3f} "
        f"max={s.max():.3f} "
        f"std={s.std():.4f}"
    )