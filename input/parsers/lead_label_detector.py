"""
parsers/lead_label_detector.py — Detect ECG Lead Labels

Reads lead labels (I, II, III, aVR, aVL, aVF, V1–V6) from ECG images/PDFs.

Strategy (in order of preference):
  1. PDF text layer — extract text + positions from PyMuPDF
  2. Tesseract OCR — read labels from image (if installed)
  3. Heuristic fallback — assign by layout position
"""

import cv2
import numpy as np
import re
from typing import Dict, List, Optional, Tuple

# All possible lead labels in standard forms
LEAD_NAMES_12 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
                 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# Regex patterns to match lead names in OCR text
_LEAD_PATTERNS = {
    'I':   re.compile(r'\b(?:Lead\s*)?I(?!I|V)\b', re.IGNORECASE),
    'II':  re.compile(r'\b(?:Lead\s*)?II(?!I)\b', re.IGNORECASE),
    'III': re.compile(r'\b(?:Lead\s*)?III\b', re.IGNORECASE),
    'aVR': re.compile(r'\ba?VR\b', re.IGNORECASE),
    'aVL': re.compile(r'\ba?VL\b', re.IGNORECASE),
    'aVF': re.compile(r'\ba?VF\b', re.IGNORECASE),
    'V1':  re.compile(r'\bV1\b', re.IGNORECASE),
    'V2':  re.compile(r'\bV2\b', re.IGNORECASE),
    'V3':  re.compile(r'\bV3\b', re.IGNORECASE),
    'V4':  re.compile(r'\bV4\b', re.IGNORECASE),
    'V5':  re.compile(r'\bV5\b', re.IGNORECASE),
    'V6':  re.compile(r'\bV6\b', re.IGNORECASE),
}

# Standard clinical 3×4 layout ordering
CLINICAL_3x4 = [
    ['I',   'aVR', 'V1', 'V4'],
    ['II',  'aVL', 'V2', 'V5'],
    ['III', 'aVF', 'V3', 'V6'],
]

# 4×3 separated layout ordering (common for digital/generated ECGs)
SEPARATED_4x3 = [
    ['I',   'II',  'III'],
    ['aVR', 'aVL', 'aVF'],
    ['V1',  'V2',  'V3'],
    ['V4',  'V5',  'V6'],
]

# Tesseract configuration
_TESSERACT_CMD = None
_TESSERACT_AVAILABLE = None


def _get_tesseract():
    """Lazy-init Tesseract. Returns (pytesseract module, available bool)."""
    global _TESSERACT_CMD, _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        if _TESSERACT_AVAILABLE:
            import pytesseract
            return pytesseract, True
        return None, False

    try:
        import pytesseract
        # Try common Windows paths
        import shutil, os
        exe = shutil.which('tesseract')
        if exe is None:
            for path in [
                r'C:\Program Files\Tesseract-OCR\tesseract.exe',
                r'D:\Tesseract-OCR\tesseract.exe',
                r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            ]:
                if os.path.isfile(path):
                    exe = path
                    break
        if exe:
            pytesseract.pytesseract.tesseract_cmd = exe
            _TESSERACT_CMD = exe
            # Quick sanity check
            pytesseract.get_tesseract_version()
            _TESSERACT_AVAILABLE = True
            print(f"  [OK] Tesseract OCR available: {exe}")
            return pytesseract, True
        else:
            _TESSERACT_AVAILABLE = False
            return None, False
    except Exception:
        _TESSERACT_AVAILABLE = False
        return None, False


# ── Method 1: PDF text layer ─────────────────────────────────────

def detect_labels_from_pdf(page) -> Optional[Dict[str, Tuple[float, float]]]:
    """
    Extract lead labels and their positions from a PDF page's text layer.
    Returns dict: lead_name → (x_center, y_center) in page coordinates.
    Uses PyMuPDF page object.
    """
    try:
        text_dict = page.get_text("dict")
    except Exception:
        return None

    labels: Dict[str, Tuple[float, float]] = {}

    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:  # text block
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                bbox = span.get("bbox", [0, 0, 0, 0])
                cx = (bbox[0] + bbox[2]) / 2
                cy = (bbox[1] + bbox[3]) / 2

                for lead_name, pattern in _LEAD_PATTERNS.items():
                    if lead_name in labels:
                        continue
                    if pattern.fullmatch(text):
                        labels[lead_name] = (cx, cy)
                        break

    if len(labels) >= 3:
        print(f"  [PDF-TEXT] Labels found: {sorted(labels.keys())}")
        return labels
    return None


# ── Method 2: Tesseract OCR ──────────────────────────────────────

def detect_labels_from_ocr(gray_img: np.ndarray,
                           cell_regions: List[Tuple[int, int, int, int]] = None
                           ) -> Optional[Dict[str, Tuple[float, float]]]:
    """
    Use Tesseract OCR to read lead labels from an ECG image.
    cell_regions: list of (y0, y1, x0, x1) bounding boxes for each cell.
    Returns dict: lead_name → (x_center, y_center).
    """
    pytesseract, available = _get_tesseract()
    if not available:
        return None

    h, w = gray_img.shape
    labels: Dict[str, Tuple[float, float]] = {}

    # If cell regions provided, OCR each cell's label area
    if cell_regions:
        for (y0, y1, x0, x1) in cell_regions:
            cell_h = y1 - y0
            cell_w = x1 - x0
            # Label is usually in top-left corner (top 25%, left 30%)
            label_region = gray_img[
                y0:y0 + max(20, cell_h // 4),
                x0:x0 + max(30, cell_w // 3)
            ]
            if label_region.size < 100:
                continue

            # Upscale for better OCR
            scale = max(1, 60 // max(label_region.shape[0], 1))
            if scale > 1:
                label_region = cv2.resize(label_region, None,
                                          fx=scale, fy=scale,
                                          interpolation=cv2.INTER_CUBIC)

            try:
                text = pytesseract.image_to_string(
                    label_region,
                    config='--psm 7 -c tessedit_char_whitelist=IVaAbcdefghilmnopqrstuvwxyz0123456789'
                ).strip()

                for lead_name, pattern in _LEAD_PATTERNS.items():
                    if lead_name not in labels and pattern.search(text):
                        labels[lead_name] = (
                            (x0 + x1) / 2.0,
                            (y0 + y1) / 2.0,
                        )
                        break
            except Exception:
                continue
    else:
        # OCR the whole image and find label positions
        try:
            data = pytesseract.image_to_data(
                gray_img, output_type=pytesseract.Output.DICT,
                config='--psm 6'
            )
            for i, text in enumerate(data['text']):
                text = text.strip()
                if not text:
                    continue
                for lead_name, pattern in _LEAD_PATTERNS.items():
                    if lead_name not in labels and pattern.search(text):
                        x = data['left'][i] + data['width'][i] / 2
                        y = data['top'][i] + data['height'][i] / 2
                        labels[lead_name] = (x, y)
                        break
        except Exception:
            return None

    if len(labels) >= 3:
        print(f"  [OCR] Labels found: {sorted(labels.keys())}")
        return labels
    return None


# ── Method 3: Heuristic fallback ─────────────────────────────────

def assign_labels_by_layout(layout_type: str,
                            n_rows: int,
                            n_cols: int,
                            n_leads: int = 12
                            ) -> List[List[str]]:
    """
    Assign lead labels based on layout type and dimensions.
    Returns 2D list [row][col] → lead_name.
    """
    if layout_type == 'clinical' and n_rows == 3 and n_cols == 4:
        return CLINICAL_3x4

    if n_rows == 4 and n_cols == 3:
        return SEPARATED_4x3

    if n_rows == 3 and n_cols == 4:
        return CLINICAL_3x4

    if n_rows == 2 and n_cols == 6:
        return [
            ['I', 'II', 'III', 'aVR', 'aVL', 'aVF'],
            ['V1', 'V2', 'V3', 'V4', 'V5', 'V6'],
        ]

    if n_rows == 6 and n_cols == 2:
        return [
            ['I',   'V1'],
            ['II',  'V2'],
            ['III', 'V3'],
            ['aVR', 'V4'],
            ['aVL', 'V5'],
            ['aVF', 'V6'],
        ]

    # Single column strips
    if n_cols == 1:
        leads = LEAD_NAMES_12[:n_leads] if n_leads <= 12 else LEAD_NAMES_12
        # Pad if more rows than leads
        return [[leads[i]] if i < len(leads) else ['unknown']
                for i in range(n_rows)]

    # Generic: fill row-major
    leads = LEAD_NAMES_12[:n_leads]
    result = []
    idx = 0
    for r in range(n_rows):
        row = []
        for c in range(n_cols):
            if idx < len(leads):
                row.append(leads[idx])
                idx += 1
            else:
                row.append('unknown')
        result.append(row)
    return result


# ── Main entry: combine all methods ──────────────────────────────

def detect_lead_labels(gray_img: np.ndarray = None,
                       color_img: np.ndarray = None,
                       pdf_page=None,
                       cell_regions: List[Tuple[int, int, int, int]] = None,
                       layout_type: str = 'clinical',
                       n_rows: int = 3,
                       n_cols: int = 4,
                       n_leads: int = 12
                       ) -> List[List[str]]:
    """
    Detect lead labels using best available method.
    Returns 2D list [row][col] → lead_name.
    """
    # Method 1: PDF text layer
    if pdf_page is not None:
        pdf_labels = detect_labels_from_pdf(pdf_page)
        if pdf_labels:
            return _labels_to_grid(pdf_labels, cell_regions, n_rows, n_cols)

    # Method 2: OCR
    if gray_img is not None:
        ocr_labels = detect_labels_from_ocr(gray_img, cell_regions)
        if ocr_labels:
            return _labels_to_grid(ocr_labels, cell_regions, n_rows, n_cols)

    # Method 3: Heuristic
    print(f"  [HEURISTIC] Label assignment for {layout_type} "
          f"({n_rows}x{n_cols})")
    return assign_labels_by_layout(layout_type, n_rows, n_cols, n_leads)


def _labels_to_grid(labels: Dict[str, Tuple[float, float]],
                    cell_regions: List[Tuple[int, int, int, int]],
                    n_rows: int,
                    n_cols: int) -> List[List[str]]:
    """Map detected label positions to grid cells."""
    if not cell_regions:
        # Can't map without cell regions, fall back to heuristic
        # but sort by position to get ordering
        sorted_labels = sorted(labels.items(), key=lambda x: (x[1][1], x[1][0]))
        result = []
        idx = 0
        for r in range(n_rows):
            row = []
            for c in range(n_cols):
                if idx < len(sorted_labels):
                    row.append(sorted_labels[idx][0])
                    idx += 1
                else:
                    row.append('unknown')
            result.append(row)
        return result

    # Map each label to its nearest cell
    grid = [['unknown'] * n_cols for _ in range(n_rows)]
    cell_idx = 0
    for r in range(n_rows):
        for c in range(n_cols):
            if cell_idx >= len(cell_regions):
                break
            y0, y1, x0, x1 = cell_regions[cell_idx]
            cx = (x0 + x1) / 2.0
            cy = (y0 + y1) / 2.0

            # Find the label closest to this cell
            best_name = 'unknown'
            best_dist = float('inf')
            for name, (lx, ly) in labels.items():
                dist = ((lx - cx) ** 2 + (ly - cy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    best_name = name
            grid[r][c] = best_name
            cell_idx += 1

    return grid
