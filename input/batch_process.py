"""
batch_process.py — Batch Processor untuk ECG Input Pipeline

Cara pakai:
    python batch_process.py

Script ini akan membaca SEMUA file di dalam folder `input_batch/`,
memprosesnya sekaligus, dan menyimpan hasilnya di `output_handoff/`.
File yang berhasil diproses akan dipindah ke `input_processed/`.
File yang gagal akan dipindah ke `input_error/`.

Sangat cocok untuk WFDB (.hea + .dat) karena script ini akan mencari
pasangannya terlebih dahulu sebelum memproses, menghindari error karena
file belum selesai di-copy.
"""

import os
import json
import shutil
import gc
from datetime import datetime

# ── Konfigurasi folder ───────────────────────────────────────────
INPUT_DIR   = "input_batch"     # taruh file input di sini
OUTPUT_DIR  = "output_handoff"  # output JSON tersimpan di sini
DONE_DIR    = "input_processed" # file yang sudah diproses dipindah ke sini
ERROR_DIR   = "input_error"     # file yang gagal diproses

# Format yang didukung
SUPPORTED_EXTENSIONS = {
    '.hea', '.csv', '.txt',
    '.png', '.jpg', '.jpeg',
    '.json', '.pdf', '.xml'
}

def setup_folders():
    for folder in [INPUT_DIR, OUTPUT_DIR, DONE_DIR, ERROR_DIR]:
        os.makedirs(folder, exist_ok=True)


def get_output_path(input_path: str) -> str:
    """Generate nama file output JSON dari nama file input."""
    basename = os.path.splitext(os.path.basename(input_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(OUTPUT_DIR, f"{basename}_{timestamp}.json")


def process_batch():
    setup_folders()
    
    files = [f for f in os.listdir(INPUT_DIR) if os.path.isfile(os.path.join(INPUT_DIR, f))]
    
    if not files:
        print(f"[Info] Folder '{INPUT_DIR}' kosong. Tidak ada yang perlu diproses.")
        return

    print("=" * 55)
    print("  [Batch] Memulai Batch Processing")
    print("=" * 55)
    print(f"  Ditemukan {len(files)} file di '{INPUT_DIR}'\n")

    from ecg_input_router import load_ecg

    processed_count = 0
    error_count = 0

    for filename in files:
        file_path = os.path.join(INPUT_DIR, filename)
        file_path = os.path.abspath(file_path)
        ext = os.path.splitext(filename)[1].lower()

        # Skip file yang tidak didukung atau hidden file
        if ext not in SUPPORTED_EXTENSIONS or filename.startswith('.') or filename.startswith('~'):
            # Skip .dat silently, karena akan diproses berbarengan dengan .hea
            if ext != '.dat':
                print(f"  [Skip] {filename} (Format tidak didukung)")
            continue

        print(f"  [Process] Memproses: {filename}")

        try:
            load_path = file_path

            # Khusus WFDB — Pastikan .dat ada, lalu strip .hea
            if ext == '.hea':
                load_path = os.path.splitext(file_path)[0]
                dat_path = load_path + '.dat'
                if not os.path.exists(dat_path):
                    print(f"     [Error] GAGAL: File .dat tidak ditemukan untuk {filename}!")
                    error_count += 1
                    continue

            # Infer expected leads from filename for images
            expected_leads = None
            lower_name = filename.lower()
            if "6lead" in lower_name or "6-lead" in lower_name or "6l" in lower_name or lower_name.startswith("6."):
                expected_leads = 6
            elif "12lead" in lower_name or "12-lead" in lower_name or "12l" in lower_name or lower_name.startswith("12."):
                expected_leads = 12
            elif "vendor_scan.png" in lower_name:
                expected_leads = 6
            elif "test_ecg_image.png" in lower_name:
                expected_leads = 6

            # Parse file
            ecg = load_ecg(load_path, vendor=f"Auto-detected from {filename}", expected_leads=expected_leads)

            # Export ke JSON
            output_path = get_output_path(file_path)
            result = ecg.to_dict()

            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)

            # Pindah file ke folder done
            done_path = os.path.join(DONE_DIR, filename)
            shutil.move(file_path, done_path)

            # Kalau WFDB, pindah juga .dat-nya
            if ext == '.hea':
                dat_src = load_path + '.dat'
                if os.path.exists(dat_src):
                    shutil.move(dat_src, os.path.join(DONE_DIR, os.path.basename(dat_src)))

            print(f"     [OK] Berhasil -> {os.path.basename(output_path)}")
            processed_count += 1

        except Exception as e:
            print(f"     [Error] GAGAL: {e}")
            error_count += 1

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
            # Paksa garbage collector bekerja untuk menghapus cache/array besar 
            # dari OpenCV dan Pandas di memori agar memori tidak penuh (OutOfMemoryError)
            gc.collect()

    print("\n" + "=" * 55)
    print(f"  [Selesai] Batch selesai! Berhasil: {processed_count} | Gagal: {error_count}")
    print("=" * 55)


if __name__ == "__main__":
    process_batch()
