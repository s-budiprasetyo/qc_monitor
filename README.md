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

## Pembaruan (Tahap 2b)
- **Verifikasi karyawan (✕):** setelah upload Data awal / SAP / Jadwal, jendela VERIFIKASI terbuka otomatis bila ada karyawan baru. Centang ✕ pada orang yang tidak boleh tampil. Daftar ini dipakai di tabel monitor, Lembur, Absensi dan Jadwal.
- **Lonceng (Pusat Notifikasi):** target belum ada punya kolom ISI TARGET / ABAIKAN / HAPUS DATA. OP107 otomatis menjadi catatan "mengerjakan OP107".
- **Tampilan:** hub dengan gambar dan jalur sirkuit milikmu, ikon dari file Excel di tiap jendela. Folder baru **assets** dan **components/hub** wajib ikut diupload ke GitHub.


## Tahap 5
- Kotak kosong di tabel bisa diklik (setelah login) untuk mencatat kegiatan lain; muncul kotak biru K.
- Google Sheet bulanan otomatis: lihat PANDUAN_SHEET_BULANAN.md.

## Tahap 8b: Monitoring Label (halaman Upload Foreman)
- Tombol **MONITORING LABEL**: pilih tanggal kerja, shift (Pagi/Sore), operator, pabrik (Pabrik 1: 21 meja, Pabrik 2: 19, QC SK: 5) dan meja;
  klik **+ Type** (kategori, lalu type dari file target) untuk menambah kolom type; isi Lengket / Garis / Kotor; SIMPAN.
- Satu baris tersimpan per (operator, meja, type). Meja yang sama boleh diisi operator berbeda. Type yang sama untuk operator+meja+tanggal+shift
  ditolak (ubah lewat tabel). Tanggal posting dihitung otomatis: Pagi = tanggal kerja, Sore = hari kerja berikutnya menurut jadwal operator.
- Data masuk ke Google Sheet bulan tanggal kerja (tab `label_afkir` dan `meja_abaikan`); bila Sheet bulannya belum ada, simpan ditolak seperti upload hasil kerja.
- Notifikasi **Meja yang belum dicek** per pabrik; tombol Abaikan mencatat "Diabaikan oleh <nama>" (bisa dibatalkan).
- Daftar operator sementara = karyawan jenis PERIKSA (atau jenis kosong) yang tidak disilang di Verifikasi; Tahap 3 menambah Daftar Operator.

- Revisi 8c: isian angka label default kosong (placeholder 0) dan terblok saat diklik; baris jenis afkir **Proses** ditambahkan (total = Lengket+Garis+Kotor+Proses). Tab Google Sheet lama tanpa kolom `proses` tetap terbaca (kolom diisi kosong).

## Tahap 8d: jenis label, SNI, kelola jenis label
- Tabel master `jenis_label` (Type SAP + Warna SAP -> Label; kolom Kategori, SNI, Keterangan). Data awal dari `assets/jenis_label_awal.csv`
  (dibuat dari Excel type_warna_SAP.xlsx) dipakai sampai tabel pertama kali disimpan dari halaman admin.
- Warna putih (W) memakai nama type sebagai label; warna lain memakai kode warna (mis. CE7 + DR -> label DR). Type CRJP tanpa label.
- Label SNI = label kedua untuk tiap type CW kecuali CW52J: kolom `SNI <label>` muncul otomatis di samping label induknya
  (disimpan sebagai baris tersendiri, kategori `SNI`, kolom `induk` = label induk). % afkir SNI = afkir SNI / pcs bagus SAP type induknya.
- Admin: bagian **Jenis label (tambah / ubah / unggah Excel)** di bawah halaman Upload Admin; lonceng memberi tahu type+warna dari hasil SAP
  yang belum terpetakan (pasangkan ke label atau TANPA LABEL).
- `label.label_untuk_sap(type, warna)` = fungsi pencocok untuk laporan % label afkir (Tahap 4).
