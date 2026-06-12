"""
model_diagrams.py — Diagram arsitektur 2 model:
  fig_unet.png   : U-Net (segmentasi trace, fallback digitalisasi raster)
  fig_ecgnet.png : ECGNet 1D-ResNet (klasifikasi 12-lead -> 5 superclass)
Output -> lap_img/
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = "C:/BRINDATA/EKG-BRIN/lap_img"


def box(ax, x, y, w, h, text, fc, ec="#334155", fs=9):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02",
                                fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs)


def arrow(ax, x1, y1, x2, y2, color="#334155", style="-|>"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=12, color=color, lw=1.3))


def unet():
    fig, ax = plt.subplots(figsize=(12, 6.4)); ax.set_xlim(0, 12); ax.set_ylim(0, 7)
    ax.axis("off")
    enc = [("gambar\n3×H×W", "#e0f2fe"), ("32", "#dbeafe"), ("64", "#bfdbfe"),
           ("128", "#93c5fd"), ("256", "#60a5fa")]
    dec = [("256", "#fca5a5"), ("128", "#fda4af"), ("64", "#fecaca"),
           ("32", "#fee2e2"), ("mask + offset\n2×H×W", "#fef3c7")]
    # encoder turun (kiri)
    ys = [5.6, 4.5, 3.4, 2.3, 1.2]
    for i, (t, c) in enumerate(enc):
        box(ax, 0.6, ys[i], 1.8, 0.8, t, c)
        if i: arrow(ax, 1.5, ys[i - 1], 1.5, ys[i] + 0.8)
    ax.text(1.5, 6.6, "ENCODER (turun, MaxPool)", ha="center", fontsize=9,
            color="#1e3a8a", fontweight="bold")
    # bottleneck
    box(ax, 4.8, 0.7, 2.4, 0.9, "bottleneck 512\n(DoubleConv)", "#1e3a8a", fs=9)
    ax.text(6.0, 0.4, "fitur paling abstrak", ha="center", fontsize=8, color="#64748b")
    arrow(ax, 2.4, 1.6, 4.8, 1.15)
    # decoder naik (kanan)
    xs = 9.6
    for i, (t, c) in enumerate(dec):
        box(ax, xs, ys[4 - i], 1.8, 0.8, t, c)
        if i: arrow(ax, xs + 0.9, ys[4 - i + 1], xs + 0.9, ys[4 - i] + 0.8)
    ax.text(xs + 0.9, 6.6, "DECODER (naik, ConvTranspose)", ha="center", fontsize=9,
            color="#b91c1c", fontweight="bold")
    arrow(ax, 7.2, 1.15, 9.6, 1.6)
    # skip connections
    for i in range(4):
        arrow(ax, 2.4, ys[i + 1] + 0.4, 9.6, ys[i + 1] + 0.4, color="#16a34a",
              style="-|>")
    ax.text(6.0, 5.2, "skip-connection (jaga detail tepi trace)", ha="center",
            fontsize=9, color="#16a34a")
    ax.set_title("U-Net — segmentasi trace EKG dari GAMBAR (fallback raster/foto)\n"
                 "out_ch=2: peta trace + offset baseline (memisah lead bertumpuk)",
                 fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_unet.png"), dpi=120)
    plt.close(fig)


def ecgnet():
    fig, ax = plt.subplots(figsize=(17, 4.2)); ax.set_xlim(0, 18.6); ax.set_ylim(0, 4)
    ax.axis("off")
    blocks = [
        ("input\n12×1000\n(12 lead)", "#e0f2fe", 1.7),
        ("Stem\nConv1d k15 s2\n→32", "#dbeafe", 1.7),
        ("ResBlock\n32→32", "#bfdbfe", 1.5),
        ("ResBlock\n32→64 ↓", "#93c5fd", 1.5),
        ("ResBlock\n64→64", "#bfdbfe", 1.5),
        ("ResBlock\n64→128 ↓", "#60a5fa", 1.5),
        ("ResBlock\n128→128", "#bfdbfe", 1.5),
        ("ResBlock\n128→256 ↓", "#3b82f6", 1.5),
        ("Global\nAvgPool\n+FC", "#fde68a", 1.5),
        ("5 prob\nNORM/MI/\nSTTC/CD/HYP", "#bbf7d0", 1.9),
    ]
    x = 0.3
    for i, (t, c, w) in enumerate(blocks):
        box(ax, x, 1.4, w, 1.2, t, c, fs=8.2)
        if i:
            arrow(ax, x - 0.25, 2.0, x, 2.0)
        x += w + 0.25
    ax.text(9.3, 3.4, "1D-ResNet: konvolusi 1-dimensi sepanjang WAKTU "
            "(deteksi pola P-QRS-T)", ha="center", fontsize=10, color="#1e3a8a")
    ax.text(9.3, 0.6, "tiap ResBlock: Conv1d k7 → BN → ReLU → Dropout, + jalur pintas "
            "(residual). ↓ = panjang waktu dikecilkan ×½", ha="center", fontsize=8.8,
            color="#64748b")
    ax.set_title("ECGNet — klasifikasi 12-lead → 5 superclass (multi-label, dilatih PTB-XL)",
                 fontsize=12)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_ecgnet.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    unet(); ecgnet()
    print("-> fig_unet.png, fig_ecgnet.png")
