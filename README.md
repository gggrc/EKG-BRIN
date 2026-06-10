# EKG-BRIN — Digitalisasi & Klasifikasi EKG (U-Net)

Mengubah EKG analog (PDF/kertas) → **sinyal digital (mV)** → **klasifikasi diagnosis** →
data **siap FHIR** untuk SatuSehat.

```
  INPUT                PROSES (engine U-Net)              OUTPUT
  ┌─────────┐    ┌──────────────────────────────┐   ┌──────────────────┐
  │ PDF EKG │ →  │ 1. Digitalisasi (U-Net)      │ → │ sinyal mV /lead  │
  │ Export/ │    │ 2. Deteksi 12 lane + decode  │   │ + diagnosis      │
  │         │    │ 3. Klasifikasi (ECGNet)      │   │ → Data_Siap_FHIR/│
  └─────────┘    └──────────────────────────────┘   │    FHIR/         │
                                                     └──────────────────┘
```

## 📁 Struktur folder

| Folder | Isi | Untuk |
|---|---|---|
| **`Export/`** | **INPUT** — PDF EKG nyata | data masukan |
| **`training/`** | **PROSES** — engine U-Net (kode + model) | digitalisasi + klasifikasi |
| **`Data_Siap_FHIR/`** | **OUTPUT** — JSON siap FHIR + panduan | ⭐ **handoff ke tim FHIR** |
| `output/ekg_fhir/` | App FHIR (Flutter) | dikerjakan tim FHIR |
| `ptb-xl-...1.0.3/` | Dataset pelatihan PTB-XL | latih ulang model |
| `input/parsers/` | `layout_detector.py` (util deteksi grid) | dipakai engine |

> Catatan: folder engine bernama `training/` (fungsinya = PROSES). Bisa di-rename
> ke `proses/` nanti saat folder tidak sedang dibuka di VSCode.

## ⭐ Untuk tim FHIR — MULAI DI SINI
Buka **`Data_Siap_FHIR/`**:
- `*.json` — 11 rekaman: data EKG digital + pengukuran klinis device + flag mutu
- `README.md` — **panduan pemetaan field → FHIR R4** (lengkap dengan contoh kode)

Tinggal mapping field ke resource FHIR. Tidak perlu menyentuh kode engine.

## ▶️ Cara tercepat — proses EKG baru (1 perintah)
Dari dalam `training/` (env: `tf_gpu`):

```bash
python run_ecg.py --pdf "C:/path/ekg_baru.pdf"     # 1 file
python run_ecg.py --folder "C:/folder_pdf"          # banyak file sekaligus
```
Hasil ke `training/hasil/`:
- `<nama>.json` — sinyal mV 12-lead + **klasifikasi AI** (NORM/MI/STTC/CD/HYP) +
  ukuran klinis cetak device + flag mutu (skema siap-FHIR)
- `<nama>_overlay.png` — output (merah) di atas input (hitam) per-lead, untuk cek visual

## 🔧 Menjalankan engine (batch & utilitas)
Dari dalam `training/` (env: `tf_gpu` — ada torch+CUDA):

```bash
python process_export.py     # Digitalisasi semua PDF -> output FHIR-ready
python clinical_check.py     # Validasi klinis (HR/ritme vs diagnosis device)
python sidebyside_all.py     # Perbandingan input|output 1:1 -> export_test/sidebyside/
python zoom_all.py           # Overlay per-lead diperbesar -> export_test/zoom/
python classify/train_cls.py # Klasifikasi 5 superclass -> classify/ecgnet_best.pt
```

## 📊 Hasil validasi (11 EKG Export)
- **Digitalisasi:** sintetik Pearson r=0.955; nyata HR **MAE 1.0 bpm**
- **Konsistensi ritme vs diagnosis device:** **100%** (10/10)
- **Morfologi ST-T** (iskemia): median r=0.95
- **Klasifikasi:** macro-AUC **0.925** (NORM 0.95, MI 0.92, STTC 0.94, CD 0.92, HYP 0.90)

## ⚠️ Status
Prototipe **tervalidasi pada data uji** — untuk **pengembangan/penelitian/integrasi FHIR**.
Untuk **penggunaan klinis ke pasien** masih perlu: validasi lebih luas (banyak merek device),
review kardiolog, dan jalur regulasi.

---
File engine inti: `digitize_real.py` (digitalisasi), `decode.py` (decode mV),
`unet.py`/`train.py` (model segmentasi), `classify/` (klasifikasi),
`process_export.py` (pipeline), `clinical_check.py` (validasi).
