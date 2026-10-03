"""Penyimpanan data: CSV lokal (uji coba) atau Google Sheet (produksi).
Semua nilai disimpan sebagai teks supaya kode karyawan seperti 0023 tidak berubah."""
import os
import time
import pandas as pd

KOLOM = {
    "karyawan": ["prn", "nama_web", "nama_sap", "user", "pass_hash", "kode_opr"],
    "target": ["grup", "type", "op", "target"],
    "alias": ["nama_sap", "prn"],
    "abaikan": ["nama_sap"],
    "update_log": ["nama_file", "waktu"],
    "lembur": ["prn", "tgl", "jam"],
    "absensi": ["prn", "tgl", "kode", "keterangan", "waktu"],
    "roster": ["prn", "status"],  # status: ya (tampil di monitor) | tidak (disilang admin)
    "target_abaikan": ["grup", "type", "op"],
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

    def write_laporan(self, nama, df):
        df.to_csv(self._path("laporan_" + nama.replace(" ", "_")), index=False)

    def tambah_baris(self, nama, kolom, baris):
        p = self._path("laporan_" + nama.replace(" ", "_"))
        ada = os.path.exists(p)
        pd.DataFrame([baris], columns=kolom).to_csv(p, mode="a", header=not ada, index=False)


class SheetsStore:
    """Google Sheet. Hemat kuota API (batas baca 60 per menit): daftar tab dibaca sekali lalu disimpan,
    dan permintaan yang ditolak karena kuota (429/5xx) diulang otomatis dengan jeda."""
    def __init__(self, creds, sheet_id):
        import gspread
        self._gs = gspread
        self.sh = self._retry(lambda: gspread.service_account_from_dict(creds).open_by_key(sheet_id))
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

    def tables(self):
        return [t for t in self._sheets(segar=True) if t not in TAB_LAPORAN]

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

    def write_laporan(self, nama, df):
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
        if not self._retry(lambda: ws.get("A1:A1")):
            self._retry(lambda: ws.update(range_name="A1", values=[kolom], value_input_option="USER_ENTERED"))
            try:
                self._retry(lambda: ws.format("1:1", {"textFormat": {"bold": True}}))
            except Exception:
                pass
        self._retry(lambda: ws.append_row(baris, value_input_option="USER_ENTERED"))


def buat_store(secrets=None):
    secrets = secrets or {}
    if "gcp_service_account" in secrets and "sheet_id" in secrets:
        return SheetsStore(dict(secrets["gcp_service_account"]), secrets["sheet_id"])
    return LocalStore(os.environ.get("QC_DATA_DIR", "data"))
