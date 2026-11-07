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

    def read_bulan(self, nama, bulan):
        d = self.read(nama)
        return d[d["id"].str.contains(f"|{bulan}-", regex=False)].reset_index(drop=True)

    def write_bulan(self, nama, bulan, df):
        d = self.read(nama)
        d = d[~d["id"].str.contains(f"|{bulan}-", regex=False)]
        self.write(nama, pd.concat([d, df], ignore_index=True))

    def pastikan_bulan(self, bulan):
        return True

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
        self._tabs_waktu = 0.0
        self._snap = None  # (waktu, {tab: baris}) hasil satu kali baca banyak tab sekaligus

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
            self._tabs_waktu = time.time()
        return self._tabs

    def punya_tab(self, nama):
        """Ada tab ini di buku? Bila belum tampak, daftar tab dibaca ulang (paling sering tiap 20 detik) karena tab
        bisa dibuat oleh aplikasi lain (admin vs utama)."""
        ada = nama in self._sheets()
        if not ada and time.time() - self._tabs_waktu > 20:
            ada = nama in self._sheets(segar=True)
        return ada

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

    def _snapshot(self):
        """Tab pengaturan kecil dibaca sekaligus dalam SATU permintaan API (bukan satu per tab) lalu dipakai 20 detik.
        Tab bulanan (besar) dan foto tidak ikut. Gagal apa pun -> None, pembaca kembali ke cara lama."""
        if self._snap and time.time() - self._snap[0] < 20:
            return self._snap[1]
        try:
            judul = [t for t in self._sheets(segar=True) if t not in TAB_LAPORAN and t != "foto_alasan" and not _POLA_BULAN.match(t)]
            rng = ["'" + t.replace("'", "''") + "'" for t in judul]
            vr = self._retry(lambda: self.sh.values_batch_get(rng)).get("valueRanges", [])
            hasil = {t: vr[i].get("values", []) for i, t in enumerate(judul)}
            self._snap = (time.time(), hasil)
            return hasil
        except Exception:
            self._snap = None
            return None

    def _lepas_snapshot(self):
        self._snap = None

    def read(self, nama):
        def kerja():
            ws = self._sheets().get(nama)
            if ws is None and self.punya_tab(nama):
                ws = self._sheets().get(nama)
            if ws is None:
                return pd.DataFrame(columns=kolom_tabel(nama))
            snap = None if nama == "foto_alasan" or _POLA_BULAN.match(nama) else self._snapshot()
            if snap is not None and nama in snap:
                v = snap[nama]
                if v:
                    n = len(v[0])
                    return pd.DataFrame([(r + [""] * n)[:n] for r in v[1:]], columns=v[0])
                return pd.DataFrame(columns=kolom_tabel(nama))
            v = self._retry(ws.get_all_values)
            if not v:
                return pd.DataFrame(columns=kolom_tabel(nama))
            return pd.DataFrame(v[1:], columns=v[0])
        return self._segarkan_bila_tab_hilang(kerja)

    def write(self, nama, df):
        self._lepas_snapshot()
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
        self._lepas_snapshot()
        ws = self._tab_laporan(nama, kolom, 1000)
        if ws.col_count < len(kolom):  # kisi terlalu sempit untuk semua kolom
            self._retry(lambda: ws.resize(cols=len(kolom)))
        isi = self._retry(lambda: ws.col_values(1))
        if not isi or str(isi[0]).strip() != kolom[0]:  # judul kolom hilang: pasang di baris 1 (data yang ada turun ke bawah)
            self._retry(lambda: ws.insert_row(kolom, 1, value_input_option="USER_ENTERED"))
            try:
                self._retry(lambda: ws.format("1:1", {"textFormat": {"bold": True}}))
            except Exception:
                pass
            isi = self._retry(lambda: ws.col_values(1))
        tujuan = len(isi) + 1  # baris kosong pertama setelah data
        if ws.row_count < tujuan:
            self._retry(lambda: ws.add_rows(tujuan - ws.row_count + 100))
        self._retry(lambda: ws.update(range_name=f"A{tujuan}", values=[list(baris)], value_input_option="USER_ENTERED"))

    def hapus_baris(self, nama, cocok):
        """Hapus baris tab laporan yang semua kolom di dict `cocok` (judul kolom -> nilai) sama. Return jumlah terhapus."""
        return self._segarkan_bila_tab_hilang(lambda: self._hapus_baris(nama, cocok))

    def _hapus_baris(self, nama, cocok):
        self._lepas_snapshot()
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
# tabel yang tumbuh tiap bulan: disimpan di Google Sheet bulan masing-masing (dipilah menurut kolom tgl)
TABEL_BULANAN = ("lembur", "absensi", "alasan", "pengajuan", "kegiatan", "pindah_hasil", "masalah_abaikan")
JUDUL_BUKU = ("TOTOQC {b}", "QCTOTO {b}")  # nama kedua hanya toleransi salah ketik


class BukuBulananBelumAda(Exception):
    """Upload ditolak: Google Sheet bulan itu belum ada / belum dibagikan / belum dihubungkan."""


def _urut(df):
    return sorted(map(tuple, df.fillna("").astype(str).values.tolist()))


class SheetsStore:
    """Dua jenis Google Sheet. (1) Sheet UTAMA = master kecil: karyawan, target, alias, bagian, roster, daftar bulan.
    (2) Satu Sheet per bulan "TOTOQC YYYY-MM": hasil, jadwal, lembur, absensi, alasan + foto, pengajuan, kegiatan, dll.
    serta dua tab laporan bulan itu. Bulan lama yang belum punya Sheet sendiri tetap dibaca dari Sheet utama."""
    def __init__(self, creds, sheet_id, folder_id=None):
        import gspread
        self._gs = gspread
        self.klien = gspread.service_account_from_dict(creds)
        self.folder_id = folder_id or None
        self.utama = _Buku(self._retry(lambda: self.klien.open_by_key(sheet_id)))
        self.sh = self.utama.sh
        self._buku = {}          # bulan -> _Buku
        self._reg = None         # bulan -> sheet_id (tembolok daftar buku)
        self._dicari = {}        # bulan -> waktu terakhir dicari
        self.peringatan = []     # pesan masalah

    _retry = _Buku._retry

    def _email_akun(self):
        return getattr(getattr(self.klien, "auth", None), "service_account_email", "akun layanan")

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

    def _daftarkan(self, bulan, sh, judul):
        reg = self.utama.read("buku_bulan")
        reg = reg[reg["bulan"] != bulan]
        reg = pd.concat([reg, pd.DataFrame([{"bulan": bulan, "sheet_id": sh.id, "nama": judul}])], ignore_index=True)
        self.utama.write("buku_bulan", reg)
        self._reg = None
        self._buku[bulan] = _Buku(sh)
        return self._buku[bulan]

    def hubungkan_link(self, bulan, tautan):
        """Admin menempel link/ID Google Sheet bulan itu. Return nama file. ValueError bila tidak bisa dibuka."""
        m = re.search(r"/d/([A-Za-z0-9_-]{20,})", tautan or "") or re.fullmatch(r"\s*([A-Za-z0-9_-]{30,})\s*", tautan or "")
        if not m:
            raise ValueError("Link tidak dikenali. Salin alamat lengkap Google Sheet dari browser (https://docs.google.com/spreadsheets/d/...).")
        if m.group(1) == self.sh.id:
            raise ValueError("Itu link Sheet UTAMA (master). Tempel link Sheet khusus bulan ini.")
        try:
            sh = self._retry(lambda: self.klien.open_by_key(m.group(1)))
        except Exception as e:
            raise ValueError(f"File tidak bisa dibuka. Pastikan sudah dibagikan ke {self._email_akun()} sebagai Editor. ({type(e).__name__})")
        self._daftarkan(bulan, sh, sh.title)
        return sh.title

    def _cari(self, bulan):
        """Cari Google Sheet 'TOTOQC <bulan>' yang dibagikan ke akun layanan (dibuat manual oleh admin) lalu daftarkan."""
        if time.time() - self._dicari.get(bulan, 0) < 30:
            return None
        self._dicari[bulan] = time.time()
        try:
            for pola in JUDUL_BUKU:
                judul = pola.format(b=bulan)
                ada = self._retry(lambda: self.klien.list_spreadsheet_files(title=judul, folder_id=self.folder_id))
                ada = [a for a in ada if a.get("name") == judul and a.get("id") != self.sh.id]
                if ada:
                    sh = self._retry(lambda: self.klien.open_by_key(ada[0]["id"]))
                    return self._daftarkan(bulan, sh, judul)
        except Exception as e:
            self.peringatan.append(f"Gagal mencari Google Sheet bulan {bulan}: {type(e).__name__}: {e}")
        return None

    def _buku_bulan(self, bulan):
        """Buku bulan itu (terdaftar, atau ditemukan lewat nama). None bila belum ada."""
        return self._buka(bulan) or self._cari(bulan)

    def pastikan_bulan(self, bulan):
        """Dipanggil sebelum menyimpan data bulan itu. Lolos bila ada buku bulanan, atau bulan lama yang
        masih di Sheet utama. Selain itu upload ditolak."""
        if self._buku_bulan(bulan):
            return True
        if any(f"{p}_{bulan}" in self.utama.tables(segar=False) for p in ("hasil", "jadwal")):
            return True
        raise BukuBulananBelumAda(
            f"Google Sheet bulan {bulan} belum terhubung, jadi upload DIBATALKAN (tidak ada data yang tersimpan). "
            f"Buat Google Sheet kosong bernama TOTOQC {bulan}, bagikan ke {self._email_akun()} sebagai Editor, "
            f"atau tempel linknya di bagian Informasi → Hubungkan Google Sheet bulanan. Lalu ulangi upload.")

    def _untuk_tulis(self, nama):
        m = _POLA_BULAN.match(nama)
        if not m:
            return self.utama
        self.pastikan_bulan(m.group(1))
        return self._buku_bulan(m.group(1)) or self.utama

    def _untuk_baca(self, nama):
        m = _POLA_BULAN.match(nama)
        if not m:
            return self.utama
        b = self._buka(m.group(1))
        if b is not None and b.punya_tab(nama):
            return b
        return self.utama  # bulan lama / belum dipindah: masih di Sheet utama

    # --- tabel bulanan (lembur, absensi, ...): dipilah menurut bulan dari kolom tgl
    def _baca_bulanan(self, nama):
        master = self.utama.read(nama)
        bagian, di_buku = [], set()
        for bulan in sorted(self._registri()):
            try:
                b = self._buka(bulan)
                if b is not None and b.punya_tab(nama):
                    bagian.append(b.read(nama))
                    di_buku.add(bulan)
            except Exception as e:
                self.peringatan.append(f"Gagal membaca {nama} bulan {bulan}: {type(e).__name__}: {e}")
        if di_buku:
            master = master[~master["tgl"].astype(str).str[:7].isin(di_buku)]
        return pd.concat([master] + bagian, ignore_index=True) if bagian else master

    def _tulis_bulanan(self, nama, df):
        kol = kolom_tabel(nama)
        df = df.fillna("").astype(str)
        for c in kol:
            if c not in df.columns:
                df[c] = ""
        df = df[kol]
        bln = df["tgl"].str[:7]
        punya_buku = set()
        for bulan in sorted(self._registri()):
            b = self._buka(bulan)
            if b is None:
                continue
            punya_buku.add(bulan)
            bag = df[bln == bulan].reset_index(drop=True)
            ada = b.punya_tab(nama)
            if not ada and bag.empty:
                continue
            if ada and _urut(b.read(nama)[kol]) == _urut(bag):
                continue
            b.write(nama, bag)  # buku bulan ditulis LEBIH DULU; bila gagal, Sheet utama belum disentuh
        sisa = df[~bln.isin(punya_buku)].reset_index(drop=True)
        if _urut(self.utama.read(nama)[kol]) != _urut(sisa):
            self.utama.write(nama, sisa)

    # --- foto alasan: satu tab per bulan (dipilih dari tanggal di id foto "prn|tgl|no")
    def read_bulan(self, nama, bulan):
        b = self._buka(bulan)
        if b is not None and b.punya_tab(nama):
            return b.read(nama)
        d = self.utama.read(nama)  # data lama di Sheet utama
        return d[d["id"].str.contains(f"|{bulan}-", regex=False)].reset_index(drop=True)

    def write_bulan(self, nama, bulan, df):
        b = self._buka(bulan)
        if b is not None:
            b.write(nama, df)
            return
        d = self.utama.read(nama)
        d = d[~d["id"].str.contains(f"|{bulan}-", regex=False)]
        self.utama.write(nama, pd.concat([d, df], ignore_index=True))

    def read(self, nama):
        if nama in TABEL_BULANAN:
            return self._baca_bulanan(nama)
        return self._untuk_baca(nama).read(nama)

    def write(self, nama, df):
        if nama in TABEL_BULANAN:
            return self._tulis_bulanan(nama, df)
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


    # --- merapikan Sheet utama: periksa / salin / hapus salinan lama bulan yang sudah punya Sheet sendiri
    def _kunci_cek(self, nama):
        return ["tgl"] if nama.startswith("hasil_") else ["prn", "tgl"]

    def audit_bulan(self, bulan):
        """Bandingkan Sheet utama dengan Sheet bulan. Return list dict(tabel, master, buku, status) dengan status:
        'aman' (salinan master boleh dihapus), 'salin' (ada data di master yang belum ada di Sheet bulan), 'kosong' (tidak ada di master)."""
        b = self._buka(bulan)
        if b is None:
            raise ValueError(f"Sheet bulan {bulan} belum terhubung.")
        ada_master = set(self.utama.tables(segar=True))
        hasil = []
        for nama in (f"hasil_{bulan}", f"jadwal_{bulan}"):
            m = self.utama.read(nama) if nama in ada_master else None
            k = b.read(nama) if b.punya_tab(nama) else None
            if m is None:
                hasil.append(dict(tabel=nama, master=0, buku=0 if k is None else len(k), status="kosong"))
                continue
            kc = self._kunci_cek(nama)
            kunci_k = set(map(tuple, k[kc].values.tolist())) if k is not None else set()
            kurang = [t for t in map(tuple, m[kc].values.tolist()) if t not in kunci_k]
            hasil.append(dict(tabel=nama, master=len(m), buku=0 if k is None else len(k), status="salin" if kurang else "aman"))
        for nama in TABEL_BULANAN:
            m = self.utama.read(nama)
            m = m[m["tgl"].astype(str).str[:7] == bulan]
            hasil.append(dict(tabel=nama, master=len(m), buku=0, status="salin" if len(m) else "kosong"))
        f = self.utama.read("foto_alasan") if "foto_alasan" in ada_master else pd.DataFrame(columns=["id", "data"])
        f = f[f["id"].str.contains(f"|{bulan}-", regex=False)]
        kf = b.read("foto_alasan") if b.punya_tab("foto_alasan") else pd.DataFrame(columns=["id", "data"])
        kurang = set(f["id"]) - set(kf["id"])
        hasil.append(dict(tabel="foto_alasan", master=len(f), buku=len(kf),
                          status="kosong" if not len(f) else ("salin" if kurang else "aman")))
        return hasil

    def salin_bulan(self, bulan):
        """Salin (bukan pindah) data bulan itu dari Sheet utama ke Sheet bulan. Tidak ada yang dihapus. Return jumlah tabel disalin."""
        b = self._buka(bulan)
        if b is None:
            raise ValueError(f"Sheet bulan {bulan} belum terhubung.")
        n = 0
        for a in self.audit_bulan(bulan):
            if a["status"] != "salin":
                continue
            nama = a["tabel"]
            if nama in TABEL_BULANAN:
                self._tulis_bulanan(nama, self._baca_bulanan(nama))  # buku ditulis dulu, lalu master dirapikan
            elif nama == "foto_alasan":
                m = self.utama.read(nama)
                m = m[m["id"].str.contains(f"|{bulan}-", regex=False)]
                k = b.read(nama) if b.punya_tab(nama) else pd.DataFrame(columns=["id", "data"])
                b.write(nama, pd.concat([k, m[~m["id"].isin(set(k["id"]))]], ignore_index=True))
            else:
                m = self.utama.read(nama)
                if b.punya_tab(nama):
                    k = b.read(nama)
                    kc = self._kunci_cek(nama)
                    ada = set(map(tuple, k[kc].values.tolist()))
                    baru = m[[tuple(r) not in ada for r in m[kc].values.tolist()]]
                    gab = pd.concat([k, baru], ignore_index=True)
                else:
                    gab = m
                b.write(nama, gab)
            n += 1
        return n

    def hapus_dari_master(self, bulan):
        """Hapus salinan lama di Sheet utama, HANYA untuk tabel yang diperiksa 'aman'. Return daftar tabel yang dihapus."""
        dihapus = []
        for a in self.audit_bulan(bulan):
            if a["status"] != "aman":
                continue
            if a["tabel"] == "foto_alasan":  # hanya baris bulan itu yang dihapus dari master
                f = self.utama.read("foto_alasan")
                self.utama.write("foto_alasan", f[~f["id"].str.contains(f"|{bulan}-", regex=False)])
                dihapus.append("foto_alasan (baris bulan ini)")
                continue
            ws = self.utama._sheets(segar=True).get(a["tabel"])
            if ws is not None:
                self._retry(lambda: self.sh.del_worksheet(ws))
                self.utama._sheets(segar=True)
                self.utama._lepas_snapshot()
                dihapus.append(a["tabel"])
        return dihapus

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
