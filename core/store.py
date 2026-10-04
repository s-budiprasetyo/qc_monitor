"""Penyimpanan data: CSV lokal (uji coba) atau Google Sheet (produksi).
Semua nilai disimpan sebagai teks supaya kode karyawan seperti 0023 tidak berubah."""
import os
import re
import time
import pandas as pd

KOLOM = {
    "karyawan": ["prn", "nama_web", "nama_sap", "user", "pass_hash", "kode_opr", "jenis", "tipe"],
    "target": ["grup", "type", "op", "target"],
    "alias": ["nama_sap", "prn"],
    "abaikan": ["nama_sap"],
    "update_log": ["nama_file", "waktu"],
    "lembur": ["prn", "tgl", "jam"],
    "absensi": ["prn", "tgl", "kode", "keterangan", "waktu"],
    "buku_bulan": ["bulan", "sheet_id", "nama"],  # Google Sheet per bulan (dibuat otomatis di folder Drive)
    "kegiatan": ["prn", "tgl", "teks", "waktu", "email"],  # kegiatan lain hari itu (tanpa hasil pcs)
    "bagian": ["prn", "bagian"],  # QC | SK, dari file jadwal kerja tempat orang itu terdaftar
    "roster": ["prn", "status"],  # status: ya (tampil di monitor) | tidak (disilang admin)
    "target_abaikan": ["grup", "type", "op"],
    "alasan": ["prn", "tgl", "no", "masalah", "menit", "foto"],  # alasan tidak target (maks 5 baris per orang per hari)
    "foto_alasan": ["id", "data"],  # foto kecil (base64) milik alasan
    "pengajuan": ["prn", "tgl", "menit", "status", "waktu", "email"],  # status: menunggu | V | X
    "pindah_hasil": ["prn", "tgl"],  # hasil kerja yang oleh admin dihitung di tanggal kerja (Transaction Date)
    "masalah_abaikan": ["prn", "tgl"],  # ketidaksesuaian jadwal yang diputuskan admin: abaikan
}
TAB_LAPORAN = ("HASIL KERJA KARYAWAN", "ALASAN TIDAK TARGET")
KOLOM_HASIL = ["tgl", "nama_sap", "type", "lokasi", "grup", "op", "periksa", "trx"]  # trx = Transaction Date (hari kerja sebenarnya)


def kolom_tabel(nama):
    if nama.startswith("hasil_"):
        return KOLOM_HASIL
    if nama.startswith("jadwal_"):
        return ["prn", "tgl", "status"]
    return KOLOM[nama]


class LocalStore:
    def __init__(self, folder="data"):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)

    def _path(self, nama):
        return os.path.join(self.folder, f"{nama}.csv")

    def read(self, nama):
        p = self._path(nama)
        if not os.path.exists(p):
            return pd.DataFrame(columns=kolom_tabel(nama))
        return pd.read_csv(p, dtype=str, keep_default_na=False)

    def write(self, nama, df):
        df.fillna("").astype(str).to_csv(self._path(nama), index=False)

    def tables(self):
        return [f[:-4] for f in os.listdir(self.folder) if f.endswith(".csv")]

    def write_laporan(self, nama, df, bulan=None):
        df.to_csv(self._path("laporan_" + nama.replace(" ", "_")), index=False)

    def tambah_baris(self, nama, kolom, baris, bulan=None):
        p = self._path("laporan_" + nama.replace(" ", "_"))
        ada = os.path.exists(p)
        pd.DataFrame([baris], columns=kolom).to_csv(p, mode="a", header=not ada, index=False)
    def hapus_baris(self, nama, cocok, bulan=None):
        p = self._path("laporan_" + nama.replace(" ", "_"))
        if not os.path.exists(p):
            return 0
        df = pd.read_csv(p, dtype=str).fillna("")
        m = pd.Series(True, index=df.index)
        for k, v in cocok.items():
            m &= df[k].str.strip() == str(v).strip()
        df[~m].to_csv(p, index=False)
        return int(m.sum())


class _Buku:
    """Satu file Google Sheet (buku). Hemat kuota API (batas baca 60 per menit): daftar tab dibaca sekali lalu disimpan,
    dan permintaan yang ditolak karena kuota (429/5xx) diulang otomatis dengan jeda."""
    def __init__(self, sh):
        import gspread
        self._gs = gspread
        self.sh = sh
        self._tabs = None

    def _retry(self, fn):
        for i in range(6):
            try:
                return fn()
            except self._gs.exceptions.APIError as e:
                kode = getattr(getattr(e, "response", None), "status_code", 0)
                if kode not in (429, 500, 502, 503) or i == 5:
                    raise
                time.sleep(3 * (i + 1))

    def _sheets(self, segar=False):
        if self._tabs is None or segar:
            self._tabs = {w.title: w for w in self._retry(self.sh.worksheets)}
        return self._tabs

    def _segarkan_bila_tab_hilang(self, fn):
        """Tab bisa dihapus/diganti manual di Google Sheet; daftar tab yang tersimpan jadi basi (error 400).
        Dalam kasus itu daftar tab dibaca ulang lalu perintah diulang sekali."""
        try:
            return fn()
        except self._gs.exceptions.APIError as e:
            kode = getattr(getattr(e, "response", None), "status_code", 0)
            if kode not in (400, 404):
                raise
            self._sheets(segar=True)
            return fn()

    def read(self, nama):
        def kerja():
            ws = self._sheets().get(nama)
            if ws is None:
                return pd.DataFrame(columns=kolom_tabel(nama))
            v = self._retry(ws.get_all_values)
            if not v:
                return pd.DataFrame(columns=kolom_tabel(nama))
            return pd.DataFrame(v[1:], columns=v[0])
        return self._segarkan_bila_tab_hilang(kerja)

    def write(self, nama, df):
        df = df.fillna("").astype(str)
        baris, kol = max(len(df) + 10, 100), max(len(df.columns), 6)

        def kerja():
            ws = self._sheets().get(nama)
            if ws is None:
                ws = self._retry(lambda: self.sh.add_worksheet(nama, rows=baris, cols=kol))
                self._tabs[nama] = ws
            self._retry(ws.clear)
            self._retry(lambda: ws.resize(rows=baris, cols=kol))
            self._retry(lambda: ws.update(range_name="A1", values=[list(df.columns)] + df.values.tolist(),
                                          value_input_option="RAW"))
        self._segarkan_bila_tab_hilang(kerja)
        if nama not in TAB_LAPORAN:
            try:
                self._retry(self._tabs[nama].hide)
            except Exception:
                pass

    def tables(self, segar=True):
        return [t for t in self._sheets(segar=segar) if t not in TAB_LAPORAN]

    # --- dua tab yang terlihat untuk admin (laporan); tab data aplikasi disembunyikan
    def _tab_laporan(self, nama, kolom, baris):
        ws = self._sheets().get(nama)
        if ws is None:
            kosong = self._sheets().get("Sheet1")
            if kosong is not None and not any(t in self._tabs for t in TAB_LAPORAN) and len(self._retry(kosong.get_all_values)) == 0:
                self._retry(lambda: kosong.update_title(nama))
                del self._tabs["Sheet1"]
                self._tabs[nama] = ws = kosong
            else:
                ws = self._retry(lambda: self.sh.add_worksheet(nama, rows=baris, cols=max(len(kolom), 6)))
                self._tabs[nama] = ws
        return ws

    def sembunyikan_data_aplikasi(self):
        """Sembunyikan tab data internal supaya yang tampak hanya dua tab laporan."""
        for t, ws in list(self._sheets().items()):
            if t not in TAB_LAPORAN:
                try:
                    self._retry(ws.hide)
                except Exception:
                    pass

    def write_laporan(self, nama, df, bulan=None):
        df = df.fillna("")

        def kerja():
            ws = self._tab_laporan(nama, list(df.columns), max(len(df) + 50, 200))
            self._retry(ws.clear)
            self._retry(lambda: ws.resize(rows=max(len(df) + 50, 200), cols=max(len(df.columns), 6)))
            self._retry(lambda: ws.update(range_name="A1", values=[list(df.columns)] + df.values.tolist(),
                                          value_input_option="USER_ENTERED"))
            return ws
        ws = self._segarkan_bila_tab_hilang(kerja)
        try:
            self._retry(lambda: ws.freeze(rows=1))
            self._retry(lambda: ws.format("1:1", {"textFormat": {"bold": True}}))
        except Exception:
            pass
        self.sembunyikan_data_aplikasi()

    def tambah_baris(self, nama, kolom, baris):
        self._segarkan_bila_tab_hilang(lambda: self._tambah_baris(nama, kolom, baris))

    def _tambah_baris(self, nama, kolom, baris):
        ws = self._tab_laporan(nama, kolom, 1000)
        a1 = self._retry(lambda: ws.get("A1:A1"))
        if not a1 or str(a1[0][0]).strip() != kolom[0]:  # judul kolom hilang: pasang di baris 1 (data yang ada turun ke bawah)
            self._retry(lambda: ws.insert_row(kolom, 1, value_input_option="USER_ENTERED"))
            try:
                self._retry(lambda: ws.format("1:1", {"textFormat": {"bold": True}}))
            except Exception:
                pass
        self._retry(lambda: ws.append_row(baris, value_input_option="USER_ENTERED"))

    def hapus_baris(self, nama, cocok):
        """Hapus baris tab laporan yang semua kolom di dict `cocok` (judul kolom -> nilai) sama. Return jumlah terhapus."""
        return self._segarkan_bila_tab_hilang(lambda: self._hapus_baris(nama, cocok))

    def _hapus_baris(self, nama, cocok):
        if nama not in [w.title for w in self._retry(lambda: self.sh.worksheets())]:
            return 0
        ws = self.sh.worksheet(nama)
        nilai = self._retry(lambda: ws.get_all_values())
        if not nilai:
            return 0
        kol = {k: nilai[0].index(k) for k in cocok if k in nilai[0]}
        if len(kol) != len(cocok):
            return 0
        hapus = [i + 1 for i, r in enumerate(nilai) if i > 0 and all(
            (r[j] if j < len(r) else "").strip() == str(cocok[k]).strip() for k, j in kol.items())]
        for i in sorted(hapus, reverse=True):
            self._retry(lambda i=i: ws.delete_rows(i))
        return len(hapus)


_POLA_BULAN = re.compile(r"^(?:hasil|jadwal)_(\d{4}-\d{2})$")


class SheetsStore:
    """Google Sheet utama (pengaturan, absensi, lembur, alasan, dll) + satu Google Sheet per bulan di folder Drive
    (tabel hasil_ dan jadwal_ bulan itu serta dua tab laporan bulan itu). Bulan yang sudah ada di Sheet utama tetap
    di sana; bulan baru otomatis dibuatkan Google Sheet sendiri bila drive_folder_id diisi."""
    def __init__(self, creds, sheet_id, folder_id=None):
        import gspread
        self._gs = gspread
        self.klien = gspread.service_account_from_dict(creds)
        self.folder_id = folder_id or None
        self.utama = _Buku(self._retry(lambda: self.klien.open_by_key(sheet_id)))
        self.sh = self.utama.sh
        self._buku = {}          # bulan -> _Buku
        self._reg = None         # bulan -> sheet_id (tembolok daftar buku)
        self.peringatan = []     # pesan masalah (mis. gagal membuat Google Sheet bulan baru)

    _retry = _Buku._retry

    # --- daftar buku bulanan (tabel 'buku_bulan' di Sheet utama)
    def _registri(self, segar=False):
        if self._reg is None or segar:
            df = self.utama.read("buku_bulan")
            self._reg = dict(zip(df["bulan"], df["sheet_id"]))
        return self._reg

    def daftar_buku(self):
        df = self.utama.read("buku_bulan")
        return [dict(bulan=b, sheet_id=i, nama=n) for b, i, n in zip(df["bulan"], df["sheet_id"], df["nama"])]

    def _buka(self, bulan):
        reg = self._registri()
        if bulan not in reg:
            return None
        if bulan not in self._buku:
            self._buku[bulan] = _Buku(self._retry(lambda: self.klien.open_by_key(reg[bulan])))
        return self._buku[bulan]

    def _buat(self, bulan):
        """Buat Google Sheet bulan baru di folder Drive lalu catat di daftar. None bila tidak bisa."""
        if not self.folder_id:
            return None
        judul = f"TOTOQC {bulan}"
        try:
            sh = self._retry(lambda: self.klien.create(judul, folder_id=self.folder_id))
        except Exception as e:
            self.peringatan.append(f"Gagal membuat Google Sheet {judul} di folder Drive: {type(e).__name__}: {e}")
            return None
        reg = self.utama.read("buku_bulan")
        reg = pd.concat([reg, pd.DataFrame([{"bulan": bulan, "sheet_id": sh.id, "nama": judul}])], ignore_index=True)
        self.utama.write("buku_bulan", reg)
        self._reg = None
        self._buku[bulan] = _Buku(sh)
        return self._buku[bulan]

    def _untuk_tulis(self, nama):
        m = _POLA_BULAN.match(nama)
        if not m:
            return self.utama
        bulan = m.group(1)
        b = self._buka(bulan)
        if b:
            return b
        ada = {f"hasil_{bulan}", f"jadwal_{bulan}"} & set(self.utama.tables(segar=False))
        if ada:  # bulan lama yang sudah di Sheet utama tetap di sana
            return self.utama
        return self._buat(bulan) or self.utama

    def _untuk_baca(self, nama):
        m = _POLA_BULAN.match(nama)
        return (self._buka(m.group(1)) if m else None) or self.utama

    def read(self, nama):
        return self._untuk_baca(nama).read(nama)

    def write(self, nama, df):
        self._untuk_tulis(nama).write(nama, df)

    def tables(self):
        hasil = list(self.utama.tables())
        self._registri(segar=True)
        for bulan in self._registri():
            try:
                b = self._buka(bulan)
                hasil += [t for t in b.tables(segar=False) if _POLA_BULAN.match(t)]
            except Exception:
                pass
        return hasil

    # --- laporan (tab terlihat). bulan=None -> Sheet utama
    def _buku_laporan(self, bulan):
        return (self._buka(bulan) if bulan else None) or self.utama

    def bulan_punya_buku(self, bulan):
        return bulan in self._registri()

    def write_laporan(self, nama, df, bulan=None):
        self._buku_laporan(bulan).write_laporan(nama, df)

    def tambah_baris(self, nama, kolom, baris, bulan=None):
        self._buku_laporan(bulan).tambah_baris(nama, kolom, baris)

    def hapus_baris(self, nama, cocok, bulan=None):
        n = 0
        for b in {id(x): x for x in (self._buku_laporan(bulan), self.utama)}.values():
            n += b.hapus_baris(nama, cocok)
        return n


def buat_store(secrets=None):
    secrets = secrets or {}
    if "gcp_service_account" in secrets and "sheet_id" in secrets:
        return SheetsStore(dict(secrets["gcp_service_account"]), secrets["sheet_id"], secrets.get("drive_folder_id"))
    return LocalStore(os.environ.get("QC_DATA_DIR", "data"))
