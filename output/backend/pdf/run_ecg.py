"""
run_ecg.py — SATU PINTU untuk memproses EKG baru.

Kasih sebuah PDF EKG (atau folder berisi PDF), skrip ini menjalankan SELURUH
pipeline dan menyimpan hasilnya:

  PDF  ->  [1] Digitalisasi U-Net (sinyal mV 12-lead)
        ->  [2] Klasifikasi AI (5 superclass: NORM/MI/STTC/CD/HYP)
        ->  [3] Ukuran klinis tercetak device (HR/PR/QRS/QT/QTc/RV5/SV1/Dx)
        ->  [4] JSON siap-FHIR  +  gambar overlay (cek visual)

Contoh pakai:
    python run_ecg.py --pdf "C:/path/ekg_baru.pdf"
    python run_ecg.py --pdf "../Export/20260604-154120/20251118-145257-0007.pdf"
    python run_ecg.py --folder "C:/folder_berisi_pdf"          # proses semua
    python run_ecg.py --pdf ekg.pdf --out hasil_saya --no-image

Output (default ke folder ./hasil/):
    hasil/<nama>.json          -> data siap FHIR + klasifikasi AI
    hasil/<nama>_overlay.png   -> output(merah) di atas input(hitam), per-lead

Catatan: klasifikasi AI = SKRINING eksperimental (dilatih PTB-XL, test
macro-AUC 0.925). Bukan diagnosis final — selalu tinjau oleh dokter.
"""
import os
import sys
import glob
import json
import argparse

import numpy as np
import cv2
import torch

# --- komponen pipeline yang sudah ada ---
from digitize_real import digitize, render_pdf
from process_export import build                      # JSON siap-FHIR
from lead_quality import lead_quality_flags

HERE = os.path.dirname(os.path.abspath(__file__))
CKPT = os.path.join(HERE, 'checkpoints', 'unet_best.pt')
CLS_CKPT = os.path.join(HERE, 'classify', 'ecgnet_best.pt')
CLS_NORM = os.path.join(HERE, 'classify', 'norm_stats.npz')
LEAD_ORDER = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
              'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
CLASSES = ['NORM', 'MI', 'STTC', 'CD', 'HYP']
CLASS_ID = {
    'NORM': 'Normal',
    'MI':   'Myocardial Infarction (infark)',
    'STTC': 'ST/T Change (iskemia/repolarisasi)',
    'CD':   'Conduction Disturbance (gangguan konduksi)',
    'HYP':  'Hypertrophy (hipertrofi)',
}


# ----------------------------------------------------------------------------
# [2] Klasifikasi AI
# ----------------------------------------------------------------------------
def classify(leads, fs):
    """leads: {nama: sinyal mV}. Kembalikan dict prob 5 superclass + ringkasan."""
    if not (os.path.exists(CLS_CKPT) and os.path.exists(CLS_NORM)):
        return None
    sys.path.insert(0, os.path.join(HERE, 'classify'))
    from model import ECGNet

    # susun (12, 1000): tiap lead di-resample ke 1000 sampel; lead hilang -> 0
    X = np.zeros((12, 1000), np.float32)
    for i, nm in enumerate(LEAD_ORDER):
        s = leads.get(nm)
        if s is None or len(s) < 5:
            continue
        s = np.asarray(s, np.float32)
        X[i] = np.interp(np.linspace(0, 1, 1000),
                         np.linspace(0, 1, len(s)), s)

    st = np.load(CLS_NORM)
    mu = st['mu'].reshape(12, 1)
    sd = st['sd'].reshape(12, 1)
    X = (X - mu) / sd

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    net = ECGNet().to(dev).eval()
    net.load_state_dict(torch.load(CLS_CKPT, map_location=dev)['model'])
    with torch.no_grad():
        p = torch.sigmoid(net(torch.from_numpy(X[None]).to(dev)))[0].cpu().numpy()

    probs = {c: round(float(p[j]), 3) for j, c in enumerate(CLASSES)}
    positive = [c for c in CLASSES if probs[c] >= 0.5]
    top = max(CLASSES, key=lambda c: probs[c])
    return {
        'method': 'ECGNet 1D-ResNet (PTB-XL, multi-label)',
        'note': 'SKRINING eksperimental — bukan diagnosis final, tinjau dokter.',
        'probabilities': probs,
        'positive_labels': positive,          # prob >= 0.5
        'top_label': top,
        'top_label_desc': CLASS_ID[top],
    }


# ----------------------------------------------------------------------------
# [4] Gambar overlay per-lead (output merah di atas input hitam)
# ----------------------------------------------------------------------------
def make_overlay(pdf_path, leads, meta, out_png):
    pmv = meta['px_per_mV']; bases = meta['lane_baselines']; n = len(bases)
    y0, y1, x0, x1 = meta['ecg_region']
    x_lo = x0 + int(6.5 * meta['px_per_mm'])
    bgr = render_pdf(pdf_path, meta['dpi'])
    low, _ = lead_quality_flags(leads, meta['px_per_sec'])
    names = list(leads.keys()); panels = []
    for i, nm in enumerate(names):
        b = bases[i]
        d_up = (b - bases[i - 1]) if i > 0 else 150
        d_dn = (bases[i + 1] - b) if i < n - 1 else 150
        ytop = max(0, b - int(0.62 * d_up))
        ybot = min(bgr.shape[0], b + int(0.62 * d_dn))
        crop = bgr[ytop:ybot, x_lo:x1].copy()
        sig = np.asarray(leads[nm], np.float32)
        ys = np.clip((b - sig * pmv) - ytop, 0, crop.shape[0] - 1)
        col = (0, 140, 0) if nm in low else (0, 0, 255)
        cv2.polylines(crop, [np.stack([np.arange(len(sig)), ys], 1).astype(np.int32)],
                      False, col, 2, cv2.LINE_AA)
        crop = cv2.resize(crop, (crop.shape[1], max(crop.shape[0], 100) * 2))
        tag = nm + (' (low-conf)' if nm in low else '')
        cv2.putText(crop, tag, (4, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                    (0, 120, 0) if nm in low else (180, 0, 0), 2)
        panels.append(crop)
    w = min(p.shape[1] for p in panels)
    panels = [cv2.resize(p, (w, p.shape[0])) for p in panels]
    sep = np.full((3, w, 3), (80, 80, 80), np.uint8)
    st = []
    for p in panels:
        st += [p, sep]
    cv2.imwrite(out_png, np.vstack(st))


# ----------------------------------------------------------------------------
# Proses 1 PDF
# ----------------------------------------------------------------------------
def process_one(pdf_path, out_dir, dev, make_img=True):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    # [1] digitalisasi (juga menulis <name>_signals.json di export_test)
    leads, meta = digitize(pdf_path, CKPT, dev,
                           os.path.join(HERE, 'export_test'))
    # [3]+[4 data] JSON siap-FHIR (patient + sinyal + ukuran cetak + mutu)
    rec = build(pdf_path, leads, meta)
    # [2] klasifikasi AI
    ai = classify(leads, int(meta['px_per_sec']))
    if ai:
        rec['ai_screening'] = ai

    os.makedirs(out_dir, exist_ok=True)
    json_path = os.path.join(out_dir, name + '.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)

    img_path = None
    if make_img:
        img_path = os.path.join(out_dir, name + '_overlay.png')
        make_overlay(pdf_path, leads, meta, img_path)

    return rec, json_path, img_path


def summarize(rec, json_path, img_path):
    q = rec['quality']; r = rec['recording']
    print(f"\n  File          : {rec['source_file']}")
    print(f"  Pasien        : ID={rec['patient']['id']}  "
          f"sex={rec['patient']['sex']}")
    print(f"  Sinyal        : {r['lead_count']} lead, {r['sampling_rate_hz']}Hz, "
          f"{r['duration_sec']}s")
    pm = rec['printed_measurements']
    print(f"  Device cetak  : HR={pm['heart_rate_bpm']}  Dx='{pm['diagnosis']}'")
    hc = q['hr_crosscheck']
    print(f"  HR cek-silang : digital={hc['digital_bpm']}  device={hc['printed_bpm']}"
          f"  beda={hc['abs_diff_bpm']} bpm")
    if q['low_confidence_leads']:
        print(f"  Low-conf lead : {q['low_confidence_leads']}")
    if q['missing_leads']:
        print(f"  Lead hilang   : {q['missing_leads']}")
    ai = rec.get('ai_screening')
    if ai:
        top = ai['top_label']
        print(f"  AI skrining   : {top} ({ai['top_label_desc']})  "
              f"prob={ai['probabilities'][top]}")
        print(f"                  semua: {ai['probabilities']}")
        if ai['positive_labels']:
            print(f"                  label positif (>=0.5): {ai['positive_labels']}")
    print(f"  -> JSON       : {json_path}")
    if img_path:
        print(f"  -> Gambar     : {img_path}")


def main():
    ap = argparse.ArgumentParser(
        description='Proses EKG baru: PDF -> sinyal mV + klasifikasi AI + JSON siap-FHIR + gambar.')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--pdf', help='satu file PDF EKG')
    g.add_argument('--folder', help='folder berisi banyak PDF (diproses semua)')
    ap.add_argument('--out', default=os.path.join(HERE, 'hasil'),
                    help='folder output (default: ./hasil)')
    ap.add_argument('--no-image', action='store_true',
                    help='lewati pembuatan gambar overlay (lebih cepat)')
    args = ap.parse_args()

    if args.pdf:
        pdfs = [args.pdf]
    else:
        pdfs = sorted(glob.glob(os.path.join(args.folder, '**', '*.pdf'),
                                recursive=True))
    if not pdfs:
        print('Tidak ada PDF ditemukan.'); return

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"Device: {dev} | {len(pdfs)} PDF -> {args.out}")
    ok = 0
    for p in pdfs:
        if not os.path.exists(p):
            print(f"  ! lewati (tak ada): {p}"); continue
        try:
            rec, jp, ip = process_one(p, args.out, dev,
                                      make_img=not args.no_image)
            summarize(rec, jp, ip)
            ok += 1
        except Exception as e:
            print(f"  ! GAGAL {os.path.basename(p)}: {e}")
    print(f"\nSelesai: {ok}/{len(pdfs)} berhasil -> {args.out}")


if __name__ == '__main__':
    main()
