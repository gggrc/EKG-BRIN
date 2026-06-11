"""
strip_dataset.py — Dataset PER-LEAD untuk segmentasi target-BERSIH (metode
Rahimi et al. 2025, arXiv:2506.10617, untuk menangani trace OVERLAPPING).

Ide: tiap sampel = STRIP satu lead (dipotong di sekitar baseline lead). TARGET
mask = HANYA trace lead itu (diturunkan dari peta offset = ground-truth pemilik
piksel). Trace tetangga yang menumpuk di strip = INTERFERENSI yang harus DIABAIKAN
model. Augmentasi **OverlaySignal**: tempel potongan trace lead lain di TEPI
atas/bawah strip (GT tetap bersih) -> model belajar memisahkan target dari tumpukan.

Reuse dataset sintetik yang ada (images/ masks/ offsets/ meta/).
"""
import os
import glob
import json
import random
from collections import OrderedDict

import numpy as np
import cv2
import torch
from torch.utils.data import Dataset, Sampler

STRIP_H = 320          # tinggi strip (px=±1.6mV) -> QRS R/S tinggi tak terpotong
CROP_W = 256           # lebar window training
OWN_TOL = 8            # px: |y+offset - baseline| < tol => piksel milik lead ini


class RecordGroupedSampler(Sampler):
    """Kelompokkan 12 lead per-record berurutan (record diacak tiap epoch) ->
    gambar tiap record cukup dimuat 1x (cache) -> training jauh lebih cepat."""
    def __init__(self, items, shuffle=True):
        self.groups = OrderedDict()
        for idx, (rid, _) in enumerate(items):
            self.groups.setdefault(rid, []).append(idx)
        self.rids = list(self.groups.keys()); self.shuffle = shuffle
        self.n = sum(len(v) for v in self.groups.values())

    def __iter__(self):
        rids = self.rids[:]
        if self.shuffle:
            random.shuffle(rids)
        for rid in rids:
            for idx in self.groups[rid]:
                yield idx

    def __len__(self):
        return self.n


def _img_path(root, rid):
    for ext in (".jpg", ".png"):
        p = os.path.join(root, "images", rid + ext)
        if os.path.exists(p):
            return p
    return os.path.join(root, "images", rid + ".jpg")


def _list_ids(root):
    ims = sorted(glob.glob(os.path.join(root, "images", "*.jpg")) +
                 glob.glob(os.path.join(root, "images", "*.png")))
    return [os.path.splitext(os.path.basename(p))[0] for p in ims]


def split_ids(root, val_frac=0.15, seed=0):
    ids = _list_ids(root)
    rng = np.random.RandomState(seed)
    rng.shuffle(ids)
    nval = max(1, int(len(ids) * val_frac))
    return ids[nval:], ids[:nval]


class LeadStripDataset(Dataset):
    """Yield (strip 3xHxW, clean_target 1xHxW) per (record, lead)."""

    def __init__(self, root, ids=None, train=True, strip_h=STRIP_H, crop_w=CROP_W,
                 overlay_p=0.45):
        self.root = root
        self.ids = ids if ids is not None else _list_ids(root)
        self.train = train
        self.H = strip_h
        self.W = crop_w
        self.overlay_p = overlay_p
        self._cache = OrderedDict()      # LRU: rid -> (img,msk,off,meta)
        self._cache_max = 6
        # daftar (rid, lead_name) — semua lead tiap record
        self.items = []
        for rid in self.ids:
            mp = os.path.join(root, "meta", rid + ".json")
            try:
                meta = json.load(open(mp))
            except Exception:
                continue
            for nm in meta.get("lead_boxes", {}):
                self.items.append((rid, nm))

    def __len__(self):
        return len(self.items)

    def _load(self, rid):
        if rid in self._cache:
            self._cache.move_to_end(rid)
            return self._cache[rid]
        img = cv2.cvtColor(cv2.imread(_img_path(self.root, rid), cv2.IMREAD_COLOR),
                           cv2.COLOR_BGR2RGB)
        msk = cv2.imread(os.path.join(self.root, "masks", rid + ".png"),
                         cv2.IMREAD_GRAYSCALE)
        off = np.load(os.path.join(self.root, "offsets", rid + ".npz"))["off"].astype(np.float32)
        meta = json.load(open(os.path.join(self.root, "meta", rid + ".json")))
        self._cache[rid] = (img, msk, off, meta)
        if len(self._cache) > self._cache_max:
            self._cache.popitem(last=False)
        return img, msk, off, meta

    def _clean_target(self, msk_crop, off_crop, r0, baseline):
        """Target = piksel mask yg offset-nya menunjuk ke baseline lead INI."""
        H, W = msk_crop.shape
        yy = (np.arange(H)[:, None] + r0).astype(np.float32)   # global y
        owner_base = yy + off_crop                              # baseline pemilik
        own = (np.abs(owner_base - baseline) < OWN_TOL) & (msk_crop > 127)
        return own.astype(np.float32)

    def _overlay(self, img, rng):
        """OverlaySignal: tempel potongan trace lead LAIN di tepi atas/bawah
        (interferensi). Diambil dari record acak; target TIDAK diubah."""
        rid2 = self.ids[rng.randint(len(self.ids))]
        try:
            i2 = cv2.cvtColor(cv2.imread(_img_path(self.root, rid2), cv2.IMREAD_COLOR),
                              cv2.COLOR_BGR2RGB)
        except Exception:
            return img
        H, W = img.shape[:2]
        bh = rng.randint(24, 46)                       # tinggi pita interferensi
        if i2.shape[0] < bh + 2 or i2.shape[1] < W + 2:
            return img
        sy = rng.randint(0, i2.shape[0] - bh)
        sx = rng.randint(0, i2.shape[1] - W)
        patch = i2[sy:sy + bh, sx:sx + W]
        img = img.copy()
        if rng.random() < 0.5:                          # tepi atas
            img[:bh] = np.minimum(img[:bh], patch)      # tinta gelap menimpa
        else:                                           # tepi bawah
            img[H - bh:] = np.minimum(img[H - bh:], patch)
        return img

    def __getitem__(self, i):
        rid, lead = self.items[i]
        img, msk, off, meta = self._load(rid)
        H, W = img.shape[:2]
        b = int(meta["lead_boxes"][lead]["baseline_y"])
        x0_lead = int(meta["lead_boxes"][lead]["x0"])
        rng = np.random.RandomState() if self.train else np.random.RandomState(i)

        # crop vertikal: strip di sekitar baseline
        r0 = int(np.clip(b - self.H // 2, 0, max(0, H - self.H)))
        r1 = r0 + self.H
        # crop horizontal: window selebar W di area trace lead
        if self.train:
            xw0 = rng.randint(max(0, x0_lead - 10),
                              max(1, W - self.W))
        else:
            xw0 = min(max(0, x0_lead), max(0, W - self.W))
        xw1 = xw0 + self.W
        img_c = img[r0:r1, xw0:xw1]
        msk_c = msk[r0:r1, xw0:xw1]
        off_c = off[r0:r1, xw0:xw1]
        # pad bila kurang
        ph, pw = self.H - img_c.shape[0], self.W - img_c.shape[1]
        if ph > 0 or pw > 0:
            img_c = cv2.copyMakeBorder(img_c, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            msk_c = cv2.copyMakeBorder(msk_c, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=0)
            off_c = cv2.copyMakeBorder(off_c, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=0)

        target = self._clean_target(msk_c, off_c, r0, b)

        if self.train:
            if rng.random() < self.overlay_p:
                img_c = self._overlay(img_c, rng)
            if rng.random() < 0.3:
                g = rng.uniform(0.8, 1.2)
                img_c = np.clip(((img_c / 255.0) ** g) * 255.0, 0, 255).astype(np.uint8)
            if rng.random() < 0.3:
                n = rng.normal(0, rng.uniform(2, 8), img_c.shape)
                img_c = np.clip(img_c.astype(np.float32) + n, 0, 255).astype(np.uint8)
            if rng.random() < 0.5:                       # flip horizontal
                img_c = img_c[:, ::-1].copy(); target = target[:, ::-1].copy()

        x = torch.from_numpy(np.ascontiguousarray(img_c.transpose(2, 0, 1)).astype(np.float32) / 255.0)
        t = torch.from_numpy(np.ascontiguousarray(target))[None]
        return x, t


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    tr, va = split_ids(root)
    ds = LeadStripDataset(root, ids=tr, train=True)
    print("strip items:", len(ds))
    x, t = ds[0]
    print("x", x.shape, "t", t.shape, "target frac", float(t.mean()))
