import pandas as pd
import numpy as np
from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE


def parse_csv(file_path: str,
              sampling_rate: int = 500,
              vendor: str = "Unknown CSV Vendor") -> UniversalECG:
    """
    Parse CSV di mana setiap kolom adalah satu lead.
    Auto-detect 6 vs 12 lead dari kolom yang tersedia.
    """
    df = pd.read_csv(file_path)

    column_aliases = {
        'I':   ['I', 'lead_I', 'LeadI', 'lead1', 'L1'],
        'II':  ['II', 'lead_II', 'LeadII', 'lead2', 'L2'],
        'III': ['III', 'lead_III', 'LeadIII', 'lead3', 'L3'],
        'aVR': ['aVR', 'AVR', 'avr', 'aVr'],
        'aVL': ['aVL', 'AVL', 'avl', 'aVl'],
        'aVF': ['aVF', 'AVF', 'avf', 'aVf'],
        'V1':  ['V1', 'v1', 'lead_V1', 'C1'],
        'V2':  ['V2', 'v2', 'lead_V2', 'C2'],
        'V3':  ['V3', 'v3', 'lead_V3', 'C3'],
        'V4':  ['V4', 'v4', 'lead_V4', 'C4'],
        'V5':  ['V5', 'v5', 'lead_V5', 'C5'],
        'V6':  ['V6', 'v6', 'lead_V6', 'C6'],
    }

    leads_data = {}
    for standard_name, aliases in column_aliases.items():
        for alias in aliases:
            if alias in df.columns:
                values = df[alias].fillna(0).tolist()
                leads_data[standard_name] = [round(float(v), 4) for v in values]
                break

    # Auto-detect num_leads
    num_leads = 12 if any(l in leads_data for l in ['V1', 'V2', 'V3']) else 6

    n_samples = len(df)
    duration  = round(n_samples / sampling_rate, 2)

    all_vals = [v for s in leads_data.values() for v in s]
    y_abs = max(abs(min(all_vals)), abs(max(all_vals))) * 1.2 if all_vals else 2.5

    return UniversalECG(
        leads         = leads_data,
        sampling_rate = sampling_rate,
        duration_sec  = duration,
        num_leads     = num_leads,
        units         = "mV",
        mv_per_mm     = STANDARD_SCALE["mv_per_mm"],
        mm_per_sec    = STANDARD_SCALE["mm_per_sec"],
        y_min         = round(-y_abs, 3),
        y_max         = round( y_abs, 3),
        input_format  = "csv",
        device_vendor = vendor,
        metadata      = ECGMetadata(),
        notes         = f"Kolom asli: {list(df.columns)[:6]}..."
    )


if __name__ == "__main__":
    result = parse_csv('sample_inputs/vendor_portable_A.csv', vendor="Vendor A")
    print(f"Leads     : {list(result.leads.keys())}")
    print(f"Num leads : {result.num_leads}")
    print(f"Duration  : {result.duration_sec} s")
    print("OK")
