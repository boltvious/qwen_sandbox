# Qwen Sandbox & Ninja CLI 🥷

Project ini adalah **sandbox environment** dan **CLI tool** untuk berinteraksi dengan API Qwen (chat.qwen.ai / coder.qwen.ai) secara aman dan efisien.

## 📋 Daftar Isi
- [Fitur](#fitur)
- [Struktur Project](#struktur-project)
- [Setup & Instalasi](#setup--instalasi)
- [Cara Penggunaan](#cara-penggunaan)
- [Alur Autentikasi](#alur-autentikasi)
- [Keamanan](#keamanan)
- [Troubleshooting](#troubleshooting)

---

## ✨ Fitur

### 1. **Ninja CLI (`ninja_tos`)**
   - CLI tool untuk chat dengan Qwen AI langsung dari terminal
   - Auto-extract cookie dari browser (Chrome, Edge, Brave) menggunakan `rookiepy`
   - Penyimpanan token aman dalam file `.qwen_auth.json`
   - Support multiple API prefixes (`/api/v2`, `/api/v1`, `/api`)
   - Session probing otomatis untuk deteksi endpoint valid

### 2. **Sandbox Server (`sandbox_server.py`)**
   - Environment terisolasi untuk menjalankan kode Python dengan aman
   - Folder terpisah: `input/`, `output/`, `scripts/`
   - Bisa proses file lokal (TXT, JPG, PNG, dll) tanpa upload ke web
   - Cocok untuk testing kode yang dihasilkan oleh Qwen AI

### 3. **Auth System**
   - Wizard setup interaktif (paste manual atau auto-extract)
   - JWT token decoder untuk cek masa berlaku session
   - Display status akun (email, nama, expired date)
   - Token hanya dikirim via header `Authorization`, tidak di-cookie

---

## 📁 Struktur Project

```
/workspace/
├── auth.py              # Ekstraksi cookie dari browser
├── auth_store.py        # Wizard setup & penyimpanan token
├── client.py            # HTTP client dengan handling auth
├── coder_cli.py         # Entry point CLI utama
├── chat.py / chat_v5.py # Modul chat dengan Qwen
├── sandbox_server.py    # Local sandbox server
├── test_*.py            # File testing
└── README.md            # Dokumentasi ini
```

---

## 🚀 Setup & Instalasi

### Prasyarat
- Python 3.8+
- Browser modern (Chrome/Edge/Brave) dengan session login Qwen aktif

### Langkah Instalasi
1. Clone repo ini:
   ```bash
   git clone https://github.com/boltvious/qwen_sandbox.git
   cd qwen_sandbox
   ```

2. Install dependencies:
   ```bash
   pip install httpx rich rookiepy
   ```

3. Jalankan wizard setup:
   ```bash
   python auth_store.py
   ```

4. Pilih metode login:
   - **Opsi 1**: Paste cookie manual dari DevTools browser
   - **Opsi 2**: Auto-extract dari browser (butuh akses admin/root)

---

## 💻 Cara Penggunaan

### Menggunakan Ninja CLI
```bash
python coder_cli.py "Halo, buatkan fungsi Python untuk hitung luas lingkaran"
```

### Menggunakan Sandbox Server
1. Letakkan file input di folder `input/`:
   ```
   input/data.txt
   input/foto.jpg
   ```

2. Simpan script Python di folder `scripts/`:
   ```
   scripts/proses_data.py
   ```

3. Jalankan sandbox:
   ```bash
   python sandbox_server.py scripts/proses_data.py
   ```

4. Cek hasil di folder `output/`.

---

## 🔐 Alur Autentikasi

1. **Load Saved Auth**: Sistem cek file `.qwen_auth.json` untuk token tersimpan.
2. **Wizard (jika belum ada token)**:
   - User pilih metode (manual paste atau auto-extract).
   - Token divalidasi dengan call ke endpoint `/api/v2/auths/`.
3. **Build Client**:
   - Token dipasang di header `Authorization: Bearer <token>`.
   - Hanya cookie non-sensitif (`_bl_uid`, `locale`) yang dikirim.
4. **Session Probe**: Sistem uji coba prefix API yang valid.
5. **Ready**: CLI siap digunakan hingga token expired.

---

## 🛡️ Keamanan

### Best Practices yang Diterapkan:
- ✅ Token **TIDAK** dikirim sebagai cookie, hanya via header `Authorization`.
- ✅ File `.qwen_auth.json` ditandai rahasia (jangan di-commit ke Git).
- ✅ JWT payload didecode hanya untuk display, tanpa verifikasi signature.
- ✅ Cookie sensitif difilter sebelum dikirim ke server.
- ✅ Base URL dapat diubah via environment variable `QWEN_BASE_URL`.

### Peringatan:
- ⚠️ Jangan share file `.qwen_auth.json` atau isi cookie ke siapa pun.
- ⚠️ Gunakan opsi auto-extract hanya di komputer pribadi.
- ⚠️ Token expired otomatis, jalankan ulang `python auth_store.py` jika perlu refresh.

---

## 🔧 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `Auth gagal bro` | Pastikan sudah login di browser, lalu jalankan `python auth_store.py` lagi. |
| `Belum nemu prefix API` | Cek koneksi internet, atau coba ganti `QWEN_BASE_URL` via env var. |
| `Gagal extract cookie` | Jalankan terminal sebagai Administrator (Windows) atau sudo (Linux/Mac). |
| `Token expired` | Session Qwen punya masa berlaku. Ulangi wizard setup untuk refresh. |
| `ModuleNotFoundError` | Install dependencies: `pip install httpx rich rookiepy`. |

---

## 📝 Catatan Pengembangan

- **Commit Identity**: `codercode-ai <ai@codercode.local>`
- **Branch Utama**: `main`
- **Push Policy**: Selalu emit tag `<push_request>` sebelum push ke remote.

---

## 🤝 Kontribusi

Pull request welcome! Untuk fitur baru, pastikan:
1. Tidak merusak alur auth yang sudah ada.
2. Menambahkan test case di folder `test_*.py`.
3. Update dokumentasi ini jika ada perubahan signifikan.

---

**Dibuat dengan ❤️ untuk komunitas Qwen AI Indonesia.**