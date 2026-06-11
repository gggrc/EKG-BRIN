"""
training/dataset.py — Dataset (image, mask) untuk training U-Net.

Gambar EKG sintetik berukuran besar (~2000 px). Untuk muat di RTX 3060 (6 GB)
dan menjaga garis tipis tetap tajam, training memakai RANDOM CROP berukuran
tetap (default 256x256) — bukan resize (resize menipiskan/menghapus trace).

Mode:
  - train=True  : random crop, augmentasi ringan on-the-fly, bias ke area trace
  - train=False : kembalikan gambar penuh (untuk inference/validasi via tiling)
"""

import os
import glob
import json

import numpy as np
import cv2
import torch
from torch.utils.data import Dataset


def _list_ids(root):
    ims = sorted(glob.glob(os.path.join(root, "images", "*.jpg")) +
                 glob.glob(os.path.join(root, "images", "*.png")))
    return [os.path.splitext(os.path.basename(p))[0] for p in ims]


def _img_path(root, rid):
    for ext in (".jpg", ".png"):
        p = os.path.join(root, "images", rid + ext)
        if os.path.exists(p):
            return p
    return os.path.join(root, "images", rid + ".jpg")


class ECGSegDataset(Dataset):
    def __init__(self, root, ids=None, crop=256, train=True,
                 prefer_trace_p=0.7):
        self.root = root
        self.ids = ids if ids is not None else _list_ids(root)
        self.crop = crop
        self.train = train
        self.prefer_trace_p = prefer_trace_p

    def __len__(self):
        return len(self.ids)

    def _load(self, rid):
        # RGB: warna memisahkan grid (merah) dari trace (hitam) — krusial agar
        # baseline datar tidak tertukar dengan garis grid horizontal.
        img = cv2.imread(_img_path(self.root, rid), cv2.IMREAD_COLOR)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        msk = cv2.imread(os.path.join(self.root, "masks", rid + ".png"),
                         cv2.IMREAD_GRAYSCALE)
        off = np.load(os.path.join(self.root, "offsets", rid + ".npz"))["off"]
        return img, msk, off.astype(np.float32)

    def _rand_crop(self, img, msk, off, rng):
        h, w = img.shape[:2]
        cs = self.crop
        if h < cs or w < cs:  # pad bila lebih kecil dari crop
            ph, pw = max(0, cs - h), max(0, cs - w)
            img = cv2.copyMakeBorder(img, 0, ph, 0, pw,
                                     cv2.BORDER_CONSTANT, value=(255, 255, 255))
            msk = cv2.copyMakeBorder(msk, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=0)
            off = cv2.copyMakeBorder(off, 0, ph, 0, pw, cv2.BORDER_CONSTANT, value=0)
            h, w = img.shape[:2]

        prefer = rng.random() < self.prefer_trace_p
        for _ in range(8 if prefer else 1):
            y = rng.randint(0, h - cs + 1)
            x = rng.randint(0, w - cs + 1)
            mc = msk[y:y + cs, x:x + cs]
            if not prefer or mc.max() > 0:
                return (img[y:y + cs, x:x + cs], mc, off[y:y + cs, x:x + cs])
        return (img[y:y + cs, x:x + cs], msk[y:y + cs, x:x + cs],
                off[y:y + cs, x:x + cs])

    def _augment(self, img, rng):
        # Augmentasi ringan tambahan (image saja; mask tak berubah bentuk)
        if rng.random() < 0.3:
            g = rng.uniform(0.8, 1.2)
            img = np.clip(((img / 255.0) ** g) * 255.0, 0, 255).astype(np.uint8)
        if rng.random() < 0.3:
            n = rng.normal(0, rng.uniform(2, 8), img.shape)
            img = np.clip(img.astype(np.float32) + n, 0, 255).astype(np.uint8)
        return img

    def __getitem__(self, i):
        rid = self.ids[i]
        img, msk, off = self._load(rid)
        if self.train:
            rng = np.random.RandomState()
            img, msk, off = self._rand_crop(img, msk, off, rng)
            img = self._augment(img, rng)
            if rng.random() < 0.5:  # flip horizontal (offset tak berubah)
                img = img[:, ::-1].copy()
                msk = msk[:, ::-1].copy()
                off = off[:, ::-1].copy()

        x = torch.from_numpy(
            np.ascontiguousarray(img.transpose(2, 0, 1)).astype(np.float32) / 255.0)
        m = torch.from_numpy((msk > 127).astype(np.float32))[None]
        # offset dinormalisasi ke ~mV (bagi 100 px/mV) agar skala loss wajar
        o = torch.from_numpy((off.astype(np.float32) / 100.0))[None]
        return x, m, o


def split_ids(root, val_frac=0.15, seed=0):
    ids = _list_ids(root)
    rng = np.random.RandomState(seed)
    rng.shuffle(ids)
    nval = max(1, int(len(ids) * val_frac))
    return ids[nval:], ids[:nval]  # train, val


if __name__ == "__main__":
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
    tr, va = split_ids(root)
    ds = ECGSegDataset(root, ids=tr, train=True)
    x, y = ds[0]
    print("train ids", len(tr), "val ids", len(va))
    print("x", x.shape, x.dtype, "y", y.shape, "trace frac", float(y.mean()))
