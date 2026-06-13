"""
training/decode.py — Inference U-Net + decoder mask -> sinyal mV.

Dua tahap:
  1) predict_mask : jalankan U-Net pada gambar penuh via TILING (overlap),
     gabungkan peta probabilitas -> mask biner trace.
  2) mask_to_signals : untuk tiap lead (pakai kalibrasi & kotak di meta),
     ambil centroid kolom -> tinggi piksel -> mV -> resample ke jumlah
     sampel asli. Menghasilkan dict {lead: np.array(mV)}.

Dipakai oleh validate.py dan untuk digitalisasi gambar nyata.
"""

import numpy as np
import torch


# ----------------------------------------------------------------------------
# Inference U-Net (tiling) pada gambar penuh
# ----------------------------------------------------------------------------
@torch.no_grad()
def predict_mask(net, img, device="cuda", tile=256, overlap=32, thr=0.5):
    """
    img: np.uint8 (H,W,3) RGB atau (H,W) grayscale -> mask biner (H,W).
    Grayscale otomatis di-broadcast ke 3 channel.
    """
    net.eval()
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, axis=2)
    h, w = img.shape[:2]
    x = img.astype(np.float32) / 255.0
    prob = np.zeros((h, w), np.float32)
    cnt = np.zeros((h, w), np.float32)
    step = tile - overlap
    ys = sorted(set(list(range(0, max(1, h - tile + 1), step)) + [max(0, h - tile)]))
    xs = sorted(set(list(range(0, max(1, w - tile + 1), step)) + [max(0, w - tile)]))
    for y in ys:
        for xx in xs:
            patch = x[y:y + tile, xx:xx + tile]
            ph, pw = patch.shape[:2]
            if ph < tile or pw < tile:
                patch = np.pad(patch, ((0, tile - ph), (0, tile - pw), (0, 0)),
                               constant_values=1.0)
            t = torch.from_numpy(patch.transpose(2, 0, 1))[None].to(device)
            with torch.amp.autocast('cuda', enabled=(device == "cuda")):
                p = torch.sigmoid(net(t))[0, 0].float().cpu().numpy()
            prob[y:y + ph, xx:xx + pw] += p[:ph, :pw]
            cnt[y:y + ph, xx:xx + pw] += 1.0
    prob /= np.maximum(cnt, 1e-6)
    return (prob > thr).astype(np.uint8) * 255


@torch.no_grad()
def predict_mask_offset(net, img, device="cuda", tile=256, overlap=32, thr=0.5):
    """U-Net 2-output -> (mask biner HxW, offset_px HxW).
    offset_px = prediksi (baseline_lead - y) dalam piksel (dikali 100 dari mV)."""
    net.eval()
    if img.ndim == 2:
        img = np.repeat(img[:, :, None], 3, axis=2)
    h, w = img.shape[:2]
    x = img.astype(np.float32) / 255.0
    prob = np.zeros((h, w), np.float32)
    offs = np.zeros((h, w), np.float32)
    cnt = np.zeros((h, w), np.float32)
    step = tile - overlap
    ys = sorted(set(list(range(0, max(1, h - tile + 1), step)) + [max(0, h - tile)]))
    xs = sorted(set(list(range(0, max(1, w - tile + 1), step)) + [max(0, w - tile)]))
    for y in ys:
        for xx in xs:
            patch = x[y:y + tile, xx:xx + tile]
            ph, pw = patch.shape[:2]
            if ph < tile or pw < tile:
                patch = np.pad(patch, ((0, tile - ph), (0, tile - pw), (0, 0)),
                               constant_values=1.0)
            t = torch.from_numpy(patch.transpose(2, 0, 1))[None].to(device)
            with torch.amp.autocast('cuda', enabled=(device == "cuda")):
                out = net(t)[0].float().cpu().numpy()
            prob[y:y + ph, xx:xx + pw] += 1 / (1 + np.exp(-out[0, :ph, :pw]))
            offs[y:y + ph, xx:xx + pw] += out[1, :ph, :pw] * 100.0  # mV->px
            cnt[y:y + ph, xx:xx + pw] += 1.0
    prob /= np.maximum(cnt, 1e-6)
    offs /= np.maximum(cnt, 1e-6)
    return (prob > thr).astype(np.uint8) * 255, offs


# ----------------------------------------------------------------------------
# Decoder: mask -> sinyal mV per lead
# ----------------------------------------------------------------------------
def _clusters(ys, gap=3):
    """Kelompokkan indeks piksel yang berdekatan menjadi gugus (run)."""
    if ys.size == 0:
        return []
    groups = []
    start = prev = ys[0]
    for y in ys[1:]:
        if y - prev <= gap:
            prev = y
        else:
            groups.append((start, prev))
            start = prev = y
    groups.append((start, prev))
    return groups


def _column_trace_y(mask_col, y_lo, y_hi, near=None, max_jump=None):
    """
    Cari posisi-y trace di satu kolom dalam pita [y_lo:y_hi] dengan pelacakan
    KONTINUITAS: bila ada beberapa gugus piksel, pilih gugus yang centroid-nya
    paling dekat ke posisi sebelumnya (near). Mencegah lompat ke trace lead lain
    sekaligus menangkap QRS tinggi (lompatan besar tapi kontinu).
    """
    seg = mask_col[y_lo:y_hi]
    ys = np.where(seg > 0)[0]
    if ys.size == 0:
        return None
    ys = ys + y_lo
    groups = _clusters(ys)
    cents = [0.5 * (a + b) for a, b in groups]
    if near is None:
        return float(np.median(ys))
    # SATU gugus = trace tunggal tak ambigu -> SELALU ikuti (jangan tolak via
    # max_jump; kalau ditolak, puncak R/S yang curam jadi terpotong).
    if len(groups) == 1:
        return float(cents[0])
    # Banyak gugus = ada risiko trace lead lain -> pilih terdekat ke 'near'
    # dan tolak lompatan tak masuk akal (cegah lompat ke tetangga).
    cents = np.array(cents)
    j = int(np.argmin(np.abs(cents - near)))
    pick = cents[j]
    if max_jump is not None and abs(pick - near) > max_jump:
        return None
    return float(pick)


def mask_to_signals(mask, meta, half_frac=0.5, max_jump_frac=0.45,
                    continuity=True):
    """
    mask: np.uint8 (H,W). meta: dict dari generator (px_per_mV, px_per_sec,
    fs, lead_boxes{name:{x0,baseline_y,seg_sec}}).
    half_frac    : lebar pita pencarian (x cell_h) di atas/bawah baseline.
                   0.5 = persis setengah jarak antar-lane (tanpa tumpang-tindih
                   tetangga). Lebih besar -> bisa bocor ke lead tetangga.
    max_jump_frac: batas lompatan-y antar kolom (x cell_h) untuk kontinuitas.
    return: {lead: np.array(mV, len = seg_sec*fs)}
    """
    px_mv = meta["px_per_mV"]
    px_s = meta["px_per_sec"]
    fs = meta["fs"]
    cell_h = meta.get("cell_h", mask.shape[0])
    half = int(cell_h * half_frac // 1)
    max_jump = cell_h * max_jump_frac
    H, W = mask.shape
    out = {}
    for name, box in meta["lead_boxes"].items():
        x0 = int(round(box["x0"]))
        base = box["baseline_y"]
        seg_sec = box["seg_sec"]
        n = int(round(seg_sec * fs))
        x1 = min(W, x0 + int(round(seg_sec * px_s)))
        y_lo = max(0, base - half)
        y_hi = min(H, base + half)
        cols = range(x0, x1)
        ys = []
        last = base
        for x in cols:
            if not (0 <= x < W):
                cy = None
            elif continuity:
                cy = _column_trace_y(mask[:, x], y_lo, y_hi, near=last,
                                     max_jump=max_jump)
            else:
                # Mask bersih + pita sempit -> centroid langsung, tanpa drift
                cy = _column_trace_y(mask[:, x], y_lo, y_hi, near=None)
            if cy is not None:
                last = cy
            ys.append(cy if cy is not None else np.nan)  # putus -> NaN
        ys = np.array(ys, np.float32)
        # Interpolasi celah (lebih baik daripada menahan nilai terakhir)
        idx = np.arange(len(ys))
        good = ~np.isnan(ys)
        if good.sum() == 0:
            out[name] = np.zeros(n, np.float32)
            continue
        ys = np.interp(idx, idx[good], ys[good])
        mv = (base - ys) / px_mv    # piksel -> mV (atas = positif)
        xp = np.linspace(0, 1, len(mv))
        xq = np.linspace(0, 1, n)
        out[name] = np.interp(xq, xp, mv).astype(np.float32)
    return out


def dp_trace(mask, base, y_lo, y_hi, x_lo, x_hi, px_mv,
             smooth=0.004, baseline_pull=0.0008):
    """
    Pelacak trace berbasis DYNAMIC PROGRAMMING (Viterbi).
    Cari jalur y(x) TERHALUS yang kontinu menembus mask di pita [y_lo,y_hi].
    Cocok untuk lead yang ter-overlap trace lead lain (mis. V1 yang ditembus
    R-wave V2): lonjakan tajam (lompat ke spike tetangga lalu balik) dihukum,
    sehingga tracker tetap di trace asli yang halus.

    smooth        : bobot kehalusan (|dy|^2 antar kolom)
    baseline_pull : tarikan lembut ke baseline (cegah hanyut ke lead lain)
    """
    cols = list(range(x_lo, x_hi))
    # kandidat per kolom = centroid tiap gugus piksel; bila kosong -> baseline
    cand, W = [], []
    for x in cols:
        seg = mask[y_lo:y_hi, x]
        ys = np.where(seg > 0)[0]
        if ys.size == 0:
            cand.append([float(base)]); W.append([0.0]); continue
        ys = ys + y_lo
        groups = _clusters(ys)
        c = [0.5 * (a + b) for a, b in groups]
        w = [float(b - a + 1) for a, b in groups]   # tinggi gugus (massa)
        cand.append(c); W.append(w)
    n = len(cols)
    INF = 1e18
    # DP maju
    costs = [[0.0] * len(cand[0])]
    for i, c in enumerate(cand[0]):
        costs[0][i] = baseline_pull * (c - base) ** 2
    back = [[0] * len(cand[0])]
    for k in range(1, n):
        ck = cand[k]; prev = cand[k - 1]; pc = costs[k - 1]
        row = [INF] * len(ck); bk = [0] * len(ck)
        for i, ci in enumerate(ck):
            best, bj = INF, 0
            for j, cj in enumerate(prev):
                v = pc[j] + smooth * (ci - cj) ** 2
                if v < best:
                    best, bj = v, j
            row[i] = best + baseline_pull * (ci - base) ** 2
            bk[i] = bj
        costs.append(row); back.append(bk)
    # backtrack
    yk = int(np.argmin(costs[-1]))
    path = [0] * n
    for k in range(n - 1, -1, -1):
        path[k] = cand[k][yk]; yk = back[k][yk] if k > 0 else yk
    ys = np.array(path, float)
    mv = (base - ys) / px_mv
    return mv


def dp_trace2(mask, base, y_lo, y_hi, x_lo, x_hi, px_mv,
              accel=0.02, baseline_pull=0.0006):
    """
    Pelacak DP ORDE-2 (momentum global-optimal). Hukum PERCEPATAN
    |y[k]-2y[k-1]+y[k-2]|^2 -> jalur cenderung lurus/mulus dan MENERUSKAN arah
    saat menyilang trace lead tetangga (mis. R-V2 menembus QS-V1 di LVH) ->
    amplitudo PENUH tak terpotong, dan tetap stabil (tak liar seperti greedy).
    """
    cols = list(range(x_lo, x_hi))
    cand = []
    for x in cols:
        if 0 <= x < mask.shape[1]:
            idx = np.where(mask[y_lo:y_hi, x] > 0)[0]
        else:
            idx = np.array([], int)
        if idx.size == 0:
            cand.append([float(base)])
        else:
            idx = idx + y_lo
            cand.append([0.5 * (a + b) for a, b in _clusters(idx)])
    n = len(cols)
    if n < 3:
        return np.zeros(n, np.float32)
    ys = _dp2_backtrack(cand, base, accel, baseline_pull)
    return (base - ys) / px_mv


def _dp2_backtrack(cand, base, accel, baseline_pull):
    n = len(cand)
    prev = {}
    bptr = [dict() for _ in range(n)]
    for j, cj in enumerate(cand[0]):
        for i, ci in enumerate(cand[1]):
            prev[(i, j)] = baseline_pull * ((ci - base) ** 2 + (cj - base) ** 2)
            bptr[1][(i, j)] = None
    for k in range(2, n):
        cur = {}
        Ck, Ck1, Ck2 = cand[k], cand[k - 1], cand[k - 2]
        for m, cm in enumerate(Ck):
            bp = baseline_pull * (cm - base) ** 2
            best = None
            for (i, j), pc in prev.items():
                a = cm - 2 * Ck1[i] + Ck2[j]
                v = pc + accel * a * a + bp
                if best is None or v < best[0]:
                    best = (v, (i, j))
            cur[(m, best[1][0])] = best[0]
            bptr[k][(m, best[1][0])] = best[1]
        prev = cur
    end = min(prev.items(), key=lambda kv: kv[1])[0]
    path = [0.0] * n
    k = n - 1
    cur = end
    while k >= 1:
        m, i = cur
        path[k] = cand[k][m]
        if k == 1:
            path[0] = cand[0][i]
            break
        cur = bptr[k][cur]
        k -= 1
    return np.array(path, float)


def momentum_trace(mask, base, y_lo, y_hi, x_lo, x_hi, px_mv,
                   maxv=22, vel_mem=0.6):
    """
    Pelacak trace berbasis MOMENTUM — mengikuti arah/laju trace sehingga bisa
    menembus PERSILANGAN dengan trace lead tetangga (mis. R-V2 masif menyilang
    QS-V1 di LVH) dan menangkap amplitudo PENUH tanpa terpotong.

    Prediksi posisi berikut = posisi terakhir + kecepatan (diekstrapolasi),
    lalu pilih gugus piksel terdekat ke prediksi. Band boleh lebar; momentum +
    kontinuitas yang menjaga tetap pada trace yang benar.
    """
    ys = []
    last = float(base)
    vel = 0.0
    for x in range(x_lo, x_hi):
        if not (0 <= x < mask.shape[1]):
            ys.append(np.nan); continue
        idx = np.where(mask[y_lo:y_hi, x] > 0)[0]
        if idx.size == 0:
            ys.append(np.nan); continue
        idx = idx + y_lo
        cents = np.array([0.5 * (a + b) for a, b in _clusters(idx)])
        pred = last + np.clip(vel, -maxv, maxv)
        c = float(cents[int(np.argmin(np.abs(cents - pred)))])
        vel = vel_mem * vel + (1 - vel_mem) * (c - last)
        last = c
        ys.append(c)
    ys = np.array(ys, float)
    good = ~np.isnan(ys)
    if good.sum() == 0:
        return np.zeros(x_hi - x_lo, np.float32)
    ys = np.interp(np.arange(len(ys)), np.where(good)[0], ys[good])
    return (base - ys) / px_mv


def despike(mv, win=25, thr_mv=0.6, maxrun=8):
    """
    Buang spike sempit yang melompat dari tren lokal — khas artefak decode saat
    R-wave lead tetangga melintas sesaat (mis. R-V2 masif menembus lajur V1 pada
    LVH). Median window LEBAR (win) supaya tren acuan tak ikut terangkat spike;
    hanya RUN pendek (<=maxrun) yang diapit sampel normal yang dibuang -> QRS
    asli (lebih lebar/menetap) tetap utuh.
    """
    x = np.asarray(mv, float).copy()
    n = len(x)
    if n < win + 2:
        return x
    half = win // 2
    med = np.copy(x)
    for i in range(n):
        a, b = max(0, i - half), min(n, i + half + 1)
        med[i] = np.median(x[a:b])
    dev = np.abs(x - med)
    bad = dev > thr_mv
    # buang RUN pendek (<=3 sampel) outlier yang diapit sampel normal -> spike
    # sempit (khas R lead tetangga melintas). QRS asli lebih lebar -> aman.
    i = 0
    while i < n:
        if bad[i]:
            j = i
            while j < n and bad[j]:
                j += 1
            run = j - i
            if run <= maxrun:
                l = x[i - 1] if i > 0 else x[j % n]
                r = x[j] if j < n else x[i - 1]
                x[i:j] = np.linspace(l, r, run + 2)[1:-1]
            i = j
        else:
            i += 1
    return x


def decode_offset(mask, offset, lanes, x_lo, x_hi, px_mv):
    """
    Decode SADAR-LEAD pakai peta offset. Tiap piksel-trace diprediksi baseline-
    nya = y + offset[y,x], lalu di-assign ke lead dengan baseline TERDEKAT.
    Maka piksel R-wave yang spasialnya di lajur tetangga tetap masuk ke lead
    pemiliknya (karena offset-nya menunjuk balik ke baseline lead itu) ->
    amplitudo PENUH & tak tertukar walau trace bersilangan.

    return: {lead_index: np.array(mV per kolom)}  (di-assign per posisi lanes)
    """
    H, W = mask.shape
    lanes = np.asarray(lanes, float)
    nL = len(lanes)
    cols = list(range(x_lo, min(W, x_hi)))
    # akumulasi y per lead per kolom
    out_y = [np.full(len(cols), np.nan) for _ in range(nL)]
    for ci, x in enumerate(cols):
        ys = np.where(mask[:, x] > 0)[0]
        if ys.size == 0:
            continue
        pred_base = ys + offset[ys, x]               # baseline prediksi piksel
        # assign tiap piksel ke lead baseline terdekat
        d = np.abs(pred_base[:, None] - lanes[None, :])
        owner = np.argmin(d, axis=1)
        nearest = d[np.arange(len(ys)), owner]
        for L in range(nL):
            sel = ys[(owner == L) & (nearest < 90)]   # toleransi 90px
            if sel.size:
                out_y[L][ci] = sel.mean()
    res = {}
    for L in range(nL):
        y = out_y[L]
        good = ~np.isnan(y)
        if good.sum() == 0:
            res[L] = np.zeros(len(cols), np.float32); continue
        y = np.interp(np.arange(len(y)), np.where(good)[0], y[good])
        res[L] = ((lanes[L] - y) / px_mv).astype(np.float32)
    return res


def load_net(ckpt_path, device="cuda"):
    from unet import UNet
    ck = torch.load(ckpt_path, map_location=device, weights_only=False)
    net = UNet(in_ch=ck.get("in_ch", 3), out_ch=ck.get("out_ch", 1),
               base=ck.get("base", 32)).to(device)
    net.load_state_dict(ck["model"])
    net.eval()
    return net