"""
training/classify/train_cls.py — Latih ECGNet klasifikasi 5 superclass PTB-XL.

Split RESMI strat_fold: 1-8 train, 9 val, 10 test (benchmark PTB-XL).
Multi-label -> BCEWithLogits. Metrik: macro-AUC (standar benchmark) + per-kelas.
Early-stopping pada val macro-AUC.

Output: classify/ecgnet_best.pt + laporan AUC test.
"""
import os, time
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import TensorDataset, DataLoader
from sklearn.metrics import roc_auc_score, f1_score

from model import ECGNet

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, 'cache')
CLASSES = ['NORM', 'MI', 'STTC', 'CD', 'HYP']


def load():
    X = np.load(os.path.join(CACHE, 'X.npy'))          # (N,1000,12)
    Y = np.load(os.path.join(CACHE, 'Y.npy'))          # (N,5)
    folds = np.load(os.path.join(CACHE, 'folds.npy'))
    X = np.transpose(X, (0, 2, 1))                     # -> (N,12,1000)
    # standardisasi per-lead pakai statistik TRAIN
    tr = folds <= 8
    mu = X[tr].mean((0, 2), keepdims=True)
    sd = X[tr].std((0, 2), keepdims=True) + 1e-6
    X = (X - mu) / sd
    return X.astype(np.float32), Y.astype(np.float32), folds


def macro_auc(y, p):
    aucs = []
    for j in range(y.shape[1]):
        if y[:, j].sum() > 0 and y[:, j].sum() < len(y):
            aucs.append(roc_auc_score(y[:, j], p[:, j]))
    return float(np.mean(aucs)), aucs


@torch.no_grad()
def evaluate(net, dl, dev):
    net.eval(); P = []; Yt = []
    for x, y in dl:
        with torch.cuda.amp.autocast(enabled=(dev == 'cuda')):
            p = torch.sigmoid(net(x.to(dev)))
        P.append(p.float().cpu().numpy()); Yt.append(y.numpy())
    return np.concatenate(Yt), np.concatenate(P)


def run(epochs=40, batch=128, patience=6):
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    print('device:', dev)
    X, Y, folds = load()
    print('data:', X.shape, 'distribusi:', {c: int(Y[:, j].sum()) for j, c in enumerate(CLASSES)})
    idx_tr = folds <= 8; idx_va = folds == 9; idx_te = folds == 10
    mk = lambda I, sh: DataLoader(TensorDataset(torch.from_numpy(X[I]),
                                  torch.from_numpy(Y[I])), batch_size=batch,
                                  shuffle=sh, num_workers=0, pin_memory=(dev == 'cuda'))
    tl, vl, te = mk(idx_tr, True), mk(idx_va, False), mk(idx_te, False)
    print(f"train {idx_tr.sum()} | val {idx_va.sum()} | test {idx_te.sum()}")

    net = ECGNet().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=1e-3, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    bce = nn.BCEWithLogitsLoss()
    scaler = torch.cuda.amp.GradScaler(enabled=(dev == 'cuda'))
    best = 0.0; since = 0
    for ep in range(1, epochs + 1):
        net.train(); t0 = time.time(); run_loss = 0
        for x, y in tl:
            x, y = x.to(dev), y.to(dev)
            opt.zero_grad(set_to_none=True)
            with torch.cuda.amp.autocast(enabled=(dev == 'cuda')):
                loss = bce(net(x), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update()
            run_loss += loss.item()
        sched.step()
        yv, pv = evaluate(net, vl, dev)
        auc, _ = macro_auc(yv, pv)
        print(f"ep {ep:3d}/{epochs} | loss {run_loss/len(tl):.4f} | "
              f"val macroAUC {auc:.4f} | {time.time()-t0:.1f}s")
        if auc > best + 1e-4:
            best = auc; since = 0
            torch.save({'model': net.state_dict()}, os.path.join(HERE, 'ecgnet_best.pt'))
        else:
            since += 1
            if since >= patience:
                print(f"early-stop ep {ep} (best val AUC {best:.4f})"); break

    # TEST dgn checkpoint terbaik
    net.load_state_dict(torch.load(os.path.join(HERE, 'ecgnet_best.pt'))['model'])
    yt, pt = evaluate(net, te, dev)
    auc, aucs = macro_auc(yt, pt)
    f1 = f1_score(yt, (pt > 0.5).astype(int), average='macro', zero_division=0)
    print("\n=== HASIL TEST (fold 10) ===")
    print(f"  macro-AUC = {auc:.3f}  (benchmark PTB-XL ~0.90-0.93)")
    print(f"  macro-F1  = {f1:.3f}")
    j = 0
    for c in CLASSES:
        if yt[:, CLASSES.index(c)].sum() > 0:
            a = roc_auc_score(yt[:, CLASSES.index(c)], pt[:, CLASSES.index(c)])
            print(f"  AUC {c:5s} = {a:.3f}")


if __name__ == '__main__':
    run()
