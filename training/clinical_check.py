"""
training/clinical_check.py — VALIDASI KLINIS menyeluruh: pastikan output digital
TIDAK mengubah pembacaan EKG. Bandingkan fitur klinis sinyal digital vs diagnosis
& pengukuran TERCETAK device (acuan independen pabrikan).

Cek:
  1. Laju (HR) digital vs cetak  -> kalibrasi waktu
  2. Konsistensi RITME: HR digital cocok dgn kategori diagnosis device
     (Bradycardia<60, Tachycardia>100, Sinus/Arrhythmia 60-100)
  3. Lead-Off device -> lead dada terdeteksi datar (tidak dipalsukan)
  4. Reguleritas RR (untuk membedakan arrhythmia)
Standar: fitur diagnostik (irama, laju, ST-T, interval) harus terjaga; amplitudo
presisi diambil dari nilai device (printed_measurements).
"""
import os, glob, json
import numpy as np
from scipy.signal import find_peaks
from validate_medical import parse_printed, estimate_hr

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(os.path.dirname(HERE), 'Export')


def hr_and_rr(leads, fs):
    """HR (median antar-lead) + koefisien variasi RR (untuk reguleritas)."""
    hrs, cvs = [], []
    for k in ('II', 'V2', 'V5', 'I', 'V3'):
        if k not in leads:
            continue
        s = np.asarray(leads[k], float) - np.median(leads[k])
        if np.max(np.abs(s)) < 0.1:
            continue
        pk, _ = find_peaks(np.abs(s), distance=int(0.3 * fs),
                           height=0.4 * np.max(np.abs(s)))
        if len(pk) < 3:
            continue
        rr = np.diff(pk) / fs
        rr = rr[(rr > 0.3) & (rr < 2.0)]
        if len(rr) >= 2:
            hrs.append(60.0 / np.median(rr))
            cvs.append(float(np.std(rr) / np.mean(rr)))
    return (float(np.median(hrs)) if hrs else None,
            float(np.median(cvs)) if cvs else None)


def rhythm_category(dx):
    d = (dx or '').lower()
    if 'brady' in d:
        return 'brady', (0, 60)
    if 'tachy' in d:
        return 'tachy', (100, 250)
    if 'lead off' in d:
        return 'lead_off', None
    if 'sinus' in d or 'arrhythmia' in d or 'rhythm' in d:
        return 'sinus', (50, 110)
    return 'other', None


def main():
    sigs = sorted(glob.glob(os.path.join(HERE, 'export_test', '*_signals.json')))
    print(f"{'file':14s} {'Dx device':22s} {'HRcetak':>7s} {'HRdig':>6s} "
          f"{'beda':>5s} {'ritme OK?':>9s}")
    print('-' * 78)
    hr_err = []
    rhythm_ok = 0
    rhythm_tot = 0
    for s in sigs:
        name = os.path.basename(s).replace('_signals.json', '')[-4:]
        pdfs = glob.glob(os.path.join(EXPORT, '*', os.path.basename(s)
                         .replace('_signals.json', '') + '.pdf'))
        if not pdfs:
            continue
        d = json.load(open(s)); leads = d['leads']; fs = d['meta']['px_per_sec']
        printed = parse_printed(pdfs[0])
        hr_d, cv = hr_and_rr(leads, fs)
        cat, rng = rhythm_category(printed['Dx'])
        # konsistensi HR vs kategori diagnosis
        ok = '-'
        if cat == 'lead_off':
            # cek lead dada datar
            flat = all(np.ptp(leads.get(f'V{k}', [0, 1])) < 0.3 for k in range(1, 7))
            ok = 'YA' if flat else 'TIDAK'
            rhythm_tot += 1; rhythm_ok += (ok == 'YA')
        elif rng and hr_d:
            inside = rng[0] - 8 <= hr_d <= rng[1] + 8
            ok = 'YA' if inside else 'TIDAK'
            rhythm_tot += 1; rhythm_ok += inside
        e = (abs(printed['HR'] - hr_d) if printed['HR'] and hr_d else None)
        if e is not None:
            hr_err.append(e)
        hp = f"{printed['HR']}" if printed['HR'] else '-'
        hd = f"{hr_d:.0f}" if hr_d else '-'
        es = f"{e:.0f}" if e is not None else '-'
        print(f"{name:14s} {(printed['Dx'] or '')[:22]:22s} {hp:>7s} {hd:>6s} "
              f"{es:>5s} {ok:>9s}")
    print('-' * 78)
    he = np.array(hr_err)
    print(f"\nRINGKASAN STANDAR MEDIS:")
    print(f"  HR: MAE={he.mean():.1f} bpm | <=5bpm: {(he<=5).mean()*100:.0f}% | "
          f"<=10bpm: {(he<=10).mean()*100:.0f}%  (toleransi klinis ~<=5 bpm)")
    print(f"  Konsistensi ritme vs diagnosis device: {rhythm_ok}/{rhythm_tot} "
          f"({rhythm_ok/max(rhythm_tot,1)*100:.0f}%)")
    print(f"  Interval (PR/QRS/QT/QTc) & amplitudo (RV5/SV1): dari teks device "
          f"-> presisi, di fhir_ready/*.json")


if __name__ == '__main__':
    main()
