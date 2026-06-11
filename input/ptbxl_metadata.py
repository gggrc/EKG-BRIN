"""
ptbxl_metadata.py
Baca metadata pasien dari ptbxl_database.csv dan scp_statements.csv.
"""
import pandas as pd
import ast
import os
from universal_schema import ECGMetadata

_db_cache = None
_scp_cache = None


def _load_db(ptbxl_path: str = 'ptb-xl') -> pd.DataFrame:
    global _db_cache
    if _db_cache is None:
        csv_path = os.path.join(ptbxl_path, 'ptbxl_database.csv')
        df = pd.read_csv(csv_path, index_col='ecg_id')
        df.scp_codes = df.scp_codes.apply(ast.literal_eval)
        _db_cache = df
    return _db_cache


def _load_scp(ptbxl_path: str = 'ptb-xl') -> pd.DataFrame:
    global _scp_cache
    if _scp_cache is None:
        scp_path = os.path.join(ptbxl_path, 'scp_statements.csv')
        _scp_cache = pd.read_csv(scp_path, index_col=0)
    return _scp_cache


def get_metadata_by_ecg_id(ecg_id: int,
                            ptbxl_path: str = 'ptb-xl') -> ECGMetadata:
    """
    Ambil metadata satu rekaman berdasarkan ecg_id (nomor file PTB-XL).
    Contoh: ecg_id=1 untuk file 00001_hr.
    """
    db  = _load_db(ptbxl_path)
    scp = _load_scp(ptbxl_path)

    if ecg_id not in db.index:
        return ECGMetadata(patient_id=str(ecg_id))

    row = db.loc[ecg_id]

    # Ambil deskripsi diagnosis dari scp_codes
    scp_codes_dict = row.scp_codes  # {'NORM': 100.0} misalnya
    report_parts = []
    for code in scp_codes_dict:
        if code in scp.index:
            desc = scp.loc[code].get('description', code)
            report_parts.append(str(desc))
    report_text = "; ".join(report_parts) if report_parts else row.get('report', '')

    sex_map = {0: 'M', 1: 'F'}
    sex_val = row.get('sex', None)

    return ECGMetadata(
        patient_id    = str(int(row.get('patient_id', ecg_id))),
        age           = int(row.age) if pd.notna(row.get('age')) else None,
        sex           = sex_map.get(int(sex_val)) if pd.notna(sex_val) else None,
        height        = float(row.height) if pd.notna(row.get('height')) else None,
        weight        = float(row.weight) if pd.notna(row.get('weight')) else None,
        report        = str(row.get('report', report_text)).strip(),
        scp_codes     = str(list(scp_codes_dict.keys())),
        heart_axis    = str(row.get('heart_axis', '')).strip() or None,
        infarction_stadium = str(row.get('infarction_stadium1', '')).strip() or None,
        validated_by_human = bool(row.get('validated_by_human', False)),
        device        = str(row.get('device', 'Schiller AG')).strip(),
        recording_date = str(row.get('recording_date', '')).strip() or None,
    )


def get_metadata_by_filename(filename: str,
                              ptbxl_path: str = 'ptb-xl') -> ECGMetadata:
    """
    Ambil metadata dari nama file, misal '00001_hr' → ecg_id=1.
    """
    import re
    match = re.search(r'(\d{5})', os.path.basename(filename))
    if match:
        ecg_id = int(match.group(1))
        return get_metadata_by_ecg_id(ecg_id, ptbxl_path)
    return ECGMetadata()


if __name__ == "__main__":
    meta = get_metadata_by_ecg_id(1)
    print("=== Metadata ECG ID 1 ===")
    print(f"  Patient ID : {meta.patient_id}")
    print(f"  Age        : {meta.age}")
    print(f"  Sex        : {meta.sex}")
    print(f"  Height     : {meta.height} cm")
    print(f"  Weight     : {meta.weight} kg")
    print(f"  Report     : {meta.report}")
    print(f"  SCP codes  : {meta.scp_codes}")
    print(f"  Device     : {meta.device}")
    print(f"  Date       : {meta.recording_date}")