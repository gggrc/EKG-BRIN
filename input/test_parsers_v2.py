"""Quick test script for the updated parsers."""
import os, json, sys

def test_image(path, desc):
    from parsers.parse_image import parse_image
    print(f"\n{'='*60}")
    print(f"  TEST: {desc}")
    print(f"  File: {path}")
    print(f"{'='*60}")
    try:
        r = parse_image(path)
        print(f"  Leads      : {list(r.leads.keys())}")
        print(f"  Num leads  : {r.num_leads}")
        print(f"  Y range    : {r.y_min} ~ {r.y_max} mV")
        print(f"  Calibration: {r.calibration}")
        print(f"  Layout     : {r.original_layout}")
        if r.lead_amplitudes:
            print(f"  Lead amplitudes:")
            for lead, stats in r.lead_amplitudes.items():
                if not lead.endswith('_rhythm'):
                    std = stats['std_mV']
                    rng = stats['range_mV']
                    print(f"    {lead:>5}: std={std:.4f}  range={rng:.4f} mV")
        
        # Save JSON
        out_name = os.path.splitext(os.path.basename(path))[0]
        out_path = f"output_handoff/{out_name}_test.json"
        with open(out_path, 'w') as f:
            json.dump(r.to_dict(), f, indent=2)
        print(f"  JSON saved : {out_path}")
        
        return r, out_path
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback; traceback.print_exc()
        return None, None


def test_pdf_restore(json_path, desc):
    from ecg_to_pdf import json_to_pdf
    print(f"\n  Restoring PDF from {json_path}...")
    try:
        pdf_path = json_to_pdf(json_path)
        print(f"  PDF saved  : {pdf_path}")
        return pdf_path
    except Exception as e:
        print(f"  ERROR restoring PDF: {e}")
        import traceback; traceback.print_exc()
        return None


if __name__ == "__main__":
    os.makedirs("output_handoff", exist_ok=True)
    
    # Test 1: Normal(100).jpg — clinical 3x4 with calibration pulse
    if os.path.exists("input_processed/Normal(100).jpg"):
        r, jp = test_image("input_processed/Normal(100).jpg", 
                           "Clinical 3x4 + cal pulse")
        if jp:
            test_pdf_restore(jp, "Normal(100) restore")
    
    # Test 2: Other processed images
    proc_dir = "input_processed"
    if os.path.isdir(proc_dir):
        for f in sorted(os.listdir(proc_dir)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png')) and 'Normal' not in f:
                test_image(os.path.join(proc_dir, f), f"Processed: {f}")
    
    # Test 3: Sample inputs
    for f in ['sample_inputs/vendor_scan.png', 'sample_inputs/vendor_scan_12lead.png']:
        if os.path.exists(f):
            test_image(f, f"Sample: {os.path.basename(f)}")
    
    print(f"\n{'='*60}")
    print("  ALL TESTS COMPLETE")
    print(f"{'='*60}")
