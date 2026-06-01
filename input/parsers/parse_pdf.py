"""
parsers/parse_pdf.py — Simple ECG PDF Parser
Extracts metadata from text layer + waveform from rendered image.
Handles 6-lead and 12-lead PDFs.
"""
import fitz  # PyMuPDF
import re
import cv2
import numpy as np
from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE

try:
    from scipy.signal import resample as _scipy_resample
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def _resample(sig, target_len):
    """Resample tanpa wajib scipy."""
    if len(sig) == target_len:
        return sig
    if _HAS_SCIPY:
        try:
            return _scipy_resample(sig, target_len)
        except Exception:
            pass
    x_old = np.linspace(0, 1, len(sig))
    x_new = np.linspace(0, 1, target_len)
    return np.interp(x_new, x_old, sig)

# ── Metadata regex patterns ───────────────────────────────────────
HR_PATTERNS = [
    r'(?:heart\s*rate|denyut\s*jantung|pulse\s*rate|pulse|hr|bpm)[^\d]*(\d{2,3})',
    r'(\d{2,3})\s*(?:bpm|dpm)',
]
NAME_PATTERNS = [
    r'(?:nama\s*pasien|patient\s*name|nama\s*/\s*name)[^\n:]*[:\|]\s*([A-Za-z\s]+?)(?:\n|$)',
]
DOB_PATTERNS = [
    r'(?:tgl\s*lahir|date\s*of\s*birth|tanggal\s*lahir|dob)[^\n:]*[:\|]\s*([^\n]+)',
]
ID_PATTERNS = [
    r'(?:no\.\s*rekam\s*medis|patient\s*id)[^\n:]*[:\|]\s*([A-Z0-9\-]+)',
    r'(?:no\.\s*pasien\s*/\s*pid)[^\n]*\s+([A-Z0-9\-]+(?:-\d+)+)',
]


def extract_metadata(text: str) -> dict:
    text_lower = text.lower()
    meta = {}
    for p in HR_PATTERNS:
        m = re.search(p, text_lower)
        if m:
            meta['heart_rate'] = int(m.group(1))
            break
    for p in NAME_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            meta['patient_name'] = m.group(1).strip()
            break
    for p in DOB_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            meta['date_of_birth'] = m.group(1).strip()
            break
    for p in ID_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            meta['patient_id'] = m.group(1).strip()
            break
    m = re.search(r'(?:rhythm|irama|interpretasi)[^\n:]*[:\|]\s*([^\n]+)',
                  text, re.IGNORECASE)
    if m:
        meta['rhythm'] = m.group(1).strip()
    return meta


def preprocess(img_bgr):
    """Binarise and remove pink grid."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    hsv  = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1   = cv2.inRange(hsv, np.array([0,  10, 130]), np.array([15, 200, 255]))
    m2   = cv2.inRange(hsv, np.array([165, 10, 130]), np.array([180, 200, 255]))
    grid = cv2.bitwise_or(m1, m2)
    pink_ratio = np.count_nonzero(grid) / (h * w)

    if pink_ratio > 0.005:
        gray_c = gray.copy()
        gray_c[grid > 0] = 255
        binary = cv2.adaptiveThreshold(gray_c, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 8)
    else:
        binary = cv2.adaptiveThreshold(gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 15, 10)
        hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w//10,10), 1))
        binary = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk))
        vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h//10,10)))
        binary = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk))
    return binary


def find_strip_rows(binary, threshold=0.003):
    """
    Find horizontal bands with signal — adaptive min_frac.
    Coba dari 0.015 turun sampai dapat jumlah strip yang masuk akal (5-12).
    """
    h, w = binary.shape
    density = np.array([np.sum(binary[y,:]) / (w*255.0) for y in range(h)])

    def _find(mf):
        bands, in_band, start = [], False, 0
        for y, d in enumerate(density):
            if not in_band and d > threshold:
                in_band, start = True, y
            elif in_band and d <= threshold:
                in_band = False
                if y - start > h * mf:
                    bands.append((start, y))
        if in_band and h - start > h * mf:
            bands.append((start, h))
        return bands

    # Coba dari longgar ke ketat; berhenti saat dapat 5-12 band
    for mf in [0.015, 0.01, 0.005, 0.025]:
        bands = _find(mf)
        if 5 <= len(bands) <= 13:
            return bands
    # Fallback: kembalikan yang paling banyak
    best = []
    for mf in [0.005, 0.01, 0.015, 0.025]:
        b = _find(mf)
        if len(b) > len(best):
            best = b
    return best


def extract_signal(strip_binary, target_samples):
    """Extract signal from one strip in pixel space."""
    h, w = strip_binary.shape
    if h < 5 or w < 5:
        return np.zeros(target_samples)
    sig = []
    for col in range(w):
        px = np.where(strip_binary[:, col] > 0)[0]
        sig.append(float(np.mean(px)) if len(px) > 0 else (sig[-1] if sig else h/2))
    sig = np.array(sig, dtype=float)
    sig = h - sig
    sig -= np.median(sig)
    if len(sig) > 10 and target_samples != len(sig):
        sig = _resample(sig, target_samples)
    return sig


def px_to_mv(signals_px: dict, target_std_mv=0.35) -> dict:
    """Global normalisation preserving relative ratios."""
    all_px = np.concatenate(list(signals_px.values()))
    gstd   = float(np.std(all_px))
    scale  = target_std_mv / gstd if gstd > 1e-6 else 1.0
    return {n: sig * scale for n, sig in signals_px.items()}


def parse_pdf(file_path: str, vendor: str = "PDF Report") -> UniversalECG:
    doc  = fitz.open(file_path)
    page = doc[0]
    text = page.get_text()
    meta = extract_metadata(text)
    print(f"  Metadata ditemukan: {meta}")

    # Render page to image
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat)
    img = np.frombuffer(pix.tobytes("png"), dtype=np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_COLOR)
    doc.close()

    from parsers.parse_image import _parse_image_array

    tl = text.lower()
    expected_leads = None
    
    if "medicore"   in tl: 
        vendor_det = "MediCore ECG-6L"
        expected_leads = 6
    elif "cardiolite" in tl: 
        vendor_det = "CardioLite Portable"
        if "6-lead" in tl or "6 lead" in tl:
            expected_leads = 6
    elif "heartscan"  in tl: 
        vendor_det = "HeartScan Pro"
        expected_leads = 12
    else:                    
        vendor_det = vendor

    # Delegate to image parser which has superior column detection
    img_ecg = _parse_image_array(img, sampling_rate=500, vendor=vendor_det, num_leads=expected_leads, source_name=file_path)

    # Merge metadata (keep the one extracted from PDF text)
    img_ecg.metadata.patient_id = meta.get('patient_id', 'unknown')
    img_ecg.metadata.age = meta.get('age')
    img_ecg.metadata.sex = meta.get('sex')
    img_ecg.metadata.report = meta.get('rhythm')
    img_ecg.input_format = "pdf"

    notes_parts = []
    if 'heart_rate' in meta: notes_parts.append(f"HR={meta['heart_rate']}bpm")
    if 'rhythm'     in meta: notes_parts.append(f"Rhythm={meta['rhythm']}")
    if 'patient_name' in meta: notes_parts.append(f"Name={meta['patient_name']}")
    if vendor_det != "PDF Report": notes_parts.append(f"Vendor={vendor_det}")

    if notes_parts:
        img_ecg.notes = " | ".join(notes_parts)

    return img_ecg


if __name__ == "__main__":
    import os
    pdfs = [
        'sample_inputs/vendor_medicore_6L.pdf',
        'sample_inputs/vendor_cardiolite_portable.pdf',
        'sample_inputs/vendor_heartscan_pro.pdf',
    ]
    for path in pdfs:
        if not os.path.exists(path):
            print(f"Skip: {path}"); continue
        print(f"\n--- {path}")
        try:
            r = parse_pdf(path)
            print(f"  Vendor   : {r.device_vendor}")
            print(f"  Leads    : {list(r.leads.keys())}")
            print(f"  Num leads: {r.num_leads}")
            print(f"  Notes    : {r.notes}")
        except Exception as e:
            import traceback; traceback.print_exc()
    print("\n[DONE]")
