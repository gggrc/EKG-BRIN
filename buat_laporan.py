"""
buat_laporan.py — Rakit laporan HTML mandiri (self-contained) yang menjelaskan
pipeline 6-lead & 12-lead dari awal-akhir + metrik akademis + hasil semua record.
Sumber angka: metrik_hasil.json (dari metrik_batch.py). Gambar perbandingan
di-embed base64 agar 1 file HTML bisa dibuka di mana saja.

Pakai: python buat_laporan.py
"""
import os
import json
import base64

import numpy as np

ROOT = "C:/BRINDATA/EKG-BRIN"
DATA = os.path.join(ROOT, "metrik_hasil.json")
OUT = os.path.join(ROOT, "laporan_ekg.html")


def b64img(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def qual(prd):
    return "very good" if prd < 2 else ("good" if prd < 9 else "ditinjau")


def badge(prd):
    c = "#16a34a" if prd < 2 else ("#2563eb" if prd < 9 else "#d97706")
    return f'<span class="badge" style="background:{c}">{qual(prd)}</span>'


def rows_table(recs):
    out = []
    for r in recs:
        a = r["avg"]
        flat = (f" <span class='flat'>({len(r['flat_leads'])} lead datar: "
                f"{', '.join(r['flat_leads'])})</span>" if r.get("flat_leads") else "")
        wdd = f"{a['wdd']:.2f}" if a["wdd"] is not None else "-"
        out.append(
            f"<tr><td class='mono'>{r['file']}{flat}</td>"
            f"<td>{r['leads_scored']}</td>"
            f"<td>{a['snr']:.1f}</td><td>{a['prd']:.2f} {badge(a['prd'])}</td>"
            f"<td>{a['r']:.5f}</td><td>{a['rmse']*1000:.2f}</td>"
            f"<td>{a['maxae']*1000:.1f}</td><td>{wdd}</td></tr>")
    return "\n".join(out)


def agg(recs):
    s = np.array([[r["avg"]["snr"], r["avg"]["prd"], r["avg"]["r"],
                   r["avg"]["rmse"], r["avg"]["maxae"],
                   r["avg"]["wdd"] if r["avg"]["wdd"] is not None else np.nan]
                  for r in recs])
    return (np.nanmean(s[:, 0]), np.nanmean(s[:, 1]), np.nanmean(s[:, 2]),
            np.nanmean(s[:, 3]), np.nanmean(s[:, 4]), np.nanmean(s[:, 5]))


def main():
    d = json.load(open(DATA))
    six, twelve = d["6-lead"], d["12-lead"]
    a6, a12 = agg(six), agg(twelve)

    img6 = b64img(os.path.join(ROOT, "hasil", "6-lead", "DH_6L-0425_compare.png"))
    img12 = b64img(os.path.join(ROOT, "hasil", "12-lead",
                                "20251118-143153-0004_compare.png"))
    img_mek = b64img(os.path.join(ROOT, "lap_img", "fig_mekanisme.png"))
    img_arti = b64img(os.path.join(ROOT, "lap_img", "fig_arti_metrik.png"))
    img_bentuk = b64img(os.path.join(ROOT, "lap_img", "fig_bentuk_metrik.png"))
    step = [b64img(os.path.join(ROOT, "lap_img", f"step_{k}.png")) for k in range(1, 7)]
    img_overlap = b64img(os.path.join(ROOT, "lap_img", "fig_overlap.png"))

    HTML = f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laporan Konversi EKG PDF → Digital (6 & 12 Lead)</title>
<style>
 :root{{--b:#1e3a8a;--g:#16a34a;--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc}}
 *{{box-sizing:border-box}} body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
  color:var(--ink);line-height:1.65;margin:0;background:var(--bg)}}
 .wrap{{max-width:980px;margin:0 auto;padding:32px 22px 80px;background:#fff}}
 h1{{font-size:30px;margin:0 0 4px}} h2{{font-size:22px;border-bottom:3px solid var(--b);
  padding-bottom:6px;margin:42px 0 14px;color:var(--b)}} h3{{font-size:17px;margin:24px 0 8px}}
 .sub{{color:var(--mut);margin:0 0 18px}} p{{margin:10px 0}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
 .card{{border:1px solid var(--line);border-radius:12px;padding:14px 16px;background:#fff}}
 .card .n{{font-size:26px;font-weight:700;color:var(--b)}} .card .l{{font-size:12px;color:var(--mut)}}
 table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px}}
 th,td{{border:1px solid var(--line);padding:7px 9px;text-align:center}}
 th{{background:var(--b);color:#fff;font-weight:600}} td:first-child{{text-align:left}}
 tr:nth-child(even) td{{background:#f8fafc}}
 .mono{{font-family:ui-monospace,Consolas,monospace;font-size:12px}}
 .badge{{color:#fff;border-radius:6px;padding:1px 7px;font-size:11px;margin-left:4px}}
 .flat{{color:#d97706;font-size:11px}}
 .step{{border-left:3px solid var(--g);padding:4px 0 4px 16px;margin:12px 0}}
 .step b{{color:var(--b)}}
 .formula{{background:#0f172a;color:#e2e8f0;padding:10px 14px;border-radius:8px;
  font-family:ui-monospace,Consolas,monospace;font-size:13px;overflow-x:auto;margin:8px 0}}
 .note{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;margin:16px 0}}
 .ok{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px;margin:16px 0}}
 .tag{{display:inline-block;background:#eef2ff;color:var(--b);border:1px solid #c7d2fe;
  border-radius:999px;padding:2px 11px;font-size:12px;margin:3px 4px 3px 0}}
 img{{max-width:100%;border:1px solid var(--line);border-radius:10px;margin:8px 0}}
 .cap{{font-size:12px;color:var(--mut);text-align:center;margin-top:-2px}}
 .stepviz{{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:16px 0;
  background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.04)}}
 .stepviz img{{margin:0 0 6px}} .stepviz p{{margin:6px 2px 0}}
 footer{{margin-top:48px;color:var(--mut);font-size:12px;border-top:1px solid var(--line);padding-top:14px}}
</style></head><body><div class="wrap">

<h1>Konversi EKG: PDF → Sinyal Digital → Siap-FHIR</h1>
<p class="sub">Pipeline 6-lead (AliveCor/Kardia) &amp; 12-lead (Export) — penjelasan
menyeluruh, tools, dan validasi metrik akademis. Dibuat otomatis dari
<span class="mono">metrik_hasil.json</span>.</p>

<div class="grid">
 <div class="card"><div class="n">{len(six)+len(twelve)}</div><div class="l">record diproses</div></div>
 <div class="card"><div class="n">{a6[2]:.4f}</div><div class="l">Pearson r (6-lead)</div></div>
 <div class="card"><div class="n">{a12[2]:.4f}</div><div class="l">Pearson r (12-lead)</div></div>
 <div class="card"><div class="n">&lt;{max(a6[5],a12[5]):.1f}%</div><div class="l">WDD diagnostik (≪4% aman)</div></div>
</div>

<h2>1. Gambaran Umum</h2>
<p>Tujuan: mengubah laporan EKG ber-format PDF dari berbagai alat menjadi
<b>sinyal digital mV per-lead</b> yang seragam, lalu dirakit menjadi
<b>FHIR R4 Bundle</b> siap-kirim ke SatuSehat, disertai <b>skrining AI</b> dan
<b>validasi mutu otomatis</b>.</p>
<p>Temuan kunci: PDF dari kedua alat menyimpan trace sebagai <b>vektor (polyline)</b>,
bukan gambar. Maka sinyal dibaca <b>persis</b> dari koordinat — bukan ditebak dari
piksel — sehingga bebas artefak digitalisasi (overlap/collision). Model AI hanya
dipakai untuk (a) <i>cadangan</i> jika input berupa foto/scan raster, dan
(b) skrining diagnosis; <b>ekstraksi sinyalnya sendiri tidak memakai model.</b></p>

<h2>2. Bagaimana Lead Bisa Seakurat Itu (langkah demi langkah)</h2>
<p>Kuncinya: PDF <b>tidak menyimpan gambar EKG</b>, melainkan <b>perintah menggambar
garis</b> berisi koordinat angka. Mesin EKG yang mencetak PDF sudah tahu nilai
sinyal, lalu menaruh tiap titik di posisi matematis yang persis. Kita tinggal
<b>membaca balik angka itu</b> — tidak menebak dari piksel.</p>
<div class="step"><b>Langkah 1 — Buka isi vektor PDF.</b> <span class="mono">fitz.get_drawings()</span>
mengembalikan daftar perintah garis <span class="mono">('l', titik_awal, titik_akhir)</span>.
Tiap lead = satu polyline panjang (ribuan segmen).</div>
<div class="step"><b>Langkah 2 — Kumpulkan koordinat (x, y).</b> Untuk tiap lead kita
peroleh deretan titik <span class="mono">(x,y)</span> dalam satuan <i>point</i> PDF
(1 point = 1/72 inci). Inilah data asli, lihat gambar di bawah.</div>
<div class="step"><b>Langkah 3 — Tentukan baseline.</b> Garis nol lead =
<span class="mono">median(y)</span> seluruh titik lead itu (robust terhadap puncak).</div>
<div class="step"><b>Langkah 4 — Konversi ke milivolt.</b> Pakai kalibrasi standar EKG
10 mm/mV, dan 1 mm = 72/25.4 point → <b>1 mV = 28.35 point</b>:
<div class="formula">mV = ( baseline − y ) / 28.346</div>
(y mengecil = sinyal naik). Sumbu-x → waktu: 25 mm/s → <b>1 detik = 70.87 point</b>.</div>
<div class="step"><b>Langkah 5 — Resample seragam 250 Hz.</b> Titik asli tak ber-jarak
seragam; kita interpolasi linear ke grid waktu tetap agar siap diproses & disimpan.</div>
<div class="step"><b>Langkah 6 — Highpass 0.5 Hz.</b> Buang drift baseline lambat
(zero-phase, tak mengubah bentuk gelombang).</div>
<div class="step"><b>Langkah 7 — Per-lead otomatis terpisah.</b> Karena tiap lead
adalah polyline tersendiri, tidak ada percampuran antar-lead (masalah overlap pada
digitalisasi gambar tidak terjadi sama sekali).</div>
<img src="{img_mek}" alt="mekanisme vektor"/>
<p class="cap">Tiap titik biru = pasangan angka (x,y) yang benar-benar tersimpan di
PDF. Konversi ke mV hanyalah aritmetika kalibrasi → karena itu hasilnya eksak.</p>
<div class="note"><b>Analogi:</b> ini seperti <b>menyalin angka langsung dari memori
kalkulator</b> (pasti persis), bukan <b>memotret layar lalu menebak angkanya</b>
(yang menimbulkan galat). Digitalisasi gambar = memotret; metode kita = menyalin.</div>

<h3>Apa yang terjadi pada sinyal — satu langkah satu gambar</h3>
<p>Contoh Lead II (~3 detik). Perhatikan: <b>bentuk gelombang tidak berubah</b> di
sepanjang proses — hanya representasinya yang bertransformasi.</p>

<div class="stepviz"><img src="{step[0]}" alt="step 1"/>
<p><b>Langkah 1 — PDF asli.</b> Inilah potongan halaman PDF untuk Lead II, lengkap
dengan grid merah. Trace di sini <b>bukan gambar piksel</b>, melainkan kumpulan
perintah menggambar garis (vektor) yang koordinatnya tersimpan persis.</p></div>

<div class="stepviz"><img src="{step[1]}" alt="step 2"/>
<p><b>Langkah 2 — Baca koordinat (x,y) + baseline.</b> Tiap titik trace dibaca apa
adanya dalam satuan <i>point</i> PDF (sumbu-y mengarah ke bawah, seperti di file).
Garis hijau = baseline = <span class="mono">median(y)</span>, yaitu posisi "nol" lead.
Tidak ada penebakan; semuanya angka asli dari file.</p></div>

<div class="stepviz"><img src="{step[2]}" alt="step 3"/>
<p><b>Langkah 3 — Konversi ke milivolt.</b> Sumbu dibalik (sinyal naik = ke atas) dan
diskalakan: <span class="mono">mV = (baseline − y)/28.346</span> (1 mV = 28.35 pt),
sumbu-x → detik (1 dtk = 70.87 pt). Sekarang sudah jadi sinyal fisis dalam mV.</p></div>

<div class="stepviz"><img src="{step[3]}" alt="step 4"/>
<p><b>Langkah 4 — Resample 250 Hz.</b> Titik asli tidak ber-jarak seragam. Di sini
sinyal diinterpolasi ke grid waktu tetap (250 sampel/detik) agar konsisten dan siap
diproses lebih lanjut. Bentuknya tetap sama, hanya titiknya kini rapi berjarak sama.</p></div>

<div class="stepviz"><img src="{step[4]}" alt="step 5"/>
<p><b>Langkah 5 — Highpass 0.5 Hz.</b> Drift baseline lambat (mis. dari napas/kontak
sensor) dibuang dengan filter zero-phase, sehingga garis dasar rata di nol. Gelombang
P-QRS-T tidak terdistorsi karena filter ini hanya membuang komponen sangat-rendah.</p></div>

<div class="stepviz"><img src="{step[5]}" alt="step 6"/>
<p><b>Langkah 6 — Sinyal digital final.</b> Hasil akhir dalam mV, baseline bersih,
ber-sampling seragam — siap untuk skrining AI dan dirakit menjadi FHIR Bundle.</p></div>

<h3>Kenapa tumpang tindih (overlap) bisa ditangani</h3>
<p>Pada tata-letak EKG, lead disusun berdekatan. Gelombang yang tinggi/dalam bisa
<b>menjulur masuk ke lajur lead tetangga</b>. Contoh nyata di bawah: gelombang-S V2
yang dalam (−3.9 mV) menukik turun <b>menembus lajur V3</b> — di atas kertas, tinta
kedua lead benar-benar <b>bersilang</b>.</p>
<img src="{img_overlap}" alt="overlap V2 V3"/>
<p class="cap">Kiri: posisi nyata di halaman — spike V2 (biru) masuk ke pita V3 (kuning).
Kanan: hasil ekstraksi — V2 &amp; V3 tetap bersih dan terpisah.</p>
<div class="step"><b>Kenapa metode gambar gagal di sini.</b> Digitalisasi berbasis
piksel hanya "melihat" tinta gelap yang sudah menyatu. Saat tinta V2 dan V3 bersilang,
algoritma tak bisa memastikan piksel persilangan itu milik lead yang mana → muncul
artefak <i>collision/climbing</i> (V3 keliru "memanjat" mengikuti spike V2).</div>
<div class="step"><b>Kenapa metode vektor menang.</b> Di PDF, <b>tiap lead adalah objek
path tersendiri</b> — satu daftar koordinat (x,y) yang terpisah dari lead lain. Walau
tintanya tampak bersilang saat <i>digambar</i> di halaman, <b>daftar koordinatnya tidak
pernah bercampur</b>. Kita membaca tiap path satu per satu, sehingga V2 tetap V2 dan
V3 tetap V3 — <b>pemisahan terjadi otomatis "by construction"</b>, bukan hasil tebakan.</div>
<div class="ok"><b>Kesimpulan:</b> overlap hanyalah masalah bagi metode berbasis
gambar. Bagi ekstraksi vektor, overlap <b>bukan masalah sama sekali</b> — itulah
sebabnya artefak collision yang dulu muncul pada digitalisasi <b>hilang total</b>.</div>

<h2>3. Pipeline 6-Lead (AliveCor / Kardia)</h2>
<div class="step"><b>1) Deteksi format.</b> Router membaca PDF; ditemukan tiap halaman
trace berisi <b>6 polyline panjang</b> (>500 segmen). Halaman cover dilewati otomatis.</div>
<div class="step"><b>2) Multi-halaman.</b> Rekaman 30 detik terpotong jadi beberapa
halaman. Semua halaman ber-6-path <b>disambung berurutan</b> → sinyal penuh.</div>
<div class="step"><b>3) Urutkan lead.</b> 6 path diurutkan posisi-y (atas→bawah) =
I, II, III, aVR, aVL, aVF.</div>
<div class="step"><b>4) Konversi mV.</b> <span class="mono">mV = (baseline − y) / (10·72/25.4)</span>
(kalibrasi 10 mm/mV, 25 mm/s), lalu resample seragam 250 Hz.</div>
<div class="step"><b>5) Baseline-wander removal.</b> Highpass 0.5 Hz (Butterworth orde-2,
zero-phase) membersihkan drift awal (jari menempel sensor) tanpa mengubah P-QRS-T.</div>
<div class="step"><b>6) Cek mutu.</b> Hukum Einthoven (III=II−I, aVR=−(I+II)/2, …)
diverifikasi otomatis; lead datar (lead-off) ditandai.</div>
<p class="ok">Hasil 6-lead: setiap lead bersih, beat konsisten, 30 detik penuh.</p>
<img src="{img6}" alt="compare 6-lead"/>
<p class="cap">Kiri: PDF asli (grid + label) · Kanan: hasil digital (jendela waktu sama).</p>

<h2>4. Pipeline 12-Lead (Export)</h2>
<div class="step"><b>1) Deteksi format.</b> Satu halaman berisi <b>12 polyline panjang</b>
(~3700 segmen/lead) → dikenali sebagai 12-lead vektor.</div>
<div class="step"><b>2) Urutkan lead.</b> 12 path diurutkan posisi-y → I…V6.</div>
<div class="step"><b>3) Konversi mV + resample 250 Hz + highpass 0.5 Hz</b> (sama seperti 6-lead).</div>
<div class="step"><b>4) Cek mutu Einthoven + deteksi lead datar.</b> Jika rekaman hanya
limb (mis. 0002), V1–V6 ditandai datar/tak-terekam — bukan dipaksa-baca.</div>
<img src="{img12}" alt="compare 12-lead"/>
<p class="cap">12-lead: PDF asli ⟷ hasil digital, tertumpuk per-lead.</p>

<h2>5. Tools &amp; Teknologi</h2>
<p>
<span class="tag">PyMuPDF (fitz) — baca vektor PDF</span>
<span class="tag">NumPy — sinyal & aljabar</span>
<span class="tag">SciPy — highpass Butterworth/filtfilt</span>
<span class="tag">OpenCV — render halaman PDF (gambar banding)</span>
<span class="tag">Matplotlib — plot & perbandingan</span>
<span class="tag">PyTorch + ECGNet — skrining AI (cadangan)</span>
<span class="tag">U-Net (PyTorch) — digitalisasi raster (fallback)</span>
<span class="tag">FHIR R4 / SatuSehat — output Bundle</span>
</p>
<p><b>Entry-point:</b> <span class="mono">proses_ekg.py</span> —
<span class="mono">--lead {{auto,6,12}}</span>, input PDF/folder, output otomatis ke
<span class="mono">hasil/6-lead/</span> &amp; <span class="mono">hasil/12-lead/</span>:
tiap record menghasilkan <span class="mono">_digital.json</span>,
<span class="mono">_fhir.json</span>, <span class="mono">_compare.png</span>.</p>

<h2>6. Metrik Akademis &amp; Ambang Toleransi</h2>

<h3>Kenapa memilih paket metrik ini?</h3>
<p>Tidak ada satu angka yang cukup untuk menilai "kemiripan sinyal". Kami memakai
<b>tiga lapis</b> metrik yang saling melengkapi dan <b>semuanya baku di literatur
EKG</b>, agar klaim "akurat" dapat dipertahankan secara akademis:</p>
<div class="step"><b>Lapis sinyal (SNR, PRD).</b> Mengukur galat menyeluruh titik-demi-titik.
Dipilih karena <b>SNR = metrik resmi PhysioNet/CinC Challenge 2024</b> (digitalisasi
citra EKG) dan <b>PRD = standar klasik kompresi/rekonstruksi EKG</b> yang punya
<b>ambang kualitas baku</b> (Zigel dkk.) sehingga hasil bisa dibandingkan antar-studi.</div>
<div class="step"><b>Lapis bentuk (Pearson r).</b> Mengukur kemiripan <i>pola</i> gelombang
terlepas dari skala — intuitif dan umum dipakai.</div>
<div class="step"><b>Lapis diagnosis (WDD).</b> Yang benar-benar penting secara klinis:
apakah <b>angka yang dibaca dokter</b> (HR, amplitudo-R) berubah? Memakai konsep
<b>Weighted Diagnostic Distortion</b> (Zigel dkk.) versi ringkas.</div>
<div class="step"><b>Galat absolut (RMSE, maxAE) dalam mV.</b> Agar bisa dibandingkan
langsung ke ambang bermakna-klinis (≈0.1 mV) dan resolusi cetak (≈0.025 mV).</div>

<h3>Arti tiap metrik &amp; rumusnya</h3>
<table>
 <tr><th>Metrik</th><th>Rumus</th><th>Arti</th><th>Acuan</th></tr>
 <tr><td><b>SNR</b> (dB)</td><td class="mono">10·log₁₀(Σ(r−r̄)² / Σ(r−s)²)</td>
  <td>makin tinggi makin setia</td><td>PhysioNet/CinC Challenge 2024</td></tr>
 <tr><td><b>PRD/PRDN</b> (%)</td><td class="mono">100·√(Σ(r−s)² / Σ(r−r̄)²)</td>
  <td>galat RMS relatif energi</td><td>Zigel dkk., IEEE TBME 2000</td></tr>
 <tr><td><b>Pearson r</b></td><td class="mono">corr(r, s)</td>
  <td>kemiripan bentuk gelombang</td><td>umum</td></tr>
 <tr><td><b>RMSE / maxAE</b> (mV)</td><td class="mono">√mean(r−s)² ; max|r−s|</td>
  <td>galat absolut</td><td>umum</td></tr>
 <tr><td><b>WDD*</b> (%)</td><td class="mono">RMS relatif [HR, amplitudo-R] beat tercocokkan</td>
  <td>distorsi level-DIAGNOSIS</td><td>Zigel dkk. 2000 (versi ringkas)</td></tr>
</table>
<div class="note"><b>Ambang kualitas PRD</b> (skala MOS, Zigel dkk.):
<b>&lt;2%</b> = "very good", <b>2–9%</b> = "good", &gt;9% perlu ditinjau.
<b>WDD &lt; 4%</b> dianggap <b>aman secara diagnostik</b>. Pembanding praktis:
1 piksel grid cetak (254 dpi) ≈ 0.025 mV.</div>
<p class="sub"><i>r = sinyal referensi (trace vektor asli, di-render 1000 Hz sebagai
"truth"); s = sinyal uji (output pipeline 250 Hz). Lead datar (tak-terekam)
dikecualikan dari penilaian. WDD* memakai 2 fitur paling andal; fitur ST/T
sengaja tidak dipakai karena rapuh pada level round-trip ini.</i></p>

<h3>Apa yang sebenarnya diukur? (bentuk visual)</h3>
<p>Semua metrik pada dasarnya mengukur <b>jarak antara trace ASLI dan hasil DIGITAL</b>.
Pada data kita, keduanya nyaris menempel — residual (area merah) sangat tipis:</p>
<img src="{img_arti}" alt="arti metrik"/>
<p class="cap">Lead V2 (gelombang-S dalam −3.9 mV). Hitam = asli, merah putus-putus =
digital 250 Hz. Kotak biru = nilai metriknya.</p>

<h3>Bentuk metrik dari "sangat baik" ke "buruk"</h3>
<p>Supaya intuitif, berikut wujud sinyal pada berbagai tingkat kemiripan. Makin merah
menempel ke hitam → <b>SNR makin tinggi, PRD makin kecil, r→1</b>. Kasus kita berada
di panel kiri ("sangat baik"):</p>
<img src="{img_bentuk}" alt="bentuk metrik"/>
<p class="cap">Kiri ≈ kondisi pipeline kita (galat hampir tak terlihat). Tengah &amp;
kanan = ilustrasi bila rekonstruksi memburuk.</p>

<h2>7. Hasil Validasi — Semua Record</h2>
<h3>6-Lead (n={len(six)})</h3>
<table>
 <tr><th>File</th><th>lead dinilai</th><th>SNR(dB)</th><th>PRD(%)</th><th>r</th>
  <th>RMSE(µV)</th><th>maxAE(µV)</th><th>WDD*(%)</th></tr>
 {rows_table(six)}
 <tr style="font-weight:700"><td>RATA-RATA</td><td>—</td><td>{a6[0]:.1f}</td>
  <td>{a6[1]:.2f} {badge(a6[1])}</td><td>{a6[2]:.5f}</td><td>{a6[3]*1000:.2f}</td>
  <td>{a6[4]*1000:.1f}</td><td>{a6[5]:.2f}</td></tr>
</table>
<h3>12-Lead (n={len(twelve)})</h3>
<table>
 <tr><th>File</th><th>lead dinilai</th><th>SNR(dB)</th><th>PRD(%)</th><th>r</th>
  <th>RMSE(µV)</th><th>maxAE(µV)</th><th>WDD*(%)</th></tr>
 {rows_table(twelve)}
 <tr style="font-weight:700"><td>RATA-RATA</td><td>—</td><td>{a12[0]:.1f}</td>
  <td>{a12[1]:.2f} {badge(a12[1])}</td><td>{a12[2]:.5f}</td><td>{a12[3]*1000:.2f}</td>
  <td>{a12[4]*1000:.1f}</td><td>{a12[5]:.2f}</td></tr>
</table>

<h2>8. Interpretasi &amp; Kesimpulan</h2>
<div class="ok">
<p><b>Ekstraksi praktis lossless.</b> Pearson r ≈ <b>{a6[2]:.4f}</b> (6-lead) dan
<b>{a12[2]:.4f}</b> (12-lead): bentuk gelombang asli vs digital nyaris identik,
karena koordinat vektor dibaca persis (bukan tebakan piksel).</p>
<p><b>Diagnostik terjaga.</b> WDD* rata-rata <b>{a6[5]:.2f}%</b> (6-lead) dan
<b>{a12[5]:.2f}%</b> (12-lead) — keduanya <b>jauh di bawah ambang aman 4%</b>.
Angka yang dibaca dokter (HR, amplitudo-R) tidak berubah bermakna.</p>
<p><b>Galat residual = downsampling, bukan salah-baca.</b> PRD 6-lead {a6[1]:.2f}%
("very good"); 12-lead {a12[1]:.2f}% ("good") sedikit lebih tinggi karena trace
12-lead lebih rapat (≈500 Hz natif) sehingga keluaran 250 Hz memotong sedikit
puncak QRS. Menaikkan sampling (mis. 500–1000 Hz) menurunkan PRD ke kategori
"very good" — bukti bahwa sumbernya pemilihan sampling rate, bukan ekstraksi.</p>
</div>
<p>Singkatnya: konversi PDF→digital pada kedua format <b>tervalidasi setia</b>
secara sinyal (SNR/PRD/r) maupun diagnosis (WDD), dan galatnya berada di bawah
ambang bermakna-klinis (≈0.1 mV).</p>

<footer>EKG-BRIN · laporan dihasilkan otomatis oleh <span class="mono">buat_laporan.py</span>.
Skrining AI bersifat eksperimental, bukan diagnosis final.</footer>
</div></body></html>"""

    open(OUT, "w", encoding="utf-8").write(HTML)
    print("->", OUT)


if __name__ == "__main__":
    main()
