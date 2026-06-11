import json
from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE


def parse_json(file_path: str) -> UniversalECG:
    """
    Parse JSON dari alat IoT/BLE.
    Mendukung berbagai struktur JSON dari vendor berbeda.
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    leads_data = {}
    name_map = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF',
                'avr': 'aVR', 'avl': 'aVL', 'avf': 'aVF'}

    # Struktur A: {"leads": {"I": [...], ...}}
    if "leads" in data:
        raw_leads = data["leads"]
        # Coba 12 lead dulu, fallback ke 6
        for lead in LEADS_12:
            for key in [lead, name_map.get(lead, lead)]:
                if key in raw_leads:
                    leads_data[lead] = [round(float(v), 4) for v in raw_leads[key]]
                    break

    # Struktur B: {"leadI": [...], "leadII": [...]}
    elif "leadI_counts" in data or "leadI" in data:
        key_map = {
            'I':   ['leadI', 'leadI_counts', 'lead_I'],
            'II':  ['leadII', 'leadII_counts', 'lead_II'],
            'III': ['leadIII', 'leadIII_counts', 'lead_III'],
            'aVR': ['leadAVR', 'aVR', 'AVR'],
            'aVL': ['leadAVL', 'aVL', 'AVL'],
            'aVF': ['leadAVF', 'aVF', 'AVF'],
        }
        for lead, keys in key_map.items():
            for k in keys:
                if k in data:
                    leads_data[lead] = [round(float(v), 4) for v in data[k]]
                    break

    # Struktur C: {"channels": [{"name": "I", "data": [...]}]}
    elif "channels" in data:
        for ch in data["channels"]:
            name = name_map.get(ch.get("name", ""), ch.get("name", ""))
            if name in LEADS_12:
                leads_data[name] = [round(float(v), 4) for v in ch["data"]]

    if not leads_data:
        raise ValueError(f"Struktur JSON tidak dikenali: {list(data.keys())}")

    # Auto-detect num_leads
    num_leads = 12 if any(l in leads_data for l in ['V1', 'V2', 'V3']) else 6

    fs       = int(data.get("fs", data.get("samplingFrequencyHz",
               data.get("sampling_rate", 500))))
    duration = float(data.get("duration", data.get("duration_sec", 10.0)))
    vendor   = str(data.get("device", data.get("deviceId",
               data.get("vendor", "Unknown IoT Device"))))
    patient_id = str(data.get("patientId", data.get("patient_id", "unknown")))

    all_vals = [v for s in leads_data.values() for v in s]
    y_abs    = max(abs(min(all_vals)), abs(max(all_vals))) * 1.2 if all_vals else 2.5

    return UniversalECG(
        leads         = leads_data,
        sampling_rate = fs,
        duration_sec  = duration,
        num_leads     = num_leads,
        units         = "mV",
        mv_per_mm     = STANDARD_SCALE["mv_per_mm"],
        mm_per_sec    = STANDARD_SCALE["mm_per_sec"],
        y_min         = round(-y_abs, 3),
        y_max         = round( y_abs, 3),
        input_format  = "json",
        device_vendor = vendor,
        metadata      = ECGMetadata(patient_id=patient_id),
    )


if __name__ == "__main__":
    result = parse_json('sample_inputs/vendor_iot.json')
    print(f"Vendor    : {result.device_vendor}")
    print(f"Patient   : {result.metadata.patient_id}")
    print(f"Leads     : {list(result.leads.keys())}")
    print(f"Num leads : {result.num_leads}")
    print("OK")
