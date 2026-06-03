# ECG Input Pipeline 🫀

Pipeline ini berfungsi sebagai "pintu gerbang utama" untuk memproses berbagai format file EKG mentah (Gambar Scan EKG, File WFDB/MIT-BIH, dan XML) menjadi satu format standar (JSON Seragam) yang siap dimasukkan ke dalam Model AI / Core System.

Sistem ini didesain sangat tangguh (Robust), dilengkapi dengan:
- **Konversi Multi-Format:** Mengubah `.pdf`, `.png`, `.jpg`, `.hea/.dat`, `.xml` secara otomatis.
- **Computer Vision & OCR:** Mendeteksi garis kalibrasi EKG absolut dan menggunakan Tesseract OCR untuk membaca label lead.
- **Dynamic Layout Parser:** Mengekstrak gelombang dari layout apapun (3x4 klinis, 12 strips, dll).
- **Batch Processing:** Memproses ribuan file sekaligus tanpa hambatan.

---

## 🛠️ Instalasi

### 1. Install Dependencies Python
Pipeline ini sangat mudah diinstal. Cukup jalankan perintah ini di terminal Anda:
```bash
pip install -r requirements.txt
```
*Ini akan otomatis menginstal library penting seperti NumPy, OpenCV (cv2), WFDB, PyMuPDF, Matplotlib, dan PyTesseract.*

### 2. Install Tesseract OCR (Wajib untuk Sistem Adaptif)
Karena pipeline ini menggunakan Computer Vision pintar berbasis teks:
1. Unduh dan Install Tesseract OCR untuk Windows dari [sini](https://github.com/UB-Mannheim/tesseract/wiki).
2. Pastikan terinstal di: `C:\Program Files\Tesseract-OCR\tesseract.exe`
3. Jika lokasi instalasi berbeda, ubah path-nya di dalam file `config.py`.

---

## 🚀 Cara Penggunaan (Workflow)

Pipeline ini mengadopsi sistem Folder Masuk & Keluar (*In/Out Queue*).

### Skenario 1: Simulasi Data Input dari PTB-XL (Testing)
Jika Anda tidak punya file gambar EKG mentah, Anda bisa membuatnya sendiri menggunakan dataset PTB-XL.
1. Jalankan `python regenerate_real_samples.py`.
2. Script ini akan membuat berbagai jenis format (`.png`, `.pdf`, WFDB `.hea`, `.xml`) berdasarkan data medis sungguhan.
3. Pindahkan file-file hasil simulasi tersebut dari folder `sample_inputs` ke folder **`input_batch`**.

### Skenario 2: Memproses File Secara Massal (Batch Process)
1. Masukkan semua file EKG mentah Anda ke dalam folder **`input_batch/`**.
2. Jalankan perintah:
   ```bash
   python batch_process.py
   ```
3. Script ini akan memproses semuanya.
   - File yang BERHASIL diekstrak gelombangnya akan dipindahkan ke **`input_processed/`**.
   - Output hasil ekstraknya (berupa file JSON) akan disimpan di **`output_handoff/`**.
   - File yang ERROR / rusak akan dipindahkan ke **`input_error/`**.

### Skenario 3: Memverifikasi Hasil (Visualisasi)
Untuk memastikan data JSON yang dihasilkan benar-benar akurat 100% dengan gambar aslinya:
1. Jalankan:
   ```bash
   python plot_json.py output_handoff/NAMA_FILE.json
   ```
2. Anda bisa menambahkan bendera `--no-show` jika hanya ingin menyimpan fotonya.
3. Hasil foto grafiknya akan otomatis tersimpan di folder **`output_plots/`**.

---

## 📂 Struktur & Penjelasan File

**File Inti (Penting):**
*   `batch_process.py`: *Script utama* yang Anda jalankan untuk memproses massal seluruh file di `input_batch`.
*   `watch_folder.py`: Versi otomatis dari batch. Jika dijalankan, ia akan diam (standby) memantau folder. Begitu Anda mencemplungkan gambar ke folder, ia langsung memprosesnya saat itu juga (Real-time).
*   `config.py`: Tempat mengatur path Tesseract OCR dan parameter global.
*   `ecg_input_router.py`: "Otak pengarah". Ia yang mendeteksi "oh ini PDF, kirim ke parser PDF", "oh ini WFDB, kirim ke parser WFDB".
*   `universal_schema.py`: Cetak biru (blueprint) data. Memastikan bentuk datanya konsisten tidak peduli apa format awalnya.
*   `export_to_handoff.py`: Mengubah data dari `universal_schema.py` menjadi file JSON akhir.
*   `plot_json.py`: Pembuat grafik (Plotter) untuk mengecek kualitas ekstrak JSON.
*   `parsers/parse_image.py`: *Core Engine* (Computer Vision) untuk mengekstrak gelombang dari gambar & PDF.
*   `parsers/parse_wfdb.py`: Mengekstrak EKG digital `.hea` dan `.dat`.
*   `parsers/parse_xml.py`: Mengekstrak format medis XML (HL7/Philips).

**File Bantuan Data (Utility):**
*   `regenerate_real_samples.py`: Meng-generate dummy file EKG berdasarkan database sungguhan (PTB-XL).
*   `ptbxl_metadata.py`: Modul pembantu untuk script regenerasi di atas.
*   `ecg_to_pdf.py`: Modul pembantu untuk mengubah sinyal jadi dokumen EKG PDF.

### 🗑️ File yang Boleh Anda Hapus (Redundan / Tidak Dipakai)
Karena proses eksperimen sudah selesai, beberapa file *scratch/testing* lama bisa Anda HAPUS sendiri agar repositori lebih bersih saat diserahkan ke tim Anda:
- `generate_pdf_samples.py` (sudah diganti `regenerate_real_samples.py`)
- `generate_test_samples.py`
- `quick_plot_verify.py`
- `test_parsers_v2.py`
- `verify_output.py`
