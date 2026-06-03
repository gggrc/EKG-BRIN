"""
ecg_to_pdf.py — Round-trip JSON → PDF renderer
Preserves scale, waveform, and metadata from the JSON exactly.
"""
import json, sys, os, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

LEADS_6  = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF']
LEADS_12 = LEADS_6 + ['V1', 'V2', 'V3', 'V4', 'V5', 'V6']


def get_scale(ecg: dict) -> dict:
    """Extract scale from JSON — supports both old and new schema."""
    scale = ecg.get('scale', {})
    return {
        'y_min':      scale.get('y_min',      ecg.get('y_min',  -2.5)),
        'y_max':      scale.get('y_max',      ecg.get('y_max',   2.5)),
        'mv_per_mm':  scale.get('mv_per_mm',  0.1),
        'mm_per_sec': scale.get('mm_per_sec', 25.0),
    }


def render_strip(ecg: dict, leads_subset: list) -> io.BytesIO:
    """Render ECG strip using scale from JSON (round-trip accurate)."""
    sc       = get_scale(ecg)
    y_min    = sc['y_min']
    y_max    = sc['y_max']
    fs       = ecg['sampling_rate']
    duration = ecg['duration_sec']
    t        = np.linspace(0, duration, int(fs * duration))

    n    = len(leads_subset)
    fig, axes = plt.subplots(n, 1, figsize=(18, n * 1.5))
    if n == 1: axes = [axes]
    fig.patch.set_facecolor('white')

    for i, lead in enumerate(leads_subset):
        sig = ecg['leads'].get(lead, [0.0] * len(t))
        sig = np.array(sig[:len(t)])
        axes[i].plot(t, sig, 'k-', linewidth=0.7)
        axes[i].set_ylabel(lead, fontsize=8, rotation=0, labelpad=24, va='center')
        axes[i].set_xlim(0, duration)
        axes[i].set_ylim(y_min, y_max)          # ← exact same scale as original
        axes[i].grid(True, color='#ffaaaa', linewidth=0.3, alpha=0.8)
        axes[i].set_facecolor('#fff8f8')
        axes[i].tick_params(labelsize=5)
        axes[i].spines['top'].set_visible(False)
        axes[i].spines['right'].set_visible(False)

    plt.tight_layout(pad=0.2)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()
    buf.seek(0)
    return buf


def json_to_pdf(json_path: str, output_path: str = None) -> str:
    with open(json_path) as f:
        ecg = json.load(f)

    if output_path is None:
        base = os.path.splitext(os.path.basename(json_path))[0]
        output_path = os.path.join(
            os.path.dirname(json_path) or 'output_handoff',
            f"{base}_restored.pdf"
        )

    # Determine leads to render
    available = list(ecg['leads'].keys())
    # Filter out rhythm strip for main render
    main_leads = [l for l in available if not l.endswith('_rhythm')]
    if all(l in main_leads for l in LEADS_12):
        render_leads = LEADS_12
    else:
        render_leads = [l for l in LEADS_6 if l in main_leads]

    sc   = get_scale(ecg)
    meta = ecg.get('metadata', {})

    c = canvas.Canvas(output_path, pagesize=landscape(A4))
    w, h = landscape(A4)

    # Header
    c.setFillColorRGB(0.15, 0.15, 0.4)
    c.rect(0, h - 20*mm, w, 20*mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(8*mm, h - 9*mm, "ECG Report — Restored from Digital Record")
    c.setFont("Helvetica", 7.5)
    c.drawRightString(w - 8*mm, h - 8*mm,
        f"Source: {ecg.get('input_format','?').upper()}  |  "
        f"Vendor: {ecg.get('device_vendor','?')}")
    c.drawRightString(w - 8*mm, h - 15*mm,
        f"Timestamp: {str(ecg.get('timestamp','?'))[:19]}")

    # Patient metadata
    c.setFillColorRGB(0, 0, 0)
    my = h - 30*mm
    left_fields = [
        ("Patient ID",   str(meta.get('patient_id', '-'))),
        ("Age",          f"{meta.get('age','-')} y/o" if meta.get('age') else '-'),
        ("Sex",          {'M':'Male','F':'Female'}.get(str(meta.get('sex','')),'-')),
    ]
    right_fields = [
        ("Recording Date", str(meta.get('recording_date', '-'))[:19]),
        ("Device",         str(meta.get('device', ecg.get('device_vendor', '-')))),
        ("Report",         str(meta.get('report', ecg.get('notes', '-')))[:50]),
    ]
    for i, (k, v) in enumerate(left_fields):
        y = my - i*6*mm
        c.setFont("Helvetica-Bold", 8); c.drawString(8*mm, y, f"{k}:")
        c.setFont("Helvetica",      8); c.drawString(45*mm, y, v)
    for i, (k, v) in enumerate(right_fields):
        y = my - i*6*mm
        c.setFont("Helvetica-Bold", 8); c.drawString(120*mm, y, f"{k}:")
        c.setFont("Helvetica",      8); c.drawString(160*mm, y, v)

    # Parameter bar
    c.setFillColorRGB(0.9, 0.9, 1.0)
    c.rect(8*mm, my - 20*mm, w - 16*mm, 9*mm, fill=1, stroke=0)
    c.setFillColorRGB(0, 0, 0); c.setFont("Helvetica", 7.5)
    params = [
        ("Rate",     f"{ecg['sampling_rate']} Hz"),
        ("Duration", f"{ecg['duration_sec']} s"),
        ("Leads",    f"{ecg['num_leads']}-lead"),
        ("Scale",    f"{sc['mm_per_sec']} mm/s | {1/sc['mv_per_mm']:.0f} mm/mV"),
        ("Y range",  f"{sc['y_min']} ~ {sc['y_max']} mV"),
        ("Units",    ecg.get('units', 'mV')),
        ("SCP",      str(meta.get('scp_codes', '-'))[:25]),
    ]
    for i, (k, v) in enumerate(params):
        c.drawString(12*mm + i*38*mm, my - 14*mm, f"{k}: {v}")

    # ECG strip
    buf     = render_strip(ecg, render_leads)
    img_top = my - 28*mm
    c.drawImage(ImageReader(buf), 8*mm, 12*mm,
                width=w - 16*mm, height=img_top - 12*mm)

    # Footer
    c.setFont("Helvetica", 6); c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawString(8*mm, 6*mm,
        f"Restored from: {os.path.basename(json_path)}  |  "
        "Scale preserved from original recording.")
    c.drawRightString(w - 8*mm, 6*mm, "ECG Input Pipeline — Round-trip output")

    c.save()
    print(f"PDF restored: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('json_path', nargs='?', help='Path to JSON file')
    parser.add_argument('--out', help='Output PDF path')
    args = parser.parse_args()
    if not args.json_path:
        print('Usage: python ecg_to_pdf.py "output_handoff/result.json"')
        sys.exit(1)
    if not os.path.exists(args.json_path):
        print(f"File not found: {args.json_path}"); sys.exit(1)
    json_to_pdf(args.json_path, args.out)
