import json
import argparse
import os
import matplotlib.pyplot as plt

def plot_ecg_json(json_path: str, show_plot: bool = True):
    if not os.path.exists(json_path):
        print(f"Error: File '{json_path}' tidak ditemukan.")
        return

    OUTPUT_DIR = "output_plots"
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Loading data from {json_path}...")
    with open(json_path, 'r') as f:
        data = json.load(f)

    leads = data.get('leads', {})
    sampling_rate = data.get('sampling_rate', 500)
    
    if not leads:
        print("Error: Tidak ada data leads di dalam file JSON.")
        return

    print(f"Ditemukan {len(leads)} leads. Sampling rate: {sampling_rate} Hz.")

    # Membuat figure dengan subplot sebanyak jumlah lead
    num_leads = len(leads)
    # Ubah ukuran figure agar jauh lebih lebar (25) dan tidak terlalu tinggi per lead (1.2)
    fig, axes = plt.subplots(num_leads, 1, figsize=(25, 1.2 * num_leads), sharex=True, sharey=True)
    
    if num_leads == 1:
        axes = [axes]

    for ax, (lead_name, signal) in zip(axes, leads.items()):
        # Membuat sumbu waktu (X) berdasarkan sampling rate
        time_axis = [i / sampling_rate for i in range(len(signal))]
        
        ax.plot(time_axis, signal, color='black', linewidth=1.0)
        ax.set_ylabel(lead_name, fontsize=12, fontweight='bold', rotation=0, labelpad=20)
        ax.grid(True, which='major', color='#ffaaaa', linestyle='-', linewidth=0.5)
        ax.grid(True, which='minor', color='#ffdddd', linestyle='-', linewidth=0.2)
        ax.minorticks_on()
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[-1].set_xlabel("Time (seconds)", fontsize=12)
    fig.suptitle(f"ECG Waveform: {os.path.basename(json_path)}", fontsize=16)
    
    # Mengurangi spasi vertikal antar grafik agar lebih padat
    plt.subplots_adjust(top=0.95, hspace=0.1)
    
    # Menyimpan file ke output_plots
    basename = os.path.splitext(os.path.basename(json_path))[0]
    save_path = os.path.join(OUTPUT_DIR, f"{basename}_plot.png")
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"Grafik berhasil disimpan di: {save_path}")
    
    if show_plot:
        print("Menampilkan grafik... Tutup jendela grafik untuk keluar.")
        plt.show()
    else:
        plt.close(fig)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot ECG JSON file")
    parser.add_argument("json_file", type=str, help="Path ke file JSON di dalam output_handoff")
    parser.add_argument("--no-show", action="store_true", help="Hanya simpan gambar tanpa menampilkan jendela popup")
    args = parser.parse_args()
    
    plot_ecg_json(args.json_file, show_plot=not args.no_show)
