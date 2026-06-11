"""
training/process_export.py — Jalankan INPUT + PROSES untuk semua PDF Export,
lalu tulis output BERSIH & TERSTRUKTUR yang gampang dipetakan ke FHIR oleh
orang lain (FHIR-nya tugas terpisah).

Alur: PDF -> render -> U-Net segmentasi -> deteksi 12 lane (label PDF) ->
decode DP/Viterbi -> despike -> kalibrasi (25mm/s, 10mm/mV).

Output per rekaman -> export_test/fhir_ready/<name>.json  (skema lihat README).
Tidak membuat FHIR; hanya menyediakan data numerik + nilai klinis tercetak +
flag mutu, dalam bentuk yang siap dipetakan.
"""
import os, glob, json, re
import numpy as np
import torch
import fitz

from digitize_real import digitize
from validate_medical import parse_printed, estimate_hr
from lead_quality import lead_quality_flags

HERE = os.path.dirname(os.path.abspath(__file__))
EXPORT = os.path.join(os.path.dirname(HERE), '12-lead')
OUT = os.path.join(HERE, 'export_test', 'fhir_ready')
CKPT = os.path.join(HERE, 'checkpoints', 'unet_best.pt')


def patient_info(pdf_path):
    t = fitz.open(pdf_path)[0].get_text()
    pid = re.search(r'ID\s*:?\s*(\w+)', t)
    rec = re.search(r'(\d{2}-\d{2}-\d{4}\s+\d{2}:\d{2}:\d{2})', t)
    return {
        'id': pid.group(1) if pid else os.path.basename(pdf_path)[:8],
        'sex': 'male' if 'Male' in t else 'female' if 'Female' in t else 'unknown',
        'recording_datetime': rec.group(1) if rec else None,
    }


def hr_digital(leads, fs):
    for k in ('II', 'V2', 'I', 'V5'):
        if k in leads:
            hr = estimate_hr(leads[k], fs)
            if hr and 25 < hr < 220:
                return round(hr, 1)
    return None


def build(pdf_path, leads, meta):
    fs = int(meta['px_per_sec'])
    printed = parse_printed(pdf_path)
    low, qinfo = lead_quality_flags(leads, fs)
    missing = meta.get('missing_leads', [])
    hr_d = hr_digital(leads, fs)

    lead_block = {}
    for nm, sig in leads.items():
        lead_block[nm] = {
            'units': 'mV',
            'confidence': 'low' if nm in low else 'high',
            'signal': [round(float(v), 4) for v in sig],
        }

    return {
        'schema': 'ekg-brin/processed-ecg/v1',
        'source_file': os.path.basename(pdf_path),
        'patient': patient_info(pdf_path),
        'recording': {
            'device': 'ECG REPORT device (PDF export)',
            'sampling_rate_hz': fs,
            'duration_sec': round(meta['duration_sec'], 3),
            'n_samples': len(next(iter(leads.values()))),
            'lead_count': len(leads),
            'units': 'mV',
            'calibration': {
                'px_per_mm': meta['px_per_mm'],
                'paper_speed_mm_per_sec': 25,
                'gain_mm_per_mV': 10,
            },
        },
        'leads': lead_block,
        'printed_measurements': {        # dari teks PDF device (acuan pabrikan)
            'heart_rate_bpm': printed['HR'],
            'PR_ms': printed['PR_ms'],
            'QRS_ms': printed['QRS_ms'],
            'QT_ms': printed['QT_ms'],
            'QTc_ms': printed['QTc_ms'],
            'RV5_mV': printed['RV5_mV'],
            'SV1_mV': printed['SV1_mV'],
            'diagnosis': printed['Dx'],
        },
        'quality': {
            'low_confidence_leads': sorted(low),
            'missing_leads': missing,
            'lane_detection_method': meta.get('lane_method'),
            'hr_crosscheck': {
                'digital_bpm': hr_d, 'printed_bpm': printed['HR'],
                'abs_diff_bpm': (round(abs(hr_d - printed['HR']), 1)
                                 if hr_d and printed['HR'] else None),
            },
            'notes': ('Lead low_confidence/missing: pakai nilai cetak device '
                      '(printed_measurements) atau tinjau manual.'),
        },
    }


def main():
    os.makedirs(OUT, exist_ok=True)
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    pdfs = sorted(glob.glob(os.path.join(EXPORT, '*', '*.pdf')))
    print(f"INPUT+PROSES {len(pdfs)} PDF -> output FHIR-ready\n")
    for p in pdfs:
        name = os.path.splitext(os.path.basename(p))[0]
        leads, meta = digitize(p, CKPT, dev, os.path.join(HERE, 'export_test'))
        rec = build(p, leads, meta)
        with open(os.path.join(OUT, name + '.json'), 'w', encoding='utf-8') as f:
            json.dump(rec, f, ensure_ascii=False, indent=2)
        q = rec['quality']
        print(f"  {name:22s} {rec['recording']['lead_count']} lead, "
              f"{rec['recording']['sampling_rate_hz']}Hz, "
              f"{rec['recording']['duration_sec']}s | low-conf={q['low_confidence_leads']} "
              f"| HRdiff={q['hr_crosscheck']['abs_diff_bpm']}")
    print(f"\nOutput bersih -> {OUT}")


if __name__ == '__main__':
    main()
