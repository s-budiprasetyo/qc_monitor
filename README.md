# Monitoring Hasil Kerja Karyawan QC (Tahap 1)

Dua aplikasi dari satu proyek: `app_publik.py` (halaman utama) dan `app_admin.py` (admin).

## Uji coba di komputer
1. `pip install -r requirements.txt`
2. Salin `.streamlit/secrets.toml.example` menjadi `.streamlit/secrets.toml`, isi bagian `[admin]` saja (hapus `sheet_id` dan `[gcp_service_account]` agar data tersimpan di folder `data/`).
3. Isi data awal: `python seed.py DATA_KARYAWAN.xlsx PENCAPAIAN_KERJA_QC.xlsx`
4. `streamlit run app_admin.py` lalu upload file SAP lewat tombol HASIL KERJA.
5. `streamlit run app_publik.py` untuk melihat tabel.

## Tahap 1 sudah mencakup
Penyimpanan (CSV lokal atau Google Sheet), perhitungan persen (sudah siap lembur dan menit masalah), halaman utama (tabel), halaman admin dengan tombol Hasil Kerja, tabel Informasi dan lonceng kalibrasi nama.
Tombol lain di admin masih nonaktif sampai tahap berikutnya.

## Pasang di cloud (tanpa Python di komputer)
Ikuti langkah di chat: GitHub (repo), Google Sheet + service account, Streamlit Cloud (dua app: app_publik.py dan app_admin.py).
Setelah online, buka halaman admin, klik DATA AWAL dan upload DATA_KARYAWAN.xlsx dan PENCAPAIAN_KERJA_QC.xlsx, lalu HASIL KERJA untuk file SAP.

## Pembaruan (Tahap 2)
Jadwal Kerja (upload QC/SK + Setting Manual), Absensi, Lembur, tampilan admin baru, dan halaman utama berwarna
(putih masuk, kuning tidak masuk berkode S/I/CT/D/R, merah muda libur). Folder `components` wajib ikut diupload ke GitHub.
