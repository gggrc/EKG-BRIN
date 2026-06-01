"""
parsers/parse_image.py — ECG Image Parser (clean version)

Layout support:
  strips_6:    6 horizontal strips (1 lead per row)
  strips_12:   12 horizontal strips
  clinical:    3 rows x 4 cols (standard clinical layout)
               Row 0: I, aVR, V1, V4
               Row 1: II, aVL, V2, V5
               Row 2: III, aVF, V3, V6
               (+ optional rhythm strip row)
"""
import cv2
import numpy as np
import collections

try:
    import pytesseract
    import config
    if hasattr(config, 'TESSERACT_CMD'):
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    _HAS_OCR = True
except Exception:
    _HAS_OCR = False

# Hindari scipy/OpenBLAS yang bisa gagal load saat memori sistem terfragmentasi.
# Gunakan implementasi NumPy-only yang jauh lebih hemat memori.
try:
    from scipy.signal import resample as _scipy_resample, find_peaks as _scipy_find_peaks
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False


def resample(sig, target_len):
    """Resample signal ke target_len menggunakan np.interp (tidak butuh OpenBLAS)."""
    if len(sig) == target_len:
        return sig
    if _HAS_SCIPY:
        try:
            return _scipy_resample(sig, target_len)
        except Exception:
            pass
    # Fallback: linear interpolation via numpy
    x_old = np.linspace(0, 1, len(sig))
    x_new = np.linspace(0, 1, target_len)
    return np.interp(x_new, x_old, sig)


def find_peaks(x, distance=None, prominence=None):
    """Find peaks sederhana tanpa scipy (fallback numpy)."""
    if _HAS_SCIPY:
        try:
            kwargs = {}
            if distance is not None:
                kwargs['distance'] = distance
            if prominence is not None:
                kwargs['prominence'] = prominence
            return _scipy_find_peaks(x, **kwargs)
        except Exception:
            pass
    # Fallback: sederhana — cari local maxima
    x = np.asarray(x)
    n = len(x)
    peaks = []
    min_dist = int(distance) if distance else 1
    for i in range(1, n - 1):
        if x[i] > x[i - 1] and x[i] > x[i + 1]:
            if not peaks or (i - peaks[-1]) >= min_dist:
                peaks.append(i)
    return np.array(peaks), {}


from universal_schema import UniversalECG, ECGMetadata, LEADS_6, LEADS_12, STANDARD_SCALE

CLINICAL_LAYOUT = [
    ['I',   'aVR', 'V1', 'V4'],
    ['II',  'aVL', 'V2', 'V5'],
    ['III', 'aVF', 'V3', 'V6'],
]


def preprocess(img_bgr):
    """Binarise image, remove pink/red grid, deskew."""
    h, w = img_bgr.shape[:2]
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    # Remove pink/red grid via HSV masking
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0,  10,130]), np.array([15,200,255]))
    m2 = cv2.inRange(hsv, np.array([165,10,130]), np.array([180,200,255]))
    grid_mask = cv2.bitwise_or(m1, m2)
    pink_ratio = np.count_nonzero(grid_mask) / (h * w)

    if pink_ratio > 0.005:
        gray_clean = gray.copy()
        gray_clean[grid_mask > 0] = 255
        binary = cv2.adaptiveThreshold(
            gray_clean, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 8)
    else:
        binary = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 15, 10)
        # Remove grid lines morphologically
        hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(w//15,15), 1))
        binary = cv2.subtract(binary,
                              cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk))
        vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(h//15,15)))
        binary = cv2.subtract(binary,
                              cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk))
    return binary


def detect_strip_rows(binary, min_frac=None, threshold=0.003, expected_leads=None):
    """
    Find horizontal bands that contain signal.
    min_frac: minimum band height as fraction of image height.
              If None, auto-detected adaptively.
    """
    h, w = binary.shape
    density = np.array([np.sum(binary[y,:]) / (w*255.0) for y in range(h)])

    def _find_bands(mf):
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

    if min_frac is not None:
        return _find_bands(min_frac)

    # Adaptive
    target = expected_leads if expected_leads is not None else 12
    results = {}
    for mf in [0.03, 0.015, 0.01, 0.008, 0.006, 0.005, 0.002]:
        bands = _find_bands(mf)
        n = len(bands)
        if n == target:
            return bands
        results[n] = bands

    valid_counts = [k for k in results.keys() if k > 1]
    if valid_counts:
        best_k = min(valid_counts, key=lambda x: abs(x - target))
        return results[best_k]

    # Fallback to whatever we found
    if results:
        return results[max(results.keys())]
    return []


def detect_col_dividers(binary, row_bounds=None, n_expected=3):
    """Find vertical column dividers using only the ECG strip regions."""
    h, w = binary.shape

    if not row_bounds:
        return [(0, w)], False

    # Gunakan region dari baris-baris pertama (maksimal 3 baris atas)
    # Ini menghindari header/footer, dan juga menghindari rhythm strip di bawah.
    n_rows = min(3, len(row_bounds))
    mask = np.zeros((h, w), dtype=bool)
    for i in range(n_rows):
        y0, y1 = row_bounds[i]
        mask[y0:y1, :] = True
        
    masked_binary = binary.copy()
    masked_binary[~mask] = 0
    
    active_h = sum([y1 - y0 for y0, y1 in row_bounds[:n_rows]])
    if active_h == 0: active_h = h

    col_density = np.array([np.sum(masked_binary[:, x]) / (active_h*255.0) for x in range(w)])

    # Find valleys (gaps between columns)
    inv = 1 - col_density / (col_density.max() + 1e-9)
    min_dist = w // (n_expected + 2)
    peaks, _ = find_peaks(inv, distance=min_dist, prominence=0.11)
    
    # Filter: peak yang valid harus benar-benar celah kosong (densitas < 1.5%)
    valid_peaks = [p for p in peaks if col_density[p] < 0.015]

    if len(valid_peaks) >= n_expected - 1:
        dividers = sorted(valid_peaks[:n_expected-1])
        cols = [0] + [int(d) for d in dividers] + [w]
        return [(cols[i], cols[i+1]) for i in range(len(cols)-1)
                if cols[i+1] - cols[i] > w * 0.05], True

    # Jika tidak ada gap kolom yang jelas, kembalikan 1 kolom saja untuk fallback aman,
    # atau biarkan equal division tapi dengan flag false.
    cw = w // n_expected
    return [(i*cw, (i+1)*cw if i < n_expected-1 else w) for i in range(n_expected)], False


def detect_layout(binary, expected_leads=None):
    """
    Detect layout type.
    Returns: (layout_type, strip_rows, col_groups, rhythm_row)
      layout_type: 'strips_6', 'strips_12', 'clinical'
    """
    h, w = binary.shape
    strips = detect_strip_rows(binary, expected_leads=expected_leads)
    n = len(strips)

    # Filter strips terlebih dahulu (asumsi header di atas, ambil bagian grafik di bawah jika > expected)
    max_leads = expected_leads if expected_leads is not None else 12
    if n > max_leads and max_leads == 6:
        filtered_strips = strips[-max_leads:]
    else:
        filtered_strips = strips[:min(n, max_leads)]

    if n == 0:
        return 'strips_1', [(0, h)], [(0, w)], None
    if n == 1:
        layout = 'strips_1'
        print(f"  Layout: {n} horizontal strips detected")
        return layout, strips, [(0, w)], None

    print(f"  Layout: {n} horizontal strips detected")

    # Jika jumlah strips sangat banyak (>16), kemungkinan noise, batasi.
    if n > 16:
        if expected_leads == 6:
            n = 6
        elif n >= 12:
            n = 12
        else:
            n = 6
            print(f"  Layout fallback: forced 6 equal strips")

    # Jika expected_leads == 6, asumsikan ini murni strips_6. 
    # Mendeteksi 3x2 sangat rentan terhadap false-positive akibat jeda detak jantung.
    if expected_leads == 6:
        n_leads = len(filtered_strips)
        layout = f'strips_{n_leads}'
        print(f"  Layout: {layout}")
        return layout, filtered_strips, [(0, w)], None

    # Cek struktur kolom untuk layout clinical (3x4)
    col_groups, is_clinical = detect_col_dividers(binary, filtered_strips, n_expected=4)
    target_cols = 4

    if is_clinical and len(col_groups) >= 3:
        # Terdeteksi sebagai clinical layout!
        if not (3 <= len(filtered_strips) <= 4):
            print(f"  Layout fallback: forced {len(filtered_strips)} rows for clinical layout (was {n} strips)")
            if len(filtered_strips) < 3:
                sh = h // 4
                filtered_strips = [(i*sh, (i+1)*sh) for i in range(4)]
        
        main_rows = filtered_strips[:3]
        has_rhythm = len(filtered_strips) >= 4
        print(f"  Layout: clinical 3x{len(col_groups)}"
              f"{(' + rhythm') if has_rhythm else ''}")
        return 'clinical', main_rows, col_groups, filtered_strips[3] if has_rhythm else None

    # Jika bukan clinical, pastikan col_groups hanya 1 kolom utuh
    col_groups = [(0, w)]
    
    # Clinical fallback dari jumlah row (khusus 12 lead)
    if expected_leads != 6 and 3 <= len(filtered_strips) <= 4:
        # Mungkin gambar ini clinical tapi tidak terdeteksi gap vertical jelas.
        main_rows = filtered_strips[:3]
        has_rhythm = len(filtered_strips) == 4
        print(f"  Layout fallback: clinical by row count (3-4 rows)")
        col_groups, _ = detect_col_dividers(binary, filtered_strips, n_expected=4)
        return 'clinical', main_rows, col_groups, filtered_strips[3] if has_rhythm else None

    # Strips layout
    n_leads = len(filtered_strips)
    layout = f'strips_{n_leads}'
    print(f"  Layout: {layout}")
    return layout, filtered_strips, [(0, w)], None


def extract_signal(strip_binary, target_samples):
    """Extract signal from one binary strip using continuity tracking and gravity penalty."""
    # Crop out the extreme 5% edges to remove adjacent lead bleed
    h_orig, w = strip_binary.shape
    margin = max(1, int(h_orig * 0.05))
    strip_binary = strip_binary.copy()
    strip_binary[:margin, :] = 0
    strip_binary[-margin:, :] = 0
    
    h = h_orig
    sig = []
    center_y = h / 2.0
    last_y = center_y  # Start at the middle
    max_jump = h / 4.0 # Maximum allowed disconnected jump in one column
    
    for col in range(w):
        px = np.where(strip_binary[:, col] > 0)[0]
        if len(px) == 0:
            # If no pixels, gradually pull last_y towards baseline
            last_y = last_y * 0.8 + center_y * 0.2
            sig.append(last_y)
            continue
            
        # Group adjacent pixels into blobs (gap > 2 pixels means separate blobs)
        diffs = np.diff(px)
        split_idx = np.where(diffs > 2)[0] + 1
        blobs = np.split(px, split_idx)
        
        # Filter out disjoint blobs that jump too far discontinuously
        valid_blobs = [b for b in blobs if min(abs(b[0] - last_y), abs(b[-1] - last_y)) < max_jump]
        
        if not valid_blobs:
            last_y = last_y * 0.8 + center_y * 0.2
            sig.append(last_y)
            continue
            
        # Find the blob closest to last_y, but add a gravity penalty to prefer the center
        # This prevents getting stuck in the noise floor (false valleys) at the edges
        best_blob = min(valid_blobs, key=lambda b: abs(np.mean(b) - last_y) + 0.5 * abs(np.mean(b) - center_y))
        last_y = float(np.mean(best_blob))
        sig.append(last_y)
        
    sig = np.array(sig, dtype=float)
    sig = h - sig               # flip: positive = up
    sig -= np.median(sig)       # baseline correction
    
    if len(sig) > 10 and target_samples != len(sig):
        sig = resample(sig, target_samples)
    return sig


def px_to_mv_global(signals_px: dict, target_std_mv=0.35) -> dict:
    """
    Convert pixel-space signals to mV.
    Preserves relative amplitude ratios across all leads.
    Uses a single global scale factor.
    """
    all_px = np.concatenate(list(signals_px.values()))
    global_std = float(np.std(all_px))
    scale = target_std_mv / global_std if global_std > 1e-6 else 1.0
    return {name: (sig * scale) for name, sig in signals_px.items()}


def detect_calibration_scale(binary):
    """
    Mendeteksi sinyal kalibrasi (1 mV) pada margin kiri gambar.
    Mengembalikan rasio pixel per mV (float).
    """
    h, w = binary.shape
    left_margin = binary[:, :int(w * 0.05)]
    
    # Hubungkan garis-garis vertikal yang terputus (morphological close)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(10, int(h * 0.01))))
    vert_lines = cv2.morphologyEx(left_margin, cv2.MORPH_OPEN, kernel)
    
    # Cari kontur (garis vertikal)
    contours, _ = cv2.findContours(vert_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter kontur yang cukup tinggi (> 2% dari tinggi gambar)
    heights = [cv2.boundingRect(c)[3] for c in contours if cv2.boundingRect(c)[3] > h * 0.02]
    
    if heights:
        # Ambil tinggi yang paling umum (modus) untuk menghindari outlier / noise
        counter = collections.Counter(heights)
        most_common_height = counter.most_common(1)[0][0]
        return float(most_common_height)
    return None


def ocr_detect_labels(img_bgr):
    """
    Menggunakan Tesseract OCR untuk mencari kotak pembatas teks label (I, II, aVR, V1, dll).
    Mengembalikan dictionary: { 'V1': (x, y, w, h), ... }
    """
    if not _HAS_OCR:
        return {}
        
    try:
        h, w = img_bgr.shape[:2]
        # Untuk mempercepat dan mengurangi false positive, crop setengah kiri gambar (di mana label biasanya berada)
        left_half = img_bgr[:, :int(w*0.5)]
        
        # Upscale gambar 2x agar teks kecil terbaca jelas oleh OCR
        left_half = cv2.resize(left_half, (0,0), fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(left_half, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        
        # PSM 11 = Sparse text (mencari teks yang terpisah-pisah)
        data = pytesseract.image_to_data(thresh, config='--psm 11', output_type=pytesseract.Output.DICT)
        
        labels_found = {}
        valid_labels = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
        valid_lower = [l.lower() for l in valid_labels]
        
        for i in range(len(data['text'])):
            text = data['text'][i].strip()
            # Bersihkan tanda baca aneh yang sering nempel
            clean_text = ''.join(e for e in text if e.isalnum()).lower()
            
            # Cek kecocokan
            if clean_text in valid_lower:
                idx = valid_lower.index(clean_text)
                label = valid_labels[idx]
                
                # Konversi koordinat kembali ke ukuran gambar asli (/2)
                x = int(data['left'][i] / 2)
                y = int(data['top'][i] / 2)
                w_box = int(data['width'][i] / 2)
                h_box = int(data['height'][i] / 2)
                
                # Simpan koordinat label
                labels_found[label] = (x, y, w_box, h_box)
                
        return labels_found
    except Exception as e:
        print(f"OCR Error: {e}")
        return {}


def parse_image(file_path: str,
                sampling_rate: int = 500,
                vendor: str = "Scanned/Photo",
                num_leads: int = None) -> UniversalECG:

    # Normalisasi path agar backslash Windows tidak diinterpretasi sebagai
    # escape character (\v, \t, dll) oleh numpy/cv2.
    import pathlib
    file_path = str(pathlib.Path(file_path))

    # Baca image via Python open() + imdecode (aman untuk path Windows)
    with open(file_path, 'rb') as _f:
        raw = np.frombuffer(_f.read(), dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"Cannot read image: {file_path}")

    return _parse_image_array(img, sampling_rate, vendor, num_leads, file_path)

def _parse_image_array(img, sampling_rate, vendor, num_leads, source_name="Image"):
    """Internal function that parses an already decoded image array."""
    h, w = img.shape[:2]
    binary = preprocess(img)

    # 1. Deteksi Kalibrasi Absolut (Prioritas Utama)
    abs_scale_px = detect_calibration_scale(binary)
    if abs_scale_px:
        print(f"  [Calibration] Ditemukan sinyal kalibrasi absolut: 1 mV = {abs_scale_px} px")
    else:
        print("  [Calibration] Tidak ada pulse kalibrasi, menggunakan baseline global.")

    # 2. Deteksi Layout menggunakan OCR (jika diaktifkan)
    ocr_labels = {}
    try:
        import config
        if getattr(config, 'ENABLE_OCR_LAYOUT', False):
            ocr_labels = ocr_detect_labels(img)
            if ocr_labels:
                print(f"  [OCR] Ditemukan {len(ocr_labels)} label EKG di gambar.")
    except Exception:
        pass

    # 3. Deteksi Layout
    layout_type, strip_rows, col_groups, rhythm_row = detect_layout(binary, expected_leads=num_leads)

    target_samples = sampling_rate * 10  # 10 seconds total

    raw_px = {}   # lead_name -> pixel-space signal

    if layout_type == 'clinical':
        # Each column = target_samples // n_cols samples
        n_cols = len(col_groups)
        samples_per_col = target_samples // n_cols

        for row_i, (y0, y1) in enumerate(strip_rows):
            if row_i >= len(CLINICAL_LAYOUT):
                break
            for col_i, (x0, x1) in enumerate(col_groups):
                if col_i >= len(CLINICAL_LAYOUT[row_i]):
                    break
                lead_name = CLINICAL_LAYOUT[row_i][col_i]
                strip = binary[y0:y1, x0:x1]
                if strip.size == 0:
                    continue
                sig = extract_signal(strip, samples_per_col)
                # Concatenate columns: each column is a time segment
                # For clinical layout, we just use the full strip per lead
                # (each cell already contains the full lead signal for that time window)
                if lead_name not in raw_px:
                    raw_px[lead_name] = sig
                else:
                    # Extend if multiple columns have the same lead (shouldn't happen)
                    raw_px[lead_name] = np.concatenate([raw_px[lead_name], sig])

        # Resample each lead to target_samples
        for name in list(raw_px.keys()):
            sig = raw_px[name]
            if len(sig) != target_samples:
                raw_px[name] = resample(sig, target_samples)

        num_leads_out = 12

    else:
        # Strips layout: each strip is one lead
        n_strips = len(strip_rows)
        if n_strips >= 10:
            leads_order = LEADS_12
            num_leads_out = 12
        else:
            leads_order = LEADS_6
            num_leads_out = 6

        for i, (y0, y1) in enumerate(strip_rows):
            if i >= len(leads_order):
                break
            lead_name = leads_order[i]
            strip = binary[y0:y1, :]
            if strip.size == 0:
                continue
            raw_px[lead_name] = extract_signal(strip, target_samples)

    # Override num_leads if specified
    if num_leads is not None:
        num_leads_out = num_leads

    # Rhythm strip
    if rhythm_row is not None:
        y0, y1 = rhythm_row
        rhythm_strip = binary[y0:y1, :]
        if rhythm_strip.size > 0:
            raw_px['II_rhythm'] = extract_signal(rhythm_strip, target_samples)

    if not raw_px:
        raise ValueError(f"No signal extracted from image: {source_name}")

    # Convert to mV
    if abs_scale_px:
        # Konversi absolut: mV = pixel / tinggi pulse
        # Catatan: di extract_signal, baseline correction memusatkan sinyal ke 0.
        # Jadi sinyal positif = atas.
        signals_mv = {name: (sig / abs_scale_px) for name, sig in raw_px.items()}
    else:
        signals_mv = px_to_mv_global(raw_px)
        
    print(f"     [OK] Berhasil -> {len(signals_mv)} leads extracted.")

    leads_data = {n: [round(float(v), 4) for v in s]
                  for n, s in signals_mv.items()}

    all_vals = [v for s in leads_data.values() for v in s]
    y_abs = max(abs(min(all_vals)), abs(max(all_vals))) * 1.2 if all_vals else 1.0

    # Standardize dictionary key order
    ordered_leads = {}
    for standard_lead in LEADS_12 + ['II_rhythm']:
        if standard_lead in leads_data:
            ordered_leads[standard_lead] = leads_data[standard_lead]
    for n in leads_data:
        if n not in ordered_leads:
            ordered_leads[n] = leads_data[n]
    leads_data = ordered_leads

    # Tentukan jumlah lead output yang sebenarnya
    out_leads = 12 if len(leads_data) >= 12 else (6 if len(leads_data) >= 6 else len(leads_data))
    if num_leads is not None:
        out_leads = num_leads

    lead_stats = {
        name: {
            'std_mV': round(float(np.std(sig)), 4),
            'range_mV': round(float(np.ptp(sig)), 4),
            'baseline_mV': round(float(np.median(sig)), 4),
        }
        for name, sig in signals_mv.items()
    }

    all_vals = [v for s in leads_data.values() for v in s]
    y_abs = max(abs(min(all_vals)), abs(max(all_vals))) * 1.2

    return UniversalECG(
        leads         = leads_data,
        sampling_rate = sampling_rate,
        duration_sec  = 10.0,
        num_leads     = num_leads_out,
        units         = "mV",
        mv_per_mm     = STANDARD_SCALE["mv_per_mm"],
        mm_per_sec    = STANDARD_SCALE["mm_per_sec"],
        y_min         = round(-y_abs, 3),
        y_max         = round( y_abs, 3),
        input_format  = "image",
        device_vendor = vendor,
        metadata      = ECGMetadata(),
        notes         = f"Layout: {layout_type} | {num_leads_out}-lead",
        lead_amplitudes = lead_stats,
    )


if __name__ == "__main__":
    import os
    tests = [
        ('test_ecg_image.png',                  "6-strip"),
        ('sample_inputs/vendor_scan.png',        "6-strip"),
        ('sample_inputs/vendor_scan_12lead.png', "12-strip"),
    ]
    proc = 'input_processed'
    if os.path.isdir(proc):
        for f in os.listdir(proc):
            if f.lower().endswith(('.jpg','.jpeg','.png')):
                tests.append((os.path.join(proc, f), f"Processed:{f}"))
    for path, desc in tests:
        if not os.path.exists(path):
            print(f"[SKIP] {path}"); continue
        print(f"\n[TEST] {path} ({desc})")
        try:
            r = parse_image(path)
            print(f"  Leads     : {list(r.leads.keys())}")
            print(f"  Num leads : {r.num_leads}")
            print(f"  Y range   : {r.y_min} ~ {r.y_max} mV")
            if r.lead_amplitudes:
                for lead, s in r.lead_amplitudes.items():
                    print(f"    {lead:>5}: std={s['std_mV']:.4f}  range={s['range_mV']:.4f}")
        except Exception as ex:
            import traceback; traceback.print_exc()
    print("\n[DONE]")
