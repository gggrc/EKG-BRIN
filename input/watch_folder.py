"""
watch_folder.py — Automasi ECG Input Pipeline

Cara pakai:
    python watch_folder.py

Taruh file apapun ke folder `input_watch/`:
    - PDF laporan EKG (berbagai vendor)
    - CSV sinyal EKG
    - PNG/JPG foto atau scan EKG
    - JSON dari alat IoT/BLE
    - WFDB (.hea) dari PhysioNet

Sistem otomatis mendeteksi format, memproses, dan menyimpan
output JSON ke folder `output_handoff/`.

Auto-reload: kalau ada file .py yang berubah, proses otomatis
restart sehingga kode terbaru langsung aktif tanpa perlu
menghentikan dan menjalankan ulang secara manual.

Tidak perlu ubah kode apapun untuk tambah file baru.
"""

import os
import sys
import time
import json
import shutil
import subprocess
from datetime import datetime

# ── Konfigurasi folder ───────────────────────────────────────────
WATCH_DIR   = "input_watch"     # taruh file input di sini
OUTPUT_DIR  = "output_handoff"  # output JSON tersimpan di sini
DONE_DIR    = "input_processed" # file yang sudah diproses dipindah ke sini
ERROR_DIR   = "input_error"     # file yang gagal diproses
POLL_SEC    = 3                 # cek folder setiap N detik
RELOAD_SEC  = 2                 # cek perubahan .py setiap N detik

# Format yang didukung
SUPPORTED_EXTENSIONS = {
    '.hea', '.csv', '.txt',
    '.png', '.jpg', '.jpeg',
    '.json', '.pdf', '.xml'
}

# Env var untuk membedakan reloader vs worker process
_WORKER_ENV = "_ECG_WORKER_PROCESS"

# File yang sedang diproses (hindari proses dobel)
_processing = set()


# ════════════════════════════════════════════════════════════════
#  AUTO-RELOADER
# ════════════════════════════════════════════════════════════════

def _collect_py_mtimes(base_dir: str) -> dict:
    """Kumpulkan semua file .py dan mtime-nya (rekursif, skip venv)."""
    mtimes = {}
    skip = {'venv', '.venv', '__pycache__', '.git', 'node_modules'}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                try:
                    mtimes[path] = os.path.getmtime(path)
                except OSError:
                    pass
    return mtimes


def _run_reloader():
    """
    Reloader loop: jalankan worker sebagai subprocess,
    restart kalau ada .py yang berubah atau worker crash.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    print("=" * 55)
    print("  [reload] ECG Input Pipeline — auto-reload ON")
    print("=" * 55)
    print("  [reload] Tekan Ctrl+C untuk berhenti sepenuhnya.")
    print()

    env = os.environ.copy()
    env[_WORKER_ENV] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    mtimes = _collect_py_mtimes(base_dir)
    worker = None

    def start_worker():
        return subprocess.Popen(
            [sys.executable] + sys.argv,
            env=env,
            cwd=base_dir,
        )

    worker = start_worker()

    try:
        while True:
            time.sleep(RELOAD_SEC)

            # Cek apakah worker masih hidup
            if worker.poll() is not None:
                code = worker.returncode
                if code == 0:
                    print("\n  [reload] Worker selesai, restart...")
                else:
                    print(f"\n  [reload] Worker berhenti (exit={code}), restart dalam 2s...")
                    time.sleep(2)
                mtimes = _collect_py_mtimes(base_dir)
                worker = start_worker()
                continue

            # Cek perubahan file .py
            new_mtimes = _collect_py_mtimes(base_dir)
            changed = []
            for path, mtime in new_mtimes.items():
                if mtimes.get(path) != mtime:
                    changed.append(os.path.relpath(path, base_dir))
            for path in set(mtimes) - set(new_mtimes):
                changed.append(f"[deleted] {os.path.relpath(path, base_dir)}")

            if changed:
                print(f"\n  [reload] Perubahan terdeteksi:")
                for c in changed:
                    print(f"           - {c}")
                print("  [reload] Restart worker...\n")
                worker.terminate()
                try:
                    worker.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    worker.kill()
                mtimes = new_mtimes
                worker = start_worker()

    except KeyboardInterrupt:
        print("\n\n  [reload] Watch mode dihentikan.")
        if worker and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=3)
            except subprocess.TimeoutExpired:
                worker.kill()


# ════════════════════════════════════════════════════════════════
#  WORKER — logika pemrosesan EKG
# ════════════════════════════════════════════════════════════════

def setup_folders():
    for folder in [WATCH_DIR, OUTPUT_DIR, DONE_DIR, ERROR_DIR]:
        os.makedirs(folder, exist_ok=True)


def get_output_path(input_path: str) -> str:
    """Generate nama file output JSON dari nama file input."""
    basename = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{basename}_{timestamp}.json")


def process_file(file_path: str):
    """Proses satu file: parse -> export JSON -> pindah ke done/error."""
    from ecg_input_router import load_ecg

    # Normalisasi ke absolute path agar backslash Windows (mis. \vendor -> \v)
    # tidak diinterpretasi sebagai escape character oleh opencv/numpy.
    file_path = os.path.abspath(file_path)
    filename = os.path.basename(file_path)

    print(f"\n{'='*55}")
    print(f"  [in]  File baru: {filename}")
    print(f"  [in]  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    try:
        # Khusus WFDB — strip ekstensi .hea karena wfdb.rdrecord tidak pakai ekstensi
        load_path = file_path
        if file_path.endswith('.hea'):
            load_path = os.path.splitext(file_path)[0]
            dat_path = load_path + '.dat'
            if not os.path.exists(dat_path):
                raise FileNotFoundError(
                    f"File .dat tidak ditemukan: {dat_path}\n"
                    f"Untuk WFDB, taruh .hea dan .dat bersama-sama."
                )

        # Parse file
        ecg = load_ecg(load_path, vendor=f"Auto-detected from {filename}")

        # Export ke JSON
        output_path = get_output_path(file_path)
        result = ecg.to_dict()

        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        # Pindah file input ke folder done
        done_path = os.path.join(DONE_DIR, filename)
        shutil.move(file_path, done_path)

        # Kalau WFDB, pindah juga .dat-nya
        if file_path.endswith('.hea'):
            dat_src = os.path.splitext(file_path)[0] + '.dat'
            if os.path.exists(dat_src):
                shutil.move(dat_src, os.path.join(DONE_DIR,
                    os.path.basename(dat_src)))

        print(f"  [ok]  Berhasil diproses!")
        print(f"  [ok]  Lead    : {list(ecg.leads.keys())}")
        print(f"  [ok]  Rate    : {ecg.sampling_rate} Hz")
        print(f"  [ok]  Vendor  : {ecg.device_vendor}")
        print(f"  [ok]  Patient : {ecg.metadata.patient_id}")
        if ecg.notes:
            print(f"  [ok]  Notes   : {ecg.notes}")
        print(f"  [ok]  Output  : {output_path}")

    except Exception as e:
        print(f"  [err] GAGAL: {e}")

        # Pindah ke error folder
        error_path = os.path.join(ERROR_DIR, filename)
        try:
            shutil.move(file_path, error_path)
        except Exception:
            pass

        # Simpan log error
        error_log = os.path.join(ERROR_DIR, f"{filename}.error.txt")
        with open(error_log, 'w') as f:
            f.write(f"File: {filename}\n")
            f.write(f"Waktu: {datetime.now().isoformat()}\n")
            f.write(f"Error: {str(e)}\n")

    finally:
        _processing.discard(file_path)


def scan_and_process():
    """Scan folder input, proses semua file baru yang ditemukan."""
    if not os.path.exists(WATCH_DIR):
        return

    for filename in os.listdir(WATCH_DIR):
        file_path = os.path.join(WATCH_DIR, filename)

        # Skip folder, hidden files, file yang sedang diproses
        if not os.path.isfile(file_path):
            continue
        if filename.startswith('.') or filename.startswith('~'):
            continue
        if file_path in _processing:
            continue

        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        # Skip .dat — diproses bersama .hea
        if ext == '.dat':
            continue

        # Tunggu file selesai di-copy (size stabil)
        try:
            size1 = os.path.getsize(file_path)
            time.sleep(0.5)
            size2 = os.path.getsize(file_path)
            if size1 != size2:
                continue  # file masih di-copy
        except Exception:
            continue

        _processing.add(file_path)
        process_file(file_path)


def _run_worker():
    """Worker: loop utama pemrosesan file."""
    setup_folders()

    print("=" * 55)
    print("  ECG Input Pipeline — Watch Mode")
    print("=" * 55)
    print(f"  Watching : {os.path.abspath(WATCH_DIR)}")
    print(f"  Output   : {os.path.abspath(OUTPUT_DIR)}")
    print(f"  Done     : {os.path.abspath(DONE_DIR)}")
    print(f"  Error    : {os.path.abspath(ERROR_DIR)}")
    print(f"  Poll     : setiap {POLL_SEC} detik")
    print("=" * 55)
    print()
    print("  Format yang didukung:")
    print("    PDF   -> laporan EKG klinis (multi-vendor)")
    print("    CSV   -> data sinyal dari alat portable")
    print("    PNG/JPG -> foto atau scan EKG")
    print("    JSON  -> output alat IoT/BLE")
    print("    HEA   -> WFDB format (PhysioNet) -- taruh .hea + .dat")
    print()
    print("  Taruh file ke folder: input_watch/")
    print("  Output JSON ada di  : output_handoff/")
    print()

    # Proses file yang mungkin sudah ada di folder sebelum watch dimulai
    existing = [f for f in os.listdir(WATCH_DIR)
                if os.path.isfile(os.path.join(WATCH_DIR, f))]
    if existing:
        print(f"  Ditemukan {len(existing)} file yang belum diproses...")
        scan_and_process()

    # Loop utama
    try:
        while True:
            scan_and_process()
            time.sleep(POLL_SEC)
    except KeyboardInterrupt:
        print("\n\n  Watch mode dihentikan.")


if __name__ == "__main__":
    if os.environ.get(_WORKER_ENV):
        # Proses ini adalah worker yang dispawn oleh reloader
        _run_worker()
    else:
        # Proses pertama — jalankan sebagai reloader
        _run_reloader()
