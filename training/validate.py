"""
training/validate.py — Ukur kemiripan sinyal hasil digitalisasi vs ground-truth.

Pipeline: gambar -> U-Net mask -> decode mV -> bandingkan dengan sinyal asli
PTB-XL (signals/<id>.npy) pada segmen yang sesuai (meta.gt_start/gt_len).

Metrik (per lead, lalu dirata-rata):
  - SNR (dB)   : metrik utama (PhysioNet CinC 2024). Makin tinggi makin baik.
  - Pearson r  : korelasi bentuk gelombang.
  - PRD (%)    : Percent RMS Difference. Makin kecil makin baik.

Jalankan:
    python training/validate.py --ckpt checkpoints/unet_best.pt --n 20
"""

import os
import glob
import json
import argparse

import numpy as np
import cv2
import torch

from decode import predict_mask, mask_to_signals, load_net

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "dataset")


def _align(a, b):
    """Samakan panjang (resample b ke len a) untuk perbandingan adil."""
    if len(a) != len(b):
        xp = np.linspace(0, 1, len(b))
        xq = np.linspace(0, 1, len(a))
        b = np.interp(xq, xp, b)
    return a, b


def snr_db(gt, est):
    gt, est = _align(gt, est)
    gt = gt - gt.mean()
    est = est - est.mean()
    noise = gt - est
    ps = np.sum(gt ** 2)
    pn = np.sum(noise ** 2) + 1e-12
    return 10.0 * np.log10(ps / pn + 1e-12)


def pearson_r(gt, est):
    gt, est = _align(gt, est)
    if gt.std() < 1e-9 or est.std() < 1e-9:
        return 0.0
    return float(np.corrcoef(gt, est)[0, 1])


def prd_pct(gt, est):
    gt, est = _align(gt, est)
    num = np.sqrt(np.sum((gt - est) ** 2))
    den = np.sqrt(np.sum((gt - gt.mean()) ** 2)) + 1e-12
    return 100.0 * num / den


def evaluate(ckpt, n, device, save_examples=2):
    net = load_net(ckpt, device)
    from dataset import _list_ids, _img_path
    ids = _list_ids(ROOT)[:n]

    rows = []
    for k, rid in enumerate(ids):
        img = cv2.cvtColor(cv2.imread(_img_path(ROOT, rid), cv2.IMREAD_COLOR),
                           cv2.COLOR_BGR2RGB)
        meta = json.load(open(os.path.join(ROOT, "meta", rid + ".json")))
        gtsig = np.load(os.path.join(ROOT, "signals", rid + ".npy"))  # (N,12)

        mask = predict_mask(net, img, device=device)
        est = mask_to_signals(mask, meta)

        for name, box in meta["lead_boxes"].items():
            li = box["lead_idx"]
            s, ln = box["gt_start"], box["gt_len"]
            gt = gtsig[s:s + ln, li].astype(np.float32)
            ev = est[name]
            rows.append((rid, name, snr_db(gt, ev),
                         pearson_r(gt, ev), prd_pct(gt, ev)))

        if k < save_examples:
            _save_example(rid, meta, gtsig, est)

    arr = np.array([(r[2], r[3], r[4]) for r in rows], np.float32)
    print(f"\nEvaluasi {len(ids)} gambar, {len(rows)} lead:")
    print(f"  SNR     : {arr[:,0].mean():6.2f} dB  "
          f"(median {np.median(arr[:,0]):.2f})")
    print(f"  Pearson : {arr[:,1].mean():6.3f}     "
          f"(median {np.median(arr[:,1]):.3f})")
    print(f"  PRD     : {arr[:,2].mean():6.2f} %   "
          f"(median {np.median(arr[:,2]):.2f})")

    # Interpretasi cepat
    r = arr[:, 1].mean()
    verdict = ("sangat baik" if r > 0.95 else "baik" if r > 0.85 else
               "cukup" if r > 0.7 else "perlu perbaikan/training lebih")
    print(f"  -> kualitas rekonstruksi: {verdict}")
    return arr


def _save_example(rid, meta, gtsig, est):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = list(meta["lead_boxes"].keys())[:6]
    fig, axes = plt.subplots(len(names), 1, figsize=(12, 1.6 * len(names)),
                             squeeze=False)
    for i, name in enumerate(names):
        box = meta["lead_boxes"][name]
        gt = gtsig[box["gt_start"]:box["gt_start"] + box["gt_len"],
                   box["lead_idx"]]
        ev = est[name]
        ax = axes[i][0]
        ax.plot(np.linspace(0, 1, len(gt)), gt, color="#1f77b4", lw=1.0,
                label="asli (PTB-XL)")
        ax.plot(np.linspace(0, 1, len(ev)), ev, color="#d62728", lw=0.8,
                alpha=0.8, label="hasil U-Net")
        ax.set_ylabel(name, fontsize=8)
        ax.tick_params(labelsize=6)
        if i == 0:
            ax.legend(fontsize=7, loc="upper right")
    fig.suptitle(f"Validasi {rid}: asli vs digitalisasi", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    out = os.path.join(HERE, f"validate_{rid}.png")
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print(f"  contoh -> {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", default=os.path.join(HERE, "checkpoints",
                                                   "unet_best.pt"))
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    evaluate(args.ckpt, args.n, dev)
