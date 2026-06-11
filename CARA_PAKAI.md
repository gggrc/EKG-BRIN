# Cara Pakai EKG-BRIN — Input & Proses

Panduan singkat: **di mana menaruh input** dan **bagaimana menjalankan proses**
digitalisasi EKG (PDF → sinyal mV → klasifikasi → JSON siap-FHIR).

---

## 🟢 Cara tercepat — proses EKG baru (1 perintah)

Dari dalam folder `training/` (env conda `tf_gpu` — sudah ada PyTorch + CUDA):

```bash
# satu file PDF (path bebas, di mana saja)
python run_ecg.py --pdf "D:/EKG/pasien_baru.pdf"

# satu folder berisi banyak PDF (diproses semua, rekursif)
python run_ecg.py --folder "D:/EKG/batch_hari_ini"

# opsi
python run_ecg.py --pdf ekg.pdf --out hasil_saya   # folder output sendiri
python run_ecg.py --pdf ekg.pdf --no-image         # lewati gambar (lebih cepat)
```

**Hasil** (default ke `training/hasil/`):

| File | Isi |
|---|---|
| `<nama>.json` | sinyal mV 12-lead + **klasifikasi AI** + ukuran klinis cetak device + flag mutu (skema siap-FHIR) |
| `<nama>_overlay.png` | output (merah) di atas input (hitam) per-lead — untuk cek visual |

---

## 📥 Di mana menaruh INPUT

Ada **3 jenis input** yang berbeda:

### 1. EKG untuk diproses (yang biasa)
- **Path bebas** → tinggal tunjuk lewat `run_ecg.py --pdf` / `--folder`.
- Atau ikut pola batch: taruh di **`Export/<subfolder>/<nama>.pdf`** (1 PDF per subfolder).
  Lalu jalankan `python process_export.py` (memproses semua `Export/*/*.pdf`).

Format yang didukung: **PDF EKG 12-lead** (layout strips, kalibrasi 25 mm/s, 10 mm/mV).

### 2. Dataset latih model (PTB-XL) — *tidak perlu disentuh untuk pemakaian biasa*
```
ptb-xl-a-large-publicly-available-electrocardiography-dataset-1.0.3/
```
Dipakai hanya saat melatih ulang U-Net & classifier.
> Tidak ikut di GitHub (≈3 GB). Unduh dari PhysioNet bila perlu latih ulang.

### 3. Dataset sintetik (otomatis dibuat dari PTB-XL) — *tidak perlu disentuh*
```
training/dataset/   (images/ masks/ meta/ offsets/ signals/)
```
Dibuat oleh `training/synth_generator.py`. Tidak ikut di GitHub (≈1.7 GB).

---

## ⚙️ Alur proses (apa yang terjadi di dalam)

```
PDF  ─► [1] render @254dpi (10 px/mm)
     ─► [2] U-Net segmentasi trace (checkpoints/unet_best.pt)
     ─► [3] deteksi 12 lane (pakai label teks PDF) + decode mV (momentum-trace)
     ─► [4] kalibrasi (25 mm/s → 250 px/s, 10 mm/mV → 100 px/mV)
     ─► [5] klasifikasi AI 5-superclass (classify/ecgnet_best.pt)
     ─► [6] ukuran klinis dari teks PDF device (HR/PR/QRS/QT/QTc/RV5/SV1/Dx)
     ─► JSON siap-FHIR  +  gambar overlay
```

**Kalibrasi**: 254 dpi = 10 px/mm; 25 mm/s → 250 px/detik; 10 mm/mV → 100 px/mV.
**Sampling output**: 250 Hz, durasi ~7.4 s per lead.

---

## 📤 Output untuk tim FHIR

- `Data_Siap_FHIR/` — kumpulan JSON + **panduan pemetaan field → FHIR R4**
  (`Data_Siap_FHIR/README.md`). Tim FHIR cukup mapping, tak perlu sentuh engine.
- Skema JSON: `ekg-brin/processed-ecg/v1`
  (patient, recording, leads{mV,confidence}, printed_measurements, quality, ai_screening).

---

## ✅ Status validasi (11 EKG nyata)

| Aspek | Hasil |
|---|---|
| Digitalisasi (sintetik, ground-truth) | Pearson **0.924** |
| HR vs device | MAE **1.0 bpm** (100% ≤5 bpm) |
| Konsistensi ritme vs diagnosis device | **10/10 (100%)** |
| Klasifikasi (PTB-XL test) | macro-AUC **0.925** |

> ⚠️ Prototipe tervalidasi pada data uji — untuk pengembangan/penelitian/integrasi
> FHIR. Klasifikasi AI = **skrining**, bukan diagnosis final. Penggunaan klinis ke
> pasien masih perlu validasi lebih luas + review kardiolog + jalur regulasi.

---

## 🧩 Prasyarat (environment)

- Python + conda env `tf_gpu`: PyTorch 2.7 (CUDA cu118), OpenCV, PyMuPDF (fitz),
  NumPy, scikit-learn, wfdb.
- Model yang diperlukan untuk menjalankan (ikut di repo):
  `training/checkpoints/unet_best.pt`, `training/classify/ecgnet_best.pt`,
  `training/classify/norm_stats.npz`.
