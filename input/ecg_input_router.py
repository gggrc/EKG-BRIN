import os
from universal_schema import UniversalECG


def detect_format(file_path: str) -> str:
    """Deteksi format berdasarkan ekstensi file."""
    ext = os.path.splitext(file_path)[1].lower()

    format_map = {
        '.hea': 'wfdb',
        '.dat': 'wfdb',
        '.csv': 'csv',
        '.txt': 'csv',
        '.xml': 'xml',
        '.pdf': 'pdf',
        '.png': 'image',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.mat': 'mat',
        '.hdf5': 'hdf5',
        '.h5': 'hdf5',
        '.json': 'json',
        '.edf': 'edf',
    }

    if ext == '':
        # Mungkin path WFDB tanpa ekstensi (sudah di-strip .hea oleh caller)
        if os.path.exists(file_path + '.hea'):
            detected = 'wfdb'
            print(f"  Format terdeteksi: wfdb (record tanpa ekstensi, .hea ditemukan)")
            return detected

    detected = format_map.get(ext, 'unknown')
    print(f"  Format terdeteksi: {detected} (dari ekstensi '{ext}')")
    return detected


def load_ecg(file_path: str, 
             sampling_rate: int = 500,
             use_6_lead: bool = True,
             vendor: str = "Unknown",
             expected_leads: int = None) -> UniversalECG:
    """
    Router utama. Input: path file apapun.
    Output: UniversalECG yang siap dikirim ke FHIR converter.
    """
    fmt = detect_format(file_path)
    
    if fmt == 'wfdb':
        from parsers.parse_wfdb import parse_wfdb
        path_no_ext = os.path.splitext(file_path)[0]
        # Auto-detect: kalau ada 12 lead di file, ambil 12. Kalau tidak, ambil 6.
        return parse_wfdb(path_no_ext, use_6_lead=False)
        # parse_wfdb akan otomatis return hanya lead yang tersedia
    
    elif fmt == 'csv':
        from parsers.parse_csv import parse_csv
        return parse_csv(file_path, sampling_rate=sampling_rate, vendor=vendor)
    
    elif fmt == 'image':
        from parsers.parse_image import parse_image
        return parse_image(file_path, num_leads=expected_leads, sampling_rate=sampling_rate, vendor=vendor)
        # num_leads=None → auto-detect otomatis
    
    elif fmt == 'json':
        from parsers.parse_json import parse_json
        return parse_json(file_path)

    elif fmt == 'pdf':
        from parsers.parse_pdf import parse_pdf
        return parse_pdf(file_path, vendor=vendor)
    
    elif fmt == 'xml':
        from parsers.parse_xml import parse_xml
        return parse_xml(file_path, vendor=vendor)
    
    else:
        raise ValueError(f"Format '{fmt}' belum didukung. File: {file_path}")


# ---- TEST SEMUA FORMAT ----
if __name__ == "__main__":
    print("=" * 50)
    print("TEST ROUTER — semua format")
    print("=" * 50)
    
    test_files = [
        ('ptb-xl/records500/00000/00001_hr.hea',         "PhysioNet WFDB"),
        ('sample_inputs/vendor_portable_A.csv',           "Vendor CSV A"),
        ('sample_inputs/vendor_portable_B.csv',           "Vendor CSV B"),
        ('sample_inputs/vendor_scan.png',                 "Vendor Scan"),
        ('sample_inputs/vendor_iot.json',                 "IoT Device"),
        ('sample_inputs/vendor_medicore_6L.pdf',          "MediCore"),
        ('sample_inputs/vendor_cardiolite_portable.pdf',  "CardioLite"),
        ('sample_inputs/vendor_heartscan_pro.pdf',        "HeartScan"),
    ]
    
    for file_path, vendor in test_files:
        if os.path.exists(file_path):
            print(f"\n📄 Testing: {file_path}")
            try:
                result = load_ecg(file_path, vendor=vendor)
                print(f"  ✅ Berhasil!")
                print(f"     Lead: {list(result.leads.keys())}")
                print(f"     Rate: {result.sampling_rate} Hz")
                print(f"     Durasi: {result.duration_sec} detik")
            except Exception as e:
                print(f"  ❌ Error: {e}")
        else:
            print(f"\n⏭ Skip {file_path} (file tidak ada)")
    
    print("\n" + "=" * 50)
    print("Test selesai.")