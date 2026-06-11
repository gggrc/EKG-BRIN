"""
illustrasi.py — Buat gambar ilustrasi untuk laporan:
  1) fig_mekanisme.png : zoom QRS menampilkan TITIK vektor (x,y) asli yg
     tersimpan di PDF + anotasi kalibrasi -> kenapa eksak.
  2) fig_arti_metrik.png : referensi vs digital ditumpuk + residual diarsir,
     beserta nilai SNR/PRD/r/RMSE -> apa yang sebenarnya diukur metrik.
  3) fig_bentuk_metrik.png : 3 panel (sangat baik -> buruk) memperlihatkan
     bagaimana wujud sinyal saat r/SNR/PRD berubah.
Output -> folder lap_img/.
"""
import os
import numpy as np
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = "C:/BRINDATA/EKG-BRIN"
OUT = os.path.join(ROOT, "lap_img")
os.makedirs(OUT, exist_ok=True)
PT = 72.0 / 25.4
PMV = 10.0 * PT
PSEC = 25.0 * PT


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


def get_lead(pdf, idx=1):
    """Ambil 1 lead (default lead II, idx urut-y) -> (t_sec, mv, x_pt, y_pt)."""
    doc = fitz.open(pdf)
    page = next(doc[p] for p in range(doc.page_count)
                if len(long_paths(doc[p])) in (6, 12))
    P = sorted(long_paths(page),
               key=lambda Q: np.median([y for _, y in Q]))[idx]
    xs = np.array([x for x, _ in P]); ys = np.array([y for _, y in P])
    o = np.argsort(xs); xs, ys = xs[o], ys[o]
    ux, i = np.unique(xs, return_index=True); uy = ys[i]
    base = np.median(uy)
    t = (ux - ux.min()) / PSEC
    mv = (base - uy) / PMV
    doc.close()
    return t, mv, ux, uy, base


# ---------- 1) MEKANISME: titik vektor pada QRS ----------
def fig_mekanisme():
    t, mv, ux, uy, base = get_lead(os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf"), 1)
    # cari satu QRS (puncak tertinggi) dan zoom ±0.18s
    i = int(np.argmax(mv))
    fs_pts = 1.0 / np.median(np.diff(t))
    w = t[i] - 0.12, t[i] + 0.18
    m = (t >= w[0]) & (t <= w[1])

    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.plot(t[m], mv[m], '-', color="#94a3b8", lw=1, zorder=1)
    ax.plot(t[m], mv[m], 'o', color="#1e3a8a", ms=4.5, zorder=3,
            label="titik (x,y) tersimpan di PDF")
    # anotasi beberapa titik
    idxs = np.where(m)[0]
    for k in idxs[::max(1, len(idxs)//6)]:
        ax.annotate(f"({ux[k]:.1f}, {uy[k]:.1f})pt",
                    (t[k], mv[k]), textcoords="offset points",
                    xytext=(6, 8), fontsize=7.5, color="#475569")
    ax.axhline(0, color="r", lw=0.5, alpha=0.5)
    # panah kalibrasi 1 mV
    x0 = w[0] + 0.01
    ax.annotate("", xy=(x0, 1.0), xytext=(x0, 0.0),
                arrowprops=dict(arrowstyle="<->", color="#16a34a", lw=1.5))
    ax.text(x0 + 0.004, 0.5, "1 mV = 28.35 pt\n(10 mm)", color="#16a34a", fontsize=9)
    ax.set_title("Mekanisme akurat: tiap titik trace = koordinat angka PERSIS di PDF "
                 "(bukan piksel tebakan)", fontsize=11)
    ax.set_xlabel("detik"); ax.set_ylabel("mV"); ax.grid(True, alpha=0.25)
    ax.legend(loc="upper right", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_mekanisme.png"), dpi=120)
    plt.close(fig)


# ---------- 2) ARTI METRIK: ref vs digital + residual ----------
def _metrics(r, s):
    rm = r - r.mean(); err = r - s
    ss = np.sum(rm**2) + 1e-12; sse = np.sum(err**2)
    return (10*np.log10(ss/(sse+1e-12)), 100*np.sqrt(sse/ss),
            float(np.corrcoef(r, s)[0, 1]), float(np.sqrt(np.mean(err**2))),
            float(np.max(np.abs(err))))


def fig_arti_metrik():
    t, mv, ux, uy, base = get_lead(os.path.join(ROOT, "12-lead",
                                   "20260604-153829", "20251118-143153-0004.pdf"), 7)  # V2
    i = int(np.argmax(np.abs(mv)))
    w = t[i] - 0.25, t[i] + 0.35
    m = (t >= w[0]) & (t <= w[1])
    tt, ref = t[m], mv[m]
    # digital 250Hz: resample lalu kembalikan ke grid tt
    n = max(2, int((tt[-1]-tt[0])*250))
    tg = np.linspace(tt[0], tt[-1], n)
    sg = np.interp(tg, tt, ref)
    s = np.interp(tt, tg, sg)
    snr, prd, r, rmse, mx = _metrics(ref, s)

    fig, ax = plt.subplots(figsize=(11, 4.4))
    ax.plot(tt, ref, color="#0f172a", lw=1.6, label="referensi (trace asli, padat)")
    ax.plot(tg, sg, '--', color="#dc2626", lw=1.3, label="digital 250 Hz (output)")
    ax.fill_between(tt, ref, s, color="#fca5a5", alpha=0.6, label="selisih (residual)")
    ax.axhline(0, color="r", lw=0.4, alpha=0.4)
    ax.set_title("Apa yang diukur metrik: jarak antara trace ASLI dan hasil DIGITAL",
                 fontsize=11)
    ax.set_xlabel("detik"); ax.set_ylabel("mV"); ax.grid(True, alpha=0.25)
    ax.legend(loc="lower right", fontsize=9)
    txt = (f"SNR = {snr:.1f} dB  (sinyal jauh > galat)\n"
           f"PRD = {prd:.2f}%   (galat relatif kecil)\n"
           f"r   = {r:.4f}   (bentuk hampir identik)\n"
           f"RMSE= {rmse*1000:.1f} µV ; maxAE = {mx*1000:.0f} µV")
    ax.text(0.02, 0.97, txt, transform=ax.transAxes, va="top", fontsize=9.5,
            family="monospace", bbox=dict(boxstyle="round", fc="#eff6ff", ec="#bfdbfe"))
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_arti_metrik.png"), dpi=120)
    plt.close(fig)


# ---------- 3) BENTUK METRIK: sangat baik -> buruk ----------
def fig_bentuk_metrik():
    t, mv, ux, uy, base = get_lead(os.path.join(ROOT, "6-lead", "DH_6L-0425.pdf"), 1)
    i = int(np.argmax(mv)); w = t[i]-0.3, t[i]+0.5
    m = (t >= w[0]) & (t <= w[1]); tt, ref = t[m], mv[m]
    rng = np.random.RandomState(0)
    cases = [("Sangat baik (≈ kasus kita)", ref + rng.normal(0, 0.01, ref.shape)),
             ("Sedang", ref + rng.normal(0, 0.08, ref.shape)),
             ("Buruk", ref*0.8 + rng.normal(0, 0.22, ref.shape))]
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8), sharey=True)
    for ax, (title, s) in zip(axes, cases):
        snr, prd, r, rmse, mx = _metrics(ref, s)
        ax.plot(tt, ref, color="#0f172a", lw=1.4)
        ax.plot(tt, s, color="#dc2626", lw=1.0, alpha=0.85)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("detik"); ax.grid(True, alpha=0.25)
        ax.text(0.03, 0.96, f"SNR {snr:.0f}dB\nPRD {prd:.1f}%\nr {r:.3f}",
                transform=ax.transAxes, va="top", fontsize=9, family="monospace",
                bbox=dict(boxstyle="round", fc="#f8fafc", ec="#e2e8f0"))
    axes[0].set_ylabel("mV")
    fig.suptitle("Bentuk metrik: makin mirip (hitam=asli, merah=hasil) → SNR tinggi, "
                 "PRD kecil, r→1", fontsize=11)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(os.path.join(OUT, "fig_bentuk_metrik.png"), dpi=120)
    plt.close(fig)


if __name__ == "__main__":
    fig_mekanisme(); fig_arti_metrik(); fig_bentuk_metrik()
    print("ilustrasi ->", OUT)
