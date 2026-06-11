"""
training/sidebyside_all.py — Side-by-side INPUT | OUTPUT pada skala 1:1 SEJATI.
Kedua panel berukuran piksel & kalibrasi identik (10 px/mm, lead di baris yang
SAMA, trace mulai di x yang sama), sehingga baris-per-baris sejajar dan skala
persis sama. Resolusi tinggi supaya tiap lengkungan jelas.

Output: export_test/sidebyside/<name>_1to1.png
"""
import os, glob, json
import numpy as np, cv2
from digitize_real import render_pdf
from lead_quality import lead_quality_flags

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(os.path.dirname(HERE), '12-lead')
OUT = os.path.join(HERE, 'export_test', 'sidebyside')


def render_output_canvas(d, shape):
    """Kanvas output: ukuran & posisi IDENTIK input (grid + trace di baseline)."""
    m = d['meta']; pmv = m['px_per_mV']; bases = m['lane_baselines']
    x0 = m['ecg_region'][2]; x_lo = x0 + int(6.5 * m['px_per_mm'])
    H, W = shape[:2]
    low, _ = lead_quality_flags(d['leads'], m['px_per_sec'])
    out = np.full((H, W, 3), 255, np.uint8)
    for x in range(0, W, 10):
        cv2.line(out, (x, 0), (x, H), (218, 196, 196), 1)
    for yy in range(0, H, 10):
        cv2.line(out, (0, yy), (W, yy), (218, 196, 196), 1)
    for x in range(0, W, 50):
        cv2.line(out, (x, 0), (x, H), (160, 128, 128), 1)
    for yy in range(0, H, 50):
        cv2.line(out, (0, yy), (W, yy), (160, 128, 128), 1)
    for i, nm in enumerate(d['leads']):
        b = bases[i]; sig = np.array(d['leads'][nm])
        col = (0, 140, 0) if nm in low else (20, 20, 20)
        xs = x_lo + np.arange(len(sig)); ys = np.clip((b - sig * pmv).astype(int), 0, H - 1)
        cv2.polylines(out, [np.stack([xs, ys], 1).astype(np.int32)], False, col, 1, cv2.LINE_AA)
        cv2.putText(out, nm, (max(2, x0 - 38), b), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    (180, 0, 0), 1)
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    for s in sorted(glob.glob(os.path.join(HERE, 'export_test', '*_signals.json'))):
        name = os.path.basename(s).replace('_signals.json', '')
        pdfs = glob.glob(os.path.join(EXPORT, '*', name + '.pdf'))
        if not pdfs:
            continue
        d = json.load(open(s))
        bgr = render_pdf(pdfs[0], d['meta']['dpi'])
        out = render_output_canvas(d, bgr.shape)
        cv2.putText(bgr, 'INPUT (asli)', (60, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 200), 3)
        cv2.putText(out, 'OUTPUT (digital)', (60, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 150, 0), 3)
        sep = np.full((bgr.shape[0], 16, 3), (0, 180, 0), np.uint8)
        side = np.hstack([bgr, sep, out])          # 1:1, tanpa diperkecil
        cv2.imwrite(os.path.join(OUT, name + '_1to1.png'), side)
        print(f"  {name}  ({side.shape[1]}x{side.shape[0]})")
    print(f"\nSide-by-side 1:1 -> {OUT}")


if __name__ == '__main__':
    main()
