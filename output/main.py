"""
output/main.py — Hasilkan FHIR Bundle dari hasil digitalisasi.

Alur: file EKG -> digitalisasi (input/) -> UniversalECG -> FHIR Bundle (SatuSehat).
Bila ada token SatuSehat, Bundle bisa langsung dikirim (REST).

Cara pakai:
    python output/main.py <file_ekg>     # gambar/PDF/CSV/...
    python output/main.py                 # demo (12.jpeg)
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_INPUT = os.path.join(_ROOT, "input")
if _INPUT not in sys.path:
    sys.path.insert(0, _INPUT)

import numpy as np
from fhir_converter import to_fhir_bundle, save_bundle

OUT_DIR = os.path.join(_HERE, "fhir_output")


def _estimate_hr(ecg):
    """Estimasi HR kasar dari lead II (deteksi R-peak) — pelengkap demo."""
    leads = ecg.get("leads", {})
    sig = leads.get("II_rhythm") or leads.get("II")
    fs = ecg.get("sampling_rate", 500) or 500
    if not sig or len(sig) < fs:
        return None
    s = np.asarray(sig, float)
    s = s - np.median(s)
    try:
        from scipy.signal import find_peaks
        pk, _ = find_peaks(s, distance=int(0.3 * fs),
                           prominence=max(0.15, 0.4 * np.std(s)))
    except Exception:
        return None
    if len(pk) < 2:
        return None
    rr = np.diff(pk) / fs
    hr = 60.0 / float(np.mean(rr))
    return int(round(hr)) if 30 < hr < 220 else None


def run(path, expected_leads=None):
    os.makedirs(OUT_DIR, exist_ok=True)
    base = os.path.splitext(os.path.basename(path))[0]
    print("=" * 58)
    print(f"  OUTPUT FHIR  -  {os.path.basename(path)}")
    print("=" * 58)

    # 1) Digitalisasi
    from ecg_input_router import load_ecg
    import io, contextlib
    with contextlib.redirect_stdout(io.StringIO()):
        ecg = load_ecg(path, expected_leads=expected_leads).to_dict()
    print(f"[1] Digitalisasi: {ecg['num_leads']} lead, {ecg['sampling_rate']} Hz")

    # 2) Pengukuran/diagnosis (placeholder klasifikasi: HR + label demo)
    hr = _estimate_hr(ecg)
    analysis = {"heart_rate_bpm": hr,
                "labels": ["NORM"],
                "conclusion": (f"Automated ECG: HR {hr} bpm; " if hr else "")
                              + "kelas NORM (decision support - validasi klinis)."}
    print(f"[2] Analisis: HR={hr} bpm, label={analysis['labels']}")

    # 3) Konversi ke FHIR Bundle
    bundle = to_fhir_bundle(ecg, analysis)
    n_obs = sum(1 for e in bundle["entry"]
                if e["resource"]["resourceType"] == "Observation")
    print(f"[3] FHIR Bundle: {len(bundle['entry'])} resource "
          f"(1 DiagnosticReport, {n_obs} Observation, Patient, Device)")

    # 4) Simpan
    out = save_bundle(bundle, os.path.join(OUT_DIR, f"{base}_bundle.json"))
    print(f"[4] Tersimpan: {out}")
    print("    (kirim: fhir_converter.send_to_satusehat(bundle, BASE_URL, TOKEN))")
    print("=" * 58)
    return bundle


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run(sys.argv[1])
    else:
        demo = os.path.join(_INPUT, "sample_inputs", "12.jpeg")
        print(f"(demo: {demo})\n")
        run(demo, expected_leads=12)
