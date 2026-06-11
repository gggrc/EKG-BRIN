"""
verify_output.py — Verifikasi output JSON dari ECG Input Pipeline
"""
import json, os, sys, math, statistics

MIN_STD_MV      = 0.001
MAX_ABS_MV      = 50.0
EXPECTED_6  = {'I', 'II', 'III', 'aVR', 'aVL', 'aVF'}
EXPECTED_12 = EXPECTED_6 | {'V1', 'V2', 'V3', 'V4', 'V5', 'V6'}
# patient_id now lives inside metadata.patient_id
REQUIRED_FIELDS = [
    'leads', 'sampling_rate', 'duration_sec', 'num_leads',
    'input_format', 'device_vendor', 'timestamp'
]


def verify_json(file_path: str) -> dict:
    results = {'file': os.path.basename(file_path),
               'passed': [], 'warnings': [], 'errors': [],
               'signal_stats': {}}

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        results['passed'].append("JSON valid")
    except Exception as e:
        results['errors'].append(f"Cannot read JSON: {e}")
        return results

    missing = [f for f in REQUIRED_FIELDS if f not in data]
    if missing:
        results['errors'].append(f"Missing fields: {missing}")
    else:
        results['passed'].append("All required fields present")

    fs = data.get('sampling_rate', 500)
    if isinstance(fs, int) and fs in [100, 250, 500, 1000]:
        results['passed'].append(f"sampling_rate: {fs} Hz")
    else:
        results['warnings'].append(f"Unusual sampling_rate: {fs}")

    nl = data.get('num_leads', 0)
    if nl in [6, 12]:
        results['passed'].append(f"num_leads: {nl}")
    else:
        results['warnings'].append(f"Unusual num_leads: {nl}")

    leads = data.get('leads', {})
    actual = set(leads.keys())
    expected = EXPECTED_12 if nl == 12 else EXPECTED_6
    missing_leads = expected - actual
    if missing_leads:
        results['warnings'].append(f"Missing leads: {sorted(missing_leads)}")
    else:
        results['passed'].append(f"Leads OK: {sorted(actual)}")

    exp_samples = int(fs * data.get('duration_sec', 10))
    bad_samples = []
    flat, anomaly, nan_leads = [], [], []

    for lead, sig in leads.items():
        n = len(sig)
        if abs(n - exp_samples) > 20:
            bad_samples.append(f"{lead}:{n}")
        bad = [v for v in sig if not math.isfinite(v)]
        if bad:
            nan_leads.append(lead); continue
        mean_v = statistics.mean(sig)
        std_v  = statistics.stdev(sig) if len(sig) > 1 else 0
        min_v, max_v = min(sig), max(sig)
        results['signal_stats'][lead] = {
            'mean': round(mean_v,4), 'std': round(std_v,4),
            'min': round(min_v,4), 'max': round(max_v,4),
            'range': round(max_v-min_v,4)
        }
        if std_v < MIN_STD_MV: flat.append(lead)
        if abs(min_v) > MAX_ABS_MV or abs(max_v) > MAX_ABS_MV:
            anomaly.append(lead)

    if bad_samples: results['warnings'].append(f"Sample count off: {bad_samples}")
    else: results['passed'].append(f"Sample counts OK (~{exp_samples})")
    if nan_leads: results['errors'].append(f"NaN/Inf in: {nan_leads}")
    else: results['passed'].append("No NaN/Inf")
    if flat: results['warnings'].append(f"Flat leads: {flat}")
    else: results['passed'].append("All leads have signal variance")
    if anomaly: results['warnings'].append(f"Out-of-range leads: {anomaly}")
    else: results['passed'].append("Signal range OK")

    # Check scale field
    scale = data.get('scale')
    if scale and all(k in scale for k in ['y_min','y_max']):
        results['passed'].append(f"Scale present: y={scale['y_min']}~{scale['y_max']} mV")
    else:
        results['warnings'].append("No scale field — round-trip may lose y-range")

    return results


def print_report(result):
    file = result['file']
    p, w, e = result['passed'], result['warnings'], result['errors']
    status = "FAIL" if e else ("WARN" if w else "OK")
    print(f"\n{'─'*60}")
    print(f"  [{status}]  {file}")
    print(f"{'─'*60}")
    for x in p: print(f"  ✅ {x}")
    for x in w: print(f"  ⚠️  {x}")
    for x in e: print(f"  ❌ {x}")
    stats = result['signal_stats']
    if stats:
        print(f"\n  {'Lead':<6} {'Mean':>8} {'Std':>8} {'Min':>8} {'Max':>8} {'Range':>8}")
        print(f"  {'─'*6} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
        for lead, s in stats.items():
            flat = " ← FLAT" if s['std'] < MIN_STD_MV else ""
            print(f"  {lead:<6} {s['mean']:>8.4f} {s['std']:>8.4f} "
                  f"{s['min']:>8.4f} {s['max']:>8.4f} {s['range']:>8.4f}{flat}")
    print(f"\n  {len(p)} passed, {len(w)} warnings, {len(e)} errors")


def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_output.py output_handoff/")
        return
    target = sys.argv[1]
    files = []
    if os.path.isdir(target):
        files = [os.path.join(target,f) for f in sorted(os.listdir(target))
                 if f.endswith('.json')]
    elif os.path.isfile(target):
        files = [target]
    if not files:
        print("No JSON files found.")
        return
    print(f"\n{'='*60}")
    print(f"  ECG Verifier — {len(files)} file(s)")
    print(f"{'='*60}")
    ok = warn = fail = 0
    for fp in files:
        r = verify_json(fp)
        print_report(r)
        if r['errors']: fail += 1
        elif r['warnings']: warn += 1
        else: ok += 1
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {ok} OK, {warn} warnings, {fail} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
