import wfdb
import numpy as np
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE
from ptbxl_metadata import get_metadata_by_filename


def parse_wfdb(file_path: str, use_6_lead: bool = False,
               ptbxl_path: str = 'ptb-xl') -> UniversalECG:
    record     = wfdb.rdrecord(file_path)
    signal     = record.p_signal
    name_map   = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF',
                  'avr': 'aVR', 'avl': 'aVL', 'avf': 'aVF'}
    norm_names = [name_map.get(n, n) for n in record.sig_name]
    fs         = record.fs

    # Auto-detect 6 vs 12
    available = set(norm_names)
    if use_6_lead or not (available >= set(LEADS_12)):
        target_leads = LEADS_6
    else:
        target_leads = LEADS_12

    leads_data = {}
    for lead in target_leads:
        if lead in norm_names:
            idx = norm_names.index(lead)
            vals = np.nan_to_num(signal[:, idx], nan=0.0)
            leads_data[lead] = [round(float(v), 4) for v in vals]
        else:
            leads_data[lead] = [0.0] * record.sig_len

    # Resample ke 500 Hz kalau perlu
    if fs != 500:
        from scipy.signal import resample
        n_target = int(record.sig_len * 500 / fs)
        for lead in leads_data:
            leads_data[lead] = [round(float(v), 4)
                                 for v in resample(leads_data[lead], n_target)]
        fs = 500

    # Hitung y range dari sinyal nyata
    all_vals = [v for sig in leads_data.values() for v in sig]
    y_min = max(-5.0, min(all_vals) * 1.2)
    y_max = min( 5.0, max(all_vals) * 1.2)

    # Metadata dari PTB-XL CSV
    try:
        meta = get_metadata_by_filename(file_path, ptbxl_path)
    except Exception:
        meta = ECGMetadata(patient_id='unknown')

    return UniversalECG(
        leads         = leads_data,
        sampling_rate = int(fs),
        duration_sec  = round(record.sig_len / fs, 2),
        num_leads     = len(target_leads),
        units         = "mV",
        mv_per_mm     = STANDARD_SCALE["mv_per_mm"],
        mm_per_sec    = STANDARD_SCALE["mm_per_sec"],
        y_min         = round(y_min, 3),
        y_max         = round(y_max, 3),
        input_format  = "wfdb",
        device_vendor = meta.device or "PTB-XL/Schiller AG",
        metadata      = meta,
        notes         = f"SCP: {meta.scp_codes} | {meta.report}"
    )


if __name__ == "__main__":
    result = parse_wfdb('ptb-xl/records500/00000/00001_hr')
    print("=== PARSER WFDB ===")
    print(f"Leads     : {list(result.leads.keys())}")
    print(f"Rate      : {result.sampling_rate} Hz")
    print(f"Y range   : {result.y_min} ~ {result.y_max} mV")
    print(f"Patient   : {result.metadata.patient_id}")
    print(f"Age/Sex   : {result.metadata.age} / {result.metadata.sex}")
    print(f"Report    : {result.metadata.report}")
    print(f"Device    : {result.metadata.device}")
    print("[OK] Berhasil!")