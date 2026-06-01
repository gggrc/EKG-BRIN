"""
parsers/calibration_detector.py — Calibration & Scale Detection

Detects calibration info from ECG images to convert pixels → mV accurately.

Three methods (tried in order of accuracy):
  1. Calibration pulse: rectangular 1mV step in left margin
  2. Grid spacing: pink/red grid → px/mm → px/mV
  3. Estimation: based on strip dimensions and typical ECG proportions
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


@dataclass
class CalibrationResult:
    """Result of calibration detection."""
    px_per_mV: float                          # pixels per millivolt
    px_per_sec: Optional[float] = None        # pixels per second
    method: str = 'estimated'                 # 'calibration_pulse', 'grid_spacing', 'estimated'
    confidence: float = 0.0                   # 0.0 – 1.0
    gain_mm_per_mV: float = 10.0              # standard: 10 mm/mV
    speed_mm_per_sec: float = 25.0            # standard: 25 mm/s
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'px_per_mV': round(self.px_per_mV, 2),
            'px_per_sec': round(self.px_per_sec, 2) if self.px_per_sec else None,
            'method': self.method,
            'confidence': round(self.confidence, 3),
            'gain_mm_per_mV': self.gain_mm_per_mV,
            'speed_mm_per_sec': self.speed_mm_per_sec,
        }


# ── Method 1: Calibration Pulse Detection ────────────────────────

def detect_calibration_pulse(gray_img: np.ndarray,
                             strip_regions: List[Tuple[int, int]]
                             ) -> Optional[CalibrationResult]:
    """
    Detect 1 mV calibration pulse in the left margin of ECG strips.

    The calibration pulse looks like:
        ┌──┐
        │  │
    ────┘  └────
    Height of step = 1 mV in pixel space.
    """
    from scipy.ndimage import uniform_filter1d

    pulse_heights: List[float] = []
    h_img, w_img = gray_img.shape

    for y_start, y_end in strip_regions:
        strip = gray_img[y_start:y_end, :]
        strip_h, strip_w = strip.shape
        if strip_h < 20 or strip_w < 40:
            continue

        # Look at leftmost 15 % of strip
        left_w = max(30, int(strip_w * 0.15))
        left_region = strip[:, :left_w]

        # Adaptive threshold to binarise
        binary = cv2.adaptiveThreshold(
            left_region, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=max(15, (left_w // 4) | 1),  # odd number
            C=10,
        )

        # Extract vertical profile column-by-column
        profile = []
        for col in range(left_w):
            col_pixels = np.where(binary[:, col] > 0)[0]
            if len(col_pixels) > 0:
                profile.append(float(np.mean(col_pixels)))
            else:
                profile.append(strip_h / 2.0)

        profile = np.array(profile, dtype=float)
        profile = strip_h - profile  # flip so up = positive

        if len(profile) < 10:
            continue

        # Smooth to suppress noise
        smoothed = uniform_filter1d(profile, size=max(3, left_w // 15))

        # Detect step: look for plateau significantly above baseline
        baseline = np.percentile(smoothed[:max(3, len(smoothed) // 5)], 50)
        above = smoothed - baseline
        peak_val = np.max(above)

        if peak_val < strip_h * 0.04:
            continue  # no obvious pulse

        # Find the step region (where signal is > 50 % of peak)
        thresh = peak_val * 0.5
        high_mask = above > thresh
        high_indices = np.where(high_mask)[0]

        if len(high_indices) < 3:
            continue

        # The plateau height is the average above baseline in the high region
        plateau_height = np.mean(above[high_indices])
        pulse_heights.append(plateau_height)

    if not pulse_heights:
        return None

    # Robust estimate: median
    median_height = float(np.median(pulse_heights))
    # Confidence scales with agreement across strips
    if len(pulse_heights) >= 2:
        spread = np.std(pulse_heights) / (median_height + 1e-9)
        confidence = min(0.95, 0.6 + 0.35 * (1 - min(spread, 1.0)))
    else:
        confidence = 0.5

    return CalibrationResult(
        px_per_mV=median_height,
        method='calibration_pulse',
        confidence=confidence,
        details={
            'pulse_heights': [round(h, 1) for h in pulse_heights],
            'n_strips_detected': len(pulse_heights),
        },
    )


# ── Method 2: Grid Spacing Detection ─────────────────────────────

def detect_grid_spacing(color_img: np.ndarray) -> Optional[CalibrationResult]:
    """
    Detect pink/red ECG grid lines and measure spacing.

    Standard ECG paper:
      small grid = 1 mm,  large grid = 5 mm
      gain = 10 mm/mV  →  1 mV = 10 mm = 2 large boxes
      speed = 25 mm/s  →  1 s  = 25 mm = 5 large boxes
    """
    from scipy.signal import find_peaks

    h, w = color_img.shape[:2]
    if h < 100 or w < 100:
        return None

    hsv = cv2.cvtColor(color_img, cv2.COLOR_BGR2HSV)

    # Mask for pink/red/light-red grid lines
    masks = []
    for (lo, hi) in [
        (np.array([0,  15, 140]), np.array([12, 160, 255])),
        (np.array([165, 15, 140]), np.array([180, 160, 255])),
        (np.array([0,  8, 200]), np.array([5, 60, 255])),   # very light pink
    ]:
        masks.append(cv2.inRange(hsv, lo, hi))
    grid_mask = masks[0]
    for m in masks[1:]:
        grid_mask = cv2.bitwise_or(grid_mask, m)

    pink_ratio = np.sum(grid_mask > 0) / (h * w)
    if pink_ratio < 0.005:
        return None  # not enough grid pixels

    # ── Horizontal projection → vertical grid line spacing ────
    v_proj = np.sum(grid_mask.astype(float), axis=0)
    # ── Vertical projection → horizontal grid line spacing ────
    h_proj = np.sum(grid_mask.astype(float), axis=1)

    def _find_small_grid(proj, min_sp=4, max_sp=80):
        """Find the small-grid spacing via autocorrelation."""
        p = proj - np.mean(proj)
        if np.std(p) < 1e-6:
            return None
        acorr = np.correlate(p, p, mode='full')
        acorr = acorr[len(acorr) // 2:]
        acorr = acorr / (acorr[0] + 1e-9)
        peaks, props = find_peaks(acorr[min_sp:max_sp],
                                  prominence=0.05, distance=3)
        if len(peaks) == 0:
            return None
        return int(peaks[0] + min_sp)

    h_spacing = _find_small_grid(h_proj)
    v_spacing = _find_small_grid(v_proj)

    if h_spacing is None and v_spacing is None:
        return None

    spacing = (h_spacing or v_spacing)
    if h_spacing and v_spacing:
        spacing = (h_spacing + v_spacing) / 2.0

    px_per_mm = spacing          # 1 small grid = 1 mm
    px_per_mV = px_per_mm * 10   # standard 10 mm/mV
    px_per_sec = px_per_mm * 25  # standard 25 mm/s

    return CalibrationResult(
        px_per_mV=px_per_mV,
        px_per_sec=px_per_sec,
        method='grid_spacing',
        confidence=0.70,
        details={
            'px_per_mm': round(px_per_mm, 2),
            'h_spacing': h_spacing,
            'v_spacing': v_spacing,
            'pink_ratio': round(pink_ratio, 4),
        },
    )


# ── Method 3: Estimation (fallback) ──────────────────────────────

def estimate_calibration(strip_regions: List[Tuple[int, int]],
                         img_width: int,
                         n_cols: int = 1) -> CalibrationResult:
    """
    Last-resort estimation from image geometry.

    Typical ECG:
      10 s at 25 mm/s = 250 mm wide
      ±2 mV visible range → strip height ≈ 40 mm
    """
    if not strip_regions:
        return CalibrationResult(px_per_mV=80, px_per_sec=img_width / 10.0,
                                 method='estimated', confidence=0.15)

    avg_strip_h = float(np.mean([y1 - y0 for y0, y1 in strip_regions]))
    # A strip typically spans ~4 mV (±2 mV)
    assumed_range = 4.0
    px_per_mV = avg_strip_h / assumed_range

    # Width covers 10 seconds (or 2.5 s per column in clinical 3×4)
    total_time = 10.0
    px_per_sec = (img_width / n_cols) / (total_time / n_cols) if n_cols > 0 else img_width / total_time

    return CalibrationResult(
        px_per_mV=px_per_mV,
        px_per_sec=px_per_sec,
        method='estimated',
        confidence=0.25,
        details={
            'avg_strip_height': round(avg_strip_h, 1),
            'assumed_range_mV': assumed_range,
        },
    )


# ── Helper: quick strip-row detector ─────────────────────────────

def detect_strip_rows(gray_img: np.ndarray,
                      min_frac: float = 0.04
                      ) -> List[Tuple[int, int]]:
    """Detect horizontal bands that contain signal (strips/rows)."""
    h, w = gray_img.shape
    _, binary = cv2.threshold(gray_img, 0, 255,
                              cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    row_density = np.sum(binary, axis=1) / (w * 255.0)
    threshold = 0.008
    in_strip = False
    strips: List[Tuple[int, int]] = []
    start = 0

    for y in range(h):
        if not in_strip and row_density[y] > threshold:
            in_strip = True
            start = y
        elif in_strip and row_density[y] <= threshold:
            in_strip = False
            if (y - start) > h * min_frac:
                strips.append((start, y))
    if in_strip and (h - start) > h * min_frac:
        strips.append((start, h))

    return strips


# ── Main entry point ──────────────────────────────────────────────

def detect_calibration(color_img: np.ndarray,
                       gray_img: np.ndarray = None,
                       strip_regions: List[Tuple[int, int]] = None,
                       n_cols: int = 1) -> CalibrationResult:
    """
    Detect calibration from an ECG image.
    Tries: calibration pulse → grid spacing → estimation.
    """
    if gray_img is None:
        gray_img = cv2.cvtColor(color_img, cv2.COLOR_BGR2GRAY)

    h, w = gray_img.shape

    if strip_regions is None:
        strip_regions = detect_strip_rows(gray_img)

    # Method 1 — calibration pulse (most accurate)
    result = detect_calibration_pulse(gray_img, strip_regions)
    if result and result.confidence >= 0.45:
        print(f"  [CAL-PULSE] Calibration pulse detected: "
              f"{result.px_per_mV:.1f} px/mV "
              f"(confidence {result.confidence:.2f})")
        # Estimate px_per_sec from width and assumed 10 s
        if result.px_per_sec is None:
            result.px_per_sec = w / (10.0 / max(n_cols, 1))
        return result

    # Method 2 — grid spacing
    result2 = detect_grid_spacing(color_img)
    if result2 and result2.confidence >= 0.4:
        print(f"  [CAL-GRID] Grid spacing detected: "
              f"{result2.px_per_mV:.1f} px/mV "
              f"(confidence {result2.confidence:.2f})")
        return result2

    # Method 3 — estimation
    result3 = estimate_calibration(strip_regions, w, n_cols)
    print(f"  [CAL-EST] Calibration estimated: "
          f"{result3.px_per_mV:.1f} px/mV "
          f"(confidence {result3.confidence:.2f})")
    return result3
