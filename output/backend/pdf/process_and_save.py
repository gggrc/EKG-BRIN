import os
import sys
import uuid
import datetime
import traceback
import torch
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import shutil
import asyncio

from supabase import create_client, Client
from dotenv import load_dotenv

from digitize_real import digitize
from process_export import build

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, '.env'))

app = FastAPI(title="ECG-BRIN Backend FHIR Pipeline API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CKPT = os.path.join(HERE, 'checkpoints', 'unet_best.pt')

# -------------------------------------------------------------------
# KONFIGURASI SUPABASE
# -------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    or os.getenv("SUPABASE_ANON_KEY", "").strip()
    or os.getenv("SUPABASE_KEY", "").strip()
)

print(f"[CONFIG] SUPABASE_URL     : {SUPABASE_URL[:40]}..." if SUPABASE_URL else "[CONFIG] SUPABASE_URL: (kosong!)")
print(f"[CONFIG] SUPABASE_KEY type: {'service_role' if 'service_role' in os.getenv('SUPABASE_SERVICE_ROLE_KEY','') else 'anon/unknown'}")
print(f"[CONFIG] SUPABASE_KEY len : {len(SUPABASE_KEY)} karakter")

if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL tidak dikonfigurasi di .env!")
if not SUPABASE_KEY or len(SUPABASE_KEY) < 20:
    raise RuntimeError("SUPABASE_KEY tidak valid atau belum dikonfigurasi di .env!")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

_jobs: dict[str, dict] = {}
_executor = ThreadPoolExecutor(max_workers=1)


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val))
        return True
    except ValueError:
        return False


def _lead_config_label(n_leads: int) -> str:
    """Ubah jumlah lead ke label general untuk ecg_sessions.lead_configuration."""
    if n_leads >= 12:
        return "12 Leads"
    elif n_leads >= 6:
        return "6 Leads"
    elif n_leads >= 3:
        return "3 Leads"
    else:
        return "1 Lead"


# -------------------------------------------------------------------
# Database Save
# -------------------------------------------------------------------
def save_fhir_to_db(fhir_data: dict, patient_id: str, device_id: str,
                    meta_raw: dict | None = None, user_id: str | None = None) -> str:
    """
    Menyimpan hasil pipeline ke tiga tabel:

    ecg_sessions    — 1 row per sesi (info general: durasi, jumlah lead, status)
    ecg_signal_data — N row per sesi, 1 row per lead (sinyal mV + mutu)
    ecg_analysis    — 1 row per sesi (parameter klinis & diagnosis)
    """
    session_id = str(uuid.uuid4())

    # Validasi UUID
    if not is_valid_uuid(patient_id):
        raise ValueError(f"patient_id '{patient_id}' bukan UUID valid.")
    if not is_valid_uuid(device_id):
        raise ValueError(f"device_id '{device_id}' bukan UUID valid.")
    clean_user_id = user_id if (user_id and is_valid_uuid(user_id)) else None

    # ── Dimensi rekaman ──────────────────────────────────────────────
    if fhir_data.get('resourceType') == 'Observation':
        # Format FHIR standar
        sampling_rate = 500
        duration_sec  = 10
    else:
        # Format ekg-brin/processed-ecg/v1
        rec           = fhir_data.get('recording', {})
        duration_sec  = int(rec.get('duration_sec',     10))
        sampling_rate = int(rec.get('sampling_rate_hz', 500))

    # ── Parse leads -> {lead_name: {signal, confidence}} ────────────
    parsed_leads: dict[str, dict] = {}

    leads_block = fhir_data.get('leads', {})
    if leads_block:
        # Format ekg-brin: leads[nm] = {signal: [...], confidence: 'high'/'low'}
        for nm, d in leads_block.items():
            if isinstance(d, dict):
                sig  = d.get('signal', [])
                conf = d.get('confidence', 'high')
            else:
                sig  = list(d)
                conf = 'high'
            parsed_leads[nm] = {
                'signal':     [round(float(v), 4) for v in sig],
                'confidence': conf,
            }
    elif 'component' in fhir_data:
        # Format FHIR Observation component
        for comp in fhir_data.get('component', []):
            ct = comp.get('code', {}).get('text', '')
            ds = comp.get('valueSampledData', {}).get('data', '')
            if ct and ds:
                sig = [round(float(x), 4) for x in ds.split() if x]
                parsed_leads[ct] = {'signal': sig, 'confidence': 'high'}

    n_leads = len(parsed_leads)

    # ── Printed measurements (untuk ecg_analysis) ────────────────────
    pm = fhir_data.get('printed_measurements', {})

    def _num(key, src: dict):
        v = src.get(key)
        try:
            return float(v) if v not in (None, '', 0) else None
        except (TypeError, ValueError):
            return None

    try:
        print(f"[DB] Sesi {session_id} | {n_leads} lead | {sampling_rate} Hz | {duration_sec}s")

        # ── 1. ecg_sessions ─────────────────────────────────────────────
        # lead_configuration: label GENERAL jumlah lead (lihat gambar)
        session_payload = {
            "session_id":         session_id,
            "patient_id":         patient_id,
            "device_id":          device_id,
            "examination_time":   datetime.datetime.utcnow().isoformat() + "Z",
            "duration_sec":       duration_sec,
            "lead_configuration": _lead_config_label(n_leads),   # "12 Leads" / "6 Leads" / ...
            "status":             "COMPLETED",
            "source_type":        "PDF_CONVERSION",
        }
        if clean_user_id:
            session_payload["created_by"] = clean_user_id

        supabase.table("ecg_sessions").insert(session_payload).execute()
        print(f"[DB] ecg_sessions OK  lead_configuration='{session_payload['lead_configuration']}'")

        # ── 2. ecg_signal_data — 1 row per lead ─────────────────────────
        #
        # Kolom yang disimpan per baris:
        #   lead_type      : nama lead spesifik ("I", "aVR", "V1", ...)
        #   confidence     : "high" / "low" dari lead_quality_flags
        #   sampling_rate  : Hz
        #   sample_count   : jumlah sampel (panjang array)
        #   signal_data    : array mV sebagai JSON  [0.105, 0.095, ...]
        #   min/max_voltage: batas amplitudo lead ini
        #
        lead_rows = []
        for lead_name, info in parsed_leads.items():
            sig  = info['signal']
            conf = info['confidence']
            lead_rows.append({
                "session_id":     session_id,
                "lead_type":      lead_name,          # "I", "II", "aVR", "V1", ...
                "confidence":     conf,               # "high" / "low"
                "sampling_rate":  sampling_rate,
                "sample_count":   len(sig),
                "signal_data":    sig,                # JSONB array mV
                "min_voltage_mv": float(min(sig)) if sig else None,
                "max_voltage_mv": float(max(sig)) if sig else None,
            })

        # Batch insert semua lead sekaligus (1 HTTP request)
        supabase.table("ecg_signal_data").insert(lead_rows).execute()
        lead_names = [r["lead_type"] for r in lead_rows]
        print(f"[DB] ecg_signal_data OK  {n_leads} baris -> {lead_names}")

        # ── 3. ecg_analysis — 1 row per sesi ────────────────────────────
        heart_rate = (
            int(pm['heart_rate_bpm']) if pm.get('heart_rate_bpm')
            else (int(_num('heart_rate', meta_raw or {})) if _num('heart_rate', meta_raw or {}) else None)
        )

        # Diagnosis: gabungkan teks device + label AI screening (jika ada)
        diagnosis = (
            pm.get('diagnosis')
            or (meta_raw or {}).get('text_diagnosis')
            or (meta_raw or {}).get('raw_text')
        )
        ai = fhir_data.get('ai_screening')
        if ai and ai.get('top_label'):
            ai_note = (
                f" | AI Screening: {ai['top_label']} ({ai['top_label_desc']})"
                f" — prob={ai['probabilities'].get(ai['top_label']):.3f}"
            )
            diagnosis = (diagnosis or '') + ai_note

        analysis_payload = {
            "analysis_id":     str(uuid.uuid4()),
            "session_id":      session_id,
            "heart_rate_bpm":  heart_rate,
            "rhythm_type":     (meta_raw or {}).get('rhythm') or (meta_raw or {}).get('interpretation'),
            "pr_interval":     _num('PR_ms',  pm) or _num('pr_interval',  meta_raw or {}),
            "qrs_duration":    _num('QRS_ms', pm) or _num('qrs_duration', meta_raw or {}),
            "qt_interval":     _num('QT_ms',  pm) or _num('qt_interval',  meta_raw or {}),
            "qtc_interval_ms": _num('QTc_ms', pm) or _num('qtc_interval', meta_raw or {}),
            "electrical_axis": _num('axis', meta_raw or {}),
            "diagnosis":       diagnosis,
        }
        # Hapus field None (kecuali PK & FK) agar tidak konflik constraint
        analysis_payload = {
            k: v for k, v in analysis_payload.items()
            if v is not None or k in ("analysis_id", "session_id")
        }
        supabase.table("ecg_analysis").insert(analysis_payload).execute()
        print(f"[DB] ecg_analysis OK  HR={heart_rate} diagnosis='{diagnosis}'")

        print(f"[DB] ✓ Semua tersimpan — session_id={session_id}")
        return session_id

    except Exception as e:
        print(f"[DB ERROR]\n{traceback.format_exc()}")
        if '42501' in str(e) or 'permission denied' in str(e).lower():
            print(
                "[DB HINT] Error 42501: jalankan migrate_ecg_per_lead.sql "
                "di Supabase SQL Editor untuk memperbaiki permission & struktur tabel."
            )
        raise RuntimeError(f"Database error: {e}")


# -------------------------------------------------------------------
# Pipeline Background Thread
# -------------------------------------------------------------------
def _run_pipeline_thread(job_id: str, pdf_path: str,
                          patient_id: str, device_id: str,
                          user_id: str | None):
    try:
        _jobs[job_id]["status"] = "processing"
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[Job {job_id}] Device: {dev}")

        leads, meta = digitize(pdf_path, CKPT, dev, os.path.join(HERE, 'export_test'))
        fhir_data   = build(pdf_path, leads, meta)
        session_id  = save_fhir_to_db(fhir_data, patient_id, device_id, meta, user_id)

        _jobs[job_id].update({"status": "done", "session_id": session_id})
        print(f"[Job {job_id}] Selesai — session_id={session_id}")
    except Exception as e:
        print(f"[Job {job_id}] ERROR:\n{traceback.format_exc()}")
        _jobs[job_id].update({"status": "error", "error": str(e)})
    finally:
        try:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
        except Exception:
            pass


# -------------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------------
@app.post("/api/v1/process-ecg")
async def process_ecg_endpoint(
    patient_id: str        = Form(...),
    device_id:  str        = Form(...),
    user_id:    str        = Form(None),
    file:       UploadFile = File(...),
):
    clean_patient_id   = patient_id.strip()
    clean_device_id    = device_id.strip()
    normalised_user_id = (user_id.strip() or None) if user_id else None

    if not clean_patient_id or not is_valid_uuid(clean_patient_id):
        raise HTTPException(422, "patient_id bukan UUID yang sah.")
    if not clean_device_id or not is_valid_uuid(clean_device_id):
        raise HTTPException(422, "device_id bukan UUID yang sah.")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(422, "Hanya file PDF yang didukung.")

    temp_dir  = os.path.join(HERE, "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"raw_{uuid.uuid4()}.pdf")

    with open(temp_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "pending", "session_id": None, "error": None}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        _executor,
        _run_pipeline_thread,
        job_id, temp_path, clean_patient_id, clean_device_id, normalised_user_id,
    )

    return {"status": "accepted", "job_id": job_id, "message": "Pipeline dimulai."}


@app.get("/api/v1/job/{job_id}")
async def get_job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, f"Job '{job_id}' tidak ditemukan.")
    if job["status"] == "error":
        return JSONResponse(
            status_code=500,
            content={"status": "error", "job_id": job_id, "error": job["error"]},
        )
    return {"status": job["status"], "job_id": job_id, "session_id": job.get("session_id")}


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print("Starting FastAPI Server pada http://0.0.0.0:8000")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        if len(sys.argv) > 3:
            job_id = "cli"
            _jobs[job_id] = {"status": "pending", "session_id": None, "error": None}
            uid = sys.argv[4] if len(sys.argv) > 4 else None
            _run_pipeline_thread(job_id, sys.argv[1], sys.argv[2], sys.argv[3], uid)
        else:
            print("Format: python process_and_save.py <path_pdf> <patient_id> <device_id> [user_id]")