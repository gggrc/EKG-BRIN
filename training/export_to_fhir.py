"""
training/export_to_fhir.py — Rakit FHIR Bundle dari hasil digitalisasi Export.

Arsitektur defensibel:
  - WAVEFORM (Observation.valueSampledData) : sinyal hasil digitalisasi U-Net
  - ANGKA KLINIS (HR, PR, QRS, QT/QTc, RV5/SV1, Dx) : dari TEKS PDF device
    (pengukuran resmi pabrikan) — bukan hasil re-measure yang bisa bias
  - KONSISTENSI : HR digital vs cetak dicantumkan sebagai catatan mutu
  - LEAD V1 : ditandai low-confidence (lajur transisi rapat, R-V2 overlap)

Memakai output/fhir_converter.to_fhir_bundle (+ tambahan Observation pengukuran).
"""

import os
import sys
import json
import glob

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), 'output'))
import fhir_converter as FC  # noqa: E402
from validate_medical import parse_printed, estimate_hr  # noqa: E402
from lead_quality import lead_quality_flags  # noqa: E402


def build_ecg_analysis(pdf_path, sig_json):
    d = json.load(open(sig_json))
    leads = d['leads']
    meta = d['meta']
    fs = meta['px_per_sec']                 # Hz efektif (250)
    printed = parse_printed(pdf_path)

    # HR digital (cross-check) dari lead jelas
    hr_d = None
    for k in ('II', 'V2', 'I'):
        if k in leads:
            hr_d = estimate_hr(leads[k], fs)
            if hr_d:
                break

    pid = None
    import re
    t = __import__('fitz').open(pdf_path)[0].get_text()
    mid = re.search(r'ID\s*:?\s*(\w+)', t)
    pid = mid.group(1) if mid else os.path.basename(pdf_path)[:8]
    sex = ('male' if 'Male' in t else 'female' if 'Female' in t else 'unknown')

    ecg = {
        'leads': {k: v for k, v in leads.items()},
        'sampling_rate': int(fs),
        'num_leads': len(leads),
        'device_vendor': 'ECG REPORT device (PDF export)',
        'timestamp': None,
        'metadata': {'patient_id': pid, 'sex': sex},
    }
    # catatan mutu + flag V1
    notes = []
    if printed['HR'] and hr_d:
        notes.append(f"Validasi HR: digital {hr_d:.0f} bpm vs cetak "
                     f"{printed['HR']} bpm (selisih {abs(printed['HR']-hr_d):.0f}).")
    # Flag mutu OTOMATIS (konsistensi antar-lead), bukan hardcode
    low_set, qinfo = lead_quality_flags(leads, fs)
    lc = sorted(low_set)
    if lc:
        notes.append("Lead low-confidence (auto-QC konsistensi ritme antar-lead): "
                     + ", ".join(lc) + " — gunakan nilai cetak device.")

    concl = printed['Dx'] or ''
    if notes:
        concl = (concl + " | " + " ".join(notes)).strip(" |")

    analysis = {
        'heart_rate_bpm': printed['HR'] or (round(hr_d) if hr_d else None),
        'conclusion': concl,
        'labels': [],
        'printed': printed,           # disematkan utk Observation pengukuran
        'low_conf_leads': lc,
        'quality': qinfo,
    }
    return ecg, analysis


def _measurement_obs(printed, subject_ref, eff):
    """Observation tambahan utk pengukuran tercetak device (LOINC/teks)."""
    out = []
    M = [('PR_ms', 'PR interval', 'ms', printed.get('PR_ms')),
         ('QRS_ms', 'QRS duration', 'ms', printed.get('QRS_ms')),
         ('QT_ms', 'QT interval', 'ms', printed.get('QT_ms')),
         ('QTc_ms', 'QTc interval', 'ms', printed.get('QTc_ms')),
         ('RV5_mV', 'RV5 amplitude', 'mV', printed.get('RV5_mV')),
         ('SV1_mV', 'SV1 amplitude', 'mV', printed.get('SV1_mV'))]
    for key, disp, unit, val in M:
        if val is None:
            continue
        out.append({
            'resourceType': 'Observation', 'status': 'final',
            'category': [{'coding': [{'system': 'http://terminology.hl7.org/'
                          'CodeSystem/observation-category', 'code': 'procedure'}]}],
            'code': {'text': f'{disp} (device-printed)'},
            'subject': {'reference': subject_ref},
            'effectiveDateTime': eff,
            'valueQuantity': {'value': val, 'unit': unit},
            'note': [{'text': 'Sumber: pengukuran tercetak device (teks PDF).'}],
        })
    return out


def convert(pdf_path, sig_json, out_dir):
    from datetime import datetime
    ecg, analysis = build_ecg_analysis(pdf_path, sig_json)
    bundle = FC.to_fhir_bundle(ecg, analysis)
    # sematkan Observation pengukuran tercetak
    subj = next((e['fullUrl'] for e in bundle['entry']
                 if e['resource']['resourceType'] == 'Patient'), None)
    eff = datetime.now().isoformat()
    for obs in _measurement_obs(analysis['printed'], subj, eff):
        bundle['entry'].append(FC._entry(obs, FC._uid('obs-meas')))
    # Tandai Observation lead low-confidence (dataAbsentReason-style note)
    low = set(analysis.get('low_conf_leads', []))
    for e in bundle['entry']:
        r = e['resource']
        if r.get('resourceType') == 'Observation' and 'valueSampledData' in r:
            nm = (r.get('code', {}).get('coding', [{}])[0].get('display')
                  or r.get('code', {}).get('text', ''))
            if any(nm == ln or nm.endswith(ln) for ln in low):
                r.setdefault('note', []).append(
                    {'text': 'LOW-CONFIDENCE: auto-QC (konsistensi antar-lead). '
                     'Gunakan pengukuran tercetak device untuk lead ini.'})
                r['status'] = 'preliminary'
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    path = os.path.join(out_dir, name + '_fhir.json')
    FC.save_bundle(bundle, path)
    n_res = len(bundle['entry'])
    return path, n_res, analysis


if __name__ == '__main__':
    out = os.path.join(_HERE, 'export_test', 'fhir')
    sigs = sorted(glob.glob(os.path.join(_HERE, 'export_test', '*_signals.json')))
    print(f"Merakit FHIR untuk {len(sigs)} rekaman...\n")
    for s in sigs:
        name = os.path.basename(s).replace('_signals.json', '')
        # cari pdf padanan
        pdfs = glob.glob(os.path.join(os.path.dirname(_HERE), 'Export', '*',
                                      name + '.pdf'))
        if not pdfs:
            continue
        path, n, a = convert(pdfs[0], s, out)
        print(f"  {name:22s} -> {n:2d} resource | HR={a['heart_rate_bpm']} | "
              f"Dx={(a['printed']['Dx'] or '')[:22]}")
    print(f"\nBundle FHIR -> {out}")
