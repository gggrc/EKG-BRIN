"""
output/fhir_converter.py — UniversalECG -> FHIR R4 Bundle (SatuSehat)

Mengubah hasil digitalisasi (dict UniversalECG / hasil panggilan DB) menjadi
FHIR R4 Bundle (type=transaction) yang siap dikirim ke SatuSehat.

Struktur mengikuti IG SatuSehat (Chaidir & Hareva, INJIISCOM 2025):
  - DiagnosticReport  : kontainer laporan (category CARD, code "12-lead ECG report",
                        conclusion + conclusionCode dari klasifikasi, result[] -> Observation)
  - Observation/lead  : satu per lead, valueSampledData (origin mV, period, data)
  - Observation/HR    : valueQuantity (bpm)
  - Patient, Device   : konteks

Catatan kode:
  - Lead II = SNOMED 272730000 (terkonfirmasi dari paper). 11 lead standar lain
    SEHARUSNYA juga ada di SNOMED CT — isi `SNOMED_LEAD` dari SatuSehat IG saat final.
  - Lead yang belum punya kode SNOMED (mis. V7-V9) memakai CodeSystem provisional,
    sesuai pendekatan paper.
"""

import json
import uuid
from datetime import datetime

PROVISIONAL_LEAD_CS = "https://ekg-brin.id/fhir/CodeSystem/ecg-lead"

# Kode SNOMED CT untuk lead. II terkonfirmasi dari paper; sisanya WAJIB diverifikasi.
SNOMED_LEAD = {
    "II": ("272730000", "Lead II"),
}

# Nama tampilan lead standar (untuk fallback provisional)
LEAD_DISPLAY = {
    "I": "Lead I", "II": "Lead II", "III": "Lead III",
    "aVR": "Lead aVR", "aVL": "Lead aVL", "aVF": "Lead aVF",
    "V1": "Lead V1", "V2": "Lead V2", "V3": "Lead V3",
    "V4": "Lead V4", "V5": "Lead V5", "V6": "Lead V6",
    "II_rhythm": "Lead II (rhythm)",
}

# Superclass diagnosis (klasifikasi) -> kode standar (representatif; verifikasi ke IG)
CONCLUSION_CODE = {
    "NORM": ("snomed", "164854000", "Normal ECG", "Z01.30"),
    "MI":   ("snomed", "22298006",  "Myocardial infarction", "I21"),
    "STTC": ("snomed", "164930006", "ECG ST-T abnormal", "R94.31"),
    "CD":   ("snomed", "44808001",  "Conduction disorder of the heart", "I45.9"),
    "HYP":  ("snomed", "164873001", "Electrocardiographic left ventricular hypertrophy", "I51.7"),
}
SNOMED_SYS = "http://snomed.info/sct"
ICD10_SYS = "http://hl7.org/fhir/sid/icd-10"


def _uid(prefix):
    return f"urn:uuid:{prefix}-{uuid.uuid4().hex[:10]}"


def _lead_code(name):
    """CodeableConcept untuk satu lead: SNOMED bila ada, else provisional."""
    if name in SNOMED_LEAD:
        code, disp = SNOMED_LEAD[name]
        return {"coding": [{"system": SNOMED_SYS, "code": code, "display": disp}],
                "text": disp}
    disp = LEAD_DISPLAY.get(name, name)
    return {"coding": [{"system": PROVISIONAL_LEAD_CS, "code": name, "display": disp}],
            "text": disp}


def _lead_observation(name, values, fs, subject_url, device_url, eff):
    period_ms = round(1000.0 / fs, 4) if fs else 2.0
    data = " ".join(f"{round(float(v), 4)}" for v in values)
    res = {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "procedure"}]}],
        "code": _lead_code(name),
        "subject": {"reference": subject_url},
        "effectiveDateTime": eff,
        "valueSampledData": {
            "origin": {"value": 0, "unit": "mV",
                       "system": "http://unitsofmeasure.org", "code": "mV"},
            "period": period_ms,
            "dimensions": 1,
            "data": data,
        },
    }
    if device_url:
        res["device"] = {"reference": device_url}
    return res


def _hr_observation(hr_bpm, subject_url, eff):
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": "8867-4",
                             "display": "Heart rate"}], "text": "Heart rate"},
        "subject": {"reference": subject_url},
        "effectiveDateTime": eff,
        "valueQuantity": {"value": round(float(hr_bpm), 1), "unit": "beats/minute",
                          "system": "http://unitsofmeasure.org", "code": "/min"},
    }


def _entry(resource, fullurl):
    rtype = resource["resourceType"]
    return {"fullUrl": fullurl, "resource": resource,
            "request": {"method": "POST", "url": rtype}}


def to_fhir_bundle(ecg: dict, analysis: dict = None) -> dict:
    """
    ecg      : dict UniversalECG.to_dict() (atau hasil load_ecg dari proses DB).
    analysis : optional {'labels':[...], 'conclusion':str, 'heart_rate_bpm':int}
    """
    analysis = analysis or {}
    leads = ecg.get("leads", {}) or {}
    fs = ecg.get("sampling_rate", 500) or 500
    eff = ecg.get("timestamp") or datetime.now().isoformat()
    meta = ecg.get("metadata", {}) or {}

    patient_id = meta.get("patient_id") or f"PAT-{uuid.uuid4().hex[:6]}"
    patient_url = _uid("patient")
    device_url = _uid("device")

    entries = []

    # Patient
    entries.append(_entry({
        "resourceType": "Patient",
        "identifier": [{"value": str(patient_id)}],
        "gender": (meta.get("sex") or "unknown"),
    }, patient_url))

    # Device
    entries.append(_entry({
        "resourceType": "Device",
        "deviceName": [{"name": ecg.get("device_vendor", "Unknown"),
                        "type": "model-name"}],
    }, device_url))

    # Observations per lead
    obs_urls = []
    for name, values in leads.items():
        ourl = _uid("obs-" + name.lower())
        entries.append(_entry(
            _lead_observation(name, values, fs, patient_url, device_url, eff), ourl))
        obs_urls.append(ourl)

    # Observation HR (bila ada)
    hr = analysis.get("heart_rate_bpm")
    if hr:
        hurl = _uid("obs-hr")
        entries.append(_entry(_hr_observation(hr, patient_url, eff), hurl))
        obs_urls.append(hurl)

    # conclusionCode dari label klasifikasi
    concl_codes = []
    for lbl in analysis.get("labels", []):
        if lbl in CONCLUSION_CODE:
            _, code, disp, icd = CONCLUSION_CODE[lbl]
            concl_codes.append({"coding": [
                {"system": SNOMED_SYS, "code": code, "display": disp},
                {"system": ICD10_SYS, "code": icd},
            ], "text": disp})

    # DiagnosticReport (kontainer)
    dr = {
        "resourceType": "DiagnosticReport",
        "status": "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
            "code": "CARD", "display": "Cardiology"}]}],
        "code": {"text": f"{ecg.get('num_leads', len(leads))}-lead ECG report"},
        "subject": {"reference": patient_url},
        "effectiveDateTime": eff,
        "resultsInterpreter": [{"display": "Automated device algorithm"}],
        "result": [{"reference": u} for u in obs_urls],
    }
    if analysis.get("conclusion"):
        dr["conclusion"] = analysis["conclusion"]
    if concl_codes:
        dr["conclusionCode"] = concl_codes
    entries.insert(0, _entry(dr, _uid("dr-ecg")))

    return {"resourceType": "Bundle", "type": "transaction", "entry": entries}


def save_bundle(bundle: dict, path: str):
    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(bundle, f, indent=2)
    return path


def send_to_satusehat(bundle: dict, base_url: str, access_token: str, timeout=30):
    """
    POST Bundle (transaction) ke server FHIR SatuSehat.
    Butuh OAuth2 access_token (client-credentials). Mengembalikan (status, body).
    """
    try:
        import requests
    except Exception:
        raise RuntimeError("Modul 'requests' tidak terpasang (pip install requests).")
    headers = {"Authorization": f"Bearer {access_token}",
               "Content-Type": "application/fhir+json"}
    r = requests.post(base_url.rstrip("/"), headers=headers,
                      data=json.dumps(bundle), timeout=timeout)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/")
                           else r.text)
