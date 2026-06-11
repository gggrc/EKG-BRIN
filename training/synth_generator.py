"""
training/synth_generator.py — Generator data sintetik PTB-XL untuk U-Net segmentasi.

Ide inti (trik supervisi otomatis):
  Sinyal mV asli PTB-XL digambar dengan polyline yang SAMA ke dua kanvas:
    1) IMAGE  : kertas-EKG (grid merah) + trace hitam + degradasi
                (noise, blur, brightness, JPEG, skew, header/label, grid pudar)
    2) MASK   : trace bersih saja (biner, putih)
  Karena koordinat polyline identik, pasangan (image, mask) otomatis
  pixel-aligned -> tidak perlu anotasi manual.

Selain (image, mask), disimpan juga:
    - signal.npy  : sinyal mV ground-truth (untuk validasi SNR/Pearson/PRD)
    - meta.json   : kalibrasi (px_per_mm, px_per_mV, px_per_sec), layout,
                    kotak tiap lead, fs, daftar lead, label superclass.

Output -> training/dataset/{images,masks,signals,meta}/<id>.{png,png,npy,json}

Jalankan:
    python training/synth_generator.py --n 50            # 50 rekaman acak
    python training/synth_generator.py --n 200 --seed 7
"""

import os
import io
import json
import math
import argparse
import random

import numpy as np
import cv2

try:
    import wfdb
except ImportError:
    raise SystemExit("wfdb belum terpasang. Jalankan: pip install wfdb")

# ----------------------------------------------------------------------------
# Lokasi dataset PTB-XL (folder bersarang)
# ----------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)  # EKG-BRIN/
PTBXL_DIR = os.path.join(
    _ROOT,
    "ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3",
    "ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3",
)
DB_CSV = os.path.join(PTBXL_DIR, "ptbxl_database.csv")
SCP_CSV = os.path.join(PTBXL_DIR, "scp_statements.csv")

OUT_DIR = os.path.join(_HERE, "dataset")

# Urutan lead standar PTB-XL
PTBXL_LEADS = ['I', 'II', 'III', 'AVR', 'AVL', 'AVF',
               'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# Tata letak yang ditiru dari input nyata
CLINICAL_3x4 = [['I', 'AVR', 'V1', 'V4'],
                ['II', 'AVL', 'V2', 'V5'],
                ['III', 'AVF', 'V3', 'V6']]
SEPARATED_4x3 = [['I', 'II', 'III'],
                 ['AVR', 'AVL', 'AVF'],
                 ['V1', 'V2', 'V3'],
                 ['V4', 'V5', 'V6']]

# Pemetaan SCP -> superclass (untuk label klasifikasi, opsional)
SUPERCLASS = {
    'NORM': 'NORM',
    'IMI': 'MI', 'AMI': 'MI', 'LMI': 'MI', 'PMI': 'MI', 'ASMI': 'MI',
    'ILMI': 'MI', 'INJAS': 'MI', 'INJAL': 'MI', 'INJIN': 'MI', 'INJLA': 'MI',
    'IPLMI': 'MI', 'IPMI': 'MI', 'ALMI': 'MI', 'INJIL': 'MI',
    'STTC': 'STTC', 'NST_': 'STTC', 'ISCAL': 'STTC', 'ISCIN': 'STTC',
    'ISC_': 'STTC', 'ISCAS': 'STTC', 'ISCLA': 'STTC', 'ANEUR': 'STTC',
    'EL': 'STTC', 'ISCAN': 'STTC', 'ISCIL': 'STTC', 'ISCAL': 'STTC',
    'NDT': 'STTC', 'DIG': 'STTC', 'LNGQT': 'STTC',
    'LAFB': 'CD', 'IRBBB': 'CD', 'CLBBB': 'CD', 'CRBBB': 'CD', 'ILBBB': 'CD',
    'IVCD': 'CD', 'WPW': 'CD', 'LPFB': 'CD', '_AVB': 'CD', 'IIAVB': 'CD',
    'IIIAVB': 'CD', 'LPR': 'CD',
    'LVH': 'HYP', 'RVH': 'HYP', 'LAO/LAE': 'HYP', 'RAO/RAE': 'HYP',
    'SEHYP': 'HYP', 'VCLVH': 'HYP',
}


# ----------------------------------------------------------------------------
# Pemilihan rekaman
# ----------------------------------------------------------------------------
def load_record_list(n, seed):
    """Ambil n filename_hr acak dari database PTB-XL beserta scp_codes."""
    import csv
    rows = []
    with open(DB_CSV, newline='', encoding='utf-8') as f:
        for r in csv.DictReader(f):
            rows.append((r['filename_hr'], r.get('scp_codes', '')))
    random.Random(seed).shuffle(rows)
    return rows[:n]


def superclasses_of(scp_str):
    """Ubah string scp_codes -> daftar superclass unik."""
    out = set()
    try:
        d = eval(scp_str, {"__builtins__": {}}, {})
        for code in d:
            sc = SUPERCLASS.get(code)
            if sc:
                out.add(sc)
    except Exception:
        pass
    return sorted(out) or ['UNK']


# ----------------------------------------------------------------------------
# Penggambar trace + grid
# ----------------------------------------------------------------------------
def draw_grid(img, px_per_mm):
    """Gambar grid kertas-EKG merah: minor 1 mm, mayor 5 mm."""
    h, w = img.shape[:2]
    minor = max(2, int(round(px_per_mm)))
    major = minor * 5
    c_minor = (212, 188, 188)   # BGR merah muda pudar
    c_major = (150, 120, 120)
    for x in range(0, w, minor):
        cv2.line(img, (x, 0), (x, h), c_minor, 1)
    for y in range(0, h, minor):
        cv2.line(img, (0, y), (w, y), c_minor, 1)
    for x in range(0, w, major):
        cv2.line(img, (x, 0), (x, h), c_major, 1)
    for y in range(0, h, major):
        cv2.line(img, (0, y), (w, y), c_major, 1)


def draw_cal_pulse(img, mask, x_trace, base, px_per_mm, px_per_mv, thick, rng):
    """
    Gambar pulsa kalibrasi (bentuk ⊓, 1 mV) di margin KIRI sebelum trace, pada
    image DAN mask. Dengan ini U-Net belajar men-segmentasi pulsa kalibrasi ->
    deteksi 12 lane jadi bersih & pasti dari mask (penting untuk EKG nyata).
    Pulsa ada di kiri x_trace, jadi tidak mencemari sinyal (decode mulai di x0).
    """
    h = int(px_per_mv * rng.uniform(0.95, 1.05))   # ~1 mV
    topw = int(px_per_mm * rng.uniform(3.5, 5.0))   # lebar atap ~4 mm
    foot = int(px_per_mm * 0.6)
    gap = int(px_per_mm * rng.uniform(0.4, 1.0))
    xb = x_trace - gap                               # ujung kanan pulsa
    xa = xb - topw                                   # ujung kiri atap
    if xa - foot < 1:
        return
    pts = np.array([[xa - foot, base], [xa, base], [xa, base - h],
                    [xb, base - h], [xb, base], [xb + foot, base]], np.int32)
    cv2.polylines(img, [pts], False, (20, 20, 20), thick, cv2.LINE_AA)
    cv2.polylines(mask, [pts], False, 255, thick + 1, cv2.LINE_AA)


def signal_to_points(sig_mv, x0, baseline_y, px_per_sec, px_per_mv, fs):
    """Konversi 1 lead (mV) -> array titik piksel (Nx2) untuk polyline."""
    n = len(sig_mv)
    xs = x0 + (np.arange(n) / fs) * px_per_sec
    ys = baseline_y - sig_mv * px_per_mv
    pts = np.stack([xs, ys], axis=1).astype(np.int32)
    return pts


def render_pair(p_signal, fs, layout, leads_order, cfg, rng):
    """
    Render satu rekaman -> (image_bgr, mask_u8, meta).

    layout: 'clinical', 'separated', 'strips'
    p_signal: (samples, 12) mV
    """
    px_per_mm = cfg['px_per_mm']
    px_per_sec = 25.0 * px_per_mm        # 25 mm/s
    px_per_mv = 10.0 * px_per_mm         # 10 mm/mV
    pad = int(cfg['pad_mm'] * px_per_mm)

    lead_idx = {name: i for i, name in enumerate(PTBXL_LEADS)}
    total_sec = p_signal.shape[0] / fs

    # Tentukan grid baris/kolom & potongan waktu per sel
    if layout == 'clinical':
        grid = CLINICAL_3x4
        seg_sec = total_sec / 4.0        # tiap kolom 2.5 s (montase)
    elif layout == 'separated':
        grid = SEPARATED_4x3
        seg_sec = total_sec / 3.0
    else:  # strips: 1 lead/baris, durasi penuh
        grid = [[l] for l in leads_order]
        seg_sec = total_sec

    nrows = len(grid)
    ncols = max(len(r) for r in grid)

    # Ukuran sel
    cell_w = int(seg_sec * px_per_sec) + 2 * pad
    cell_h = int(cfg['cell_mm_h'] * px_per_mm)
    W = cell_w * ncols + 2 * pad
    H = cell_h * nrows + 2 * pad

    img = np.full((H, W, 3), 255, np.uint8)
    mask = np.zeros((H, W), np.uint8)
    # Peta offset: di tiap piksel-trace simpan (baseline_lead - y) -> jarak ber-
    # tanda ke baseline lead PEMILIK piksel. Inti pemisahan trace bersilangan.
    offset = np.zeros((H, W), np.float32)
    draw_grid(img, px_per_mm)

    seg_samples = int(round(seg_sec * fs))
    lead_boxes = {}
    trace_thick = cfg['trace_thick']

    for r, row in enumerate(grid):
        for c, name in enumerate(row):
            li = lead_idx[name]
            x0 = pad + c * cell_w + pad
            baseline_y = pad + r * cell_h + cell_h // 2
            # Pilih segmen waktu sesuai tata letak:
            #  - strips   : lead penuh 10 s
            #  - clinical : kolom c = jendela waktu ke-c (montase 4x2.5 s)
            #  - separated: tiap sel = 1/3 durasi awal
            if layout == 'strips':
                gt_start, gt_len = 0, p_signal.shape[0]
            elif layout == 'clinical':
                gt_start, gt_len = c * seg_samples, seg_samples
            else:  # separated 4x3
                gt_start, gt_len = 0, seg_samples
            seg = p_signal[gt_start:gt_start + gt_len, li]

            pts = signal_to_points(seg, x0, baseline_y, px_per_sec,
                                   px_per_mv, fs)
            cv2.polylines(img, [pts], False, (20, 20, 20),
                          trace_thick, cv2.LINE_AA)
            # Mask sedikit lebih tebal -> Dice lebih mudah naik, centroid tetap akurat
            cv2.polylines(mask, [pts], False, 255,
                          trace_thick + 1, cv2.LINE_AA)
            # Isi peta offset utk piksel trace lead INI: offset = baseline - y
            tmp = np.zeros((H, W), np.uint8)
            cv2.polylines(tmp, [pts], False, 255, trace_thick + 1)
            yy, xx = np.where(tmp > 0)
            offset[yy, xx] = baseline_y - yy.astype(np.float32)
            # Pulsa kalibrasi: tiap lane utk strips; kolom-0 saja utk montase.
            if cfg.get('cal_pulse', True) and (layout == 'strips' or c == 0):
                draw_cal_pulse(img, mask, x0, baseline_y, px_per_mm,
                               px_per_mv, trace_thick, rng)
            # Label lead
            cv2.putText(img, name, (x0 + 4, baseline_y - cell_h // 2 + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 1,
                        cv2.LINE_AA)
            lead_boxes[name] = {
                'x0': int(x0), 'baseline_y': int(baseline_y),
                'seg_sec': float(seg_sec),
                'lead_idx': int(li),
                'gt_start': int(gt_start), 'gt_len': int(gt_len),
            }

    meta = {
        'layout': layout,
        'fs': int(fs),
        'leads': leads_order,
        'px_per_mm': float(px_per_mm),
        'px_per_sec': float(px_per_sec),
        'px_per_mV': float(px_per_mv),
        'pad': int(pad),
        'cell_w': int(cell_w), 'cell_h': int(cell_h),
        'lead_boxes': lead_boxes,
        'image_size': [int(W), int(H)],
    }
    return img, mask, meta, offset


# ----------------------------------------------------------------------------
# Degradasi.
#   GEOMETRIS (rotasi/skew) -> diterapkan ke image DAN mask agar tetap sejajar.
#   FOTOMETRIS (brightness/blur/noise/shading/JPEG) -> image saja.
# ----------------------------------------------------------------------------
def degrade(img, mask, rng):
    """Kerusakan realistis (fotometris saja; geometri tetap selaras meta).

    Catatan: rotasi/skew SENGAJA tidak dipakai di sini karena decode berbasis
    meta mengasumsikan geometri tegak (baseline_y & x0 tetap). Robustness
    terhadap miring ditangani di tahap deskew terpisah untuk gambar nyata.
    """
    h, w = img.shape[:2]

    # 2) Brightness / contrast
    if rng.random() < 0.8:
        alpha = rng.uniform(0.85, 1.15)
        beta = rng.uniform(-15, 15)
        img = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)

    # 3) Blur (foto tidak fokus)
    if rng.random() < 0.5:
        k = rng.choice([3, 3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)

    # 4) Gaussian noise
    if rng.random() < 0.7:
        sigma = rng.uniform(3, 12)
        noise = rng.normal(0, sigma, img.shape).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)

    # 5) Bayangan/gradien pencahayaan tidak rata
    if rng.random() < 0.4:
        grad = np.tile(np.linspace(rng.uniform(0.8, 1.0),
                                   rng.uniform(0.8, 1.0), w), (h, 1))
        gy = np.linspace(rng.uniform(0.85, 1.0), 1.0, h)[:, None]
        shade = (grad * gy)[:, :, None]
        img = np.clip(img.astype(np.float32) * shade, 0, 255).astype(np.uint8)

    # 6) Artefak JPEG
    if rng.random() < 0.6:
        q = int(rng.uniform(35, 80))
        ok, enc = cv2.imencode('.jpg', img,
                               [int(cv2.IMWRITE_JPEG_QUALITY), q])
        if ok:
            img = cv2.imdecode(enc, cv2.IMREAD_COLOR)

    return img, mask


# ----------------------------------------------------------------------------
# Pipeline utama
# ----------------------------------------------------------------------------
def ensure_dirs():
    for sub in ('images', 'masks', 'offsets', 'signals', 'meta'):
        os.makedirs(os.path.join(OUT_DIR, sub), exist_ok=True)


def generate(n, seed):
    ensure_dirs()
    rng = np.random.RandomState(seed)
    pyrng = random.Random(seed)
    records = load_record_list(n, seed)

    base_cfg = {
        'px_per_mm': 10.0,     # 10 px/mm (~254 DPI) -> 2 sampel/px, decode tajam
        'pad_mm': 6.0,
        'cell_mm_h': 32.0,
        'trace_thick': 2,
    }
    layouts = ['clinical', 'separated', 'strips']
    # bias ke 'strips' (1 lead/baris) -> di sinilah trace antar-lead PALING sering
    # bersilang (R-tinggi lead bawah menembus lead atas). Robustness silang.
    layout_w = ['clinical', 'separated', 'strips', 'strips', 'strips']

    made = 0
    for i, (fname_hr, scp) in enumerate(records):
        rec_path = os.path.join(PTBXL_DIR, fname_hr)
        try:
            rec = wfdb.rdrecord(rec_path)
        except Exception as e:
            print(f"  lewati {fname_hr}: {e}")
            continue
        sig = rec.p_signal.astype(np.float32)  # (5000, 12)
        fs = int(rec.fs)

        # AMPLITUDO: REALISTIS (cocok device Export) -> gain ringan saja. Gain
        # ekstrem (LVH 3-4mV) sebelumnya bikin DOMAIN GAP & regresi di Export,
        # jadi dibuang. Crossing tetap muncul alami dari spacing rapat di bawah.
        sig = sig * float(rng.uniform(0.9, 1.25))

        layout = pyrng.choice(layout_w)
        # Spacing DICOCOKKAN ke Export nyata: median ~18mm, pasangan limb serapat
        # ~11mm. Range 11-26mm -> model melihat crossing se-rapat Export (yg dulu
        # tak pernah dilatih di 22-32mm -> sumber residual aVL/limb). Garis ~2px
        # (tipis, seperti Export) dgn sedikit variasi.
        cfg = dict(base_cfg)
        cfg['cell_mm_h'] = float(rng.uniform(11.0, 26.0))
        cfg['trace_thick'] = int(rng.choice([2, 2, 2, 1, 3]))
        img, mask, meta, offset = render_pair(sig, fs, layout, PTBXL_LEADS, cfg, rng)
        img, mask = degrade(img, mask, rng)
        meta['superclass'] = superclasses_of(scp)
        meta['source'] = fname_hr

        rid = f"{i:05d}"
        # Gambar disimpan JPG (hemat disk ~5x, sekaligus realistis) ; mask PNG (lossless)
        cv2.imwrite(os.path.join(OUT_DIR, 'images', rid + '.jpg'), img,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 92])
        cv2.imwrite(os.path.join(OUT_DIR, 'masks', rid + '.png'), mask)
        # offset int16 (px) terkompresi (mayoritas 0 -> kecil di disk)
        np.savez_compressed(os.path.join(OUT_DIR, 'offsets', rid + '.npz'),
                            off=offset.astype(np.int16))
        np.save(os.path.join(OUT_DIR, 'signals', rid + '.npy'), sig)
        with open(os.path.join(OUT_DIR, 'meta', rid + '.json'), 'w',
                  encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        made += 1
        if made % 10 == 0:
            print(f"  {made}/{len(records)} ... terakhir: {layout} "
                  f"{img.shape[1]}x{img.shape[0]}")

    print(f"Selesai. {made} pasangan -> {OUT_DIR}")
    print("  images/  masks/  signals/  meta/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=50)
    ap.add_argument('--seed', type=int, default=42)
    args = ap.parse_args()
    if not os.path.isfile(DB_CSV):
        raise SystemExit(f"PTB-XL tidak ditemukan: {DB_CSV}")
    generate(args.n, args.seed)
