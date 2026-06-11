"""
proses_ekg.py — SATU PINTU untuk Anda.

  pilih 6 / 12 / auto lead  ->  input PDF atau folder  ->  hasil:
    1) <nama>_digital.json : sinyal digital mV + skrining AI + cek-mutu (universal)
    2) <nama>_fhir.json    : FHIR R4 Bundle siap-SatuSehat
    3) <nama>_compare.png  : perbandingan PDF ASLI vs HASIL DIGITAL (side-by-side)

CONTOH PEMAKAIAN
  # auto-deteksi (6 atau 12 ketahuan sendiri), satu file:
  python proses_ekg.py --input 6-lead/DH_6L-0425.pdf

  # paksa 6-lead, proses SATU FOLDER:
  python proses_ekg.py --lead 6 --folder 6-lead

  # 12-lead, satu folder, output ke folder tertentu:
  python proses_ekg.py --lead 12 --folder Export --out hasil_12

  # tanpa gambar perbandingan (lebih cepat):
  python proses_ekg.py --folder 6-lead --no-compare

OPSI
  --lead {auto,6,12}   auto = deteksi otomatis (default).
                       6    = keluarkan 6 limb lead (I,II,III,aVR,aVL,aVF).
                       12   = harapkan 12 lead (bila file cuma 6, diberi tahu).
  --input FILE | --folder DIR   (pilih salah satu)
  --out DIR            folder output (default: ./hasil)
  --no-compare         lewati pembuatan gambar perbandingan
"""
import os
import sys
import re
import glob
import json
import argparse

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'input'))
sys.path.insert(0, os.path.join(HERE, 'input', 'parsers'))
sys.path.insert(0, os.path.join(HERE, 'output'))

import run_any                       # pipeline digital + AI + cek-mutu (dipakai ulang)
import fhir_converter as FC          # konverter FHIR resmi (punya tim, hanya diimpor)

LIMB6 = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
SUPPORTED = {'.pdf'}                  # skrip ini fokus PDF (6/12 lead)


# ── util: ambil HR dari notes (mis. "HR=71bpm") bila ada ──────────────
def _hr_from_notes(notes):
    if not notes:
        return None
    m = re.search(r'HR\s*=\s*(\d{2,3})', notes)
    return int(m.group(1)) if m else None


# ── 1) proses satu file -> digital JSON + FHIR JSON ───────────────────
def process_file(path, lead_mode, out_dir):
    from ecg_input_router import load_ecg
    u = load_ecg(path)

    # filter/centang sesuai pilihan lead
    if lead_mode == '6':
        u.leads = {k: v for k, v in u.leads.items() if k in LIMB6}
        u.num_leads = 6
    elif lead_mode == '12' and u.num_leads < 12:
        print(f"  [INFO] diminta 12-lead, tapi file ini {u.num_leads}-lead "
              f"-> diproses apa adanya ({u.num_leads} lead).")

    # (A) JSON digital universal (sinyal + AI + cek-mutu Einthoven)
    rec = run_any.to_fhir_ready(u, path)
    # ROUTING OTOMATIS: hasil masuk subfolder sesuai jenis lead terdeteksi
    # -> <out>/6-lead/  atau  <out>/12-lead/
    sub = f"{u.num_leads}-lead"
    out_dir = os.path.join(out_dir, sub)
    os.makedirs(out_dir, exist_ok=True)
    name = os.path.splitext(os.path.basename(path))[0]
    dig_path = os.path.join(out_dir, name + '_digital.json')
    json.dump(rec, open(dig_path, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=2)

    # (B) FHIR R4 Bundle (siap SatuSehat)
    ai = rec.get('ai_screening', {}) or {}
    analysis = {
        'labels': ai.get('positive_labels', []),
        'conclusion': (ai.get('top_label_desc', '') +
                       (' | ' + rec['quality']['einthoven_check'].get('note', '')
                        if rec['quality'].get('einthoven_check') else '')).strip(' |'),
        'heart_rate_bpm': _hr_from_notes(u.notes),
    }
    bundle = FC.to_fhir_bundle(u.to_dict(), analysis)
    fhir_path = os.path.join(out_dir, name + '_fhir.json')
    FC.save_bundle(bundle, fhir_path)

    return u, rec, dig_path, fhir_path, out_dir


# ── 2) gambar perbandingan: PDF ASLI vs HASIL DIGITAL ─────────────────
def make_compare(path, u, out_dir):
    import fitz
    import cv2
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from vector_pdf import _long_paths, PSEC_PT

    leads = {k: np.asarray(v, float) for k, v in u.leads.items()}
    names = [n for n in run_any.LEAD_ORDER if n in leads]
    fs = int(u.sampling_rate)
    rid = os.path.splitext(os.path.basename(path))[0]

    # cari halaman trace + durasinya (utk menyamakan jendela waktu)
    doc = fitz.open(path)
    img = None; dur = u.duration_sec; pno = 0
    for p in range(doc.page_count):
        lp = _long_paths(doc[p])
        if len(lp) in (6, 12):
            allx = [x for P in lp for x, _ in P]
            dur = (max(allx) - min(allx)) / PSEC_PT
            pix = doc[p].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
            img = cv2.cvtColor(
                cv2.imdecode(np.frombuffer(pix.tobytes('png'), np.uint8),
                             cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            pno = p
            break
    if img is None:                    # PDF raster: render halaman 0
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(2.0, 2.0))
        img = cv2.cvtColor(
            cv2.imdecode(np.frombuffer(pix.tobytes('png'), np.uint8),
                         cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
    doc.close()

    nrow = len(names)
    fig = plt.figure(figsize=(17, max(7, 1.4 * nrow + 1)))
    gs = fig.add_gridspec(nrow, 2, width_ratios=[1, 1.15],
                          hspace=0.35, wspace=0.12)
    axL = fig.add_subplot(gs[:, 0])
    axL.imshow(img); axL.axis('off')
    axL.set_title(f"PDF ASLI (hal.{pno+1}, ~{dur:.1f}s)", fontsize=12)

    nwin = int(dur * fs)
    for i, nm in enumerate(names):
        ax = fig.add_subplot(gs[i, 1])
        y = leads[nm][:nwin]; t = np.arange(len(y)) / fs
        ax.plot(t, y, lw=0.7, color='k')
        ax.axhline(0, color='r', lw=0.4, alpha=0.5)
        ax.set_ylabel(nm, rotation=0, ha='right', va='center', fontsize=10)
        ax.grid(True, alpha=0.25); ax.margins(x=0)
        if i == 0:
            ax.set_title("HASIL DIGITAL (siap-FHIR)", fontsize=12)
        if i < nrow - 1:
            ax.set_xticklabels([])
    ax.set_xlabel('detik')
    fig.suptitle(f"{rid}  -  ASLI vs DIGITAL  ({nrow} lead)", fontsize=14)
    out = os.path.join(out_dir, rid + '_compare.png')
    fig.savefig(out, dpi=110, bbox_inches='tight'); plt.close(fig)
    return out


def summarize(rec, dig, fhir, cmp_path):
    r = rec['recording']; ec = rec['quality'].get('einthoven_check', {})
    print(f"\n  File   : {rec['source_file']}  ({r['num_leads']} lead, "
          f"{r['duration_sec']}s @ {r['sampling_rate_hz']}Hz, {rec['device_vendor']})")
    if ec.get('status') == 'OK':
        print(f"  Mutu   : OK (Einthoven worst RMSE {ec['worst_rmse_mv']} mV)")
    elif ec.get('status') == 'REVIEW':
        print(f"  Mutu   : !! PERLU DITINJAU (RMSE {ec['worst_rmse_mv']} mV)")
    ai = rec.get('ai_screening')
    if ai:
        print(f"  AI     : {ai['top_label']} ({ai['top_label_desc']}) "
              f"prob={ai['probabilities'][ai['top_label']]}")
    print(f"  Digital: {dig}")
    print(f"  FHIR   : {fhir}")
    if cmp_path:
        print(f"  Compare: {cmp_path}")


def main():
    ap = argparse.ArgumentParser(
        description='Pilih 6/12/auto lead -> PDF/folder -> digital + FHIR + perbandingan.')
    ap.add_argument('--lead', choices=['auto', '6', '12'], default='auto',
                    help='auto (default) / 6 / 12')
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--input', help='satu file PDF')
    g.add_argument('--folder', help='folder berisi banyak PDF')
    ap.add_argument('--out', default=os.path.join(HERE, 'hasil'),
                    help='folder output (default ./hasil)')
    ap.add_argument('--no-compare', action='store_true',
                    help='lewati gambar perbandingan')
    args = ap.parse_args()

    if args.input:
        files = [args.input]
    else:
        files = sorted(f for f in glob.glob(os.path.join(args.folder, '**', '*'),
                                            recursive=True)
                       if os.path.splitext(f)[1].lower() in SUPPORTED)
    if not files:
        print('Tidak ada PDF ditemukan.'); return

    print(f"Mode lead: {args.lead} | {len(files)} file -> {args.out}")
    ok = 0
    for p in files:
        if not os.path.exists(p):
            print(f"  ! tak ada: {p}"); continue
        try:
            u, rec, dig, fhir, routed = process_file(p, args.lead, args.out)
            cmp_path = None if args.no_compare else make_compare(p, u, routed)
            summarize(rec, dig, fhir, cmp_path)
            ok += 1
        except Exception as e:
            import traceback
            print(f"  ! GAGAL {os.path.basename(p)}: {type(e).__name__}: {e}")
            traceback.print_exc()
    print(f"\nSelesai: {ok}/{len(files)} -> {args.out}")


if __name__ == '__main__':
    main()
