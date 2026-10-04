# Panduan: aktifkan verifikasi Google (supaya email pemosting tercatat)

Hanya dipasang di **app halaman utama** (bukan app admin). Selama belum dipasang, jejak mencatat "(tanpa Google) QC-NAMA".

## A. Google Cloud (project yang sama: totoqc-monitoringdata)
1. Buka https://console.cloud.google.com → pilih project **totoqc-monitoringdata**.
2. Menu **APIs & Services → OAuth consent screen** (atau "Google Auth Platform") → pilih **External** → isi nama aplikasi (mis. "Monitoring QC TOTO"), email dukungan, email kontak → simpan.
3. Di bagian **Audience / Publishing status**, tekan **Publish app** (jadi "In production"). Ini perlu supaya semua karyawan dengan akun Google apa pun bisa masuk. Cakupan yang dipakai hanya email dan profil dasar, jadi tidak perlu verifikasi Google.
4. **Credentials → Create credentials → OAuth client ID** → Application type: **Web application**.
5. **Authorized redirect URIs** → tambahkan: `https://ALAMAT-APP-HALAMAN-UTAMA.streamlit.app/oauth2callback` (ganti dengan alamat app halaman utama Anda, tanpa garis miring di akhir).
6. Buat → salin **Client ID** dan **Client secret**.

## B. Streamlit Cloud (app halaman utama → Settings → Secrets)
Tambahkan di bawah isi Secrets yang sudah ada:

```toml
[auth]
redirect_uri = "https://ALAMAT-APP-HALAMAN-UTAMA.streamlit.app/oauth2callback"
cookie_secret = "isi-teks-acak-panjang-bebas-minimal-32-huruf"
client_id = "SALIN-CLIENT-ID"
client_secret = "SALIN-CLIENT-SECRET"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Semua nilai harus memakai tanda kutip. Simpan, lalu reboot app.

## C. Cara pakai karyawan
Login (user + password) → saat memposting alasan, tekan **Verifikasi dengan Google** → pilih akun → kembali ke halaman utama → login lagi bila diminta → ajukan. Email akun Google tercatat di tab ALASAN TIDAK TARGET.
