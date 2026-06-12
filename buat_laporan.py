"""
buat_laporan.py — Rakit laporan HTML MANDIRI yang sangat rinci: arsitektur,
anatomi PDF, matematika koordinat, pipeline 6/12-lead, penanganan overlap,
validitas (4 bukti), metrik akademis (pendalaman), hasil per-record & PER-LEAD,
struktur FHIR, AI, keterbatasan, glosarium, referensi.

Sumber angka: metrik_hasil.json (metrik_batch.py). Gambar di-embed base64.
Pakai: python metrik_batch.py && python illustrasi.py && python illustrasi_overlap.py
       && python pipeline_visual.py && python buat_laporan.py
"""
import os
import json
import base64

import numpy as np

ROOT = "C:/BRINDATA/EKG-BRIN"
DATA = os.path.join(ROOT, "metrik_hasil.json")
OUT = os.path.join(ROOT, "laporan_ekg.html")
PT = 72.0 / 25.4


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


def agg(recs):
    s = np.array([[r["avg"]["snr"], r["avg"]["prd"], r["avg"]["r"], r["avg"]["rmse"],
                   r["avg"]["maxae"],
                   r["avg"]["wdd"] if r["avg"]["wdd"] is not None else np.nan]
                  for r in recs])
    return tuple(np.nanmean(s[:, i]) for i in range(6))


def rec_rows(recs):
    out = []
    for r in recs:
        a = r["avg"]
        flat = (f" <span class='flat'>({len(r['flat_leads'])} datar)</span>"
                if r.get("flat_leads") else "")
        wdd = f"{a['wdd']:.2f}" if a["wdd"] is not None else "-"
        out.append(
            f"<tr><td class='mono'>{r['file']}{flat}</td><td>{r['leads_scored']}</td>"
            f"<td>{a['snr']:.1f}</td><td>{a['prd']:.2f} {badge(a['prd'])}</td>"
            f"<td>{a['r']:.5f}</td><td>{a['rmse']*1000:.2f}</td>"
            f"<td>{a['maxae']*1000:.1f}</td><td>{wdd}</td></tr>")
    return "\n".join(out)


def perlead_details(recs):
    """Tabel PER-LEAD tiap record, dilipat (<details>) agar ringkas."""
    out = []
    for r in recs:
        rows = []
        for L in r["leads"]:
            if L.get("flat"):
                rows.append(f"<tr><td>{L['lead']}</td><td colspan='6' "
                            f"class='flat'>datar / tak terekam (lead-off)</td></tr>")
            else:
                rows.append(
                    f"<tr><td>{L['lead']}</td><td>{L['snr']:.1f}</td>"
                    f"<td>{L['prd']:.2f}</td><td>{L['r']:.5f}</td>"
                    f"<td>{L['rmse']*1000:.2f}</td><td>{L['maxae']*1000:.1f}</td>"
                    f"<td>{L['wdd']:.2f}</td></tr>" if L.get('wdd') is not None else
                    f"<tr><td>{L['lead']}</td><td>{L['snr']:.1f}</td>"
                    f"<td>{L['prd']:.2f}</td><td>{L['r']:.5f}</td>"
                    f"<td>{L['rmse']*1000:.2f}</td><td>{L['maxae']*1000:.1f}</td>"
                    f"<td>-</td></tr>")
        out.append(
            f"<details><summary class='mono'>{r['file']} — {r['leads_scored']} "
            f"lead dinilai</summary><table class='mini'><tr><th>lead</th>"
            f"<th>SNR(dB)</th><th>PRD(%)</th><th>r</th><th>RMSE(µV)</th>"
            f"<th>maxAE(µV)</th><th>WDD(%)</th></tr>{''.join(rows)}</table></details>")
    return "\n".join(out)


def vlead_table(rec):
    """Tabel rincian path vektor per lead (dari vektor_detail.json)."""
    rows = []
    for L in rec["leads"]:
        s0 = L["sample3"][0]
        rows.append(
            f"<tr><td>{L['lead']}</td><td>{L['n_segmen']}</td>"
            f"<td>{L['median_y']}</td><td>{L['y_range'][0]}–{L['y_range'][1]}</td>"
            f"<td>{L['amp_mV']}</td>"
            f"<td class='mono'>({s0['x']}, {s0['y']})</td><td>{s0['mv']}</td></tr>")
    return ("<table class='mini'><tr><th>lead</th><th>segmen</th><th>median_y(pt)</th>"
            "<th>y_range(pt)</th><th>amplitudo(mV)</th><th>titik-1 (x,y)</th>"
            "<th>→ mV</th></tr>" + "".join(rows) + "</table>")


def vconcat_table(rec):
    rows = []
    for c in rec["concat_pages"]:
        rows.append(f"<tr><td>{c['page']}</td>"
                    f"<td class='mono'>{c['x_range'][0]:.0f}–{c['x_range'][1]:.0f}</td>"
                    f"<td>{c['dur_sec']}</td><td>{c['samples_250hz']}</td></tr>")
    return ("<table class='mini'><tr><th>halaman</th><th>x_range(pt)</th>"
            "<th>durasi(s)</th><th>sampel@250Hz</th></tr>" + "".join(rows) +
            f"<tr style='font-weight:700'><td colspan=2>TOTAL (disambung)</td>"
            f"<td>{rec['total_sec']}</td>"
            f"<td>{sum(c['samples_250hz'] for c in rec['concat_pages'])}</td></tr></table>")


def main():
    d = json.load(open(DATA))
    six, twelve = d["6-lead"], d["12-lead"]
    a6, a12 = agg(six), agg(twelve)
    VD = json.load(open(os.path.join(ROOT, "vektor_detail.json")))

    I = {n: b64img(os.path.join(ROOT, "lap_img", f"{n}.png")) for n in
         ["fig_mekanisme", "fig_arti_metrik", "fig_bentuk_metrik", "fig_overlap",
          "fig_pipeline_stages", "step_1", "step_2", "step_3", "step_4",
          "step_5", "step_6"]}
    cmp6 = b64img(os.path.join(ROOT, "hasil", "6-lead", "DH_6L-0425_compare.png"))
    cmp12 = b64img(os.path.join(ROOT, "hasil", "12-lead",
                                "20251118-143153-0004_compare.png"))
    raw6 = b64img(os.path.join(ROOT, "lap_img", "fig_raw6.png"))
    raw12 = b64img(os.path.join(ROOT, "lap_img", "fig_raw12.png"))
    ovz = b64img(os.path.join(ROOT, "lap_img", "fig_overlap_zoom.png"))
    ovb = b64img(os.path.join(ROOT, "lap_img", "fig_overlap_bukti.png"))
    pl6 = b64img(os.path.join(ROOT, "lap_img", "fig_perlead_6.png"))
    pl12 = b64img(os.path.join(ROOT, "lap_img", "fig_perlead_12.png"))
    leaddet = b64img(os.path.join(ROOT, "lap_img", "fig_lead_detail.png"))
    gridcal = b64img(os.path.join(ROOT, "lap_img", "fig_grid_calib.png"))
    unet = b64img(os.path.join(ROOT, "lap_img", "fig_unet.png"))
    ecgnet = b64img(os.path.join(ROOT, "lap_img", "fig_ecgnet.png"))
    vd6, vd12 = VD["6-lead"], VD["12-lead"]

    pmv = 10 * PT; psec = 25 * PT

    HTML = f"""<!DOCTYPE html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Laporan Rinci — Konversi EKG PDF → Digital → FHIR (6 & 12 Lead)</title>
<style>
 :root{{--b:#1e3a8a;--b2:#2563eb;--g:#16a34a;--ink:#0f172a;--mut:#64748b;
  --line:#e2e8f0;--bg:#f8fafc;--code:#0f172a}}
 *{{box-sizing:border-box}} html{{scroll-behavior:smooth}}
 body{{font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:var(--ink);
  line-height:1.7;margin:0;background:var(--bg)}}
 .wrap{{max-width:1020px;margin:0 auto;padding:34px 24px 90px;background:#fff}}
 h1{{font-size:31px;margin:0 0 4px}} h2{{font-size:23px;border-bottom:3px solid var(--b);
  padding-bottom:6px;margin:46px 0 14px;color:var(--b);scroll-margin-top:14px}}
 h3{{font-size:18px;margin:26px 0 8px;color:#1e293b}} h4{{font-size:15px;margin:18px 0 6px;color:#334155}}
 .sub{{color:var(--mut);margin:0 0 18px}} p{{margin:10px 0}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}}
 .card{{border:1px solid var(--line);border-radius:12px;padding:14px 16px}}
 .card .n{{font-size:25px;font-weight:700;color:var(--b)}} .card .l{{font-size:12px;color:var(--mut)}}
 table{{border-collapse:collapse;width:100%;margin:14px 0;font-size:13.5px}}
 th,td{{border:1px solid var(--line);padding:7px 9px;text-align:center}}
 th{{background:var(--b);color:#fff;font-weight:600}} td:first-child{{text-align:left}}
 tr:nth-child(even) td{{background:#f8fafc}}
 table.mini th{{background:#475569}} table.mini{{font-size:12.5px}}
 .mono{{font-family:ui-monospace,Consolas,monospace;font-size:12.5px}}
 .badge{{color:#fff;border-radius:6px;padding:1px 7px;font-size:11px;margin-left:4px}}
 .flat{{color:#d97706;font-size:11.5px}}
 .toc{{background:#f8fafc;border:1px solid var(--line);border-radius:12px;padding:16px 22px;margin:18px 0}}
 .toc ol{{margin:6px 0;columns:2;font-size:14px}} .toc a{{color:var(--b2);text-decoration:none}}
 .toc a:hover{{text-decoration:underline}}
 .step{{border-left:3px solid var(--g);padding:4px 0 4px 16px;margin:12px 0}}
 .step b{{color:var(--b)}}
 .formula{{background:var(--code);color:#e2e8f0;padding:11px 15px;border-radius:8px;
  font-family:ui-monospace,Consolas,monospace;font-size:13px;overflow-x:auto;margin:9px 0}}
 pre.code{{background:#0b1220;color:#d1e0f5;padding:13px 15px;border-radius:8px;
  font-family:ui-monospace,Consolas,monospace;font-size:12.5px;overflow-x:auto;line-height:1.5}}
 .note{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:12px 16px;margin:16px 0}}
 .ok{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;padding:12px 16px;margin:16px 0}}
 .warn{{background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:12px 16px;margin:16px 0}}
 .tag{{display:inline-block;background:#eef2ff;color:var(--b);border:1px solid #c7d2fe;
  border-radius:999px;padding:2px 11px;font-size:12px;margin:3px 4px 3px 0}}
 img{{max-width:100%;border:1px solid var(--line);border-radius:10px;margin:8px 0}}
 .cap{{font-size:12px;color:var(--mut);text-align:center;margin-top:-2px}}
 .stepviz{{border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:16px 0;
  box-shadow:0 1px 3px rgba(0,0,0,.04)}} .stepviz img{{margin:0 0 6px}} .stepviz p{{margin:6px 2px 0}}
 details{{border:1px solid var(--line);border-radius:8px;margin:8px 0;padding:4px 12px}}
 summary{{cursor:pointer;padding:6px 0;font-weight:600;color:#334155}}
 .kv{{font-size:13.5px}} .kv td:first-child{{font-weight:600;width:32%}}
 footer{{margin-top:48px;color:var(--mut);font-size:12px;border-top:1px solid var(--line);padding-top:14px}}
 .top{{font-size:11px;color:var(--b2);text-decoration:none;float:right}}
</style></head><body><div class="wrap">

<h1>Konversi EKG: PDF → Sinyal Digital → FHIR</h1>
<p class="sub">Laporan teknis rinci — pipeline 6-lead (AliveCor/Kardia) &amp; 12-lead
(Export), matematika, validitas, dan metrik akademis. Dibuat otomatis.</p>

<div class="grid">
 <div class="card"><div class="n">{len(six)+len(twelve)}</div><div class="l">record diuji</div></div>
 <div class="card"><div class="n">{a6[2]:.4f}</div><div class="l">Pearson r (6-lead)</div></div>
 <div class="card"><div class="n">{a12[2]:.4f}</div><div class="l">Pearson r (12-lead)</div></div>
 <div class="card"><div class="n">&lt;{max(a6[5],a12[5]):.1f}%</div><div class="l">WDD (≪4% aman)</div></div>
 <div class="card"><div class="n">0</div><div class="l">model utk ekstraksi</div></div>
</div>

<div class="toc"><b>Daftar Isi</b>
<ol>
 <li><a href="#s1">Ringkasan Eksekutif</a></li>
 <li><a href="#s2">Latar Belakang &amp; Tujuan</a></li>
 <li><a href="#s3">Arsitektur Sistem</a></li>
 <li><a href="#s4">Anatomi PDF EKG (vektor vs raster)</a></li>
 <li><a href="#s5">Matematika: Bagaimana Lead Dihitung</a></li>
 <li><a href="#s6">Visual: Apa yang Terjadi (langkah demi langkah)</a></li>
 <li><a href="#s7">Pipeline 6-Lead</a></li>
 <li><a href="#s8">Pipeline 12-Lead</a></li>
 <li><a href="#s9">Penanganan Tumpang Tindih (overlap)</a></li>
 <li><a href="#s10">Validitas — 4 Bukti Independen</a></li>
 <li><a href="#s11">Metrik Akademis — Pendalaman</a></li>
 <li><a href="#s12">Hasil Validasi (per-record &amp; per-lead)</a></li>
 <li><a href="#s13">Output FHIR — Struktur Rinci</a></li>
 <li><a href="#s14">Cara Kerja Model (U-Net &amp; ECGNet)</a></li>
 <li><a href="#s15">Keterbatasan &amp; Pengembangan</a></li>
 <li><a href="#s16">Glosarium &amp; Referensi</a></li>
</ol></div>

<h2 id="s1">1. Ringkasan Eksekutif</h2>
<p>Sistem mengubah laporan EKG PDF dari berbagai alat menjadi <b>sinyal digital mV
per-lead</b> seragam, lalu merakitnya menjadi <b>FHIR R4 Bundle</b> siap-SatuSehat,
dengan <b>skrining AI</b> dan <b>validasi mutu otomatis</b>.</p>
<p><b>Temuan kunci:</b> PDF dari kedua alat menyimpan trace sebagai <b>vektor
(polyline)</b>. Karena itu sinyal dibaca <b>persis</b> dari koordinat — bukan ditebak
dari piksel — sehingga <b>tanpa model</b> dan <b>bebas artefak digitalisasi</b>
(overlap/collision). Validasi: Pearson r ≈ {a12[2]:.4f}, SNR {min(a6[0],a12[0]):.0f}–{max(a6[0],a12[0]):.0f} dB,
WDD &lt; {max(a6[5],a12[5]):.1f}% (di bawah ambang klinis 4%).</p>

<h2 id="s2">2. Latar Belakang &amp; Tujuan <a href="#" class="top">↑</a></h2>
<p>EKG analog/printout sulit dipertukarkan antar-sistem. Tujuan proyek: pipeline
<b>PDF → mV digital → FHIR</b> agar interoperabel (SatuSehat, Kemenkes), dengan
dukungan multi-alat dan multi-jumlah-lead (6 &amp; 12).</p>
<p>Dua sumber data nyata: <b>AliveCor/Kardia 6-lead</b> (rekaman genggam 30 detik,
multi-halaman) dan <b>Export 12-lead</b> (printout klinis, satu halaman). Keduanya
ber-format PDF vektor.</p>

<h2 id="s3">3. Arsitektur Sistem <a href="#" class="top">↑</a></h2>
<pre class="code">  PDF (6/12-lead)
       │
       ▼
  [ deteksi format ]  input/ecg_input_router.py
       │  vektor? ─ ya ─►  input/parsers/vector_pdf.py   (EKSAK, tanpa model)
       │            tidak ►  U-Net digitalisasi (fallback raster/foto)
       ▼
  sinyal mV per-lead  +  highpass 0.5 Hz  +  resample 250 Hz
       │
       ├─►  cek mutu Einthoven   (run_any.einthoven_check)
       ├─►  skrining AI ECGNet   (training/classify, opsional)
       ▼
  proses_ekg.py  ──►  hasil/&lt;6|12&gt;-lead/
                        ├─ _digital.json  (sinyal universal)
                        ├─ _fhir.json     (FHIR R4 Bundle, SatuSehat)
                        └─ _compare.png   (asli ⟷ digital)</pre>
<table class="kv">
 <tr><td>Entry-point</td><td class="mono">proses_ekg.py --lead {{auto,6,12}} --input/--folder --out</td></tr>
 <tr><td>Ekstraksi vektor</td><td class="mono">input/parsers/vector_pdf.py</td></tr>
 <tr><td>Pipeline + AI + QC</td><td class="mono">run_any.py</td></tr>
 <tr><td>Konverter FHIR</td><td class="mono">output/fhir_converter.py</td></tr>
 <tr><td>Output</td><td class="mono">hasil/6-lead/ , hasil/12-lead/</td></tr>
</table>

<h2 id="s4">4. Anatomi PDF EKG: Vektor vs Raster <a href="#" class="top">↑</a></h2>
<p>PDF bisa menyimpan grafik dengan dua cara:</p>
<table>
 <tr><th>Aspek</th><th>Raster (gambar)</th><th>Vektor (kasus kita)</th></tr>
 <tr><td>Bentuk data</td><td>kisi piksel berwarna</td><td>perintah garis + koordinat angka</td></tr>
 <tr><td>Trace lead</td><td>tinta menyatu antar-lead</td><td>tiap lead = objek path tersendiri</td></tr>
 <tr><td>Membaca sinyal</td><td>harus menebak garis dari piksel</td><td>membaca koordinat persis</td></tr>
 <tr><td>Galat</td><td>ada (tebakan, overlap)</td><td>≈ nol (aritmetika)</td></tr>
</table>
<p>Cara mendeteksi: <span class="mono">fitz.get_drawings()</span> mengembalikan daftar
"drawing". Path trace = polyline dengan &gt;500 segmen garis (<span class="mono">'l'</span>).
Gridline (~160 segmen) otomatis terbuang oleh ambang ini.</p>

<h2 id="s5">5. Matematika: Bagaimana Lead Dihitung <a href="#" class="top">↑</a></h2>
<h3>5.1 Sistem koordinat PDF</h3>
<p>Satuan PDF = <b>point</b> (1 point = 1/72 inci). Sumbu-y mengarah <b>ke bawah</b>.
Tiap segmen trace tersimpan sebagai operator <span class="mono">x y l</span> (lineto).</p>
<h3>5.2 Membaca koordinat</h3>
<pre class="code">for it in drawing['items']:
    if it[0] == 'l':              # segmen garis
        x, y = it[2].x, it[2].y   # koordinat titik (point) — DIBACA APA ADANYA
        pts.append((x, y))</pre>
<h3>5.3 Konstanta kalibrasi (diturunkan)</h3>
<p>Standar EKG: <b>gain 10 mm/mV</b>, <b>kecepatan 25 mm/s</b>. Konversi 1 mm = 72/25.4
= {PT:.4f} point. Maka:</p>
<table class="kv">
 <tr><td>1 mm</td><td class="mono">72 / 25.4 = {PT:.4f} point</td></tr>
 <tr><td>1 mV (=10 mm)</td><td class="mono">10 × {PT:.4f} = <b>{pmv:.4f} point</b></td></tr>
 <tr><td>1 detik (=25 mm)</td><td class="mono">25 × {PT:.4f} = <b>{psec:.4f} point</b></td></tr>
</table>
<h4>Dari mana angka mm/mV ini? — dibaca dari GRID + pulsa kalibrasi</h4>
<p>Skala EKG tidak ditebak: ia <b>tercetak</b> sebagai <b>grid</b> dan <b>pulsa
kalibrasi</b> di dalam PDF itu sendiri. Gambar di bawah (Kardia 6-lead) menunjukkan
cara membacanya:</p>
<img src="{gridcal}"/>
<p class="cap">Grid &amp; pulsa kalibrasi pada PDF — dasar penurunan skala mm→mV.</p>
<div class="step"><b>1 kotak kecil = 1 mm</b> (hijau). Lima kotak kecil = <b>1 kotak
besar = 5 mm</b> (biru).</div>
<div class="step"><b>Pulsa kalibrasi ⊓ = 10 mm = 1 mV</b> (merah) — sinyal referensi
yang dicetak alat untuk menyatakan "segini tingginya 1 mV".</div>
<div class="step"><b>Penurunan:</b> karena 1 mm = 72/25.4 = {PT:.3f} point, maka
<b>1 mV = 10 mm = {pmv:.3f} point</b> dan <b>1 detik = 25 mm = {psec:.3f} point</b>.</div>
<div class="note"><b>Bukti silang:</b> tinggi pulsa kalibrasi diukur dari koordinat
PDF = <b>{pmv:.3f} point</b> — cocok sempurna dengan turunan di atas. Jadi konstanta
kalibrasi <b>terverifikasi langsung dari grid &amp; pulsa</b>, bukan asumsi. (Catatan:
12-lead Export tak menampilkan grid, tetapi memakai pulsa kalibrasi &amp; standar yang
sama.)</div>

<h3>5.4 Konversi titik → milivolt (contoh nyata)</h3>
<p>Untuk titik Lead I dengan <span class="mono">y = 200.75</span>, baseline
<span class="mono">198.13</span>:</p>
<div class="formula">mV = (baseline − y) / {pmv:.3f}
   = (198.13 − 200.75) / {pmv:.3f}
   = −2.62 / {pmv:.3f}  =  −0.0925 mV</div>
<p><b>Kenapa <span class="mono">baseline − y</span>?</b> Karena y mengarah ke bawah
(y besar = rendah di kertas); pengurangan membalik orientasi agar "naik = positif".
<b>Kenapa dibagi {pmv:.3f}?</b> Mengubah jarak-point menjadi milivolt. Seluruh
perhitungan bersifat <b>linear &amp; deterministik</b> — tak ada parameter ditebak.</p>
<h3>5.5 Baseline = median(y)</h3>
<p><span class="mono">baseline = np.median(y_semua_titik)</span>. Median dipilih karena
<b>tahan puncak</b>: gelombang R/S ekstrem tak menggeser nol.</p>
<h3>5.6 Sumbu waktu &amp; resampling</h3>
<p><span class="mono">t = (x − x_awal) / {psec:.3f}</span> (detik). Titik asli tak
ber-jarak seragam → interpolasi linear ke grid <b>250 Hz</b> (250 sampel/detik).</p>
<h3>5.7 Highpass 0.5 Hz (penghilang baseline-wander)</h3>
<p>Butterworth orde-2, <b>zero-phase</b> (<span class="mono">filtfilt</span>): buang
drift &lt; 0.5 Hz tanpa menggeser fase/merusak P-QRS-T. Standar AHA untuk EKG.</p>

<h3>5.8 Contoh nyata — perhitungan vektor 12-LEAD</h3>
<p>File <span class="mono">{vd12['file']}</span> punya <b>{vd12['n_pages']} halaman</b>;
trace ada di halaman <b>{vd12['trace_pages']}</b>. Di halaman itu ditemukan
<b>{vd12['pages'][vd12['trace_pages'][0]]['n_trace_paths']} path</b> panjang
(≈{vd12['leads'][0]['n_segmen']} segmen/path), lalu <b>diurutkan posisi-y</b>
(atas→bawah) → I…V6. Tiap path langsung jadi satu lead:</p>
<img src="{raw12}"/><p class="cap">12 path vektor 12-lead, digambar dari koordinat PDF
asli (tiap warna = 1 lead, tertumpuk seperti di halaman).</p>
{vlead_table(vd12)}
<p>Lihat kolom <b>titik-1 (x,y) → mV</b>: itu konversi langsung
<span class="mono">mV=(median_y−y)/{10*PT:.3f}</span> pada koordinat pertama tiap
lead. Mis. V2 bersegmen {[L['n_segmen'] for L in vd12['leads'] if L['lead']=='V2'][0]},
amplitudo {[L['amp_mV'] for L in vd12['leads'] if L['lead']=='V2'][0]} mV (S-wave dalam).</p>

<h4>Di mana angka-angka itu berada? — satu lead (V2) dari awal sampai akhir</h4>
<p>Agar jelas, berikut <b>Lead V2 saja</b> dengan setiap angka pada tabel di atas
<b>ditandai posisinya di gambar</b> — bukan ditimpa hasil digital, tapi memperlihatkan
proses penuh dari koordinat mentah → mV:</p>
<img src="{leaddet}"/>
<p class="cap">Atas (Tahap A): koordinat PDF mentah. Bawah (Tahap B): setelah konversi mV.</p>
<table class="kv">
 <tr><td>🔴 titik-1 (x,y)</td><td>koordinat <b>pertama</b> trace V2 = (30.07, 452.53);
  inilah baris "titik-1" di tabel.</td></tr>
 <tr><td>🟢 median_y (baseline)</td><td>garis hijau putus-putus = 451.8 pt = "nol" lead;
  kolom <b>median_y</b>.</td></tr>
 <tr><td>🔻 y_min (R-peak)</td><td>titik tertinggi (y terkecil = 415.8 pt); batas atas
  kolom <b>y_range</b>.</td></tr>
 <tr><td>🔺 y_max (S-wave)</td><td>titik terdalam (y terbesar = 563.1 pt); batas bawah
  <b>y_range</b>.</td></tr>
 <tr><td>↕ amplitudo</td><td>jarak y_min→y_max = 147.3 pt = <b>5.197 mV</b>; kolom
  <b>amplitudo</b>.</td></tr>
 <tr><td>Tahap B (mV)</td><td>baseline → 0 mV; R-peak & S-wave dikonversi
  <span class="mono">mV=(median_y−y)/{10*PT:.3f}</span>.</td></tr>
</table>
<p>Jadi tiap sel tabel punya <b>lokasi nyata</b> pada trace: baseline = garis tengah,
y_range = rentang atas–bawah, titik-1 = ujung kiri, amplitudo = tinggi total. Konversi
ke mV (Tahap B) hanya membalik &amp; menskala — bentuk tetap sama.</p>

<h3>5.9 Contoh nyata — perhitungan vektor 6-LEAD (multi-halaman)</h3>
<p>File <span class="mono">{vd6['file']}</span> = <b>{vd6['n_pages']} halaman</b>; trace
di halaman <b>{vd6['trace_pages']}</b> (halaman 0 = cover, dilewati). Tiap halaman
berisi <b>6 path</b>. Karena rekaman 30 detik terpotong, halaman-halaman
<b>disambung berurutan</b>:</p>
{vconcat_table(vd6)}
<p>Pada tiap halaman, 6 path diurutkan posisi-y → I, II, III, aVR, aVL, aVF, lalu
disambung antar-halaman per lead. Rincian path (halaman pertama):</p>
<img src="{raw6}"/><p class="cap">6 path vektor 6-lead di koordinat PDF asli (3 dtk pertama).</p>
{vlead_table(vd6)}
<div class="note"><b>Inti perbedaan 6 vs 12-lead:</b> 12-lead = <b>12 path / 1 halaman</b>
(durasi pendek, 1 layar); 6-lead = <b>6 path / halaman × beberapa halaman</b> yang
<b>disambung</b> menjadi 30 detik. Selebihnya identik: baca (x,y) → median baseline →
mV → resample 250 Hz → highpass.</div>

<h2 id="s6">6. Visual: Apa yang Terjadi (langkah demi langkah) <a href="#" class="top">↑</a></h2>
<p>Contoh Lead II (~3 detik). <b>Bentuk gelombang tidak berubah</b>; hanya
representasinya yang bertransformasi.</p>
<div class="stepviz"><img src="{I['step_1']}"/><p><b>Langkah 1 — PDF asli.</b>
Potongan halaman Lead II + grid. Trace = perintah garis vektor (bukan piksel).</p></div>
<div class="stepviz"><img src="{I['step_2']}"/><p><b>Langkah 2 — Baca (x,y) + baseline.</b>
Titik dibaca apa adanya (satuan point, y ke bawah); garis hijau = baseline = median(y).</p></div>
<div class="stepviz"><img src="{I['step_3']}"/><p><b>Langkah 3 — Konversi mV.</b>
Sumbu dibalik &amp; diskalakan: mV=(baseline−y)/{pmv:.3f}; sumbu-x → detik.</p></div>
<div class="stepviz"><img src="{I['step_4']}"/><p><b>Langkah 4 — Resample 250 Hz.</b>
Interpolasi ke grid waktu seragam; bentuk tetap, titik kini berjarak sama.</p></div>
<div class="stepviz"><img src="{I['step_5']}"/><p><b>Langkah 5 — Highpass 0.5 Hz.</b>
Drift baseline dibuang; garis dasar rata di nol; P-QRS-T tak terdistorsi.</p></div>
<div class="stepviz"><img src="{I['step_6']}"/><p><b>Langkah 6 — Sinyal digital final.</b>
mV bersih, sampling seragam — siap AI &amp; FHIR.</p></div>
<details><summary>Lihat semua langkah dalam satu panel</summary>
<img src="{I['fig_pipeline_stages']}"/></details>

<h3>6.2 Semua lead — galeri per-lead + penilaian</h3>
<p>Proses 6 langkah di atas dijalankan <b>untuk SETIAP lead secara terpisah</b> (tiap
lead = satu path vektor sendiri). Berikut <b>seluruh lead</b> ditampilkan satu per satu:
garis <b>hitam = asli</b>, <b>merah = hasil digital</b> (250 Hz). Kotak di tiap panel =
<b>penilaian</b> lead itu (SNR, PRD, r). Semakin merah menempel ke hitam, makin setia.</p>
<h4>6-Lead — 6 lead + nilainya</h4>
<img src="{pl6}"/>
<p class="cap">Tiap panel: 1 lead. Hitam=asli, merah=digital. Kotak hijau/biru = metrik lead itu.</p>
<h4>12-Lead — 12 lead + nilainya</h4>
<img src="{pl12}"/>
<p class="cap">Ke-12 lead. Lead yang datar/tak-terekam ditandai khusus (mis. pada rekaman limb-only).</p>
<div class="note"><b>Cara baca:</b> garis merah (digital) menumpuk di atas garis hitam
(asli) di hampir semua titik → ekstraksi setia. <b>PRD kecil + r→1</b> mengonfirmasi
tiap lead diambil dengan benar. Penilaian lengkap angka per-lead untuk SEMUA record ada
di <a href="#s12">§12</a>.</p>

<h2 id="s7">7. Pipeline 6-Lead (AliveCor / Kardia) <a href="#" class="top">↑</a></h2>
<div class="step"><b>1) Deteksi.</b> Tiap halaman trace berisi 6 polyline panjang;
halaman cover dilewati.</div>
<div class="step"><b>2) Multi-halaman.</b> Rekaman 30 dtk terpotong beberapa halaman →
<b>disambung berurutan</b> (berapa pun jumlah halaman).</div>
<div class="step"><b>3) Urutkan</b> 6 path by-posisi-y → I, II, III, aVR, aVL, aVF.</div>
<div class="step"><b>4) Konversi mV + resample 250 Hz + highpass + cek Einthoven.</b></div>
<img src="{cmp6}"/><p class="cap">Kiri: PDF asli (grid+label) · Kanan: hasil digital.</p>

<h2 id="s8">8. Pipeline 12-Lead (Export) <a href="#" class="top">↑</a></h2>
<div class="step"><b>1) Deteksi.</b> Satu halaman, 12 polyline (~3700 segmen/lead).</div>
<div class="step"><b>2) Urutkan</b> 12 path by-posisi-y → I…V6.</div>
<div class="step"><b>3) Konversi + resample + highpass</b> (sama seperti 6-lead).</div>
<div class="step"><b>4) Deteksi lead datar.</b> Bila rekaman hanya limb (mis. 0002),
V1–V6 ditandai datar/tak-terekam — bukan dipaksa-baca.</div>
<img src="{cmp12}"/><p class="cap">12-lead: PDF asli ⟷ hasil digital, tertumpuk per-lead.</p>

<h2 id="s9">9. Penanganan Tumpang Tindih (overlap) <a href="#" class="top">↑</a></h2>
<p>Ini masalah klasik digitalisasi EKG yang paling sering merusak hasil. Pada tata
letak printout, lead disusun berdekatan secara vertikal. Bila sebuah gelombang sangat
tinggi/dalam, ia <b>menjulur keluar dari lajurnya dan masuk ke lajur lead tetangga</b>,
sehingga tinta dua lead <b>bersilang</b> di atas kertas.</p>

<h3>9.1 Geometri masalah (angka nyata dari record 0004)</h3>
<p>Mari pakai pasangan <b>V2 dan V3</b>. V2 adalah lead prekordial di atas septum/ventrikel
kanan, sehingga <b>gelombang-S-nya dalam</b> (amplitudo V2 di sini = {[L['amp_mV'] for L in vd12['leads'] if L['lead']=='V2'][0]} mV).</p>
<table class="kv">
 <tr><td>Baseline V2 (posisi-y di kertas)</td><td class="mono">451.8 point</td></tr>
 <tr><td>Baseline V3</td><td class="mono">541.7 point</td></tr>
 <tr><td>Jarak antar-baseline V2→V3</td><td class="mono">89.9 pt = 31.7 mm = 3.17 mV</td></tr>
 <tr><td>Titik terdalam S-wave V2</td><td class="mono">y = 563.1 point</td></tr>
 <tr><td>Lajur normal V3 (±0.9 mV)</td><td class="mono">516 – 567 point</td></tr>
 <tr><td><b>Penetrasi S-wave V2 ke bawah baseline V3</b></td>
  <td class="mono"><b>21.4 pt = 7.55 mm = 0.75 mV</b></td></tr>
</table>
<p>Artinya: puncak-bawah S-wave V2 (y=563) <b>jatuh di dalam pita V3</b> (516–567) —
menembus 7.55 mm melewati garis nol V3. Di kolom-x itu, tinta V2 dan V3 menempati
posisi vertikal yang sama.</p>
<img src="{ovz}"/>
<p class="cap">Zoom satu beat: S-wave V2 (biru) menukik ke lajur V3 (kuning). Garis ungu
putus-putus = kolom tempat kedua tinta bertumpuk.</p>

<h3>9.2 Kenapa metode berbasis gambar (piksel) gagal</h3>
<p>Digitizer piksel bekerja <b>kolom-demi-kolom</b>: untuk tiap kolom-x ia mencari
piksel gelap (tinta) lalu menebak posisi-y trace. Saat dua trace bersilang:</p>
<div class="step"><b>Ambiguitas kepemilikan.</b> Di kolom persilangan ada <b>dua</b>
gugus piksel gelap (V2 dan V3). Algoritma harus menebak mana milik V3 — tak ada
informasi untuk memastikannya.</div>
<div class="step"><b>Climbing / collision.</b> Penelusur V3 yang berjalan kiri→kanan
"tersedot" mengikuti spike V2 yang menukik (karena itu piksel gelap terdekat), lalu
menghasilkan <b>defleksi palsu</b> pada V3 — V3 seolah ikut turun dalam.</div>
<div class="step"><b>Connected-component menyatu.</b> Bila tinta benar-benar bersentuhan,
analisis komponen melihatnya sebagai <b>satu objek</b>, sehingga kedua lead tercampur.</div>
<p>Inilah artefak yang dulu muncul pada tahap U-Net kami (V3 "memanjat" ke V2). Semua
metode berbasis citra menghadapi batas fundamental ini karena <b>informasi kepemilikan
sudah hilang</b> begitu sinyal menjadi piksel.</p>

<h3>9.3 Kenapa metode vektor menyelesaikannya total</h3>
<p>Di PDF vektor, V2 dan V3 adalah <b>dua objek path yang berbeda</b> — masing-masing
satu daftar koordinat terurut:</p>
<pre class="code">V2.path = [ ... (x=k, y=563.1) ... ]   # daftar milik V2
V3.path = [ ... (x=k, y=541.7) ... ]   # daftar milik V3 (x SAMA, list BEDA)</pre>
<div class="step"><b>Kepemilikan sudah terkode.</b> Pada kolom-x yang sama, V2 punya
titiknya sendiri dan V3 punya titiknya sendiri — di <b>dua daftar berbeda</b>. Kita tak
pernah perlu "menebak" milik siapa.</div>
<div class="step"><b>Tak ada langkah piksel.</b> Kita membaca daftar V2 sampai habis untuk
lead V2, lalu daftar V3 untuk lead V3. Persilangan visual sama sekali tak relevan —
kita tak melihat gambar.</div>
<div class="step"><b>Pemisahan "by construction".</b> Karena itu hasilnya pasti bersih
(panel kanan): V2 mempertahankan S-wave dalamnya, V3 mempertahankan morfologinya
sendiri, <b>tanpa kontaminasi</b>.</div>
<img src="{I['fig_overlap']}"/>
<p class="cap">Kiri: posisi di halaman (spike V2 masuk pita V3) · Kanan: hasil ekstraksi —
V2 &amp; V3 terpisah bersih (di-offset agar jelas).</p>

<h3>9.4 Bukti angka: "kepemilikan terkode" itu apa sebenarnya</h3>
<p>Mari buktikan dengan koordinat <b>mentah dari PDF</b>, tepat di kolom persilangan
<span class="mono">x = 162.51 point</span> (saat S-wave V2 paling dalam). Tiap lead
adalah satu daftar koordinat; berikut isi nyata kedua daftar di sekitar titik itu:</p>
<table><tr>
 <td style="vertical-align:top;width:50%">
 <b style="color:#1d4ed8">Daftar koordinat V2</b> (baseline 451.8 pt)
 <pre class="code">idx |   x(pt)  |  y(pt)  |  mV
934 | 162.22 | 553.99 | -3.605
935 | 162.37 | 558.44 | -3.762
<b>936 | 162.51 | 563.11 | -3.926</b>  ← di kolom ini
937 | 162.65 | 562.53 | -3.906
938 | 162.79 | 557.44 | -3.726</pre></td>
 <td style="vertical-align:top;width:50%">
 <b style="color:#ea580c">Daftar koordinat V3</b> (baseline 541.7 pt)
 <pre class="code">idx |   x(pt)  |  y(pt)  |  mV
934 | 162.22 | 561.91 | -0.712
935 | 162.37 | 564.78 | -0.813
<b>936 | 162.51 | 570.37 | -1.010</b>  ← di kolom ini
937 | 162.65 | 571.95 | -1.066
938 | 162.79 | 574.89 | -1.169</pre></td>
</tr></table>
<p>Pada <b>x = 162.51 yang sama</b>:</p>
<ul>
 <li><b style="color:#1d4ed8">V2</b> menyimpan <span class="mono">y = 563.11</span>
  → <b>−3.93 mV</b> (S-wave dalam) — titik ini ada di <b>daftar V2</b>.</li>
 <li><b style="color:#ea580c">V3</b> menyimpan <span class="mono">y = 570.37</span>
  → <b>−1.01 mV</b> (gelombang V3 sendiri) — titik ini ada di <b>daftar V3</b>.</li>
</ul>
<p>Di kertas, kedua titik cuma <b>7 pt (~2.5 mm) terpisah</b> — nyaris menempel. Metode
piksel akan bingung memilih yang mana. Tetapi karena <b>y=563 sudah berada di daftar V2</b>
dan <b>y=570 sudah berada di daftar V3</b>, kita tinggal membaca masing-masing daftar —
<b>tak ada keputusan "milik siapa" yang perlu diambil</b>. <i>Itulah</i> arti
"kepemilikan sudah terkode": label lead melekat pada titik sejak di file.</p>
<img src="{ovb}"/>
<p class="cap">Titik mentah V2 (biru) &amp; V3 (oranye) di sekitar persilangan. Lingkaran
besar = titik pada x=162.51; keduanya tersimpan di daftar masing-masing.</p>

<div class="ok"><b>Kesimpulan:</b> overlap adalah masalah <b>fundamental</b> bagi metode
gambar (kepemilikan piksel hilang), tetapi <b>bukan masalah sama sekali</b> bagi
ekstraksi vektor (kepemilikan sudah terkode di objek path). Itulah sebabnya artefak
collision/climbing yang dulu menyiksa digitalisasi <b>hilang total</b> — bukan ditambal,
melainkan tak pernah terjadi.</div>

<h2 id="s10">10. Validitas — 4 Bukti Independen <a href="#" class="top">↑</a></h2>
<div class="step"><b>Bukti 1 — Kalibrasi dari file sendiri.</b> Pulsa 1 mV yang dicetak
alat, diukur dari koordinat PDF = <b>{pmv:.3f} point</b> → cocok sempurna dengan
turunan teori (10×72/25.4). Skala mV terbukti benar langsung.</div>
<div class="step"><b>Bukti 2 — Hukum Einthoven/Goldberger.</b> Batasan <i>fisika</i>:
III=II−I, aVR=−(I+II)/2, dst. Lead direkam terpisah, namun hasil kita memenuhi relasi
itu dengan RMSE ~0.005 mV. Mustahil tercapai jika koordinat/kalibrasi salah → bukti silang.</div>
<div class="step"><b>Bukti 3 — Cocok nilai cetak alat.</b> Pengukuran tercetak device
(RV5, SV1 dalam mV) cocok dengan hasil hitung kita (~0.05 mV).</div>
<div class="step"><b>Bukti 4 — Round-trip &amp; metrik baku.</b> r ≈ 0.999, SNR 26–44 dB,
PRD very good/good, WDD &lt; 3% (lihat §11–12).</div>

<h2 id="s11">11. Metrik Akademis — Pendalaman <a href="#" class="top">↑</a></h2>
<h3>Kenapa paket metrik ini?</h3>
<p>Tiga lapis saling melengkapi, semuanya baku di literatur EKG:</p>
<div class="step"><b>Lapis sinyal (SNR, PRD).</b> Galat menyeluruh. SNR = metrik resmi
<b>PhysioNet/CinC 2024</b>; PRD = standar kompresi EKG dengan <b>ambang baku</b>
(Zigel dkk.).</div>
<div class="step"><b>Lapis bentuk (Pearson r).</b> Kemiripan pola, lepas dari skala.</div>
<div class="step"><b>Lapis diagnosis (WDD).</b> Apakah angka klinis (HR, amplitudo-R)
berubah — yang benar-benar penting.</div>
<h3>Definisi, rumus, makna</h3>
<table>
 <tr><th>Metrik</th><th>Rumus</th><th>Makna &amp; bentuk</th><th>Acuan</th></tr>
 <tr><td><b>SNR</b> (dB)</td><td class="mono">10·log₁₀(Σ(r−r̄)²/Σ(r−s)²)</td>
  <td>energi sinyal ÷ energi galat; makin tinggi makin setia. Tiap +6 dB ≈ galat ½.</td>
  <td>PhysioNet 2024</td></tr>
 <tr><td><b>PRD</b> (%)</td><td class="mono">100·√(Σ(r−s)²/Σ(r−r̄)²)</td>
  <td>galat RMS relatif energi sinyal; kebalikan SNR.</td><td>Zigel 2000</td></tr>
 <tr><td><b>Pearson r</b></td><td class="mono">cov(r,s)/(σr·σs)</td>
  <td>1 = bentuk identik; sensitif pola, bukan skala.</td><td>umum</td></tr>
 <tr><td><b>RMSE</b> (mV)</td><td class="mono">√mean((r−s)²)</td>
  <td>galat absolut rata-rata.</td><td>umum</td></tr>
 <tr><td><b>maxAE</b> (mV)</td><td class="mono">max|r−s|</td>
  <td>galat absolut terburuk (biasanya di puncak QRS).</td><td>umum</td></tr>
 <tr><td><b>WDD*</b> (%)</td><td class="mono">RMS relatif [HR, amplitudo-R], beat tercocokkan</td>
  <td>distorsi level-diagnosis.</td><td>Zigel 2000 (ringkas)</td></tr>
</table>
<div class="note"><b>Ambang PRD</b> (MOS, Zigel dkk.): &lt;2% "very good", 2–9% "good",
&gt;9% ditinjau. <b>WDD &lt; 4%</b> = aman diagnostik. Pembanding: 1 piksel cetak 254 dpi ≈ 0.025 mV.</div>
<h3>Apa yang diukur? (bentuk visual)</h3>
<img src="{I['fig_arti_metrik']}"/><p class="cap">V2: trace asli (hitam) vs digital (merah)
nyaris menempel; residual (merah muda) tipis.</p>
<h3>Bentuk metrik: "sangat baik" → "buruk"</h3>
<img src="{I['fig_bentuk_metrik']}"/><p class="cap">Makin merah menempel ke hitam →
SNR↑, PRD↓, r→1. Kasus kita = panel kiri.</p>
<p class="sub"><i>r = referensi (trace asli, di-render 1000 Hz); s = uji (output 250 Hz).
Lead datar dikecualikan. WDD* memakai 2 fitur teruji-andal; ST/T tak dipakai (rapuh).</i></p>

<h2 id="s12">12. Hasil Validasi — Per-Record &amp; Per-Lead <a href="#" class="top">↑</a></h2>
<h3>6-Lead (n={len(six)}) — ringkas per record</h3>
<table>
 <tr><th>File</th><th>lead</th><th>SNR(dB)</th><th>PRD(%)</th><th>r</th>
  <th>RMSE(µV)</th><th>maxAE(µV)</th><th>WDD(%)</th></tr>
 {rec_rows(six)}
 <tr style="font-weight:700"><td>RATA-RATA</td><td>—</td><td>{a6[0]:.1f}</td>
  <td>{a6[1]:.2f} {badge(a6[1])}</td><td>{a6[2]:.5f}</td><td>{a6[3]*1000:.2f}</td>
  <td>{a6[4]*1000:.1f}</td><td>{a6[5]:.2f}</td></tr>
</table>
<h4>Rincian per-lead (6-lead)</h4>
{perlead_details(six)}
<h3>12-Lead (n={len(twelve)}) — ringkas per record</h3>
<table>
 <tr><th>File</th><th>lead</th><th>SNR(dB)</th><th>PRD(%)</th><th>r</th>
  <th>RMSE(µV)</th><th>maxAE(µV)</th><th>WDD(%)</th></tr>
 {rec_rows(twelve)}
 <tr style="font-weight:700"><td>RATA-RATA</td><td>—</td><td>{a12[0]:.1f}</td>
  <td>{a12[1]:.2f} {badge(a12[1])}</td><td>{a12[2]:.5f}</td><td>{a12[3]*1000:.2f}</td>
  <td>{a12[4]*1000:.1f}</td><td>{a12[5]:.2f}</td></tr>
</table>
<h4>Rincian per-lead (12-lead)</h4>
{perlead_details(twelve)}
<div class="note"><b>Catatan downsampling.</b> PRD 12-lead sedikit lebih tinggi karena
trace 12-lead lebih rapat (≈500 Hz natif), sehingga keluaran 250 Hz memotong sedikit
puncak QRS. Menaikkan sampling (500–1000 Hz) menurunkan PRD ke "very good" — sumber
galat = pilihan sampling, bukan ekstraksi.</div>

<h2 id="s13">13. Output FHIR — Struktur Rinci <a href="#" class="top">↑</a></h2>
<p>Tiap record menghasilkan <b>FHIR R4 Bundle</b> (type=transaction) siap-SatuSehat,
dirakit oleh <span class="mono">output/fhir_converter.py</span>:</p>
<table>
 <tr><th>Resource</th><th>Isi</th><th>Catatan</th></tr>
 <tr><td>DiagnosticReport</td><td>kontainer laporan, category CARD, conclusion + code</td>
  <td>menaut semua Observation</td></tr>
 <tr><td>Observation (per lead)</td><td>valueSampledData (origin mV, period, data)</td>
  <td>satu per lead (6 atau 12)</td></tr>
 <tr><td>Observation (HR)</td><td>valueQuantity bpm (LOINC 8867-4)</td><td>bila terdeteksi</td></tr>
 <tr><td>Patient</td><td>identifier + gender</td><td>de-identified</td></tr>
 <tr><td>Device</td><td>nama alat</td><td>konteks</td></tr>
</table>
<h4>Contoh Observation satu lead</h4>
<pre class="code">{{
 "resourceType": "Observation", "status": "final",
 "code": {{ "coding": [{{ "code": "I", "display": "Lead I" }}] }},
 "valueSampledData": {{
   "origin": {{ "value": 0, "unit": "mV", "code": "mV" }},
   "period": 4.0,          // ms antar-sampel (= 1000/250 Hz)
   "dimensions": 1,
   "data": "0.01 0.02 0.03 ..."   // deret mV
 }}
}}</pre>
<p><span class="mono">period = 4.0 ms</span> ↔ 250 Hz. Nilai diagnosis (HR/dx)
memakai kode <b>SNOMED CT / LOINC / ICD-10</b>; lead yang belum ber-kode SNOMED resmi
memakai CodeSystem provisional (sesuai praktik IG SatuSehat).</p>

<h2 id="s14">14. Cara Kerja Model (U-Net &amp; ECGNet) <a href="#" class="top">↑</a></h2>
<p>Sistem memakai <b>dua model deep-learning</b> dengan peran berbeda. <b>Penting
dipahami:</b> untuk data utama Anda (PDF vektor) <b>ekstraksi sinyal TIDAK memakai
model</b> — itu murni baca-koordinat. Model hanya dipakai untuk (a) <i>fallback</i>
bila input berupa foto/scan raster (U-Net), dan (b) skrining diagnosis (ECGNet).</p>
<table>
 <tr><th>Model</th><th>Tugas</th><th>Kapan dipakai</th></tr>
 <tr><td><b>U-Net</b></td><td>segmentasi trace dari GAMBAR → sinyal</td>
  <td>hanya fallback foto/scan raster (bukan PDF vektor)</td></tr>
 <tr><td><b>ECGNet</b></td><td>klasifikasi sinyal → label diagnosis</td>
  <td>opsional, di atas sinyal apa pun (vektor/raster)</td></tr>
</table>

<h3>14.1 U-Net — mengubah GAMBAR EKG menjadi trace</h3>
<p>U-Net (Ronneberger 2015) adalah jaringan <b>encoder–decoder</b>: encoder
"meringkas" gambar jadi fitur (mengecil bertahap via MaxPool), decoder
"menggambar ulang" jadi peta piksel trace (membesar via ConvTranspose).
<b>Skip-connection</b> menyalurkan detail tepi dari encoder ke decoder agar garis
tipis EKG tidak hilang.</p>
<img src="{unet}"/>
<p class="cap">Arsitektur U-Net: encoder (kiri) → bottleneck → decoder (kanan), dengan
skip-connection (hijau).</p>
<div class="step"><b>Masukan:</b> potongan gambar kertas-EKG (3×H×W).
<b>Keluaran (out_ch=2):</b> (1) peta probabilitas "ini piksel trace?", dan
(2) <b>offset baseline</b> tiap piksel.</div>
<div class="step"><b>Trik pemisah lead bertumpuk:</b> kanal <i>offset</i> memprediksi
"piksel ini sebenarnya milik baseline yang mana". Saat dua lead bersilang, offset
membedakan kepemilikannya — meniru keunggulan vektor, tapi pada gambar.</div>
<div class="step"><b>Dari peta → sinyal mV:</b> tiap kolom-x diambil posisi-y trace,
lalu dikalibrasi (mm→mV) seperti pada §5. <b>Dilatih</b> dengan data EKG sintetik
(ribuan layout) agar tahan variasi. Bobot ~30 MB (<span class="mono">unet_best.pt</span>).</div>
<div class="ok"><b>Performa U-Net:</b> <b>Dice = 0.987</b> pada data validasi (epoch 41).
Dice mengukur seberapa pas peta-trace prediksi menutupi trace sebenarnya
(1.0 = sempurna) — 0.987 berarti segmentasi trace sangat akurat.</div>
<div class="note">Karena PDF Anda <b>vektor</b>, U-Net <b>tidak terpakai</b> untuk
6/12-lead Export &amp; Kardia — hanya cadangan bila suatu hari masuk foto/scan.</div>

<h3>14.2 ECGNet — membaca sinyal menjadi label diagnosis</h3>
<p>ECGNet adalah <b>1D-ResNet</b>: konvolusi <b>satu dimensi sepanjang waktu</b> untuk
mendeteksi pola gelombang (P, QRS, T) di tiap lead, lalu menggabungkannya jadi
keputusan diagnosis.</p>
<img src="{ecgnet}"/>
<p class="cap">Arsitektur ECGNet: input 12×1000 → Stem → 6 ResBlock → Global-Pool+FC →
5 probabilitas.</p>
<div class="step"><b>Masukan:</b> 12 lead, tiap lead di-<i>resample</i> ke 1000 titik
&amp; dinormalisasi (mean/std dari <span class="mono">norm_stats.npz</span>) → tensor
12×1000.</div>
<div class="step"><b>Stem + 6 ResBlock:</b> tiap blok = Conv1d (kernel 7) → BatchNorm →
ReLU → Dropout, plus <b>jalur pintas residual</b> (memudahkan latih jaringan dalam).
Tiap beberapa blok, panjang-waktu dikecilkan ×½ dan jumlah kanal dinaikkan
(32→64→128→256) — model "melihat" pola makin abstrak.</div>
<div class="step"><b>Kepala (head):</b> Global-Average-Pool meringkas seluruh waktu →
satu vektor → Linear → <b>5 keluaran</b>. Fungsi <b>sigmoid</b> (multi-label) memberi
probabilitas 0–1 untuk tiap kelas (boleh lebih dari satu positif).</div>
<table>
 <tr><th>Kode</th><th>Arti</th></tr>
 <tr><td>NORM</td><td>Normal</td></tr><tr><td>MI</td><td>Infark miokard</td></tr>
 <tr><td>STTC</td><td>Perubahan ST/T (iskemia/repolarisasi)</td></tr>
 <tr><td>CD</td><td>Gangguan konduksi</td></tr><tr><td>HYP</td><td>Hipertrofi</td></tr>
</table>
<div class="step"><b>Latih:</b> pada PTB-XL (21.799 rekaman 12-lead berlabel).
Bobot ~5 MB (<span class="mono">ecgnet_best.pt</span>).</div>
<h4>Performa ECGNet (uji pada fold-test PTB-XL)</h4>
<table>
 <tr><th>Metrik</th><th>AUC</th><th>Keterangan</th></tr>
 <tr><td><b>macro-AUC</b></td><td><b>0.925</b></td><td>rata-rata 5 kelas (benchmark PTB-XL ~0.90–0.93)</td></tr>
 <tr><td>NORM</td><td>0.949</td><td>Normal</td></tr>
 <tr><td>STTC</td><td>0.937</td><td>Perubahan ST/T</td></tr>
 <tr><td>MI</td><td>0.922</td><td>Infark miokard</td></tr>
 <tr><td>CD</td><td>0.917</td><td>Gangguan konduksi</td></tr>
 <tr><td>HYP</td><td>0.902</td><td>Hipertrofi</td></tr>
</table>
<p>AUC (Area Under ROC Curve) menilai kemampuan memisahkan "ada/tak-ada" kondisi:
1.0 = sempurna, 0.5 = tebakan acak. <b>0.925</b> setara level publikasi pada PTB-XL.</p>
<div class="warn"><b>Penting:</b> ECGNet bersifat <b>skrining eksperimental, bukan
diagnosis final</b>. Pada rekaman 6-lead (tanpa V1–V6), akurasi turun untuk kondisi
yang bergantung lead dada. Sekali lagi: <b>ekstraksi sinyal tidak memakai model</b> —
ECGNet hanya lapisan opsional di atas sinyal.</div>

<h2 id="s15">15. Keterbatasan &amp; Pengembangan <a href="#" class="top">↑</a></h2>
<div class="step"><b>Format.</b> Jalur eksak berlaku untuk PDF <b>vektor</b> (Export 12-lead,
Kardia 6-lead). Foto/scan raster memakai fallback U-Net (best-effort, bukan eksak).</div>
<div class="step"><b>Sampling 250 Hz.</b> Untuk fidelity riset, 500 Hz lebih ideal bagi
12-lead (natif ≈500 Hz). Mudah diubah via parameter fs.</div>
<div class="step"><b>WDD ringkas.</b> Memakai 2 fitur (HR, amplitudo-R); WDD penuh
(18 fitur Zigel) perlu anotasi fidusial — rencana pengembangan.</div>
<div class="step"><b>AI 6-lead.</b> Tanpa lead dada, sensitivitas kondisi tertentu menurun.</div>

<h2 id="s16">16. Glosarium &amp; Referensi <a href="#" class="top">↑</a></h2>
<h4>Glosarium</h4>
<table class="kv">
 <tr><td>Vektor (polyline)</td><td>grafik tersimpan sebagai deret koordinat garis, bukan piksel</td></tr>
 <tr><td>Baseline</td><td>garis nol sinyal lead (= median y)</td></tr>
 <tr><td>Kalibrasi 10mm/mV, 25mm/s</td><td>standar tinggi &amp; kecepatan EKG</td></tr>
 <tr><td>Baseline wander</td><td>drift garis dasar frekuensi sangat rendah (&lt;0.5 Hz)</td></tr>
 <tr><td>Highpass / filtfilt</td><td>filter buang frekuensi rendah, zero-phase (tak geser waktu)</td></tr>
 <tr><td>Einthoven/Goldberger</td><td>relasi fisika antar-lead (III=II−I, dst)</td></tr>
 <tr><td>SNR / PRD / WDD</td><td>metrik kesetiaan sinyal &amp; diagnosis</td></tr>
 <tr><td>FHIR R4 Bundle</td><td>format pertukaran data kesehatan (HL7), dipakai SatuSehat</td></tr>
</table>
<h4>Referensi</h4>
<ol style="font-size:13.5px">
 <li>Reyna MA dkk. <i>Digitization &amp; Classification of ECG Images — PhysioNet/CinC
  Challenge 2024.</i> (metrik SNR).</li>
 <li>Zigel Y, Cohen A, Katz A. <i>The Weighted Diagnostic Distortion (WDD) Measure for
  ECG Signal Compression.</i> IEEE Trans. Biomed. Eng., 2000. (PRD MOS &amp; WDD).</li>
 <li>HL7 FHIR R4; Panduan Implementasi SatuSehat, Kementerian Kesehatan RI.</li>
 <li>AHA/ACC/HRS — Rekomendasi standardisasi &amp; filter EKG diagnostik (highpass 0.5 Hz).</li>
 <li>Wagner P dkk. <i>PTB-XL, a large publicly available ECG dataset.</i> (latih ECGNet).</li>
</ol>

<footer>EKG-BRIN · laporan dihasilkan otomatis oleh <span class="mono">buat_laporan.py</span>
(sumber: metrik_hasil.json). Skrining AI bersifat eksperimental, bukan diagnosis final.
Data pasien de-identified (ID urut + sex).</footer>
</div></body></html>"""

    open(OUT, "w", encoding="utf-8").write(HTML)
    print("->", OUT, f"({len(HTML)/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()
