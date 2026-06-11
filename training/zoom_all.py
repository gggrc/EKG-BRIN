"""
training/zoom_all.py — Overlay per-lead DIPERBESAR: output (merah) di atas input
(hitam), tiap lead satu baris tinggi, supaya tiap lengkungan/gelombang jelas
terlihat sama/tidaknya. Untuk semua file Export.

Output: export_test/zoom/<name>_zoom.png
"""
import os, glob, json
import numpy as np, cv2
from digitize_real import render_pdf
from lead_quality import lead_quality_flags

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(os.path.dirname(HERE), 'Export')
OUT = os.path.join(HERE, 'export_test', 'zoom')


def main():
    os.makedirs(OUT, exist_ok=True)
    for s in sorted(glob.glob(os.path.join(HERE, 'export_test', '*_signals.json'))):
        name = os.path.basename(s).replace('_signals.json', '')
        pdfs = glob.glob(os.path.join(EXPORT, '*', name + '.pdf'))
        if not pdfs:
            continue
        d = json.load(open(s)); m = d['meta']
        pmv = m['px_per_mV']; bases = m['lane_baselines']; n = len(bases)
        y0, y1, x0, x1 = m['ecg_region']; x_lo = x0 + int(6.5 * m['px_per_mm'])
        bgr = render_pdf(pdfs[0], m['dpi'])
        low, _ = lead_quality_flags(d['leads'], m['px_per_sec'])
        names = list(d['leads'].keys()); panels = []
        for i, nm in enumerate(names):
            b = bases[i]
            d_up = (b - bases[i - 1]) if i > 0 else 150
            d_dn = (bases[i + 1] - b) if i < n - 1 else 150
            ytop = max(0, b - int(0.62 * d_up)); ybot = min(bgr.shape[0], b + int(0.62 * d_dn))
            crop = bgr[ytop:ybot, x_lo:x1].copy()
            sig = np.array(d['leads'][nm]); ys = np.clip((b - sig * pmv) - ytop, 0, crop.shape[0] - 1)
            col = (0, 140, 0) if nm in low else (0, 0, 255)
            cv2.polylines(crop, [np.stack([np.arange(len(sig)), ys], 1).astype(np.int32)],
                          False, col, 2, cv2.LINE_AA)
            crop = cv2.resize(crop, (crop.shape[1], max(crop.shape[0], 100) * 2))
            tag = nm + (' (low-conf)' if nm in low else '')
            cv2.putText(crop, tag, (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                        (0, 120, 0) if nm in low else (180, 0, 0), 2)
            panels.append(crop)
        w = min(p.shape[1] for p in panels); panels = [cv2.resize(p, (w, p.shape[0])) for p in panels]
        sep = np.full((3, w, 3), (80, 80, 80), np.uint8); st = []
        for p in panels:
            st += [p, sep]
        cv2.imwrite(os.path.join(OUT, name + '_zoom.png'), np.vstack(st))
        print(f"  {name}")
    print(f"\nZoom per-lead -> {OUT}\n(merah=output di atas hitam=input; hijau=low-conf)")


if __name__ == '__main__':
    main()
