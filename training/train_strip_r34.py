"""
train_strip_r34.py — Strip per-lead U-Net dgn backbone ResNet34 PRE-TRAINED
ImageNet (segmentation-models-pytorch). Sesuai metode Rahimi/SOTA: encoder kuat
pre-trained -> segmentasi target-bersih lebih akurat -> lubang/over-remove
berkurang DI SUMBERNYA (bukan ditambal). Dataset & augmentasi sama (LeadStrip).

Output: checkpoints/strip_r34_best.pt (arch='r34-unet', imagenet-norm).
Jalankan: python train_strip_r34.py --epochs 20 --batch 16
"""
import os
import time
import argparse

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
import segmentation_models_pytorch as smp

from strip_dataset import LeadStripDataset, split_ids, RecordGroupedSampler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "dataset")
CKPT_DIR = os.path.join(HERE, "checkpoints")

IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)


def build_r34():
    return smp.Unet(encoder_name="resnet34", encoder_weights="imagenet",
                    in_channels=3, classes=1)


def dice_loss(logits, target, eps=1.0):
    p = torch.sigmoid(logits).reshape(logits.size(0), -1)
    t = target.reshape(target.size(0), -1)
    inter = (p * t).sum(1)
    return 1.0 - ((2 * inter + eps) / (p.sum(1) + t.sum(1) + eps)).mean()


@torch.no_grad()
def dice_metric(logits, target, thr=0.5, eps=1.0):
    p = (torch.sigmoid(logits) > thr).float().reshape(logits.size(0), -1)
    t = target.reshape(target.size(0), -1)
    inter = (p * t).sum(1)
    return ((2 * inter + eps) / (p.sum(1) + t.sum(1) + eps)).mean().item()


def run(args):
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", dev, torch.cuda.get_device_name(0) if dev == "cuda" else "")
    mean = IMAGENET_MEAN.to(dev); std = IMAGENET_STD.to(dev)
    tr_ids, va_ids = split_ids(ROOT, val_frac=0.15, seed=0)
    tr = LeadStripDataset(ROOT, ids=tr_ids, train=True)
    va = LeadStripDataset(ROOT, ids=va_ids, train=False)
    tl = DataLoader(tr, batch_size=args.batch, sampler=RecordGroupedSampler(tr.items, True),
                    num_workers=args.workers, drop_last=True, pin_memory=(dev == "cuda"))
    vl = DataLoader(va, batch_size=args.batch, sampler=RecordGroupedSampler(va.items, False),
                    num_workers=args.workers, pin_memory=(dev == "cuda"))
    print(f"train strips {len(tr)} | val strips {len(va)} | steps/epoch {len(tl)}")

    net = build_r34().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    bce = nn.BCEWithLogitsLoss()
    scaler = torch.cuda.amp.GradScaler(enabled=(dev == "cuda"))
    os.makedirs(CKPT_DIR, exist_ok=True)
    best = -1.0; since = 0
    for ep in range(1, args.epochs + 1):
        net.train(); t0 = time.time(); run_loss = 0.0
        for x, t in tl:
            x = ((x.to(dev, non_blocking=True) - mean) / std)
            t = t.to(dev, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(dev == "cuda")):
                out = net(x)
                loss = bce(out, t) + dice_loss(out, t)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            run_loss += loss.item()
        sched.step()
        net.eval(); dices = []
        with torch.no_grad():
            for x, t in vl:
                x = ((x.to(dev) - mean) / std); t = t.to(dev)
                with torch.cuda.amp.autocast(enabled=(dev == "cuda")):
                    out = net(x)
                dices.append(dice_metric(out, t))
        vd = float(np.mean(dices)) if dices else 0.0
        print(f"ep {ep:3d}/{args.epochs} | loss {run_loss/max(1,len(tl)):.4f} | "
              f"val Dice {vd:.4f} | {time.time()-t0:.1f}s")
        if vd > best + 1e-4:
            best = vd; since = 0
            torch.save({"model": net.state_dict(), "arch": "r34-unet",
                        "imagenet_norm": True, "epoch": ep, "val_dice": vd},
                       os.path.join(CKPT_DIR, "strip_r34_best.pt"))
        else:
            since += 1
            if since >= args.patience:
                print(f"early-stop ep {ep} (best Dice {best:.4f})"); break
    print(f"selesai. best val Dice {best:.4f} -> {CKPT_DIR}/strip_r34_best.pt")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=5e-4)
    ap.add_argument("--workers", type=int, default=0)
    run(ap.parse_args())
