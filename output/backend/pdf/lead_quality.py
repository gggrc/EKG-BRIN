"""
training/lead_quality.py — Flag mutu per-lead TANPA referensi (self-aware QC).

Prinsip medis: ke-12 lead merekam JANTUNG yang sama -> jumlah detak (R-peak)
harus konsisten antar-lead. Lead yang menyimpang (mis. V1 yang ter-overlap R-V2,
atau decode gerigi) terdeteksi sebagai pencilan. Juga cek kestabilan baseline.

Ini membuat pipeline jujur soal lead yang TAK ANDAL -> ditandai low-confidence
di FHIR, dan untuk lead itu dipakai nilai tercetak device. Defensibel medis:
sistem tahu batas dirinya, bukan mengklaim semua lead pasti benar.
"""

import numpy as np
from scipy.signal import find_peaks


def _beat_count(sig, fs):
    s = np.asarray(sig, float)
    s = s - np.median(s)
    if np.max(np.abs(s)) < 1e-6:
        return 0
    pk, _ = find_peaks(np.abs(s), distance=int(0.3 * fs),
                       height=0.4 * np.max(np.abs(s)))
    return len(pk)


def _polarity_inconsistent(sig, fs):
    """True bila polaritas QRS antar-beat tidak konsisten (sebagian naik,
    sebagian turun) — gejala decode tertukar trace lead tetangga yang ber-
    overlap (mis. R-V2 masif menembus V1 di LVH). Lead normal monofasik
    konsisten satu arah."""
    s = np.asarray(sig, float) - np.median(sig)
    if np.max(np.abs(s)) < 0.3:
        return False
    pk, _ = find_peaks(np.abs(s), distance=int(0.3 * fs),
                       height=0.4 * np.max(np.abs(s)))
    if len(pk) < 4:
        return False
    signs = np.sign(s[pk])                  # arah deflektsi tiap beat
    up = np.mean(signs > 0)
    # inkonsisten jika campur ~ (bukan dominan satu arah >80%)
    return 0.2 < up < 0.8


def lead_quality_flags(leads, fs):
    """
    return (low_conf_set, info_dict).
    low_conf: lead yang jumlah detaknya menyimpang dari median antar-lead,
              atau baseline tak stabil (gerigi/artefak).
    """
    beats = {nm: _beat_count(s, fs) for nm, s in leads.items()}
    flats = {}
    for nm, s in leads.items():
        a = np.asarray(s, float) - np.median(s)
        flats[nm] = float(np.mean(np.abs(a) < 0.15))   # fraksi dekat baseline
    vals = [b for b in beats.values() if b > 0]
    med = int(np.median(vals)) if vals else 0

    low = set()
    for nm in leads:
        dev = abs(beats[nm] - med)
        f = flats[nm]
        # (a) jumlah detak menyimpang dari konsensus antar-lead
        #     -> 0 detak (Lead-Off/mati) ATAU detak ekstra (gerigi/overlap).
        #     DP-tracking memberi hitungan konsisten utk lead yang benar,
        #     jadi lead amplitudo-kecil yang valid TIDAK ikut ke-flag.
        if med > 0 and dev > max(2, 0.35 * med):
            low.add(nm)
        # (b) baseline mati total (flat ~1.0, tanpa aktivitas) = Lead-Off
        elif f > 0.985:
            low.add(nm)
        # (c) baseline sangat tak stabil = artefak decode
        elif f < 0.55:
            low.add(nm)
    info = {'median_beats': med, 'beats': beats,
            'baseline_flat': {k: round(v, 2) for k, v in flats.items()}}
    return low, info


if __name__ == '__main__':
    import sys, json
    d = json.load(open(sys.argv[1]))
    low, info = lead_quality_flags(d['leads'], d['meta']['px_per_sec'])
    print('median beats (HR rujukan antar-lead):', info['median_beats'])
    for nm in d['leads']:
        print(f"  {nm:4s} beats={info['beats'][nm]:2d} "
              f"flat={info['baseline_flat'][nm]:.2f}"
              f"  {'LOW-CONF' if nm in low else ''}")
    print('low-confidence:', sorted(low) if low else 'none')
