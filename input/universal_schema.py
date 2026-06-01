from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
from datetime import datetime

@dataclass
class ECGMetadata:
    """Metadata pasien dan rekaman dari ptbxl_database.csv atau sumber lain."""
    patient_id:    str   = "unknown"
    age:           Optional[int]   = None
    sex:           Optional[str]   = None      # 'M' atau 'F'
    height:        Optional[float] = None      # cm
    weight:        Optional[float] = None      # kg
    report:        Optional[str]   = None      # diagnosis teks bebas
    scp_codes:     Optional[str]   = None      # kode diagnosis PTB-XL
    heart_axis:    Optional[str]   = None
    infarction_stadium: Optional[str] = None
    validated_by_human: Optional[bool] = None
    device:        Optional[str]   = None      # nama alat EKG
    recording_date: Optional[str]  = None      # ISO 8601


@dataclass
class UniversalECG:
    """
    Output standar dari semua parser.
    Semua nilai sinyal dalam mV, sampling_rate dalam Hz.
    Skala disimpan eksplisit agar round-trip (JSON→PDF) akurat.
    """
    # ── Sinyal ────────────────────────────────────────────────────
    leads:          Dict[str, List[float]]   # sinyal per lead dalam mV
    sampling_rate:  int                       # Hz
    duration_sec:   float
    num_leads:      int                       # 6 atau 12

    # ── Skala (untuk render ulang yang akurat) ───────────────────
    units:          str   = "mV"              # selalu mV
    mv_per_mm:      float = 0.1              # standar: 10mm/mV → 0.1 mV/mm
    mm_per_sec:     float = 25.0             # standar: 25 mm/s
    y_min:          float = -2.5             # batas bawah plot (mV)
    y_max:          float = 2.5              # batas atas plot (mV)

    # ── Provenance ───────────────────────────────────────────────
    input_format:   str   = "unknown"
    device_vendor:  str   = "unknown"
    timestamp:      str   = field(
        default_factory=lambda: datetime.now().isoformat()
    )
    notes:          Optional[str] = None

    # ── Metadata pasien ──────────────────────────────────────────
    metadata:       ECGMetadata = field(default_factory=ECGMetadata)

    # ── Calibration info (NEW — for accurate round-trip) ─────────
    calibration:    Optional[dict] = None
    # Structure:
    # {
    #     "px_per_mV":       100.0,
    #     "px_per_sec":      250.0,
    #     "method":          "calibration_pulse" | "grid_spacing" | "estimated",
    #     "confidence":      0.95,
    #     "gain_mm_per_mV":  10.0,
    #     "speed_mm_per_sec": 25.0,
    # }

    # ── Original layout info (NEW — for faithful restoration) ────
    original_layout: Optional[dict] = None
    # Structure:
    # {
    #     "type":               "clinical_3x4" | "separated_4x3" | "strips_N",
    #     "rows":               3,
    #     "cols":               4,
    #     "has_rhythm_strip":   true,
    #     "rhythm_strip_lead":  "II",
    # }

    # ── Per-lead amplitude info (NEW — preserve relative ratios) ─
    lead_amplitudes: Optional[Dict[str, dict]] = None
    # Structure:
    # {
    #     "I":  {"std_mV": 0.21, "range_mV": 1.2, "baseline_mV": 0.0},
    #     "V4": {"std_mV": 0.85, "range_mV": 3.5, "baseline_mV": 0.1},
    #     ...
    # }

    def to_dict(self) -> dict:
        result = {
            "leads":         self.leads,
            "sampling_rate": self.sampling_rate,
            "duration_sec":  self.duration_sec,
            "num_leads":     self.num_leads,
            "units":         self.units,
            "scale": {
                "mv_per_mm":  self.mv_per_mm,
                "mm_per_sec": self.mm_per_sec,
                "y_min":      self.y_min,
                "y_max":      self.y_max,
            },
            "input_format":  self.input_format,
            "device_vendor": self.device_vendor,
            "timestamp":     self.timestamp,
            "notes":         self.notes,
            "metadata": {
                "patient_id":    self.metadata.patient_id,
                "age":           self.metadata.age,
                "sex":           self.metadata.sex,
                "height":        self.metadata.height,
                "weight":        self.metadata.weight,
                "report":        self.metadata.report,
                "scp_codes":     self.metadata.scp_codes,
                "heart_axis":    self.metadata.heart_axis,
                "device":        self.metadata.device,
                "recording_date": self.metadata.recording_date,
            },
        }

        # Add new optional fields if present
        if self.calibration is not None:
            result["calibration"] = self.calibration
        if self.original_layout is not None:
            result["original_layout"] = self.original_layout
        if self.lead_amplitudes is not None:
            result["lead_amplitudes"] = self.lead_amplitudes

        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


# Lead sets standar
LEADS_6  = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
LEADS_12 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
             'V1', 'V2', 'V3', 'V4', 'V5', 'V6']

# Skala standar EKG klinis
STANDARD_SCALE = {
    "mv_per_mm":  0.1,    # 10 mm/mV
    "mm_per_sec": 25.0,   # 25 mm/s
    "y_min":      -2.5,
    "y_max":       2.5,
}