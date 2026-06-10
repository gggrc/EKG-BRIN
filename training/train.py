"""
training/train.py — Latih U-Net segmentasi trace EKG (PyTorch, GPU RTX 3060).

Loss   : BCE + Dice (atasi ketidakseimbangan kelas trace vs latar)
Metrik : Dice / IoU di set validasi
Output : training/checkpoints/unet_best.pt  (+ kurva loss)

Jalankan:
    python training/train.py --epochs 30 --batch 16 --crop 256
Smoke test cepat:
    python training/train.py --epochs 2 --batch 4 --crop 128
"""

import os
import time
import argparse

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from unet import UNet
from dataset import ECGSegDataset, split_ids

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "dataset")
CKPT_DIR = os.path.join(HERE, "checkpoints")


def dice_loss(logits, target, eps=1.0):
    p = torch.sigmoid(logits)
    p = p.reshape(p.size(0), -1)
    t = target.reshape(target.size(0), -1)
    inter = (p * t).sum(1)
    union = p.sum(1) + t.sum(1)
    return 1.0 - ((2 * inter + eps) / (union + eps)).mean()


@torch.no_grad()
def dice_metric(logits, target, thr=0.5, eps=1.0):
    p = (torch.sigmoid(logits) > thr).float()
    p = p.reshape(p.size(0), -1)
    t = target.reshape(target.size(0), -1)
    inter = (p * t).sum(1)
    union = p.sum(1) + t.sum(1)
    return ((2 * inter + eps) / (union + eps)).mean().item()


def run(args):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device: {dev}", torch.cuda.get_device_name(0) if dev == "cuda" else "")

    tr_ids, va_ids = split_ids(ROOT, val_frac=0.15, seed=0)
    tr = ECGSegDataset(ROOT, ids=tr_ids, crop=args.crop, train=True)
    va = ECGSegDataset(ROOT, ids=va_ids, crop=args.crop, train=True,
                       prefer_trace_p=1.0)
    nw = args.workers
    tl = DataLoader(tr, batch_size=args.batch, shuffle=True, num_workers=nw,
                    drop_last=True, pin_memory=(dev == "cuda"))
    vl = DataLoader(va, batch_size=args.batch, shuffle=False, num_workers=nw,
                    pin_memory=(dev == "cuda"))
    print(f"train {len(tr)} | val {len(va)} | steps/epoch {len(tl)}")

    # out_ch=2: kanal-0 trace (segmentasi), kanal-1 offset-baseline (regresi)
    net = UNet(in_ch=3, out_ch=2, base=args.base).to(dev)
    opt = torch.optim.Adam(net.parameters(), lr=args.lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    bce = nn.BCEWithLogitsLoss()
    scaler = torch.cuda.amp.GradScaler(enabled=(dev == "cuda"))

    os.makedirs(CKPT_DIR, exist_ok=True)
    best = -1e9
    since_improve = 0
    patience = args.patience
    hist = []
    for ep in range(1, args.epochs + 1):
        net.train()
        t0 = time.time()
        running = 0.0
        for x, m, o in tl:
            x = x.to(dev, non_blocking=True)
            m = m.to(dev, non_blocking=True)
            o = o.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(dev == "cuda")):
                out = net(x)
                seg = out[:, 0:1]
                off = out[:, 1:2]
                loss_seg = bce(seg, m) + dice_loss(seg, m)
                # regresi offset HANYA pada piksel trace
                diff = (off - o) * m
                loss_off = (diff * diff).sum() / (m.sum() + 1.0)
                loss = loss_seg + 0.5 * loss_off
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            running += loss.item()
        sched.step()

        net.eval()
        dices = []; offmae = []
        with torch.no_grad():
            for x, m, o in vl:
                x, m, o = x.to(dev), m.to(dev), o.to(dev)
                with torch.cuda.amp.autocast(enabled=(dev == "cuda")):
                    out = net(x); seg = out[:, 0:1]; off = out[:, 1:2]
                dices.append(dice_metric(seg, m))
                e = (torch.abs(off - o) * m).sum() / (m.sum() + 1.0)
                offmae.append(e.item())
        vd = float(np.mean(dices)) if dices else 0.0
        voff = float(np.mean(offmae)) if offmae else 0.0   # MAE offset (mV)
        # skor gabungan: Dice tinggi + offset akurat (offset penting utk crossing)
        score = vd - 0.5 * voff
        tloss = running / max(1, len(tl))
        hist.append((ep, tloss, vd, voff))
        print(f"ep {ep:3d}/{args.epochs} | loss {tloss:.4f} | "
              f"val Dice {vd:.4f} | off MAE {voff:.4f} | score {score:.4f} | "
              f"{time.time()-t0:.1f}s")
        vd = score      # pakai score utk simpan-terbaik & early-stop

        if vd > best + 1e-4:
            best = vd
            since_improve = 0
            torch.save({"model": net.state_dict(), "base": args.base,
                        "in_ch": 3, "out_ch": 2, "epoch": ep, "val_dice": vd},
                       os.path.join(CKPT_DIR, "unet_best.pt"))
        else:
            since_improve += 1
            if since_improve >= patience:
                print(f"early-stop di epoch {ep} (tak membaik {patience} epoch; "
                      f"best score {best:.4f})")
                break

    np.save(os.path.join(CKPT_DIR, "history.npy"), np.array(hist))
    np.save(os.path.join(CKPT_DIR, "history.npy"), np.array(hist))
    print(f"selesai. best val Dice {best:.4f} -> {CKPT_DIR}/unet_best.pt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--patience", type=int, default=8)   # early-stop
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--crop", type=int, default=256)
    ap.add_argument("--base", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--workers", type=int, default=0)
    run(ap.parse_args())
