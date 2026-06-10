"""
training/classify/prep_data.py — Siapkan data PTB-XL untuk klasifikasi 5
superclass (NORM, MI, STTC, CD, HYP).

- Petakan scp_codes tiap rekaman -> set superclass (MULTI-LABEL).
- Muat sinyal 100 Hz (records100, 1000x12) via wfdb, cache ke .npy.
- Pakai split RESMI strat_fold: 1-8 train, 9 val, 10 test.

Output -> classify/cache/{X,Y,folds}.npy  (sekali jalan, ~beberapa menit).
"""
import os, ast
import numpy as np
import pandas as pd
import wfdb

HERE = os.path.dirname(os.path.abspath(__file__))
PTBXL = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                     'ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3',
                     'ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3')
CACHE = os.path.join(HERE, 'cache')
CLASSES = ['NORM', 'MI', 'STTC', 'CD', 'HYP']


def superclasses_of(scp_str, scp_map):
    out = set()
    try:
        for code in ast.literal_eval(scp_str):
            c = scp_map.get(code)
            if c in CLASSES:
                out.add(c)
    except Exception:
        pass
    return out


def main():
    os.makedirs(CACHE, exist_ok=True)
    db = pd.read_csv(os.path.join(PTBXL, 'ptbxl_database.csv'), index_col='ecg_id')
    scp = pd.read_csv(os.path.join(PTBXL, 'scp_statements.csv'), index_col=0)
    scp_map = scp[scp.diagnostic == 1]['diagnostic_class'].to_dict()

    # label multi-hot
    Y = np.zeros((len(db), len(CLASSES)), np.float32)
    keep = []
    for i, (eid, row) in enumerate(db.iterrows()):
        sc = superclasses_of(row.scp_codes, scp_map)
        if sc:                          # buang rekaman tanpa label diagnostik
            for c in sc:
                Y[i, CLASSES.index(c)] = 1.0
            keep.append(i)
    keep = np.array(keep)
    print(f"rekaman berlabel: {len(keep)}/{len(db)}")
    print("distribusi:", {c: int(Y[keep, j].sum()) for j, c in enumerate(CLASSES)})

    # muat sinyal 100 Hz
    files = db['filename_lr'].values
    folds = db['strat_fold'].values
    X = np.zeros((len(keep), 1000, 12), np.float32)
    for n, i in enumerate(keep):
        rec = wfdb.rdrecord(os.path.join(PTBXL, files[i]))
        sig = rec.p_signal.astype(np.float32)
        X[n] = sig[:1000]
        if n % 2000 == 0:
            print(f"  muat {n}/{len(keep)}")
    np.save(os.path.join(CACHE, 'X.npy'), X)
    np.save(os.path.join(CACHE, 'Y.npy'), Y[keep])
    np.save(os.path.join(CACHE, 'folds.npy'), folds[keep])
    print(f"cache -> {CACHE}  X{X.shape} Y{Y[keep].shape}")


if __name__ == '__main__':
    main()
