"""
regenerate_real_samples.py
Buat ulang semua sample dari sinyal PTB-XL NYATA.
Jalankan ini untuk replace semua file dummy dengan data real.
"""
import wfdb
import numpy as np
import pandas as pd
import json
import os
import subprocess
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ── Load PTB-XL ─────────────────────────────────────────────────
print("Loading PTB-XL record...")
record = wfdb.rdrecord('ptb-xl/records500/00000/00005_hr')
signal = record.p_signal       # shape: (5000, 12)
fs     = record.fs             # 500 Hz

name_map   = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF'}
lead_names = [name_map.get(n, n) for n in record.sig_name]
# lead_names = ['I','II','III','aVR','aVL','aVF','V1','V2','V3','V4','V5','V6']

LEADS_6  = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
LEADS_12 = LEADS_6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']
lead_idx = {name: lead_names.index(name) for name in LEADS_12}

t = np.linspace(0, 10, 5000)
os.makedirs('sample_inputs', exist_ok=True)

# ════════════════════════════════════════════════════════════════
# 1. test_ecg.csv — ganti dengan sinyal nyata 6-lead
# ════════════════════════════════════════════════════════════════
print("Generating test_ecg.csv (6-lead, real PTB-XL)...")
df_6 = pd.DataFrame({
    lead: signal[:, lead_idx[lead]] for lead in LEADS_6
})
df_6.to_csv('test_ecg.csv', index=False)
print(f"  -> test_ecg.csv ({len(df_6)} rows, 6 leads)")

# ════════════════════════════════════════════════════════════════
# 2. test_ecg_image.png — 6-lead image dari sinyal nyata
# ════════════════════════════════════════════════════════════════
print("Generating test_ecg_image.png (6-lead, real PTB-XL)...")
fig, axes = plt.subplots(6, 1, figsize=(20, 12))
fig.patch.set_facecolor('white')
for i, lead in enumerate(LEADS_6):
    sig = signal[:, lead_idx[lead]]
    axes[i].plot(t, sig, 'k-', linewidth=0.7)
    axes[i].set_ylabel(lead, fontsize=8, rotation=0, labelpad=22, va='center')
    axes[i].set_xlim(0, 10)
    axes[i].set_ylim(-2.5, 2.5)
    axes[i].grid(True, color='#ffaaaa', linewidth=0.3, alpha=0.8)
    axes[i].set_facecolor('#fff5f5')
    axes[i].tick_params(labelsize=6)
plt.suptitle('ECG — PTB-XL Record 00001 (6-Lead)', fontsize=10)
plt.tight_layout()
plt.savefig('test_ecg_image.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print("  -> test_ecg_image.png")

# ════════════════════════════════════════════════════════════════
# 3. sample_inputs/ — update semua vendor samples dengan record nyata
# ════════════════════════════════════════════════════════════════

# CSV vendor A (6-lead standar)
print("Updating sample_inputs/vendor_portable_A.csv...")
df_6.to_csv('sample_inputs/vendor_portable_A.csv', index=False)

# CSV vendor B (12-lead, nama kolom berbeda)
print("Updating sample_inputs/vendor_portable_B.csv (12-lead)...")
df_12 = pd.DataFrame({
    'lead_I':   signal[:, lead_idx['I']],
    'lead_II':  signal[:, lead_idx['II']],
    'lead_III': signal[:, lead_idx['III']],
    'AVR':      signal[:, lead_idx['aVR']],
    'AVL':      signal[:, lead_idx['aVL']],
    'AVF':      signal[:, lead_idx['aVF']],
    'V1':       signal[:, lead_idx['V1']],
    'V2':       signal[:, lead_idx['V2']],
    'V3':       signal[:, lead_idx['V3']],
    'V4':       signal[:, lead_idx['V4']],
    'V5':       signal[:, lead_idx['V5']],
    'V6':       signal[:, lead_idx['V6']],
})
df_12.to_csv('sample_inputs/vendor_portable_B.csv', index=False)
print(f"  -> vendor_portable_B.csv (12-lead)")

# JSON IoT (6-lead)
print("Updating sample_inputs/vendor_iot.json...")
raw_json = {
    "device": "ECG-6L-IoT-v2",
    "fs": int(fs),
    "duration": 10,
    "leads": {
        lead: [round(float(v), 4) for v in signal[:, lead_idx[lead]]]
        for lead in LEADS_6
    }
}
with open('sample_inputs/vendor_iot.json', 'w') as f:
    json.dump(raw_json, f, indent=2)

# PNG 6-lead (untuk sample_inputs)
print("Updating sample_inputs/vendor_scan.png (6-lead)...")
fig, axes = plt.subplots(6, 1, figsize=(20, 12))
fig.patch.set_facecolor('white')
for i, lead in enumerate(LEADS_6):
    axes[i].plot(t, signal[:, lead_idx[lead]], 'k-', linewidth=0.7)
    axes[i].set_ylabel(lead, fontsize=8, rotation=0, labelpad=22, va='center')
    axes[i].set_xlim(0, 10); axes[i].set_ylim(-2.5, 2.5)
    axes[i].grid(True, color='#ffaaaa', linewidth=0.3, alpha=0.8)
    axes[i].set_facecolor('#fff5f5'); axes[i].tick_params(labelsize=6)
plt.tight_layout()
plt.savefig('sample_inputs/vendor_scan.png', dpi=150,
            bbox_inches='tight', facecolor='white')
plt.close()

# PNG 12-lead
print("Generating sample_inputs/vendor_scan_12lead.png...")
fig, axes = plt.subplots(12, 1, figsize=(20, 22))
fig.patch.set_facecolor('white')
for i, lead in enumerate(LEADS_12):
    axes[i].plot(t, signal[:, lead_idx[lead]], 'k-', linewidth=0.7)
    axes[i].set_ylabel(lead, fontsize=8, rotation=0, labelpad=22, va='center')
    axes[i].set_xlim(0, 10); axes[i].set_ylim(-2.5, 2.5)
    axes[i].grid(True, color='#ffaaaa', linewidth=0.3, alpha=0.8)
    axes[i].set_facecolor('#fff5f5'); axes[i].tick_params(labelsize=6)
plt.suptitle('ECG — PTB-XL Record 00001 (12-Lead)', fontsize=10)
plt.tight_layout()
plt.savefig('sample_inputs/vendor_scan_12lead.png', dpi=150,
            bbox_inches='tight', facecolor='white')
plt.close()
print("  -> sample_inputs/vendor_scan_12lead.png")

# ════════════════════════════════════════════════════════════════
# 3b. XML (Generic ECG format)
# ════════════════════════════════════════════════════════════════
print("Generating sample_inputs/vendor_legacy.xml (6-lead)...")
xml_lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<ECG>',
    f'  <SampleRate>{int(fs)}</SampleRate>',
    '  <Patient><PatientID>PTB-00004</PatientID></Patient>'
]
for lead in LEADS_6:
    vals = " ".join([f"{v:.4f}" for v in signal[:, lead_idx[lead]]])
    xml_lines.append(f'  <lead name="{lead}"><values>{vals}</values></lead>')
xml_lines.append('</ECG>')

with open('sample_inputs/vendor_legacy.xml', 'w') as f:
    f.write("\n".join(xml_lines))
print("  -> sample_inputs/vendor_legacy.xml")

# ════════════════════════════════════════════════════════════════
# 3c. PDF (Generate using generate_pdf_samples.py)
# ════════════════════════════════════════════════════════════════
print("Generating PDF samples via generate_pdf_samples.py...")
subprocess.run(["python", "generate_pdf_samples.py"], check=True)


# ════════════════════════════════════════════════════════════════
# 4. Verifikasi sekilas
# ════════════════════════════════════════════════════════════════
print("\n" + "="*50)
print("[OK] Semua sample sekarang pakai data PTB-XL nyata!")
print(f"\nSignal shape  : {signal.shape} (5000 samples × 12 leads)")
print(f"Sampling rate : {fs} Hz")
print(f"Durasi        : {signal.shape[0]/fs} detik")
print(f"\nRange per lead (6 utama):")
for lead in LEADS_6:
    s = signal[:, lead_idx[lead]]
    print(f"  {lead:<5}: min={s.min():.3f} max={s.max():.3f} std={s.std():.3f} mV")

print(f"\nFile yang di-update:")
print("  test_ecg.csv                      ← 6-lead CSV")
print("  test_ecg_image.png                ← 6-lead image")
print("  sample_inputs/vendor_portable_A.csv  ← 6-lead CSV")
print("  sample_inputs/vendor_portable_B.csv  ← 12-lead CSV")
print("  sample_inputs/vendor_iot.json        ← 6-lead JSON")
print("  sample_inputs/vendor_scan.png        ← 6-lead image")
print("  sample_inputs/vendor_scan_12lead.png ← 12-lead image")
print("  sample_inputs/vendor_legacy.xml      ← 6-lead XML (BARU)")
print("  sample_inputs/vendor_medicore_6L.pdf ← 6-lead PDF (BARU)")
print("  sample_inputs/vendor_cardiolite_portable.pdf ← 6-lead PDF (BARU)")
print("  sample_inputs/vendor_heartscan_pro.pdf ← 12-lead PDF (BARU)")
print("="*50)