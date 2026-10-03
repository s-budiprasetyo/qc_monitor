"""Penyimpanan data: CSV lokal (uji coba) atau Google Sheet (produksi).
Semua nilai disimpan sebagai teks supaya kode karyawan seperti 0023 tidak berubah."""
import os
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
}
KOLOM_HASIL = ["tgl", "nama_sap", "type", "lokasi", "grup", "op", "periksa"]


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


class SheetsStore:
    def __init__(self, creds, sheet_id):
        import gspread
        self._gs = gspread
        self.sh = gspread.service_account_from_dict(creds).open_by_key(sheet_id)

    def read(self, nama):
        try:
            v = self.sh.worksheet(nama).get_all_values()
        except self._gs.WorksheetNotFound:
            return pd.DataFrame(columns=kolom_tabel(nama))
        if not v:
            return pd.DataFrame(columns=kolom_tabel(nama))
        return pd.DataFrame(v[1:], columns=v[0])

    def write(self, nama, df):
        df = df.fillna("").astype(str)
        baris, kol = max(len(df) + 10, 100), max(len(df.columns), 6)
        try:
            ws = self.sh.worksheet(nama)
        except self._gs.WorksheetNotFound:
            ws = self.sh.add_worksheet(nama, rows=baris, cols=kol)
        ws.clear()
        ws.resize(rows=baris, cols=kol)
        ws.update(range_name="A1", values=[list(df.columns)] + df.values.tolist(),
                  value_input_option="RAW")

    def tables(self):
        return [w.title for w in self.sh.worksheets()]


def buat_store(secrets=None):
    secrets = secrets or {}
    if "gcp_service_account" in secrets and "sheet_id" in secrets:
        return SheetsStore(dict(secrets["gcp_service_account"]), secrets["sheet_id"])
    return LocalStore(os.environ.get("QC_DATA_DIR", "data"))
