import os
import sys
import subprocess
import time
from pathlib import Path

# Konfigurasi Folder
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Pastikan folder ada
for folder in [INPUT_DIR, OUTPUT_DIR, SCRIPTS_DIR]:
    folder.mkdir(exist_ok=True)

print("=== QWEN SANDBOX LOCAL (PYTHON) ===")
print(f"Folder Input : {INPUT_DIR}")
print(f"Folder Output: {OUTPUT_DIR}")
print(f"Folder Script: {SCRIPTS_DIR}")
print("-----------------------------------")
print("Cara Pakai:")
print("1. Simpan file (jpg, txt, dll) ke folder 'input'.")
print("2. Copy script dari coder.qwen.ai, simpan sebagai .py di folder 'scripts'.")
print("3. Jalankan script tersebut lewat command ini:")
print(f"   python {SCRIPTS_DIR}/nama_script_kamu.py")
print("-----------------------------------")
print("Tips untuk Script dari Web:")
print("- Gunakan path relatif atau variabel lingkungan jika perlu akses file.")
print("- Contoh akses file input: '../input/nama_file.jpg' atau gunakan os.getcwd()")
print("- Contoh simpan hasil: '../output/hasil.txt'")
print("-----------------------------------")

# Cek apakah ada argumen script yang langsung dijalankan
if len(sys.argv) > 1:
    script_name = sys.argv[1]
    script_path = SCRIPTS_DIR / script_name
    
    if script_path.exists():
        print(f"\nMenjalankan script: {script_name}...")
        try:
            # Jalankan script dengan working directory di folder scripts
            # Tapi kita bisa atur agar relatif terhadap base dir jika perlu
            subprocess.run([sys.executable, str(script_path)], cwd=SCRIPTS_DIR, check=True)
            print("\n[SELESAI] Script berhasil dijalankan.")
        except subprocess.CalledProcessError as e:
            print(f"\n[ERROR] Script gagal dijalankan dengan kode error: {e.returncode}")
        except Exception as e:
            print(f"\n[ERROR] Terjadi kesalahan: {e}")
    else:
        print(f"[ERROR] Script '{script_name}' tidak ditemukan di folder {SCRIPTS_DIR}")
else:
    print("\nTidak ada script yang ditentukan.")
    print("Ketik: python sandbox_server.py nama_script.py")
    print("Atau jalankan manual: python scripts/nama_script.py")
