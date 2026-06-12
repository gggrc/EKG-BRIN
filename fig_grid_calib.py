"""
fig_grid_calib.py — Gambar 'HOW menghitung dari grid': ukur kotak grid (1mm) &
pulsa kalibrasi (10mm=1mV) pada PDF Kardia 6-lead, lalu turunkan kalibrasi
1mV=28.346 pt. Output -> lap_img/fig_grid_calib.png
"""
import os
import numpy as np
import fitz
import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "C:/BRINDATA/EKG-BRIN"
OUT = os.path.join(ROOT, "lap_img")
PT = 72.0 / 25.4
PDF = os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf")
SCALE = 5.0


def main():
    doc = fitz.open(PDF)
    pg = doc[1]
    pix = pg.get_pixmap(matrix=fitz.Matrix(SCALE, SCALE))
    img = cv2.cvtColor(
        cv2.imdecode(np.frombuffer(pix.tobytes("png"), np.uint8), cv2.IMREAD_COLOR),
        cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    crop = img[int(h * 0.16):int(h * 0.30), 0:int(w * 0.16)]
    doc.close()
    ch, cw = crop.shape[:2]

    # px per mm & per mV dari render (1 pt = SCALE px)
    px_per_mm = PT * SCALE                  # 1mm
    px_per_mv = 10 * px_per_mm              # 10mm = 1mV
    px_per_5mm = 5 * px_per_mm

    # cari pulsa kalibrasi (⊓): tinta HITAM NETRAL saja (buang grid biru)
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    neutral = (crop.max(2).astype(int) - crop.min(2).astype(int)) < 45
    black = ((gray < 110) & neutral).astype(np.uint8)
    # tinggi stroke kontigu per kolom -> pulsa = stroke ~1mV (bukan border penuh)
    ext = np.zeros(cw); top_at = np.zeros(cw)
    for c in range(cw):
        ys = np.where(black[:, c])[0]
        if len(ys) == 0:
            continue
        runs = []; s = ys[0]; p = ys[0]
        for y in ys[1:]:
            if y - p <= 3:
                p = y
            else:
                runs.append((s, p)); s = y; p = y
        runs.append((s, p))
        lo, hi = max(runs, key=lambda r: r[1] - r[0])
        ext[c] = hi - lo; top_at[c] = lo
    ok = np.where((ext > 0.55 * px_per_mv) & (ext < 1.35 * px_per_mv))[0]
    if len(ok):
        px0 = int(ok.min()); pulse_top = int(top_at[px0])
    else:
        px0 = int(cw * 0.25); pulse_top = int(ch * 0.42)
    pulse_bot = int(pulse_top + px_per_mv)         # turun TEPAT 1 mV
    cx = px0 - int(0.6 * px_per_mm)                # garis ukur di kiri pulsa

    fig, ax = plt.subplots(figsize=(11, 7.5))
    ax.imshow(crop)
    # pulsa kalibrasi (10mm = 1mV) -- tepat di pulsa
    ax.annotate("", xy=(cx, pulse_top), xytext=(cx, pulse_bot),
                arrowprops=dict(arrowstyle="<->", color="#b91c1c", lw=2.6))
    ax.text(cx - 12, (pulse_top + pulse_bot) / 2,
            "pulsa kalibrasi\n10 mm = 1 mV", color="#b91c1c", fontsize=11.5,
            ha="right", va="center", fontweight="bold")
    # 1 kotak besar (5mm) di area grid bersih kanan-atas
    gx = int(cw * 0.60); gy = int(ch * 0.16)
    ax.annotate("", xy=(gx + px_per_5mm, gy), xytext=(gx, gy),
                arrowprops=dict(arrowstyle="<->", color="#2563eb", lw=2.4))
    ax.text(gx + px_per_5mm / 2, gy - 16, "1 kotak besar = 5 mm",
            color="#2563eb", fontsize=11.5, ha="center", fontweight="bold")
    # 1 kotak kecil (1mm) -- bracket dgn tick supaya jelas
    sx = gx; sy = int(ch * 0.30)
    for xx in (sx, sx + px_per_mm):
        ax.plot([xx, xx], [sy - 8, sy + 8], color="#16a34a", lw=2)
    ax.annotate("", xy=(sx + px_per_mm, sy), xytext=(sx, sy),
                arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=2.4))
    ax.text(sx + px_per_mm + 8, sy, "1 kotak kecil = 1 mm",
            color="#16a34a", fontsize=11.5, ha="left", va="center", fontweight="bold")
    ax.axis("off")
    ax.set_title("Cara baca skala dari GRID + pulsa kalibrasi (Kardia 6-lead)",
                 fontsize=13)
    # kotak rumus
    txt = ("Standar EKG:  1 kotak kecil = 1 mm,  10 mm = 1 mV,  25 mm = 1 detik\n"
           "Satuan PDF :  1 mm = 72/25.4 = 2.835 point\n"
           f"->  1 mV = 10 mm = {10*PT:.3f} point     |     1 detik = 25 mm = {25*PT:.3f} point\n"
           "Konversi sinyal:  mV = (baseline_y - y) / 28.346")
    ax.text(0.5, -0.02, txt, transform=ax.transAxes, ha="center", va="top",
            fontsize=10.5, family="monospace",
            bbox=dict(boxstyle="round", fc="#eff6ff", ec="#bfdbfe"))
    fig.tight_layout(rect=[0, 0.12, 1, 1])
    p = os.path.join(OUT, "fig_grid_calib.png")
    fig.savefig(p, dpi=120, bbox_inches="tight"); plt.close(fig)
    print("->", p)


if __name__ == "__main__":
    main()
