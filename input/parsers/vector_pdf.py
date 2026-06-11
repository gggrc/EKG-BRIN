"""
parsers/vector_pdf.py — Ekstraksi VEKTOR eksak dari PDF EKG.

Banyak PDF EKG (Export 12-lead, AliveCor/Kardia 6-lead) menyimpan trace sebagai
POLYLINE vektor, bukan gambar raster. Bila demikian, sinyal mV bisa dibaca
LANGSUNG dari koordinat (x,y) -> EKSAK, tanpa digitalisasi (tak ada overlap/
collision/box/inkonsistensi). Tervalidasi via hukum Einthoven (RMSE < 0.03 mV).

Mendukung 2 layout:
  * 12-lead : 12 path panjang di SATU halaman (sort atas->bawah = I..V6).
  * 6-lead  : 6 path panjang per halaman, rekaman 30s TERPOTONG beberapa
              halaman -> disambung berurutan (Kardia/AliveCor).

Kalibrasi standar: 25 mm/s, 10 mm/mV ; 1 mm = 72/25.4 pt.
Pra-pemrosesan: highpass 0.5 Hz (baseline-wander removal, standar AHA).

API:
    extract_vector_pdf(pdf_path, fs=250, hp=True) -> dict | None
        {leads{mV}, fs, num_leads, duration_sec, vendor, meta}
"""
import numpy as np
import fitz

try:
    from scipy.signal import butter, filtfilt
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

PT_PER_MM = 72.0 / 25.4
PMV_PT = 10.0 * PT_PER_MM        # 10 mm/mV -> pt/mV
PSEC_PT = 25.0 * PT_PER_MM       # 25 mm/s  -> pt/sec
HP_FC = 0.5                      # Hz highpass (buang baseline wander)

LEADS_12 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
            'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
LEADS_6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
MIN_SEG = 500                    # min segmen 'l' utk dianggap path trace
                                 # (gridline ~160 seg terbuang; trace ~2000-3700)


def _highpass(x, fs, fc=HP_FC):
    """Buang drift < fc Hz. Zero-phase (filtfilt) -> P-QRS-T tak terdistorsi,
    relasi antar-lead terjaga. Aman bila scipy tak ada (lewati)."""
    if not _HAS_SCIPY or len(x) < 27:
        return x
    b, a = butter(2, fc / (fs / 2.0), btype="high")
    return filtfilt(b, a, x)


def _long_paths(page):
    """Kembalikan list polyline panjang [(x,y)...] dari satu halaman."""
    out = []
    for dr in page.get_drawings():
        pts = []
        for it in dr['items']:
            if it[0] == 'l':
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts.append((it[2].x, it[2].y))
        if len(pts) > MIN_SEG:
            out.append(pts)
    return out


def _poly_to_mv(P, x_lo, x_hi, fs):
    """Polyline 1 lead -> array mV pada grid waktu seragam (fs)."""
    xs = np.array([x for x, _ in P], float)
    ys = np.array([y for _, y in P], float)
    o = np.argsort(xs, kind="stable")
    xs, ys = xs[o], ys[o]
    ux, idx = np.unique(xs, return_index=True)
    uy = ys[idx]
    base = float(np.median(ys))
    n = max(1, int(round((x_hi - x_lo) / PSEC_PT * fs)))
    xg = np.linspace(x_lo, x_hi, n)
    yg = np.interp(xg, ux, uy)
    return (base - yg) / PMV_PT          # y turun = mV naik


def _finalize(leads, fs, hp):
    """Highpass + koreksi baseline global per lead."""
    out = {}
    for nm, sig in leads.items():
        sig = np.asarray(sig, float)
        if hp:
            sig = _highpass(sig, fs)
        sig = sig - np.median(sig)
        out[nm] = [round(float(v), 4) for v in sig]
    return out


def extract_vector_pdf(pdf_path, fs=250, hp=True):
    doc = fitz.open(pdf_path)
    # kumpulkan path panjang per halaman
    page_paths = [(_long_paths(doc[p])) for p in range(doc.page_count)]
    text0 = doc[0].get_text("text") if doc.page_count else ""
    vendor = "AliveCor Kardia" if "kardia" in text0.lower() else "PDF Vektor"

    # ---- 12-lead: satu halaman dgn tepat 12 path ----
    pg12 = next((pp for pp in page_paths if len(pp) == 12), None)
    if pg12 is not None:
        pg12 = sorted(pg12, key=lambda P: np.median([y for _, y in P]))
        allx = [x for P in pg12 for x, _ in P]
        x_lo, x_hi = min(allx), max(allx)
        raw = {LEADS_12[i]: _poly_to_mv(P, x_lo, x_hi, fs)
               for i, P in enumerate(pg12)}
        leads = _finalize(raw, fs, hp)
        n = len(next(iter(leads.values())))
        doc.close()
        return {"leads": leads, "fs": fs, "num_leads": 12,
                "duration_sec": round(n / fs, 3), "vendor": vendor,
                "meta": {"source": "pdf_vector_12lead", "highpass_hz": HP_FC if hp else None,
                         "pt_per_mv": PMV_PT, "pt_per_sec": PSEC_PT, "n_samples": n}}

    # ---- 6-lead: halaman2 dgn tepat 6 path -> sambung berurutan ----
    seg_pages = [(p, pp) for p, pp in enumerate(page_paths) if len(pp) == 6]
    if seg_pages:
        parts = {nm: [] for nm in LEADS_6}
        for _, pp in seg_pages:
            pp = sorted(pp, key=lambda P: np.median([y for _, y in P]))
            allx = [x for P in pp for x, _ in P]
            x_lo, x_hi = min(allx), max(allx)
            for i, P in enumerate(pp):
                parts[LEADS_6[i]].append(_poly_to_mv(P, x_lo, x_hi, fs))
        raw = {nm: np.concatenate(parts[nm]) for nm in LEADS_6}
        leads = _finalize(raw, fs, hp)
        n = len(leads["I"])
        doc.close()
        return {"leads": leads, "fs": fs, "num_leads": 6,
                "duration_sec": round(n / fs, 3), "vendor": vendor,
                "meta": {"source": "pdf_vector_6lead_multipage",
                         "pages_joined": [p for p, _ in seg_pages],
                         "highpass_hz": HP_FC if hp else None,
                         "pt_per_mv": PMV_PT, "pt_per_sec": PSEC_PT, "n_samples": n}}

    doc.close()
    return None                          # bukan PDF vektor -> caller fallback raster
