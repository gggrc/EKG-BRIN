"""
render_compare6.py — Side-by-side PDF ASLI vs HASIL DIGITAL untuk 6-lead Kardia.

Kiri  : render halaman-1 PDF asli (grid + label lead, ~7.4s pertama).
Kanan : sinyal digital hasil ekstraksi vektor, jendela waktu SAMA (biar
        bisa dibandingkan bentuk demi bentuk).

Pakai:
  python render_compare6.py 6-lead --out hasil
  python render_compare6.py 6-lead/DH_6L-0425.pdf
"""
import os
import sys
import glob

import numpy as np
import fitz
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "input", "parsers"))
from vector_pdf import extract_vector_pdf, _long_paths, PSEC_PT, LEADS_6


def page1_window(pdf_path):
    """Halaman trace pertama + durasi (detik) segmen itu."""
    doc = fitz.open(pdf_path)
    for p in range(doc.page_count):
        lp = _long_paths(doc[p])
        if len(lp) == 6:
            allx = [x for P in lp for x, _ in P]
            dur = (max(allx) - min(allx)) / PSEC_PT
            pix = doc[p].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8),
                               cv2.IMREAD_COLOR)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            doc.close()
            return img, dur, p
    doc.close()
    return None, None, None


def compare_one(pdf_path, out_dir):
    img, dur, pno = page1_window(pdf_path)
    if img is None:
        print("! bukan 6-lead vektor:", pdf_path); return None
    vec = extract_vector_pdf(pdf_path)
    L = {k: np.asarray(v, float) for k, v in vec["leads"].items()}
    fs = vec["fs"]
    rid = os.path.splitext(os.path.basename(pdf_path))[0]

    fig = plt.figure(figsize=(17, 10))
    gs = fig.add_gridspec(6, 2, width_ratios=[1, 1.15], hspace=0.35, wspace=0.12)

    # kiri: PDF asli halaman-1 (membentang 6 baris)
    axL = fig.add_subplot(gs[:, 0])
    axL.imshow(img); axL.axis("off")
    axL.set_title(f"PDF ASLI (hal.{pno+1}, ~{dur:.1f}s pertama)", fontsize=12)

    # kanan: 6 lead hasil digital, jendela [0, dur]
    nwin = int(dur * fs)
    for i, nm in enumerate(LEADS_6):
        ax = fig.add_subplot(gs[i, 1])
        y = L[nm][:nwin]; t = np.arange(len(y)) / fs
        ax.plot(t, y, lw=0.7, color="k")
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_ylabel(nm, rotation=0, ha="right", va="center", fontsize=10)
        ax.grid(True, alpha=0.25); ax.margins(x=0)
        if i == 0:
            ax.set_title("HASIL DIGITAL (vektor eksak, highpass 0.5Hz)", fontsize=12)
        if i < 5:
            ax.set_xticklabels([])
    ax.set_xlabel("detik")

    fig.suptitle(f"{rid}  —  ASLI vs DIGITAL", fontsize=14)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, rid + "_compare.png")
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
    print("->", out)
    return out


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "6-lead"
    out_dir = "hasil"
    if "--out" in sys.argv:
        out_dir = sys.argv[sys.argv.index("--out") + 1]
    if os.path.isdir(target):
        files = sorted(glob.glob(os.path.join(target, "*.pdf")))
    else:
        files = [target]
    for f in files:
        compare_one(f, out_dir)


if __name__ == "__main__":
    main()
