# Output Proses EKG (FHIR-ready) — Panduan untuk Tim FHIR

Folder ini berisi hasil **input + proses** digitalisasi EKG (PDF → sinyal numerik mV).
Satu file JSON per rekaman. **Tugas FHIR = memetakan field di sini ke resource FHIR R4.**
Pipeline digitalisasi sudah selesai; tinggal mapping.

## Skema JSON (`ekg-brin/processed-ecg/v1`)

```
{
  "patient":     { id, sex, recording_datetime }
  "recording":   { device, sampling_rate_hz, duration_sec, n_samples,
                   lead_count, units="mV", calibration{...} }
  "leads":       { "<LEAD>": { units:"mV", confidence:"high|low", signal:[...] }, ... }
  "printed_measurements": { heart_rate_bpm, P_ms, PR_ms, QRS_ms, QT_ms, QTc_ms,
                            RV5_mV, SV1_mV, diagnosis }
  "quality":     { low_confidence_leads[], missing_leads[], hr_crosscheck{...}, notes }
}
```

- **Lead** memakai nama baku: I, II, III, aVR, aVL, aVF, V1–V6.
- **signal**: array angka **milivolt (mV)**, urut waktu, panjang = `n_samples`.
- **sampling_rate_hz**: 250 Hz → jarak antar-sampel = `1000/250 = 4 ms`.

## Pemetaan ke FHIR R4 (saran)

| Field JSON | Resource / elemen FHIR |
|---|---|
| `patient.id`, `sex` | **Patient** (identifier, gender) |
| `recording.device` | **Device** |
| `recording.datetime` | `effectiveDateTime` di Observation/DiagnosticReport |
| `leads.<L>.signal` | **Observation** per lead, `valueSampledData` (origin 0 mV, `period = 1000/sampling_rate_hz`, `dimensions=1`, `data` = string angka dipisah spasi) |
| `leads.<L>.confidence="low"` | set `Observation.status="preliminary"` + `note` |
| `printed_measurements.heart_rate_bpm` | **Observation** Heart rate (LOINC 8867-4) |
| `printed_measurements.PR_ms / QRS_ms / QT_ms / QTc_ms` | **Observation** interval (LOINC: PR 8625-6, QRS 8633-0, QT 8634-8, QTc 8636-3) |
| `printed_measurements.RV5_mV / SV1_mV` | **Observation** amplitudo (valueQuantity mV) |
| `printed_measurements.diagnosis` | **DiagnosticReport.conclusion** (+ conclusionCode bila ada SNOMED) |
| semua Observation lead+ukur | direferensi di **DiagnosticReport.result[]** (category CARD) |

### Catatan penting (akuntabilitas medis)
- **Angka klinis** (HR, PR, QRS, QT, RV5, SV1, diagnosis) diambil dari **teks PDF device** (pengukuran resmi pabrikan) — **pakai ini untuk Observation nilai**, bukan menghitung ulang dari sinyal (lebih akurat & defensibel).
- **Sinyal (waveform)** = hasil digitalisasi → simpan sebagai `valueSampledData`.
- **Lead di `low_confidence_leads` / `missing_leads`**: tandai `preliminary` / pakai nilai cetak. Mis. kasus device "Lead Off" otomatis terdeteksi (lead dada ter-flag).
- `quality.hr_crosscheck` membuktikan konsistensi waveform↔device (MAE ~1.1 bpm). Bisa dimasukkan sebagai catatan mutu.

## Contoh ringkas membuat valueSampledData (Python)
```python
import json
d = json.load(open("20251125-160137-0014.json"))
fs = d["recording"]["sampling_rate_hz"]
for lead, blk in d["leads"].items():
    sampled = {
        "origin": {"value": 0, "unit": "mV", "system": "http://unitsofmeasure.org", "code": "mV"},
        "period": 1000.0 / fs,          # ms antar-sampel
        "dimensions": 1,
        "data": " ".join(str(v) for v in blk["signal"]),
    }
    # -> Observation.valueSampledData = sampled
```

Sumber data dihasilkan oleh `training/process_export.py` (pipeline input+proses).
Pertanyaan soal kalibrasi/sinyal: lihat `training/digitize_real.py` & `decode.py`.
