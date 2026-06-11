"""
training/digitize_real.py — Terapkan U-Net (dilatih sintetik) ke EKG NYATA (Export PDF).

Alur (tanpa meta — semua dideteksi dari gambar):
  1. Render PDF @254 dpi (= 10 px/mm, cocok dgn training).
  2. Deteksi region EKG via grid merah (buang header/footer teks).
  3. U-Net -> mask trace.
  4. Deteksi lane lead: proyeksi mask per-baris -> puncak = baseline tiap lead.
  5. Kalibrasi langsung: 25 mm/s, 10 mm/mV, 10 px/mm
       -> px_per_sec=250, px_per_mV=100.
  6. Decode tiap lane (centroid kolom dalam pita) -> sinyal mV.
  7. Simpan plot + JSON sinyal.

Jalankan: python digitize_real.py --pdf ../Export/<folder>/<file>.pdf
"""

import os
import json
import argparse

import numpy as np
import cv2
import fitz
import torch
from scipy.signal import find_peaks

from decode import (load_net, predict_mask, predict_mask_offset, decode_offset,
                    _column_trace_y, dp_trace, momentum_trace, despike)

LEAD_ORDER = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
              'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


def render_pdf(pdf_path, dpi=254):
    doc = fitz.open(pdf_path)
    pix = doc[0].get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        bgr = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    else:
        bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    return bgr


def ecg_region(bgr):
    """Batas vertikal & horizontal region EKG via grid merah (header tak ber-grid)."""
    H, W = bgr.shape[:2]
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    red = (((hsv[:, :, 0] < 12) | (hsv[:, :, 0] > 168)) &
           (hsv[:, :, 1] > 25) & (hsv[:, :, 2] > 120))
    rows = np.where(red.sum(1) > W * 0.2)[0]
    cols = np.where(red.sum(0) > H * 0.2)[0]
    y0, y1 = (int(rows.min()), int(rows.max())) if rows.size else (0, H)
    x0, x1 = (int(cols.min()), int(cols.max())) if cols.size else (0, W)
    return y0, y1, x0, x1


def detect_lanes(mask, y0, y1, distance=70):
    """Baseline tiap lead = puncak proyeksi mask per-baris di region EKG.
    (fallback bila cal-pulse detector tak tersedia)"""
    band = mask[y0:y1].sum(1).astype(np.float32)
    sm = np.convolve(band, np.ones(7) / 7, 'same')
    pk, _ = find_peaks(sm, distance=distance,
                       prominence=sm.max() * 0.12, height=sm.max() * 0.30)
    return [int(y0 + p) for p in pk]


def _calpulse_peaks(bgr):
    """Posisi-y puncak pulsa-kalibrasi (baseline aktual) dari gambar ASLI."""
    import sys
    pp = os.path.join(os.path.dirname(_HERE_DIR), 'input', 'parsers')
    if pp not in sys.path:
        sys.path.insert(0, pp)
    try:
        import layout_detector as LD
    except Exception:
        return None
    h, w = bgr.shape[:2]
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    binary = (gray < 140).astype(np.uint8) * 255
    g = LD.grid_mask(bgr)
    rowpink = g.sum(1) / 255.0
    gr = np.where(rowpink > 0.15 * rowpink.max())[0]
    if len(gr) == 0:
        return None
    ys, ye = int(gr[0]), int(gr[-1]) + 1
    lw = max(3, int(w * 0.05))
    prof = binary[ys:ye, :lw].sum(1).astype(float) / (lw * 255.0)
    prof = np.convolve(prof, np.ones(5) / 5, 'same')
    pk, _ = find_peaks(prof, distance=110, prominence=prof.max() * 0.18)
    return [int(p + ys) for p in pk]


def pdf_label_positions(pdf_path, dpi=254):
    """Posisi-y label lead dari TEKS PDF (urutan device, tertelusur).
    return list (name, y_px) terurut, atau None."""
    try:
        import fitz
    except Exception:
        return None
    zoom = dpi / 72.0
    leadnames = {'I', 'II', 'III', 'aVR', 'aVL', 'aVF',
                 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'}
    pos = {}
    for b in fitz.open(pdf_path)[0].get_text('dict')['blocks']:
        for l in b.get('lines', []):
            for s in l['spans']:
                t = s['text'].strip()
                if t in leadnames and t not in pos:
                    pos[t] = (s['bbox'][1] + s['bbox'][3]) / 2 * zoom
    if len(pos) < 8:
        return None
    return sorted(pos.items(), key=lambda kv: kv[1])


def _align_cost(T, L, offset):
    return float(np.sum(np.abs(np.array(T) - np.array(L) - offset)))


def assign_names_by_labels(traces, labels, tol=45):
    """
    Cocokkan trace (baseline aktual) ke NAMA lead via posisi label PDF.
    ROBUST: label punya OFFSET ~konstan dari trace; sebagian trace bisa PALSU
    (teks header/border) & sebagian lead bisa tak terdeteksi.
    RANSAC: untuk tiap pasangan (label, trace) jadikan jangkar offset, cocokkan
    SEMUA label ke trace terdekat dalam toleransi; pilih offset dgn match
    terbanyak (error terkecil). Trace tak ter-match = PALSU (dibuang).
    return (dict{name:y}, missing_list).
    """
    T = sorted(int(t) for t in traces)
    L = [y for _, y in labels]
    Ln = [n for n, _ in labels]
    if not T or not L:
        return {}, list(Ln)

    best = None
    for lj in L:                       # jangkar offset dari tiap label
        for ti in T:
            off = ti - lj
            assign = {}
            used = set()
            err = 0.0
            nmatch = 0
            for j, ly in enumerate(L):
                target = ly + off
                cand = [(abs(t - target), t) for t in T if t not in used]
                if cand:
                    dmin, tbest = min(cand)
                    if dmin <= tol:
                        assign[Ln[j]] = tbest; used.add(tbest)
                        err += dmin; nmatch += 1
            score = (nmatch, -err)     # match terbanyak, lalu error terkecil
            if best is None or score > best[0]:
                best = (score, dict(assign))
    assign = best[1]
    missing = [n for n in Ln if n not in assign]
    return assign, missing


def detect_lanes_calmask(mask, y0, y1, x0, px_per_mm):
    """
    Deteksi baseline tiap lead dari PULSA KALIBRASI di MASK (U-Net kini dilatih
    untuk men-segmentasinya). Tiap pulsa ⊓ = 1 komponen di margin kiri; kaki
    bawahnya = baseline. Cara paling bersih & defensibel: penanda fisik 1 mV.
    Mengembalikan daftar baseline-y terurut, atau None bila gagal.
    """
    h = int(1.0 * px_per_mm * 10)            # tinggi pulsa ~1 mV = 10 mm
    xs0 = max(0, x0 - int(2 * px_per_mm))
    xs1 = x0 + int(7 * px_per_mm)
    strip = np.zeros_like(mask)
    strip[y0:y1, xs0:xs1] = mask[y0:y1, xs0:xs1]
    strip = (strip > 127).astype(np.uint8)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(strip, 8)
    bases = []
    for i in range(1, n):
        ph = stats[i, cv2.CC_STAT_HEIGHT]
        pw = stats[i, cv2.CC_STAT_WIDTH]
        area = stats[i, cv2.CC_STAT_AREA]
        # pulsa: tinggi mendekati 1 mV, lebar sempit (margin), area cukup
        if 0.55 * h <= ph <= 1.6 * h and pw <= int(8 * px_per_mm) and area > h:
            bottom = stats[i, cv2.CC_STAT_TOP] + ph     # kaki bawah = baseline
            bases.append(int(bottom))
    bases = sorted(bases)
    # gabung yang terlalu dekat (pecahan satu pulsa)
    merged = []
    for b in bases:
        if merged and b - merged[-1] < int(2 * px_per_mm):
            merged[-1] = (merged[-1] + b) // 2
        else:
            merged.append(b)
    return merged if len(merged) >= 6 else None


def _density_peaks(mask, y0, y1, x_trace=0):
    """Puncak densitas mask = baseline AKTUAL tiap trace.
    Proyeksi HANYA dari region TRACE (x >= x_trace, di kanan pulsa kalibrasi)
    supaya pulsa kalibrasi di margin kiri TIDAK bikin puncak palsu (lead I jadi
    terdeteksi di pulsa, bukan di trace). distance halus (40px) utk pisahkan
    lead limb rapat (III & aVR). Puncak ekstra disaring oleh pencocokan label."""
    band = mask[y0:y1, x_trace:].sum(1).astype(np.float32)
    sm = np.convolve(band, np.ones(5) / 5, 'same')
    pk, _ = find_peaks(sm, distance=40, prominence=sm.max() * 0.10,
                       height=sm.max() * 0.22)
    return [int(y0 + p) for p in pk]


def detect_lanes_smart(mask, y0, y1):
    """
    Deteksi 12 baseline AKTUAL dari densitas mask (akurat), lalu lengkapi lead
    yang hilang di zona transisi (V1 berada di antara aVF dan V2 — sering luput
    karena berdesakan). Khusus layout 2-blok: 6 limb (rapat) + 6 chest (renggang).
    """
    base = mask[y0:y1].sum(1).astype(np.float32)
    sm = np.convolve(base, np.ones(7) / 7, 'same')
    pk, _ = find_peaks(sm, distance=70, prominence=sm.max() * 0.12,
                       height=sm.max() * 0.30)
    pk = [int(y0 + p) for p in pk]
    if len(pk) < 6:
        return pk
    gaps = np.diff(pk)
    # pitch limb = median paruh-kecil gap (blok limb rapat); robust thd pencilan
    limb_pitch = float(np.median(sorted(gaps)[:max(2, len(gaps) // 2)]))
    # batas limb|chest = lonjakan pitch pertama (>1.6x pitch limb)
    si = next((i + 1 for i, g in enumerate(gaps) if g > 1.6 * limb_pitch), None)
    if si is None:
        return pk
    limb, chest = pk[:si], pk[si:]
    # Sisipkan V1 di tengah aVF (limb terakhir) dan V2 (chest pertama)
    if len(limb) == 6 and len(chest) == 5:
        v1 = int(round((limb[-1] + chest[0]) / 2))
        return limb + [v1] + chest
    return pk


def detect_lanes_2block(bgr):
    """
    Layout device EKG ini = 2 blok: 6 limb (rapat) + 6 chest (renggang).
    Pakai puncak pulsa-kalibrasi sebagai jangkar, pisah 2 blok via gap terbesar,
    lalu tempatkan 6 lead/ blok memakai pitch median blok (isi yang tak terdeteksi).
    """
    pk = _calpulse_peaks(bgr)
    if not pk or len(pk) < 6:
        return None
    pk = sorted(pk)
    gaps = np.diff(pk)
    # pitch limb diperkirakan dari beberapa gap terkecil (blok rapat)
    limb_pitch = float(np.median(sorted(gaps)[:max(2, len(gaps) // 2)]))
    # batas limb|chest = LONJAKAN pitch pertama (gap > 1.8x pitch limb)
    split = next((i + 1 for i, g in enumerate(gaps) if g > 1.8 * limb_pitch),
                 len(pk))
    limb, chest = pk[:split], pk[split:]
    region_bot = pk[-1] + (np.median(np.diff(chest)) if len(chest) > 1 else 300)
    out = []
    for blk, n in ((limb, 6), (chest, 6)):
        if not blk:
            continue
        pitch = float(np.median(np.diff(blk))) if len(blk) >= 2 else limb_pitch
        first = blk[0]
        for i in range(n):
            y = int(round(first + i * pitch))
            if y <= region_bot + pitch:        # jangan lewati batas bawah
                out.append(y)
    return sorted(out)


def detect_lanes_calpulse(bgr, expected=12):
    """Pakai detektor pulsa-kalibrasi brand-agnostic yang sudah teruji
    (input/parsers/layout_detector). U-Net TIDAK men-segmentasi pulsa
    kalibrasi (tak ada di data sintetik), jadi lane dideteksi dari gambar asli.
    Mengembalikan daftar baseline-y (tengah band). None bila gagal."""
    import sys
    pp = os.path.join(os.path.dirname(_HERE_DIR), 'input', 'parsers')
    if pp not in sys.path:
        sys.path.insert(0, pp)
    try:
        import layout_detector as LD
    except Exception:
        return None
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    for thr in (140, 120, 160):
        binary = (gray < thr).astype(np.uint8) * 255
        res = LD._detect_calpulse_strips(bgr, binary, expected_leads=expected)
        if res is not None and len(res.row_bands) >= 6:
            return [int((a + b) // 2) for a, b in res.row_bands]
    return None


_HERE_DIR = os.path.dirname(os.path.abspath(__file__))


def decode_lane(mask, base, half_up, half_down, x_lo, x_hi, px_mv, max_jump):
    """Pita ASIMETRIS: half_up (atas, untuk R tinggi) & half_down (bawah, untuk
    S dalam) diukur dari jarak ke lane tetangga -> lane chest yang renggang bisa
    menangkap R sampai ~3 mV tanpa terpotong, lane limb yang rapat tetap sempit."""
    H, W = mask.shape
    y_lo, y_hi = max(0, base - half_up), min(H, base + half_down)
    ys, last = [], float(base)
    for x in range(x_lo, x_hi):
        cy = _column_trace_y(mask[:, x], y_lo, y_hi, near=last,
                             max_jump=max_jump)
        if cy is not None:
            last = cy
        ys.append(cy if cy is not None else np.nan)
    ys = np.array(ys, np.float32)
    good = ~np.isnan(ys)
    if good.sum() == 0:
        return np.zeros(x_hi - x_lo, np.float32)
    idx = np.arange(len(ys))
    ys = np.interp(idx, idx[good], ys[good])
    return (base - ys) / px_mv          # mV


def digitize(pdf_path, ckpt, device, out_dir, dpi=254):
    px_per_mm = dpi / 25.4              # 254 dpi -> 10.0 px/mm
    px_per_sec = 25.0 * px_per_mm       # 25 mm/s
    px_per_mv = 10.0 * px_per_mm        # 10 mm/mV

    bgr = render_pdf(pdf_path, dpi)
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    y0, y1, x0, x1 = ecg_region(bgr)

    net = load_net(ckpt, device)
    has_offset = getattr(net, 'outc').out_channels >= 2
    if has_offset:
        mask, offmap = predict_mask_offset(net, rgb, device=device)
    else:
        mask = predict_mask(net, rgb, device=device); offmap = None

    # Baseline AKTUAL dari densitas mask
    raw = detect_lanes_smart(mask, y0, y1)
    # NAMA lead via urutan label PDF (tertelusur) — hindari salah-petakan
    # lane transisi (mis. V1 vs aVF). Lead yg labelnya tak punya trace -> missing.
    labels = pdf_label_positions(pdf_path, dpi)
    missing = []
    if labels:
        # pakai HANYA puncak densitas nyata (tanpa sisip lane fiktif)
        real = _density_peaks(mask, y0, y1, x0 + int(6.5 * px_per_mm))
        name2y, missing = assign_names_by_labels(real, labels)
        lane_method = 'pdf-label-guided'
    else:
        name2y = {LEAD_ORDER[i]: b for i, b in enumerate(raw)
                  if i < len(LEAD_ORDER)}
        lane_method = 'density'
    if len(name2y) < 2:
        raise SystemExit("Lane lead tak terdeteksi.")

    # urutkan by posisi utk hitung pita tetangga
    ordered = sorted(name2y.items(), key=lambda kv: kv[1])
    ys_sorted = [y for _, y in ordered]
    spacing = int(np.median(np.diff(ys_sorted))) if len(ys_sorted) > 1 else 150

    x_lo = x0 + int(6.5 * px_per_mm)      # mulai SETELAH pulsa kalibrasi
    x_hi = x1
    dur = (x_hi - x_lo) / px_per_sec

    leads = {}
    lane_route = {}
    n = len(ordered)
    H = mask.shape[0]

    # Decode DP/Viterbi per-lead (sederhana & andal). Pita sempit; despike.
    for i, (name, base) in enumerate(ordered):
        # Lead tepi (I paling atas / V6 bawah) pakai jarak tetangga yang ADA
        # (BUKAN 2x) supaya band tak menjangkau teks/garis header/footer.
        d_up = (base - ys_sorted[i - 1]) if i > 0 else (ys_sorted[i + 1] - base)
        d_dn = (ys_sorted[i + 1] - base) if i < n - 1 else (base - ys_sorted[i - 1])
        # 0.5x -> band bersentuhan di titik tengah (tak tumpang-tindih, tak ada
        # celah). Kompromi: minim overshoot ke tetangga & minim kliping R tinggi.
        hu = max(int(1.0 * px_per_mm), int(0.5 * d_up))
        hd = max(int(1.0 * px_per_mm), int(0.5 * d_dn))
        # Lead TERATAS tak punya tetangga di atas: R-wave bisa tinggi & sering
        # nongol di atas y0 (grid kadang terdeteksi sedikit kerendahan). Beri
        # band atas lebih lega supaya R tak terpotong; teks header di atasnya
        # SPARSE jadi DP (smoothest-path) tak nyangkut ke sana.
        if i == 0:
            hu = max(hu, int(0.55 * d_dn))
        # batasi ke REGION EKG (margin) supaya tak nangkap header/footer.
        # Untuk lead teratas, izinkan band naik di atas y0 (zona R-wave) —
        # cukup jaga jarak aman dari tepi atas halaman.
        top_ceiling = int(0.5 * px_per_mm) if i == 0 else (y0 + int(2 * px_per_mm))
        ylo = max(top_ceiling, base - hu)
        yhi = min(y1 - int(1 * px_per_mm), base + hd)
        # momentum-trace mengikuti tinta (ride-up goresan QRS) -> tangkap puncak
        # R/S yang tajam-sempit, yang smoothest-path (dp) lewati di baseline.
        # Validasi GT sintetik: momentum > dp pada Pearson (.924 vs .917) DAN
        # amplitudo (amp-err .433 vs .441), termasuk trace bersilang.
        # despike LEMBUT (thr 1.5mV, maxrun 3) supaya QRS asli tak terpangkas.
        mv = despike(momentum_trace(mask, base, ylo, yhi, x_lo, x_hi, px_per_mv),
                     win=25, thr_mv=1.5, maxrun=3)
        leads[name] = mv.tolist()
        lane_route[name] = 'momentum'
    lanes = ys_sorted

    os.makedirs(out_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    meta = {
        'source_pdf': pdf_path, 'dpi': dpi,
        'px_per_mm': px_per_mm, 'px_per_sec': px_per_sec,
        'px_per_mV': px_per_mv, 'duration_sec': dur,
        'n_lanes': len(lanes), 'lane_baselines': lanes,
        'lane_method': lane_method,
        'decode_route': lane_route,
        'missing_leads': missing,
        'ecg_region': [y0, y1, x0, x1],
    }
    with open(os.path.join(out_dir, base_name + '_signals.json'), 'w') as f:
        json.dump({'meta': meta, 'leads': leads}, f)

    _plot(leads, px_per_sec, x_hi - x_lo, base_name, out_dir, bgr, mask, lanes,
          int(spacing * 0.55), x_lo, x_hi)
    print(f"OK: {len(lanes)} lane, durasi ~{dur:.1f}s -> {out_dir}/{base_name}_*")
    return leads, meta


def _plot(leads, px_per_sec, npx, name, out_dir, bgr, mask, lanes, half,
          x_lo, x_hi):
    import matplotlib
    matplotlib.use('Agg'); import matplotlib.pyplot as plt
    # 1) overlay mask + lane di gambar
    ov = bgr.copy()
    ov[mask > 127] = (0, 0, 255)
    for b in lanes:
        cv2.line(ov, (x_lo, b), (x_hi, b), (0, 180, 0), 1)
    cv2.imwrite(os.path.join(out_dir, name + '_overlay.png'),
                cv2.resize(ov, None, fx=0.5, fy=0.5))
    # 2) sinyal decoded
    n = len(leads)
    fig, ax = plt.subplots(n, 1, figsize=(14, 1.1 * n), squeeze=False)
    t = np.arange(npx) / px_per_sec
    for i, (nm, sig) in enumerate(leads.items()):
        ax[i][0].plot(t, sig, 'k', lw=0.7)
        ax[i][0].set_ylabel(nm, fontsize=8, rotation=0, labelpad=14)
        ax[i][0].grid(alpha=.25); ax[i][0].tick_params(labelsize=6)
        ax[i][0].set_xlim(0, t[-1] if len(t) else 1)
    ax[-1][0].set_xlabel('detik')
    fig.suptitle(f'Digitalisasi EKG NYATA: {name}', fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.98))
    fig.savefig(os.path.join(out_dir, name + '_decoded.png'), dpi=120)
    plt.close(fig)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf', required=True)
    ap.add_argument('--ckpt', default='checkpoints/unet_best.pt')
    ap.add_argument('--out', default='export_test')
    args = ap.parse_args()
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    digitize(args.pdf, args.ckpt, dev, args.out)
