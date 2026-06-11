"""
pipeline_visual.py — Perlihatkan APA YANG TERJADI pada sinyal di tiap langkah
PDF -> digital, sebagai:
  1) fig_pipeline_stages.png : panel bertahap (PDF asli -> ... -> sinyal final)
  2) pipeline.gif            : animasi langkah-demi-langkah (efek 'real-time')

Lead contoh: 6-lead DH, Lead II (R-wave jelas). Jendela ~3 detik.
Output -> lap_img/.
"""
import os
import numpy as np
import fitz
import cv2
from scipy.signal import butter, filtfilt
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

ROOT = "C:/BRINDATA/EKG-BRIN"
OUT = os.path.join(ROOT, "lap_img")
os.makedirs(OUT, exist_ok=True)
PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT
PDF = os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf")
LEAD_IDX = 1            # Lead II
WIN_SEC = 3.0
SCALE = 2.0            # render PDF


def long_paths(page, min_seg=500):
    res = []
    for dr in page.get_drawings():
        pts = []
        for it in dr['items']:
            if it[0] == 'l':
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
        if len(pts) > min_seg:
            res.append(pts)
    return res


def load():
    doc = fitz.open(PDF)
    pno = next(p for p in range(doc.page_count)
               if len(long_paths(doc[p])) in (6, 12))
    page = doc[pno]
    P = sorted(long_paths(page), key=lambda Q: np.median([y for _, y in Q]))[LEAD_IDX]
    xs = np.array([x for x, _ in P]); ys = np.array([y for _, y in P])
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True); uy = ys[i]
    x0 = ux.min()
    # jendela WIN_SEC
    xmax = x0 + WIN_SEC * PSEC
    m = ux <= xmax
    ux, uy = ux[m], uy[m]
    base = float(np.median(uy))
    # render crop PDF utk stage-1
    pix = page.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
    img = cv2.cvtColor(np.frombuffer(pix.tobytes("png"), np.uint8).reshape(
        pix.height, pix.width, -1)[:, :, :3], cv2.COLOR_RGB2RGB) \
        if False else cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8),
                                   cv2.IMREAD_COLOR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    yb = int(base * SCALE)
    half = int(2.2 * 10 * SCALE / 25.4 * 25.4)   # ~ band; pakai px langsung
    half = int(0.9 * (PMV * SCALE))              # ~0.9 mV band
    x_lo_px, x_hi_px = int(ux.min() * SCALE), int(xmax * SCALE)
    crop = img[max(0, yb - half):yb + half, x_lo_px:x_hi_px]
    doc.close()
    return ux, uy, base, x0, crop


def stages(ux, uy, base, x0):
    t = (ux - x0) / PSEC
    mv_raw = (base - uy) / PMV
    # resample 250 Hz
    n = int(round((ux.max() - x0) / PSEC * 250))
    tg = np.linspace(t.min(), t.max(), n)
    mv_rs = np.interp(tg, t, mv_raw)
    # highpass 0.5 Hz
    b, a = butter(2, 0.5 / (250 / 2.0), btype="high")
    mv_hp = filtfilt(b, a, mv_rs)
    mv_hp = mv_hp - np.median(mv_hp)
    return t, mv_raw, tg, mv_rs, mv_hp


def panel(ax, kind, data, title, color="#0f172a"):
    if kind == "img":
        ax.imshow(data); ax.axis("off")
    elif kind == "pdfcoord":
        ux, uy, base = data
        ax.plot(ux, uy, '-', color="#94a3b8", lw=0.8)
        ax.plot(ux, uy, '.', color="#1e3a8a", ms=2.5)
        ax.axhline(base, color="#16a34a", lw=1.0, ls="--")
        ax.invert_yaxis()
        ax.set_ylabel("y (point)\n[PDF, y ke bawah]", fontsize=8)
        ax.set_xlabel("x (point)")
        ax.text(0.99, 0.06, "baseline = median(y)", color="#16a34a",
                fontsize=8, ha="right", transform=ax.transAxes)
    else:
        t, y = data
        if kind == "rs":
            ax.plot(t, y, '-', color="#cbd5e1", lw=0.7)
            ax.plot(t, y, '.', color=color, ms=2)
        else:
            ax.plot(t, y, '-', color=color, lw=0.9)
        ax.axhline(0, color="r", lw=0.4, alpha=0.5)
        ax.set_ylabel("mV", fontsize=8)
    ax.set_title(title, fontsize=10, loc="left")
    ax.grid(True, alpha=0.2)


def make_stages_png(crop, ux, uy, base, t, mv_raw, tg, mv_rs, mv_hp):
    fig, axes = plt.subplots(6, 1, figsize=(11, 13))
    panel(axes[0], "img", crop,
          "Langkah 1 — PDF ASLI (potongan Lead II + grid). Trace = perintah garis vektor.")
    panel(axes[1], "pdfcoord", (ux, uy, base),
          "Langkah 2 — Baca koordinat (x,y) tiap titik vektor + tentukan baseline.")
    panel(axes[2], "plain", (t, mv_raw),
          "Langkah 3 — Konversi ke mV: mV=(baseline−y)/28.346, sumbu-x→detik (flip).",
          color="#1e3a8a")
    panel(axes[3], "rs", (tg, mv_rs),
          "Langkah 4 — Resample seragam 250 Hz (titik ber-jarak tetap).",
          color="#7c3aed")
    panel(axes[4], "plain", (tg, mv_hp),
          "Langkah 5 — Highpass 0.5 Hz: baseline rata di nol (drift hilang).",
          color="#0f766e")
    panel(axes[5], "plain", (tg, mv_hp),
          "Langkah 6 — SINYAL DIGITAL FINAL (siap klasifikasi AI & FHIR).",
          color="#dc2626")
    axes[-1].set_xlabel("detik")
    fig.suptitle("Apa yang terjadi: PDF → sinyal digital (Lead II, ~3 detik)",
                 fontsize=13, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.985])
    p = os.path.join(OUT, "fig_pipeline_stages.png")
    fig.savefig(p, dpi=115); plt.close(fig)
    return p


def make_steps(crop, ux, uy, base, t, mv_raw, tg, mv_rs, mv_hp):
    """Simpan 6 gambar TERPISAH (step_1..step_6.png), satu per langkah."""
    specs = [
        ("img", crop, "Langkah 1 — PDF ASLI (potongan Lead II)", None),
        ("pdfcoord", (ux, uy, base), "Langkah 2 — Baca koordinat (x,y) + baseline", None),
        ("plain", (t, mv_raw), "Langkah 3 — Konversi ke mV (flip + kalibrasi)", "#1e3a8a"),
        ("rs", (tg, mv_rs), "Langkah 4 — Resample seragam 250 Hz", "#7c3aed"),
        ("plain", (tg, mv_hp), "Langkah 5 — Highpass 0.5 Hz (baseline rata)", "#0f766e"),
        ("plain", (tg, mv_hp), "Langkah 6 — SINYAL DIGITAL FINAL", "#dc2626"),
    ]
    paths = []
    for k, (kind, data, title, color) in enumerate(specs, 1):
        fig, ax = plt.subplots(figsize=(10, 3.2))
        panel(ax, kind, data, title, color=color or "#0f172a")
        if kind in ("plain", "rs"):
            ax.set_xlabel("detik")
        fig.tight_layout()
        p = os.path.join(OUT, f"step_{k}.png")
        fig.savefig(p, dpi=115); plt.close(fig)
        paths.append(p)
    return paths


if __name__ == "__main__":
    ux, uy, base, x0, crop = load()
    t, mv_raw, tg, mv_rs, mv_hp = stages(ux, uy, base, x0)
    p = make_stages_png(crop, ux, uy, base, t, mv_raw, tg, mv_rs, mv_hp)
    steps = make_steps(crop, ux, uy, base, t, mv_raw, tg, mv_rs, mv_hp)
    print("stages ->", p)
    for s in steps:
        print("step   ->", s)
