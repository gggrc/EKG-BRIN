import json
import os
from ecg_input_router import load_ecg


def export_for_fhir(file_path: str, 
                    output_path: str = None,
                    vendor: str = "Unknown") -> dict:
    """
    Load ECG dari file apapun, export ke JSON untuk Orang B.
    """
    ecg = load_ecg(file_path, vendor=vendor)
    result = ecg.to_dict()
    
    if output_path is None:
        basename = os.path.splitext(os.path.basename(file_path))[0]
        output_path = f"output_{basename}.json"
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"✅ Exported ke: {output_path}")
    return result


if __name__ == "__main__":
    # Test export
    result = export_for_fhir(
        'ptb-xl/records500/00000/00001_hr.hea',
        'handoff_untuk_orangB.json',
        vendor="PTB-XL PhysioNet"
    )
    
    
    print(f"\nStruktur output yang dikirim ke Orang B:")
    for key, val in result.items():
        if key == 'leads':
            print(f"  leads: {{{', '.join(result['leads'].keys())}}}")
            print(f"    contoh I[0:3]: {result['leads']['I'][:3]}")
        else:
            print(f"  {key}: {val}")