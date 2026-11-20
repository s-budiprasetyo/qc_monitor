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

## Tahap 8e: hub roda gigi + Daftar Operator
- Halaman Upload Foreman: roda gigi biru muda (klik untuk buka/tutup menu, berputar). Menu: MONITORING LABEL, DAFTAR OPERATOR (item lain bisa ditambah nanti).
- Daftar Operator: tabel master `operator` (prn, kode_opr). Sebelum pertama disimpan, daftar bawaan = karyawan jenis PERIKSA yang tidak disilang. Setelah disimpan, hanya nama di daftar itu yang muncul di NAMA OPERATOR.
- Rencana Produksi ditunda sesuai keputusan.

## Tahap 8f: roda gigi berputar di halaman Upload Admin
- `components/roda/index.html` + `core.hub.roda()`: roda gigi biru muda dengan 8 pilihan melingkar (Hasil Kerja, Lembur, Absensi, Jadwal Kerja, Evaluasi, Data Awal, Daftar Operator, Rencana Produksi [Segera]), kartu detail + status + BUKA. Putar lewat panah, klik ikon, atau roda mouse. Menambah pilihan = menambah satu baris di `MENU` (app_admin.py); lingkaran menyesuaikan jumlahnya.
- Tombol "Data awal" pindah ke roda; tombol Verifikasi dan lonceng tetap di atas.

## Tahap 8g: jendela admin/foreman serasi dengan tema biru
- Semua jendela halaman admin (Hasil Kerja, Lembur, Absensi, Jadwal, Evaluasi, Data Awal, Verifikasi, Lonceng, Daftar Operator) memakai kepala biru gradasi + ikon garis putih + tombol perbesar/tutup putih, sama dengan halaman utama. Jendela di tengah layar (desktop) dan lebar penuh di HP.
- Roda gigi: bagian bawah tidak lagi terpotong.

## Tahap 9a: aplikasi laporan (app ke-3) — % label afkir
- `app_laporan.py` + `core/laporan.py`. Hanya lihat dan unduh Excel; login admin atau foreman (user/password sama dengan app lain).
- % = afkir ÷ pcs bagus SAP (kolom Total) per karyawan, per label, per hari (Tanggal Posting). SNI dibagi pcs bagus label induknya.
  Label warna (mis. DR) dibagi pcs bagus baris SAP type+warna itu. QC dan QC SK terpisah. Kotor > 0,5% merah.
- Excel: Harian (satu tanggal) dan Bulanan (sheet Ringkasan bulan + Per hari); kolom % memakai rumus.
- Pasang sebagai app ke-3 di Streamlit Cloud: repo qc_monitor, Main file `app_laporan.py`, Secrets disalin dari app admin.
- 9b: keterangan label warna HBE (Harvest Beige), HF (Harvest Green), PP (Pastel Pink) ditambahkan ke data awal jenis label.

## Tahap 9c: tombol pindah antar aplikasi
- Secrets (letakkan SEBELUM baris `[admin]`, di baris paling atas): `url_laporan = "https://…"` di app admin; `url_admin = "https://…"` di app laporan.
- App admin/foreman: tombol "Laporan" (admin dan foreman). App laporan: admin melihat "Ke Upload Admin", foreman melihat "Ke Upload Foreman". Tombol tidak muncul bila alamat belum diisi. Tiap app punya login sendiri.

## Tahap 9d: bar atas baru, masuk antar app tanpa login ulang, kartu Informasi
- Bar atas bergaya kartu: tombol navigasi (Foreman/Admin, Laporan, Halaman Utama) + avatar, nama, peran + Keluar. Admin: Laporan + Halaman Utama; foreman: Laporan; app laporan: kembali ke Admin/Foreman; halaman utama tanpa tombol balik.
- Masuk tanpa login ulang: token HMAC berumur 30 menit di alamat (?t=), dibuang setelah dipakai. Syarat Secrets (SAMA di semua app, taruh di baris paling atas, sebelum [admin]):
  kunci_masuk = "teks acak panjang"; app admin: url_laporan, url_utama; app laporan: url_admin; app utama: kunci_masuk saja (hanya token admin yang diterima).
- Informasi update: kartu per file (waktu relatif + warna hijau/kuning/merah).

## Tahap 9e — Grup LABEL di aplikasi Laporan + Input Label
- Aplikasi laporan: menu grup **LABEL** → % Afkir Label (klik persen = rincian hari; klik RATA RATA = grafik + hari tertinggi + catatan foreman), Stok Label, Kolaborasi (placeholder).
- Foreman → gear → **INPUT LABEL**: tab *Label diterima* (stok masuk) dan *Stok label* (hitung → Simpan → Lihat selisih → Simpan / Adjust).
- Stok sistem = stok awal + diterima − (pcs bagus SAP + afkir). Stok awal = hitungan terakhir yang di-ADJUST, jika belum ada = 0 mulai 2026-11-01.
- Monitoring Label punya kolom baru `catatan` (alasan afkir). Tab baru `label_terima` dan `label_hitung` dibuat otomatis di Sheet master; kolom `catatan` ditambah ke `label_afkir`.
- Deploy: upload isi folder ke repo, reboot aplikasi admin dan laporan.

## Tahap 9f
- Laporan % Afkir Label: semua operator yang ada di SAP tampil; yang belum diinput afkirnya = 0,00%.
- Foreman: tombol **INPUT LABEL AFKIR** (dulu Monitoring Label), **INPUT LABEL BAGUS** (label diterima dari packing), **INPUT LABEL STOK** (hitung → Simpan → Lihat selisih: Type, Stok aktual, Stok sistem, Selisih; tombol Simpan dan Adjust).

## Tahap 9g
- % Label Afkir hanya kategori **Kotor**: % = kotor ÷ pcs bagus (merah bila > 0,5%). Rincian hari dan Excel ikut. Stok Label tetap memakai semua kategori afkir.
- Kotak persen yang mengambang saat rincian dibuka disembunyikan.

## Tahap 9h
- Total % rincian hari = total afkir kotor ÷ total pcs bagus semua baris label (SNI pendamping ikut dihitung di pembagi).
- Afkir **Proses** otomatis dari SAP = M + LA + LB + F, hanya type closet CW (bukan CE6/CE7/CE9/warna/SNI). Di form input kolom Proses terkunci; laporan dan stok memakai angka SAP langsung. Stok: pemakaian = pcs bagus + semua kategori afkir.

## Tahap 9i
- Form Input Label Afkir: kartu type dan SNI sejajar (tinggi sama), tombol hapus jadi ✕ kecil di pojok kanan atas kartu; baris diberi nama "Proses".
- Proses (M+LA+LB+F SAP) juga untuk label SNI pendamping (nilai sama dengan type induk), di form, laporan, dan stok.

## Tahap 10a — Stok label per meja
- Stok label = stok Foreman + stok tiap meja. Dimulai dari 0 pada 19-11-2026 (`QC_MULAI_STOK`); catatan sebelum tanggal itu tidak dihitung. Stok boleh minus.
- Halaman utama: matriks sampai hari ini; klik sel → tab HASIL KERJA / INPUT LABEL / PINDAH LABEL (karyawan hanya untuk namanya sendiri, admin semua).
- Foreman: Input Label Afkir menampilkan stok meja (klik angka untuk memindahkan), Input Label Stok per lokasi (Simpan / Adjust), Kosongkan Label Meja per pabrik.
- Laporan Stok Label: total per label dan per meja. Setelah upload: Reboot ketiga aplikasi.

## Tahap 10b
- Input Label Afkir: setelah operator + tanggal + shift dipilih, kolom type terisi otomatis dari SAP (tetap bisa + Label). Afkir Proses terisi dari SAP (M+LA+LB+F) tetapi bisa diubah; nilai yang disimpan dipakai apa adanya di laporan.
- Data SAP per bulan disimpan sementara 60 detik supaya dialog tidak lag.
- Login halaman utama: verifikasi Google bersifat opsional; user + password cukup, email (bila terverifikasi) ikut tercatat di riwayat.
- Tombol tutup (✕) jendela Foreman dibuat lebih jelas.

## Tahap 10c
- Dialog hasil kerja: bila total ≥100% tampil keterangan "Target tercapai" (tombol alasan memang hanya muncul bila <100%).

## Tahap 10d
- Verifikasi Google WAJIB lagi di halaman publik (langkah 1) dan untuk Foreman di halaman admin; email dicatat di riwayat (akses.pelaku()).
- Baris type di Input Label Afkir dirapikan (rata atas).

## Tahap 10e
- Login halaman admin: akun QC-THOFA, QC-SENJA, QC-PAMBUDI (dari tabel karyawan) berperan Foreman dan langsung masuk halaman Foreman. Daftar bisa diganti lewat Secrets [admin] foreman = [...].

## Tahap 10f
- Input Label Afkir: setelah tanggal, nama, pabrik, dan meja dipilih, bila data yang sama sudah ada muncul peringatan dengan tombol PERBAIKI DATA (membuka form berisi data lama + riwayat) atau PILIH MEJA LAIN. Form baru disembunyikan agar tidak dobel.

## Tahap 10g
- Halaman admin hanya untuk 5 akun: admin QC-SALIS (Secrets) + foreman QC-NURMUS (Musthofa), QC-RIZKI, QC-PAMBUDI (Haris Rizal Pambudi, akun khusus), QC-SATRIO (password dari tabel karyawan). Akun lain ditolak.
