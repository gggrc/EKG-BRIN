"""
parsers/parse_xml.py
Parse ECG dalam format XML:
- HL7 aECG (annotated ECG) — format klinis standar
- Generic ECG XML dari berbagai vendor
"""
import xml.etree.ElementTree as ET
import numpy as np
from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE


LEAD_NAME_MAP = {
    'MDC_ECG_LEAD_I':   'I',   'I':   'I',   'lead_i':   'I',
    'MDC_ECG_LEAD_II':  'II',  'II':  'II',  'lead_ii':  'II',
    'MDC_ECG_LEAD_III': 'III', 'III': 'III', 'lead_iii': 'III',
    'MDC_ECG_LEAD_AVR': 'aVR', 'AVR': 'aVR', 'aVR': 'aVR',
    'MDC_ECG_LEAD_AVL': 'aVL', 'AVL': 'aVL', 'aVL': 'aVL',
    'MDC_ECG_LEAD_AVF': 'aVF', 'AVF': 'aVF', 'aVF': 'aVF',
    'MDC_ECG_LEAD_V1':  'V1',  'V1':  'V1',
    'MDC_ECG_LEAD_V2':  'V2',  'V2':  'V2',
    'MDC_ECG_LEAD_V3':  'V3',  'V3':  'V3',
    'MDC_ECG_LEAD_V4':  'V4',  'V4':  'V4',
    'MDC_ECG_LEAD_V5':  'V5',  'V5':  'V5',
    'MDC_ECG_LEAD_V6':  'V6',  'V6':  'V6',
}


def _strip_ns(tag: str) -> str:
    """Hapus namespace dari tag XML: {urn:...}tag → tag"""
    return tag.split('}')[-1] if '}' in tag else tag


def _find_all_tags(root, tag: str):
    """Cari semua elemen dengan tag tertentu, ignore namespace."""
    return [e for e in root.iter() if _strip_ns(e.tag) == tag]


def _parse_aecg(root) -> dict:
    """Parse HL7 aECG format."""
    leads_data = {}
    fs = 500
    meta_info = {}

    # Sampling rate
    for e in _find_all_tags(root, 'frequencyValue'):
        try:
            fs = int(float(e.get('value', 500)))
        except Exception:
            pass

    # Patient info
    for e in _find_all_tags(root, 'id'):
        ext = e.get('extension') or e.get('root', '')
        if ext:
            meta_info['patient_id'] = ext
            break

    # Waveform sequences
    for seq in _find_all_tags(root, 'sequence'):
        code_el = None
        for child in seq:
            if _strip_ns(child.tag) == 'code':
                code_el = child
                break

        if code_el is None:
            continue

        lead_code = code_el.get('code', '')
        lead_name = LEAD_NAME_MAP.get(lead_code)
        if not lead_name:
            continue

        # Ambil digit data
        for digits_el in _find_all_tags(seq, 'digits'):
            raw = digits_el.text or ''
            try:
                values = [float(x) for x in raw.split()]
                # Konversi dari µV ke mV
                gain_el = None
                for g in _find_all_tags(seq, 'scale'):
                    gain_el = g
                    break
                gain = float(gain_el.get('value', 1000)) if gain_el else 1000
                values_mv = [round(v / gain, 4) for v in values]
                leads_data[lead_name] = values_mv
            except Exception:
                continue

    return leads_data, fs, meta_info


def _parse_generic_xml(root) -> dict:
    """Parse format XML generic dari berbagai vendor."""
    leads_data = {}
    fs = 500
    meta_info = {}

    # Coba berbagai struktur
    # Struktur A: <Waveform><LeadData><LeadID>I</LeadID><WaveFormData>...</WaveFormData>
    for lead_el in _find_all_tags(root, 'LeadData'):
        name_el = None
        data_el = None
        for child in lead_el:
            tag = _strip_ns(child.tag)
            if tag in ('LeadID', 'LeadName', 'lead_name'):
                name_el = child
            if tag in ('WaveFormData', 'LeadSampleCountTotal',
                       'waveform_data', 'samples', 'data'):
                data_el = child
        if name_el is not None and data_el is not None:
            raw_name = (name_el.text or '').strip().upper()
            lead = LEAD_NAME_MAP.get(raw_name, LEAD_NAME_MAP.get(raw_name.lower()))
            if lead and data_el.text:
                try:
                    vals = [float(x) for x in data_el.text.split()]
                    leads_data[lead] = [round(v, 4) for v in vals]
                except Exception:
                    pass

    # Struktur B: <lead name="I"><values>0.1 0.2 ...</values></lead>
    if not leads_data:
        for lead_el in root.iter():
            if _strip_ns(lead_el.tag).lower() in ('lead', 'channel'):
                name = (lead_el.get('name') or lead_el.get('id') or '').upper()
                lead = LEAD_NAME_MAP.get(name)
                if lead:
                    for child in lead_el:
                        if _strip_ns(child.tag).lower() in ('values', 'data', 'samples'):
                            try:
                                vals = [float(x) for x in (child.text or '').split()]
                                leads_data[lead] = [round(v, 4) for v in vals]
                            except Exception:
                                pass

    # Ambil sampling rate
    for tag in ('SampleRate', 'sampling_rate', 'SamplingFrequency', 'fs'):
        for el in _find_all_tags(root, tag):
            try:
                fs = int(float(el.text or el.get('value', 500)))
                break
            except Exception:
                pass

    # Patient metadata
    for tag in ('PatientID', 'patient_id', 'ID'):
        for el in _find_all_tags(root, tag):
            meta_info['patient_id'] = (el.text or '').strip()
            break

    return leads_data, fs, meta_info


def parse_xml(file_path: str, vendor: str = "XML Device") -> UniversalECG:
    tree = ET.parse(file_path)
    root = tree.getroot()
    root_tag = _strip_ns(root.tag).lower()

    # Deteksi format
    if 'ecg' in root_tag or 'aecg' in root_tag or \
       any('hl7' in str(root.attrib).lower() for _ in [1]):
        leads_data, fs, meta_info = _parse_aecg(root)
        fmt = "xml_aecg"
        
        # Fallback jika ternyata bukan aECG standar (misal vendor_legacy)
        if not leads_data:
            leads_data, fs, meta_info = _parse_generic_xml(root)
            fmt = "xml_generic"
    else:
        leads_data, fs, meta_info = _parse_generic_xml(root)
        fmt = "xml_generic"

    if not leads_data:
        raise ValueError(
            f"Tidak ada data lead yang bisa diekstrak dari XML: {file_path}\n"
            f"Root tag: {root_tag}, atribut: {dict(list(root.attrib.items())[:3])}"
        )

    num_leads = 12 if any(l in leads_data for l in ['V1', 'V2', 'V3']) else 6

    # Hitung jumlah sample dan durasi
    n_samples = len(next(iter(leads_data.values())))
    duration  = round(n_samples / fs, 2)

    # Resample ke 500 Hz
    if fs != 500:
        from scipy.signal import resample
        n_target = int(n_samples * 500 / fs)
        for lead in leads_data:
            arr = np.array(leads_data[lead])
            leads_data[lead] = [round(float(v), 4)
                                 for v in resample(arr, n_target)]
        duration = round(n_target / 500, 2)

    all_vals = [v for s in leads_data.values() for v in s]
    y_abs = max(abs(min(all_vals)), abs(max(all_vals))) * 1.2

    return UniversalECG(
        leads         = leads_data,
        sampling_rate = 500,
        duration_sec  = duration,
        num_leads     = num_leads,
        units         = "mV",
        mv_per_mm     = STANDARD_SCALE["mv_per_mm"],
        mm_per_sec    = STANDARD_SCALE["mm_per_sec"],
        y_min         = round(-y_abs, 3),
        y_max         = round( y_abs, 3),
        input_format  = fmt,
        device_vendor = vendor,
        metadata      = ECGMetadata(
            patient_id=meta_info.get('patient_id', 'unknown')
        ),
    )


def generate_sample_xml(output_path: str = 'sample_inputs/vendor_ecg.xml'):
    """Generate contoh XML ECG dari sinyal PTB-XL untuk testing."""
    import wfdb
    from ptbxl_metadata import get_metadata_by_ecg_id

    record   = wfdb.rdrecord('ptb-xl/records500/00000/00001_hr')
    signal   = record.p_signal
    name_map = {'AVR': 'aVR', 'AVL': 'aVL', 'AVF': 'aVF'}
    leads    = [name_map.get(n, n) for n in record.sig_name]
    meta     = get_metadata_by_ecg_id(1)

    root = ET.Element('ECGReport')
    root.set('xmlns', 'http://example.com/ecg')
    root.set('version', '1.0')

    # Header
    hdr = ET.SubElement(root, 'Header')
    ET.SubElement(hdr, 'PatientID').text    = str(meta.patient_id)
    ET.SubElement(hdr, 'Age').text          = str(meta.age or '')
    ET.SubElement(hdr, 'Sex').text          = str(meta.sex or '')
    ET.SubElement(hdr, 'Weight').text       = str(meta.weight or '')
    ET.SubElement(hdr, 'RecordingDate').text= str(meta.recording_date or '')
    ET.SubElement(hdr, 'Device').text       = str(meta.device or '')
    ET.SubElement(hdr, 'Report').text       = str(meta.report or '')
    ET.SubElement(hdr, 'SCPCodes').text     = str(meta.scp_codes or '')

    # Waveform
    wf = ET.SubElement(root, 'Waveform')
    ET.SubElement(wf, 'SampleRate').text    = '500'
    ET.SubElement(wf, 'Duration').text      = '10'
    ET.SubElement(wf, 'Units').text         = 'mV'

    for i, lead_name in enumerate(leads):
        lead_el = ET.SubElement(wf, 'lead')
        lead_el.set('name', lead_name)
        vals = signal[:, i]
        ET.SubElement(lead_el, 'values').text = ' '.join(
            f'{v:.4f}' for v in vals
        )

    tree = ET.ElementTree(root)
    ET.indent(tree, space='  ')
    tree.write(output_path, encoding='unicode', xml_declaration=True)
    print(f"  → {output_path}")


if __name__ == "__main__":
    import os
    os.makedirs('sample_inputs', exist_ok=True)
    print("Generating sample XML...")
    generate_sample_xml()
    print("\nParsing sample XML...")
    result = parse_xml('sample_inputs/vendor_ecg.xml')
    print(f"  Leads     : {list(result.leads.keys())}")
    print(f"  Num leads : {result.num_leads}")
    print(f"  Rate      : {result.sampling_rate} Hz")
    print(f"  Duration  : {result.duration_sec} sec")
    print(f"  Patient   : {result.metadata.patient_id}")
    print("✅ Parser XML berhasil!")