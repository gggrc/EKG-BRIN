"""
render_any.py — Gambar SIDE-BY-SIDE: INPUT asli | OUTPUT digital (hasil run_any).

Untuk tiap file EKG (format apa saja), buat 1 PNG:
  KIRI  = input asli (PDF/foto dirender; file digital -> info teks)
  KANAN = sinyal digital hasil parser (plot per-lead)

Pakai:
    python render_any.py --input "input/sample_inputs/vendor_medicore_6L.pdf"
    python render_any.py --folder input/sample_inputs --out hasil_universal/gambar

Output: <out>/<nama>_sidebyside.png
"""
import os
import sys
import glob
import argparse

import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, 'input')
for p in (INPUT_DIR, os.path.join(INPUT_DIR, 'parsers')):
    if p not in sys.path:
        sys.path.insert(0, p)

SUPPORTED = {'.pdf', '.png', '.jpg', '.jpeg', '.csv', '.txt',
             '.json', '.xml', '.hea', '.dat'}


def render_input_panel(path, target_h):
    """Kembalikan gambar BGR panel input (tinggi = target_h)."""
    ext = os.path.splitext(path)[1].lower()
    img = None
    if ext == '.pdf':
        import fitz
        page = fitz.open(path)[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        buf = np.frombuffer(pix.tobytes('png'), np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    elif ext in ('.png', '.jpg', '.jpeg'):
        img = cv2.imread(path)

    if img is None:
        # file digital -> panel info teks (tak ada gambar asli)
        panel = np.full((target_h, 700, 3), 255, np.uint8)
        msg = ['INPUT: file digital', f'({ext}) - sinyal EKSAK',
               '(tidak ada gambar', 'asli untuk dibandingkan)']
        for i, m in enumerate(msg):
            cv2.putText(panel, m, (30, 80 + i * 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (120, 120, 120), 2)
        return panel
    # skala ke tinggi target
    sc = target_h / img.shape[0]
    return cv2.resize(img, (int(img.shape[1] * sc), target_h))


def render_signal_panel(leads, fs, title):
    """Plot semua lead (1 baris per lead) -> gambar BGR."""
    names = list(leads.keys())
    n = len(names)
    fig, axes = plt.subplots(n, 1, figsize=(8, max(0.7 * n, 4)), squeeze=False)
    for i, nm in enumerate(names):
        s = np.asarray(leads[nm], float)
        t = np.arange(len(s)) / fs
        ax = axes[i][0]
        ax.plot(t, s, color='#cc0000', lw=0.7)
        ax.set_ylabel(nm, fontsize=8, rotation=0, labelpad=14, va='center')
        ax.set_xticks([]); ax.tick_params(labelsize=6)
        ax.margins(x=0)
        ax.grid(True, color='#f0c0c0', lw=0.4)
    axes[0][0].set_title(title, fontsize=11)
    fig.tight_layout(h_pad=0.2)
    fig.canvas.draw()
    buf = np.frombuffer(fig.canvas.buffer_rgba(), np.uint8)
    buf = buf.reshape(fig.canvas.get_width_height()[::-1] + (4,))
    plt.close(fig)
    return cv2.cvtColor(buf, cv2.COLOR_RGBA2BGR)


def process(path, out_dir):
    from ecg_input_router import load_ecg
    u = load_ecg(path)
    right = render_signal_panel(u.leads, int(u.sampling_rate),
                                f'OUTPUT digital — {len(u.leads)} lead, {u.sampling_rate}Hz')
    left = render_input_panel(path, right.shape[0])
    # label kiri
    cv2.rectangle(left, (0, 0), (left.shape[1] - 1, 34), (240, 240, 240), -1)
    cv2.putText(left, 'INPUT asli', (10, 25), cv2.FONT_HERSHEY_SIMPLEX,
                0.8, (0, 0, 200), 2)
    sep = np.full((right.shape[0], 6, 3), (0, 150, 0), np.uint8)
    canvas = np.hstack([left, sep, right])
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    op = os.path.join(out_dir, name + '_sidebyside.png')
    cv2.imwrite(op, canvas)
    return op, len(u.leads)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--input')
    g.add_argument('--folder')
    ap.add_argument('--out', default=os.path.join(HERE, 'hasil_universal', 'gambar'))
    args = ap.parse_args()
    files = ([args.input] if args.input else
             sorted(f for f in glob.glob(os.path.join(args.folder, '**', '*'),
                                         recursive=True)
                    if os.path.splitext(f)[1].lower() in SUPPORTED))
    print(f"{len(files)} file -> {args.out}")
    for p in files:
        try:
            op, n = process(p, args.out)
            print(f"  OK {os.path.basename(p):28s} {n} lead -> {os.path.basename(op)}")
        except Exception as e:
            print(f"  ! {os.path.basename(p)}: {type(e).__name__}: {e}")
    print(f"\nSelesai -> {args.out}")


if __name__ == '__main__':
    main()
