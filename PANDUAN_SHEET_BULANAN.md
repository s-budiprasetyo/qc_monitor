# Panduan: Google Sheet bulanan otomatis (folder Google Drive)

Setiap kali Anda mengupload file SAP (atau jadwal) untuk **bulan yang belum punya data**, aplikasi membuat Google Sheet baru
bernama `TOTOQC 2026-10` dst. di folder Drive Anda, lengkap dengan dua tab laporan (HASIL KERJA KARYAWAN dan ALASAN TIDAK TARGET).
Bulan yang sudah ada di Google Sheet utama (mis. September) **tetap di sana**. Google Sheet utama tetap menyimpan pengaturan
(karyawan, target, absensi, lembur, alasan, dll) dan daftar Google Sheet bulanan.

## Pengaturan satu kali
1. **Aktifkan Google Drive API**: https://console.cloud.google.com → project **totoqc-monitoringdata** → APIs & Services → Library → cari **Google Drive API** → Enable.
2. **Buat folder** di Google Drive Anda (mis. "TOTOQC BULANAN").
3. **Bagikan folder** ke email service account `qc-monitor@totoqc-monitoringdata.iam.gserviceaccount.com` sebagai **Editor**.
4. Buka folder itu, salin **ID folder** dari alamat (bagian setelah `/folders/`).
5. Streamlit Cloud → **app admin** → Settings → Secrets → tambahkan satu baris di bagian atas (sebelum `[gcp_service_account]`):
   ```toml
   drive_folder_id = "ID-FOLDER-ANDA"
   ```
   (App halaman utama tidak perlu baris ini; ia membaca daftar bulan dari Google Sheet utama.)
6. Reboot app admin. Upload file SAP bulan baru: Google Sheet bulan itu dibuat otomatis, dan tautannya muncul di bawah tabel Informasi.

Bila pembuatan gagal (mis. Drive API belum aktif atau folder belum dibagikan), data tetap aman tersimpan di Google Sheet utama
dan pesan penyebabnya muncul di jendela hasil upload.
