"""
parsers/layout_detector.py — Brand-agnostic ECG layout detection

Tujuan: menentukan tata-letak rekaman EKG (berapa baris × kolom, dan lead apa di
tiap sel) tanpa bergantung pada OCR — karena nama & jenis lead antar-merek SAMA,
yang berbeda hanya bentuk/tata letaknya.

Strategi (urut prioritas):
  1. GRID-BOX  : deteksi kotak grid berwarna (pink/merah). Proyeksi mask grid
                 secara horizontal & vertikal memberi struktur baris/kolom yang
                 bersih, tahan terhadap teks judul/label/tick. Cocok untuk
                 laporan ber-subplot (mis. 3×4 klinis, 4×3 terpisah, 12 strip).
  2. SIGNAL    : fallback bila grid tidak terdeteksi (grid pudar / kertas polos).
                 Pakai proyeksi kepadatan sinyal biner untuk menemukan pita baris
                 dan celah kolom.

Output: LayoutResult berisi daftar sel {name, y0, y1, x0, x1} sudah dipetakan ke
nama lead standar, plus metadata (layout_type, n_rows, n_cols).
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

LEADS_12 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
            'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


@dataclass
class Cell:
    name: str
    y0: int
    y1: int
    x0: int
    x1: int
    is_first_col: bool = False  # kolom paling kiri → mungkin ada pulse kalibrasi


@dataclass
class LayoutResult:
    layout_type: str
    cells: List[Cell]
    n_rows: int
    n_cols: int
    row_bands: List[Tuple[int, int]] = field(default_factory=list)
    method: str = 'grid'           # 'grid' | 'signal'
    pink_ratio: float = 0.0


# ── Grid mask & proyeksi ─────────────────────────────────────────

def grid_mask(img_bgr: np.ndarray) -> np.ndarray:
    """Mask piksel grid pink/merah khas kertas EKG."""
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    m1 = cv2.inRange(hsv, np.array([0,   12, 120]), np.array([15,  255, 255]))
    m2 = cv2.inRange(hsv, np.array([160, 12, 120]), np.array([180, 255, 255]))
    return cv2.bitwise_or(m1, m2)


def _projection_bands(proj: np.ndarray,
                      thresh_frac: float = 0.2,
                      min_run_frac: float = 0.03,
                      gap_merge_frac: float = 0.015) -> List[Tuple[int, int]]:
    """
    Temukan rentang (start, end) di mana proyeksi > thresh_frac * max.
    Gabungkan celah kecil, buang rentang yang terlalu pendek.
    """
    n = len(proj)
    if n == 0 or proj.max() <= 0:
        return []
    on = proj > (proj.max() * thresh_frac)
    runs = []
    i = 0
    while i < n:
        if on[i]:
            j = i
            while j < n and on[j]:
                j += 1
            runs.append([i, j])
            i = j
        else:
            i += 1
    # Gabung run yang dipisah celah kecil
    gapmax = int(gap_merge_frac * n)
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] <= gapmax:
            merged[-1][1] = r[1]
        else:
            merged.append(r)
    min_len = min_run_frac * n
    return [(a, b) for a, b in merged if (b - a) >= min_len]


# ── Pemetaan (baris × kolom) → nama lead ─────────────────────────

def leads_for(n_rows: int, n_cols: int) -> List[List[str]]:
    """
    Kembalikan grid [baris][kolom] berisi nama lead standar berdasarkan
    dimensi tata letak. Mengandalkan urutan baku (brand-agnostic).
    """
    # Klinis 3×4 standar
    if n_rows == 3 and n_cols == 4:
        return [['I', 'aVR', 'V1', 'V4'],
                ['II', 'aVL', 'V2', 'V5'],
                ['III', 'aVF', 'V3', 'V6']]
    # Terpisah 4×3 (umum pada laporan digital)
    if n_rows == 4 and n_cols == 3:
        return [['I', 'II', 'III'],
                ['aVR', 'aVL', 'aVF'],
                ['V1', 'V2', 'V3'],
                ['V4', 'V5', 'V6']]
    # 6-lead terpisah 2×3
    if n_rows == 2 and n_cols == 3:
        return [['I', 'II', 'III'],
                ['aVR', 'aVL', 'aVF']]
    # 6×2
    if n_rows == 6 and n_cols == 2:
        return [['I', 'V1'], ['II', 'V2'], ['III', 'V3'],
                ['aVR', 'V4'], ['aVL', 'V5'], ['aVF', 'V6']]
    # 2×6
    if n_rows == 2 and n_cols == 6:
        return [['I', 'II', 'III', 'aVR', 'aVL', 'aVF'],
                ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']]
    # Strip (1 kolom): satu lead per baris
    if n_cols == 1:
        return [[LEADS_12[i]] if i < len(LEADS_12) else [f'lead_{i+1}']
                for i in range(n_rows)]
    # Generik: isi row-major dari LEADS_12
    grid = []
    idx = 0
    for _ in range(n_rows):
        row = []
        for _ in range(n_cols):
            row.append(LEADS_12[idx] if idx < len(LEADS_12) else f'lead_{idx+1}')
            idx += 1
        grid.append(row)
    return grid


def _trim_outlier_rows(rows: List[Tuple[int, int]], target: int) -> List[Tuple[int, int]]:
    """
    Pangkas pita baris berlebih (mis. judul/footer yang ikut terdeteksi) hingga
    tersisa `target`. Baris pita EKG sebenarnya tersebar merata; band judul/footer
    biasanya terpisah jauh (gap besar) di ujung atas/bawah → itu yang dibuang.
    """
    rows = list(rows)
    while len(rows) > target and len(rows) >= 2:
        centers = [(a + b) / 2 for a, b in rows]
        gaps = [centers[i + 1] - centers[i] for i in range(len(centers) - 1)]
        med = float(np.median(gaps))
        if gaps[0] > 1.8 * med and gaps[0] >= gaps[-1]:
            rows = rows[1:]            # outlier di atas
        elif gaps[-1] > 1.8 * med:
            rows = rows[:-1]           # outlier di bawah
        else:
            # tak ada outlier jelas → buang pita terpendek
            i = min(range(len(rows)), key=lambda k: rows[k][1] - rows[k][0])
            rows.pop(i)
    return rows


def _expand_strip_bands(rows: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    """
    Perlebar tiap pita strip hingga titik tengah ke pita tetangga, agar puncak
    QRS yang menjulang ke atas/bawah (di luar pita baseline tipis) tetap tertangkap.
    Pita pertama tidak diperlebar ke atas & terakhir ke bawah (hindari header/footer).
    """
    rows = sorted(rows)
    n = len(rows)
    if n <= 1:
        return rows
    out = []
    for i, (y0, y1) in enumerate(rows):
        top = y0 if i == 0 else (rows[i - 1][1] + y0) // 2
        bot = y1 if i == n - 1 else (y1 + rows[i + 1][0]) // 2
        out.append((top, bot))
    return out


def _build_cells(row_bands: List[Tuple[int, int]],
                 col_bands: List[Tuple[int, int]]) -> List[Cell]:
    grid = leads_for(len(row_bands), len(col_bands))
    cells: List[Cell] = []
    for r, (y0, y1) in enumerate(row_bands):
        if r >= len(grid):
            break
        for c, (x0, x1) in enumerate(col_bands):
            if c >= len(grid[r]):
                break
            cells.append(Cell(name=grid[r][c], y0=y0, y1=y1, x0=x0, x1=x1,
                              is_first_col=(c == 0)))
    return cells


# ── Deteksi GRID-BOX ─────────────────────────────────────────────

def _detect_grid_layout(img_bgr: np.ndarray,
                        expected_leads: Optional[int] = None) -> Optional[LayoutResult]:
    h, w = img_bgr.shape[:2]
    g = grid_mask(img_bgr)
    pink_ratio = float(np.count_nonzero(g)) / (h * w)

    row_proj = g.sum(axis=1).astype(float) / 255.0
    col_proj = g.sum(axis=0).astype(float) / 255.0

    grid_rows = _projection_bands(row_proj, thresh_frac=0.2, min_run_frac=0.03)
    grid_cols = _projection_bands(col_proj, thresh_frac=0.2, min_run_frac=0.04)

    nr, nc = len(grid_rows), len(grid_cols)

    # Layout ber-subplot (baris & kolom jelas)
    if nr >= 2 and nc >= 2:
        cells = _build_cells(grid_rows, grid_cols)
        return LayoutResult(layout_type=f'grid_{nr}x{nc}', cells=cells,
                            n_rows=nr, n_cols=nc, row_bands=grid_rows,
                            method='grid', pink_ratio=pink_ratio)

    # Strip: banyak baris grid, satu kolom penuh
    if nr >= 5 and nc <= 1:
        target = expected_leads if expected_leads in (6, 12) else (12 if nr > 12 else nr)
        if nr > target:
            grid_rows = _trim_outlier_rows(grid_rows, target)
            nr = len(grid_rows)
        grid_rows = _expand_strip_bands(grid_rows)   # tangkap QRS di luar pita baseline
        cells = _build_cells(grid_rows, [(0, w)])
        return LayoutResult(layout_type=f'strips_{nr}', cells=cells,
                            n_rows=nr, n_cols=1, row_bands=grid_rows,
                            method='grid', pink_ratio=pink_ratio)

    return None  # grid tidak meyakinkan → fallback


# ── Deteksi SIGNAL (fallback) ────────────────────────────────────

def _row_bands_at(binary: np.ndarray, min_frac: float,
                  threshold: float = 0.003) -> List[Tuple[int, int]]:
    """Pita baris berisi sinyal pada satu ambang tinggi min_frac."""
    h, w = binary.shape
    density = binary.sum(axis=1).astype(float) / (w * 255.0)
    out, in_b, start = [], False, 0
    for y, d in enumerate(density):
        if not in_b and d > threshold:
            in_b, start = True, y
        elif in_b and d <= threshold:
            in_b = False
            if y - start > h * min_frac:
                out.append((start, y))
    if in_b and h - start > h * min_frac:
        out.append((start, h))
    return out


def _best_row_bands(binary: np.ndarray, target: Optional[int],
                    lo: int = 5, hi: int = 13) -> List[Tuple[int, int]]:
    """
    Pilih set pita baris terbaik. Jika target diberikan, cari ambang yang
    menghasilkan tepat target pita (atau paling dekat). Jika tidak, ambil set
    pertama yang jumlahnya dalam rentang [lo, hi].
    """
    mfs = [0.03, 0.025, 0.02, 0.015, 0.012, 0.01, 0.008, 0.006]
    results = {mf: _row_bands_at(binary, mf) for mf in mfs}
    if target is not None:
        # cari exact match dulu (ambang terbesar = paling bersih)
        for mf in mfs:
            if len(results[mf]) == target:
                return results[mf]
        # terdekat
        best = min(mfs, key=lambda mf: abs(len(results[mf]) - target))
        return results[best]
    for mf in mfs:
        if lo <= len(results[mf]) <= hi:
            return results[mf]
    # fallback: yang terbanyak namun <= hi
    cand = [results[mf] for mf in mfs if len(results[mf]) <= hi]
    return max(cand, key=len) if cand else results[mfs[-1]]


def _remove_long_lines(binary: np.ndarray) -> np.ndarray:
    """Hilangkan garis vertikal & horizontal panjang (pembatas kolom, border)."""
    h, w = binary.shape
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 25)))
    clean = cv2.subtract(binary, cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk))
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 25), 1))
    clean = cv2.subtract(clean, cv2.morphologyEx(clean, cv2.MORPH_OPEN, hk))
    return clean


def _vertical_dividers(binary: np.ndarray, height_frac: float = 0.30) -> List[int]:
    """Posisi-x garis pembatas vertikal panjang (pemisah kolom layout klinis)."""
    h, w = binary.shape
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 20)))
    vlines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk)
    vproj = vlines.sum(axis=0).astype(float) / 255.0
    tall = np.where(vproj > height_frac * h)[0]
    tall = [x for x in tall if w * 0.06 < x < w * 0.94]
    if not tall:
        return []
    # cluster posisi yang berdekatan
    centers, start, prev = [], tall[0], tall[0]
    for x in tall[1:]:
        if x - prev > w * 0.02:
            centers.append((start + prev) // 2)
            start = x
        prev = x
    centers.append((start + prev) // 2)
    return centers


def _whitespace_columns(binary: np.ndarray,
                        row_bands: List[Tuple[int, int]],
                        n_expected: int = 4) -> List[Tuple[int, int]]:
    """
    Deteksi kolom lewat CELAH WHITESPACE (untuk layout klinis tanpa garis pembatas,
    kolom hanya dipisah spasi kosong). Cari lembah densitas-kolom yang benar-benar
    kosong di seluruh tinggi region baris.
    """
    h, w = binary.shape
    if not row_bands:
        return [(0, w)]
    # Margin antar-kolom klinis = pita vertikal kosong di SELURUH tinggi area EKG
    # (tak ada lead mana pun bergoyang ke situ). Hitung tinta per kolom pada
    # rentang penuh (atas baris pertama s.d. bawah baris terakhir), lalu cari
    # kolom yang nyaris tanpa tinta dengan ambang RELATIF (adaptif terhadap gambar).
    y_top = min(b[0] for b in row_bands)
    y_bot = max(b[1] for b in row_bands)
    if y_bot - y_top < 10:
        return [(0, w)]
    col_ink = binary[y_top:y_bot, :].sum(axis=0).astype(float) / 255.0
    k = max(3, int(w * 0.004))
    sm = np.convolve(col_ink, np.ones(k) / k, mode='same')
    ref = np.percentile(sm, 90)                 # tinta khas kolom-plot
    empty = sm < max(1.0, 0.06 * ref)           # margin ~ kosong
    gaps = []
    i = 0
    while i < w:
        if empty[i]:
            j = i
            while j < w and empty[j]:
                j += 1
            if (j - i) > w * 0.012 and w * 0.07 < (i + j) / 2 < w * 0.93:
                gaps.append((i + j) // 2)
            i = j
        else:
            i += 1
    if not gaps:
        return [(0, w)]
    bounds = [0] + sorted(gaps) + [w]
    cols = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
            if bounds[i + 1] - bounds[i] > w * 0.10]
    return cols


def _detect_signal_layout(binary: np.ndarray, expected_leads: Optional[int]) -> LayoutResult:
    h, w = binary.shape
    clean = _remove_long_lines(binary)
    dividers = _vertical_dividers(binary)

    # ── Coba layout MULTIKOLOM (klinis 3×4 / terpisah) lebih dulu ──
    # Kecuali 6-lead diminta eksplisit (lebih aman diperlakukan sebagai strip).
    if expected_leads != 6:
        rows = _best_row_bands(clean, target=None, lo=3, hi=4)
        if 3 <= len(rows) <= 4:
            # Kolom: dari garis pembatas, ATAU dari celah whitespace.
            if len(dividers) >= 2:
                bounds = [0] + sorted(dividers) + [w]
                cols = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
                        if bounds[i + 1] - bounds[i] > w * 0.08]
            else:
                cols = _whitespace_columns(clean, rows, n_expected=4)
            # Baris klinis sering KONTINU (lead berganti tiap 2.5 dtk tanpa celah/garis).
            # Bila 3-4 baris tapi tak ada struktur kolom → asumsikan klinis 3×4
            # dengan 4 kolom sama lebar.
            if len(cols) < 2 and 3 <= len(rows) <= 4:
                cols = [(i * w // 4, (i + 1) * w // 4) for i in range(4)]
            nc = len(cols)

            if nc == 4 and len(rows) >= 3:
                main_rows = rows[:3]
                cells = _build_cells(main_rows, cols)
                if len(rows) >= 4:
                    ry0, ry1 = rows[3]
                    cells.append(Cell('II_rhythm', ry0, ry1, 0, w, True))
                return LayoutResult('clinical_3x4', cells, 3, 4,
                                    row_bands=main_rows, method='signal')
            if nc >= 2 and len(rows) >= 1:
                cells = _build_cells(rows, cols)
                return LayoutResult(f'grid_{len(rows)}x{nc}', cells, len(rows), nc,
                                    row_bands=rows, method='signal')

    # ── Tidak ada struktur kolom → layout STRIP (satu lead per baris) ──
    target = expected_leads
    rows = _best_row_bands(binary, target=target, lo=5, hi=13)
    nr = len(rows)
    if nr == 0:
        return LayoutResult('strips_1', [Cell('I', 0, h, 0, w, True)], 1, 1,
                            row_bands=[(0, h)], method='signal')
    cap = target if target in (6, 12) else (12 if nr > 12 else nr)
    if nr > cap:
        rows = _trim_outlier_rows(rows, cap)
        nr = len(rows)
    rows = _expand_strip_bands(rows)   # tangkap QRS di luar pita baseline
    cells = _build_cells(rows, [(0, w)])
    return LayoutResult(f'strips_{nr}', cells, nr, 1,
                        row_bands=rows, method='signal')


def _detect_calpulse_strips(img_bgr: np.ndarray,
                            binary: np.ndarray,
                            expected_leads: Optional[int] = None) -> Optional[LayoutResult]:
    """
    Deteksi layout STRIP dari PULSE KALIBRASI di margin kiri (1 pulse per lead).
    Cocok untuk laporan EKG 12-lead "full-width strip" dengan grid kontinu yang
    membuat pita baris menyatu (mis. ECG REPORT / Export). Region pulse dibagi rata
    menjadi N strip (12 atau 6) lalu dipetakan ke urutan lead baku.

    Area EKG dibatasi oleh GRID MERAH (header putih tak ber-grid) supaya teks tabel
    pengukuran di header tidak menipu deteksi pulse.
    """
    try:
        from scipy.signal import find_peaks
    except Exception:
        return None
    h, w = binary.shape

    # Batas atas/bawah area EKG dari grid merah (header & footer tanpa grid).
    g = grid_mask(img_bgr)
    rowpink = g.sum(axis=1).astype(float) / 255.0
    ys, ye = int(h * 0.12), h
    if rowpink.max() > 0:
        gr = np.where(rowpink > 0.15 * rowpink.max())[0]
        if len(gr) > 0:
            ys, ye = int(gr[0]), int(gr[-1]) + 1
    if ye - ys < int(h * 0.2):
        return None

    lw = max(3, int(w * 0.05))
    lm = binary[ys:ye, :lw]
    prof = lm.sum(axis=1).astype(float) / (lw * 255.0)
    if prof.max() < 1e-6:
        return None
    prof = np.convolve(prof, np.ones(7) / 7.0, mode='same')
    pk, _ = find_peaks(prof, distance=int(h * 0.045), prominence=prof.max() * 0.25)
    pk = [int(p + ys) for p in pk]
    if len(pk) < 8:                          # butuh banyak pulse → khas 12-lead strip
        return None
    pitch = float(np.median(np.diff(pk)))
    if pitch < 5:
        return None
    top = max(ys, int(pk[0] - pitch / 2))
    bot = min(ye, int(pk[-1] + pitch / 2))
    if expected_leads in (6, 12):
        n = expected_leads
    elif 10 <= len(pk) <= 13:
        n = 12
    elif 5 <= len(pk) <= 7:
        n = 6
    else:
        n = min(max(len(pk), 1), 12)
    bands = [(int(top + i * (bot - top) / n), int(top + (i + 1) * (bot - top) / n))
             for i in range(n)]
    cells = _build_cells(bands, [(0, w)])
    return LayoutResult(f'strips_{n}', cells, n, 1, row_bands=bands, method='calpulse')


# ── Entry point ──────────────────────────────────────────────────

def detect_layout(img_bgr: np.ndarray,
                  binary: np.ndarray,
                  expected_leads: Optional[int] = None) -> LayoutResult:
    """
    Deteksi tata letak: PULSE-KALIBRASI strip (laporan 12-lead) → GRID-BOX →
    fallback SIGNAL.
    """
    cp = _detect_calpulse_strips(img_bgr, binary, expected_leads)
    if cp is not None:
        return cp
    grid_result = _detect_grid_layout(img_bgr, expected_leads)
    if grid_result is not None:
        return grid_result
    return _detect_signal_layout(binary, expected_leads)
