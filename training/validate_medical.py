"""
training/validate_medical.py — Validasi MEDIS hasil digitalisasi vs nilai klinis
TERCETAK pada PDF (pengukuran device = ground-truth independen).

Untuk data EKG NYATA tak ada sinyal ground-truth per-sampel, sehingga kebenaran
diukur terhadap pengukuran device yang tercetak di laporan:
  - HR (bpm)        : dari deteksi R-peak sinyal digital  vs  HR tercetak
  - RV5 (mV)        : amplitudo R lead V5                  vs  tercetak
  - SV1 (mV)        : kedalaman S lead V1                  vs  tercetak

Ini menjadikan pipeline DAPAT DIPERTANGGUNGJAWABKAN secara medis: kalibrasi
waktu (HR) dan amplitudo (RV5/SV1) diverifikasi ke acuan pabrikan, bukan klaim
sepihak. Selisih dilaporkan apa adanya (MAE + per-kasus), termasuk kegagalan.

Catatan ilmiah: HR & amplitudo dipilih karena robust dan langsung menguji
kalibrasi. Durasi QRS/QT butuh deteksi titik fidusia presisi (onset/offset) yang
lebih sensitif dan dilaporkan terpisah bila tersedia.
"""

import re
import fitz
import numpy as np
from scipy.signal import find_peaks


def parse_printed(pdf_path):
    """Ekstrak nilai klinis tercetak dari teks PDF (ground-truth device)."""
    t = fitz.open(pdf_path)[0].get_text()
    def g(pat):
        m = re.search(pat, t)
        return m.groups() if m else None
    hr = g(r'HR\s*:?\s*(\d+)')
    p = g(r'\bP\s*:?\s*(\d+)\s*ms')
    pr = g(r'\bPR\s*:?\s*(\d+)')
    qrs = g(r'QRS\s*:?\s*(\d+)')
    qt = g(r'QT/QTc\s*:?\s*(\d+)/(\d+)')
    rv = g(r'RV5/SV1\s*:?\s*([\d.]+)/([\d.]+)')
    dx = re.search(r'Diagnosis Information:\s*\n?\s*(.+)', t)
    return {
        'HR': int(hr[0]) if hr else None,
        'P_ms': int(p[0]) if p else None,
        'PR_ms': int(pr[0]) if pr else None,
        'QRS_ms': int(qrs[0]) if qrs else None,
        'QT_ms': int(qt[0]) if qt else None,
        'QTc_ms': int(qt[1]) if qt else None,
        'RV5_mV': float(rv[0]) if rv else None,
        'SV1_mV': float(rv[1]) if rv else None,
        'Dx': dx.group(1).strip() if dx else None,
    }


def estimate_hr(sig, fs):
    """HR (bpm) dari deteksi R-peak; pakai median interval RR (robust)."""
    s = np.asarray(sig, float)
    s = s - np.median(s)
    if s.std() < 1e-6:
        return None
    # orientasi: pakai |sinyal| jika R negatif dominan
    thr = max(0.3 * np.max(np.abs(s)), 3 * np.std(s) * 0.0 + 0.25)
    pk, _ = find_peaks(np.abs(s), distance=int(0.3 * fs),
                       height=0.4 * np.max(np.abs(s)))
    if len(pk) < 2:
        return None
    rr = np.diff(pk) / fs
    rr = rr[(rr > 0.3) & (rr < 2.0)]        # buang outlier (0.3–2 s = 30–200 bpm)
    if len(rr) == 0:
        return None
    return 60.0 / np.median(rr)


def measure_from_signal(leads, fs):
    """Hitung HR, RV5, SV1 dari sinyal digital (mV)."""
    out = {'HR': None, 'RV5_mV': None, 'SV1_mV': None}
    # HR: pakai lead II bila ada, jika tidak V2/I
    for k in ('II', 'V2', 'I', 'V5'):
        if k in leads:
            hr = estimate_hr(leads[k], fs)
            if hr:
                out['HR'] = hr
                break
    if 'V5' in leads:
        v5 = np.asarray(leads['V5'], float)
        out['RV5_mV'] = float(np.max(v5) - np.median(v5))     # amplitudo R
    if 'V1' in leads:
        v1 = np.asarray(leads['V1'], float)
        out['SV1_mV'] = float(np.median(v1) - np.min(v1))     # kedalaman S
    return out


def compare(pdf_path, leads, fs):
    """Tabel pembanding digital vs tercetak + selisih."""
    printed = parse_printed(pdf_path)
    meas = measure_from_signal(leads, fs)
    rows = []
    for key, unit in (('HR', 'bpm'), ('RV5_mV', 'mV'), ('SV1_mV', 'mV')):
        p = printed.get(key)
        m = meas.get(key)
        err = (abs(p - m) if (p is not None and m is not None) else None)
        rows.append((key, unit, p, m, err))
    return printed, meas, rows


if __name__ == '__main__':
    import sys, json
    pdf = sys.argv[1]
    sig_json = sys.argv[2]   # output digitize_real (_signals.json)
    d = json.load(open(sig_json))
    fs = d['meta']['px_per_sec']
    printed, meas, rows = compare(pdf, d['leads'], fs)
    print('Dx tercetak:', printed['Dx'])
    print(f"{'param':8s} {'tercetak':>10s} {'digital':>10s} {'selisih':>10s}")
    for k, u, p, m, e in rows:
        ps = f'{p}' if p is not None else '-'
        ms = f'{m:.3f}' if m is not None else '-'
        es = f'{e:.3f}' if e is not None else '-'
        print(f'{k:8s} {ps:>10s} {ms:>10s} {es:>10s}  {u}')
