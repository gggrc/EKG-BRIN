"""
run_any.py — SATU PINTU UNIVERSAL (multi-format, multi-device, 6/12-lead).

Menggabungkan:
  [INPUT]  input/ecg_input_router.py  -> deteksi jenis input + ekstraksi +
           pra-pemrosesan untuk PDF / Foto / CSV / JSON / WFDB / XML
  [AI]     training/classify/ecgnet_best.pt -> klasifikasi 5 superclass
  [OUTPUT] JSON siap-FHIR (schema universal) per rekaman

Beda dengan run_ecg.py:
  - run_ecg.py  : khusus PDF device tervalidasi (pakai U-Net momentum, kualitas terbaik).
  - run_any.py  : SEMUA format & vendor (pakai router universal). Untuk file digital
                  (CSV/JSON/WFDB/XML) sinyalnya EKSAK. Untuk foto/PDF asing, kualitas
                  digitalisasi bergantung layout (brand-agnostic, best-effort).

Contoh:
    python run_any.py --input "data/ekg.csv"
    python run_any.py --input "data/rekam.json"
    python run_any.py --input "scan/foto_ekg.jpg"
    python run_any.py --folder "folder_campur"        # semua file didukung
    python run_any.py --input ekg.xml --out hasil_universal

Output (default ./hasil/): <nama>.json
"""
import os
import sys
import glob
import json
import argparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(HERE, 'input')
CLS_DIR = os.path.join(HERE, 'training', 'classify')
CLS_CKPT = os.path.join(CLS_DIR, 'ecgnet_best.pt')
CLS_NORM = os.path.join(CLS_DIR, 'norm_stats.npz')

# router & parser hidup di input/ (import relatif) -> taruh di sys.path
for p in (INPUT_DIR, os.path.join(INPUT_DIR, 'parsers')):
    if p not in sys.path:
        sys.path.insert(0, p)

LEAD_ORDER = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
              'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
CLASSES = ['NORM', 'MI', 'STTC', 'CD', 'HYP']
CLASS_DESC = {
    'NORM': 'Normal', 'MI': 'Myocardial Infarction (infark)',
    'STTC': 'ST/T Change (iskemia/repolarisasi)',
    'CD': 'Conduction Disturbance (gangguan konduksi)',
    'HYP': 'Hypertrophy (hipertrofi)',
}
SUPPORTED_EXT = {'.pdf', '.png', '.jpg', '.jpeg', '.csv', '.txt',
                 '.json', '.xml', '.hea', '.dat'}


# ----------------------------------------------------------------------------
# Klasifikasi AI (resample tiap lead -> 1000; lead hilang -> 0)
# ----------------------------------------------------------------------------
def classify(leads):
    if not (os.path.exists(CLS_CKPT) and os.path.exists(CLS_NORM)):
        return None
    import torch
    if CLS_DIR not in sys.path:
        sys.path.insert(0, CLS_DIR)
    from model import ECGNet

    X = np.zeros((12, 1000), np.float32)
    n_present = 0
    for i, nm in enumerate(LEAD_ORDER):
        s = leads.get(nm)
        if s is None or len(s) < 5:
            continue
        n_present += 1
        s = np.asarray(s, np.float32)
        X[i] = np.interp(np.linspace(0, 1, 1000),
                         np.linspace(0, 1, len(s)), s)

    st = np.load(CLS_NORM)
    X = (X - st['mu'].reshape(12, 1)) / st['sd'].reshape(12, 1)

    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    net = ECGNet().to(dev).eval()
    net.load_state_dict(torch.load(CLS_CKPT, map_location=dev)['model'])
    with torch.no_grad():
        p = torch.sigmoid(net(torch.from_numpy(X[None]).to(dev)))[0].cpu().numpy()

    probs = {c: round(float(p[j]), 3) for j, c in enumerate(CLASSES)}
    top = max(CLASSES, key=lambda c: probs[c])
    note = 'SKRINING eksperimental — bukan diagnosis final, tinjau dokter.'
    if n_present < 12:
        note += (f' CATATAN: hanya {n_present}/12 lead tersedia '
                 f'(mis. rekaman 6-lead) — akurasi klasifikasi menurun, '
                 f'terutama kondisi yang bergantung lead dada (V1-V6).')
    return {
        'method': 'ECGNet 1D-ResNet (PTB-XL, multi-label)',
        'note': note,
        'leads_used': n_present,
        'probabilities': probs,
        'positive_labels': [c for c in CLASSES if probs[c] >= 0.5],
        'top_label': top, 'top_label_desc': CLASS_DESC[top],
    }


# ----------------------------------------------------------------------------
# Pengecek mutu otomatis: hukum Einthoven/Goldberger (limb leads)
# III=II-I, aVR=-(I+II)/2, aVL=I-II/2, aVF=II-I/2. Berlaku utk 6 & 12 lead.
# RMSE besar => ekstraksi mungkin salah => flag "perlu ditinjau".
# ----------------------------------------------------------------------------
def einthoven_check(leads, tol_mv=0.10):
    need = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
    if not all(k in leads and len(leads[k]) > 5 for k in need):
        return {'status': 'skip',
                'reason': 'limb lead tak lengkap (tak bisa diperiksa)'}
    a = {k: np.asarray(leads[k], float) for k in need}
    n = min(len(v) for v in a.values())
    a = {k: v[:n] for k, v in a.items()}
    rmse = lambda x, y: float(np.sqrt(np.mean((x - y) ** 2)))
    res = {
        'III_vs_II-I':      round(rmse(a['III'], a['II'] - a['I']), 4),
        'aVR_vs_-(I+II)/2': round(rmse(a['aVR'], -(a['I'] + a['II']) / 2), 4),
        'aVL_vs_I-II/2':    round(rmse(a['aVL'], a['I'] - a['II'] / 2), 4),
        'aVF_vs_II-I/2':    round(rmse(a['aVF'], a['II'] - a['I'] / 2), 4),
    }
    worst = max(res.values())
    return {
        'status': 'OK' if worst <= tol_mv else 'REVIEW',
        'tolerance_mv': tol_mv, 'worst_rmse_mv': worst,
        'rmse_mv': res,
        'note': ('Lead turunan konsisten dgn hukum Einthoven -> ekstraksi sehat.'
                 if worst <= tol_mv else
                 'RMSE melebihi toleransi -> ekstraksi mungkin salah, '
                 'TINJAU file ini secara manual.'),
    }


# ----------------------------------------------------------------------------
# UniversalECG -> JSON siap-FHIR (schema universal v2)
# ----------------------------------------------------------------------------
def to_fhir_ready(u, src_path):
    leads = {k: [round(float(v), 4) for v in s] for k, s in u.leads.items()}
    fs = int(u.sampling_rate)
    md = u.metadata
    ai = classify(u.leads)

    # cek mutu sederhana: lead datar (Lead-Off) & kelengkapan
    flat = [k for k, s in u.leads.items()
            if float(np.std(np.asarray(s, float))) < 1e-4]
    expected = (LEAD_ORDER if u.num_leads >= 12 else LEAD_ORDER[:6])
    missing = [L for L in expected if L not in u.leads]

    rec = {
        'schema': 'ekg-brin/processed-ecg/v2-universal',
        'source_file': os.path.basename(src_path),
        'input_format': u.input_format,
        'device_vendor': u.device_vendor,
        'patient': {
            'id': md.patient_id, 'age': md.age, 'sex': md.sex,
            'report': md.report, 'device': md.device,
            'recording_date': md.recording_date,
        },
        'recording': {
            'sampling_rate_hz': fs,
            'duration_sec': round(float(u.duration_sec), 3),
            'num_leads': u.num_leads,
            'lead_count': len(u.leads),
            'units': 'mV',
            'calibration': u.calibration or {
                'gain_mm_per_mV': 1.0 / u.mv_per_mm if u.mv_per_mm else 10.0,
                'speed_mm_per_sec': u.mm_per_sec,
            },
        },
        'leads': {k: {'units': 'mV', 'signal': s} for k, s in leads.items()},
        'quality': {
            'flat_leads_possible_leadoff': flat,
            'missing_leads': missing,
            'einthoven_check': einthoven_check(u.leads),
            'notes': ('File digital (csv/json/wfdb/xml) = sinyal eksak. '
                      'Foto/PDF asing = digitalisasi best-effort (brand-agnostic).'),
        },
    }
    if ai:
        rec['ai_screening'] = ai
    return rec


def process_one(path, out_dir):
    from ecg_input_router import load_ecg
    u = load_ecg(path)
    rec = to_fhir_ready(u, path)
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    jp = os.path.join(out_dir, name + '.json')
    with open(jp, 'w', encoding='utf-8') as f:
        json.dump(rec, f, ensure_ascii=False, indent=2)
    return rec, jp


def summarize(rec, jp):
    r = rec['recording']
    print(f"\n  File     : {rec['source_file']}  (format={rec['input_format']}, "
          f"vendor={rec['device_vendor']})")
    print(f"  Sinyal   : {r['lead_count']}/{r['num_leads']} lead, "
          f"{r['sampling_rate_hz']}Hz, {r['duration_sec']}s")
    if rec['quality']['missing_leads']:
        print(f"  Lead hilang: {rec['quality']['missing_leads']}")
    if rec['quality']['flat_leads_possible_leadoff']:
        print(f"  Lead datar : {rec['quality']['flat_leads_possible_leadoff']}")
    ec = rec['quality'].get('einthoven_check', {})
    if ec.get('status') == 'OK':
        print(f"  Cek mutu   : OK (Einthoven worst RMSE {ec['worst_rmse_mv']} mV) "
              f"- ekstraksi sehat")
    elif ec.get('status') == 'REVIEW':
        print(f"  Cek mutu   : !! PERLU DITINJAU (Einthoven worst RMSE "
              f"{ec['worst_rmse_mv']} mV > {ec['tolerance_mv']}) - periksa file ini")
    ai = rec.get('ai_screening')
    if ai:
        print(f"  AI skrining: {ai['top_label']} ({ai['top_label_desc']}) "
              f"prob={ai['probabilities'][ai['top_label']]} "
              f"[pakai {ai['leads_used']}/12 lead]")
    print(f"  -> {jp}")


def main():
    ap = argparse.ArgumentParser(
        description='Universal: PDF/Foto/CSV/JSON/WFDB/XML -> sinyal + klasifikasi + JSON siap-FHIR.')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--input', help='satu file EKG (format apa saja)')
    g.add_argument('--folder', help='folder berisi banyak file (semua format)')
    ap.add_argument('--out', default=os.path.join(HERE, 'hasil'),
                    help='folder output (default ./hasil)')
    args = ap.parse_args()

    if args.input:
        files = [args.input]
    else:
        files = sorted(f for f in glob.glob(os.path.join(args.folder, '**', '*'),
                                            recursive=True)
                       if os.path.splitext(f)[1].lower() in SUPPORTED_EXT)
    if not files:
        print('Tidak ada file didukung ditemukan.'); return

    print(f"{len(files)} file -> {args.out}")
    ok = 0
    for p in files:
        if not os.path.exists(p):
            print(f"  ! tak ada: {p}"); continue
        try:
            rec, jp = process_one(p, args.out)
            summarize(rec, jp)
            ok += 1
        except Exception as e:
            print(f"  ! GAGAL {os.path.basename(p)}: {type(e).__name__}: {e}")
    print(f"\nSelesai: {ok}/{len(files)} -> {args.out}")


if __name__ == '__main__':
    main()
