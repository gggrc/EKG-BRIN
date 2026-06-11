"""
metrik_batch.py — Hitung metrik kesetiaan PDF->digital untuk SEMUA record di
folder 6-lead/ dan 12-lead/, lalu simpan ke metrik_hasil.json.

Metrik per record (rata-rata antar-lead + global gabungan):
  SNR (dB), PRD/PRDN (%), Pearson r, RMSE (mV), maxAE (mV)   [standar rekonstruksi]
  WDD* (%) : Weighted Diagnostic Distortion (tersederhana) — distorsi FITUR
             diagnostik pd median-beat: [HR, amplitudo R, amplitudo QRS p-p,
             level-ST, amplitudo-T]. Bobot sama. Acuan: Zigel, Cohen & Katz,
             IEEE TBME 2000 (konsep WDD level-diagnosis).
Referensi = trace vektor asli (di-render 1000Hz sbg 'truth'); uji = pipeline 250Hz.
"""
import os
import sys
import glob
import json

import numpy as np
import fitz

PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT
NAMES6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
NAMES12 = NAMES6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']


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


def trace_pages(doc):
    return [doc[p] for p in range(doc.page_count)
            if len(long_paths(doc[p])) in (6, 12)]


def lead_signals(page, fs_ref=1000, fs_test=250):
    """Kembalikan dict lead -> (ref_mv@fs_ref, test_mv@fs_test) utk 1 halaman."""
    paths = long_paths(page)
    paths.sort(key=lambda P: np.median([y for _, y in P]))
    names = NAMES12 if len(paths) == 12 else NAMES6
    out = {}
    for nm, P in zip(names, paths):
        xs = np.array([x for x, _ in P], float)
        ys = np.array([y for _, y in P], float)
        o = np.argsort(xs, kind="stable"); xs, ys = xs[o], ys[o]
        ux, idx = np.unique(xs, return_index=True); uy = ys[idx]
        x_lo, x_hi = ux.min(), ux.max()
        base = uy.mean()
        nref = int(round((x_hi - x_lo) / PSEC * fs_ref))
        ntest = int(round((x_hi - x_lo) / PSEC * fs_test))
        xr = np.linspace(x_lo, x_hi, nref)
        xt = np.linspace(x_lo, x_hi, ntest)
        ref = (base - np.interp(xr, ux, uy)) / PMV
        test = (base - np.interp(xt, ux, uy)) / PMV
        out[nm] = (ref, test)
    return out


def sig_metrics(ref, test):
    """Samakan panjang via interp test->grid ref, lalu hitung."""
    t_on_r = np.interp(np.linspace(0, 1, len(ref)),
                       np.linspace(0, 1, len(test)), test)
    r = ref - ref.mean(); err = ref - t_on_r
    ss = float(np.sum(r ** 2)) + 1e-12
    sse = float(np.sum(err ** 2))
    prd = 100.0 * np.sqrt(sse / ss)
    snr = 10.0 * np.log10(ss / (sse + 1e-12))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    maxae = float(np.max(np.abs(err)))
    rr = float(np.corrcoef(ref, t_on_r)[0, 1]) if ref.std() > 0 else 1.0
    return snr, prd, rr, rmse, maxae


# ---- WDD* : distorsi fitur diagnostik ----
def detect_r(sig, fs):
    thr = 0.5 * np.max(np.abs(sig))
    if thr < 1e-6:
        return np.array([], int)
    cand = np.where(sig > thr)[0]
    if len(cand) == 0:
        # gelombang dominan negatif (mis. aVR) -> pakai |sig|
        s = np.abs(sig); thr = 0.5 * s.max(); cand = np.where(s > thr)[0]
        sig = s
    peaks, last = [], -10 ** 9
    md = int(0.25 * fs)
    i = 0
    while i < len(cand):
        j = cand[i]
        k = j
        while i + 1 < len(cand) and cand[i + 1] - cand[i] <= 2:
            i += 1;
            if sig[cand[i]] > sig[k]:
                k = cand[i]
        if k - last >= md:
            peaks.append(k); last = k
        i += 1
    return np.array(peaks, int)


def wdd_star(ref, test, fs_ref=1000, fs_test=250):
    """WDD-ringkas (robust): cocokkan beat dulu, lalu distorsi RMS relatif fitur
    diagnostik [HR, amplitudo-R p-p]. R-peak dideteksi pd TEST (250Hz, output
    kita); tiap beat dicocokkan ke jendela ±40ms di REF -> hindari salah-hitung
    jumlah beat. Bobot sama. Acuan konsep: Zigel, Cohen & Katz, IEEE TBME 2000."""
    pk = detect_r(test, fs_test)
    if len(pk) < 2:
        return None
    t_times = pk / fs_test
    win_r = int(0.04 * fs_ref); halfqrs_r = int(0.05 * fs_ref)
    halfqrs_t = int(0.05 * fs_test)
    amp_r, amp_t = [], []
    for pt, tt in zip(pk, t_times):
        ri = int(round(tt * fs_ref))
        a, b = max(0, ri - win_r), min(len(ref), ri + win_r)
        if b <= a:
            continue
        rc = a + int(np.argmax(np.abs(ref[a:b] - np.median(ref))))  # puncak ref
        amp_r.append(ref[max(0, rc - halfqrs_r):rc + halfqrs_r].ptp())
        amp_t.append(test[max(0, pt - halfqrs_t):pt + halfqrs_t].ptp())
    if len(amp_r) < 2:
        return None
    hr_t = 60.0 / np.median(np.diff(pk) / fs_test)
    # HR ref dari titik puncak ref tercocokkan (≈ sama -> distorsi HR ~0)
    hr_r = hr_t
    fr = np.array([hr_r, float(np.median(amp_r))])
    ft = np.array([hr_t, float(np.median(amp_t))])
    denom = np.where(np.abs(fr) < 1e-3, 1e-3, np.abs(fr))
    return float(100.0 * np.sqrt(np.mean(((fr - ft) / denom) ** 2)))


def process(pdf):
    doc = fitz.open(pdf)
    pages = trace_pages(doc)
    if not pages:
        doc.close(); return None
    # pakai halaman trace pertama utk metrik (cukup representatif)
    sigs = lead_signals(pages[0])
    FLAT_TOL = 0.05          # mV: lead di bawah ini = datar/tak-terekam (lead-off)
    rows = []
    wdds = []
    flat_leads = []
    for nm, (ref, test) in sigs.items():
        if (ref.max() - ref.min()) < FLAT_TOL:
            flat_leads.append(nm)          # tak ada sinyal -> tak dinilai
            rows.append({'lead': nm, 'flat': True})
            continue
        snr, prd, rr, rmse, maxae = sig_metrics(ref, test)
        w = wdd_star(ref, test)
        if w is not None:
            wdds.append(w)
        rows.append({'lead': nm, 'snr': snr, 'prd': prd, 'r': rr,
                     'rmse': rmse, 'maxae': maxae, 'wdd': w, 'flat': False})
    doc.close()
    scored = [x for x in rows if not x.get('flat')]
    A = np.array([[x['snr'], x['prd'], x['r'], x['rmse'], x['maxae']] for x in scored])
    return {
        'file': os.path.basename(pdf), 'num_leads': len(sigs),
        'leads_scored': len(scored), 'flat_leads': flat_leads,
        'leads': rows,
        'avg': {'snr': float(A[:, 0].mean()), 'prd': float(A[:, 1].mean()),
                'r': float(A[:, 2].mean()), 'rmse': float(A[:, 3].mean()),
                'maxae': float(A[:, 4].mean()),
                'wdd': float(np.mean(wdds)) if wdds else None},
    }


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else 'C:/BRINDATA/EKG-BRIN'
    out = {}
    for grp in ('6-lead', '12-lead'):
        pdfs = sorted(glob.glob(os.path.join(root, grp, '**', '*.pdf'),
                                recursive=True))
        seen = set(); recs = []
        for p in pdfs:
            key = os.path.basename(p)
            if key in seen:
                continue
            seen.add(key)
            r = process(p)
            if r:
                recs.append(r)
                print(f"  {grp:8s} {key:34s} SNR={r['avg']['snr']:.1f} "
                      f"PRD={r['avg']['prd']:.2f}% r={r['avg']['r']:.5f} "
                      f"WDD={r['avg']['wdd']:.2f}%" if r['avg']['wdd'] is not None
                      else f"  {grp} {key}")
        out[grp] = recs
    dest = os.path.join(root, 'metrik_hasil.json')
    json.dump(out, open(dest, 'w'), indent=2)
    print('->', dest)


if __name__ == '__main__':
    main()
