"""Monitoring Label (foreman): meja, kategori/type, tanggal posting dari jadwal, simpan/ubah/hapus, notifikasi meja."""
import re
from datetime import date, datetime, timedelta

from pathlib import Path

import pandas as pd

from core import data, logic

PABRIK = {"Pabrik 1": 21, "Pabrik 2": 19, "QC SK": 5}  # jumlah meja per pabrik (total 45)
SHIFT = ["Pagi", "Sore"]  # SAP: Shift B = Pagi, C = Sore
KATEGORI = ["Closet", "Lavatory", "Tangki", "Urinal", "Aksesoris"]
JENIS = [("lengket", "Lengket"), ("garis", "Garis"), ("kotor", "Kotor"), ("proses", "Proses")]
KOLOM = ["tgl", "shift", "tgl_posting", "waktu", "prn", "nama", "pabrik", "meja", "kategori", "type",
         "lengket", "garis", "kotor", "proses", "total", "oleh", "induk", "catatan"]
KUNCI = ["tgl", "shift", "prn", "pabrik", "meja", "type"]
BATAS_KOTOR = 0.5  # persen dari jumlah periksa (dipakai laporan tahap berikutnya)


def hari_ini():
    return datetime.now(data.WIB).date()


def meja_daftar(pabrik):
    return [str(i) for i in range(1, PABRIK[pabrik] + 1)]


def nama_meja(pabrik, meja):
    return f"Meja {meja} · {pabrik}"


def kategori_dari_type(t):
    """Cadangan bila type tidak ada di tabel jenis label: CW/CE = Closet, L/LW = Lavatory, SW/S+angka = Tangki, U = Urinal."""
    t = str(t).strip().upper()
    if t.startswith("SNI"):
        return "SNI"
    if re.match(r"^(CW|CE)", t):
        return "Closet"
    if re.match(r"^L", t):
        return "Lavatory"
    if t.startswith("SW") or re.match(r"^S\d", t):
        return "Tangki"
    if re.match(r"^U", t):
        return "Urinal"
    return "Aksesoris"


SNI = "SNI"
_SEED = Path(__file__).resolve().parent.parent / "assets" / "jenis_label_awal.csv"


_JT = {"t": 0.0, "df": None, "sni": set(), "seed": None}


def jenis_bersih():
    """Buang tembolok tabel jenis label (panggil setelah master jenis label disimpan)."""
    _JT["t"] = 0.0
    _JT["df"] = None


def jenis_tabel():
    """Tabel pemetaan jenis label. Bila belum pernah disimpan di master, dipakai data awal dari assets/.
    Hasil di-tembolok 10 detik (dipanggil ribuan kali oleh perhitungan stok; tanpa tembolok tiap panggilan membaca ulang tabel)."""
    import time as _t
    if _JT["df"] is not None and _t.time() - _JT["t"] < 10:
        return _JT["df"].copy()
    t = data.baca("jenis_label")
    if t.empty and _SEED.exists():
        if _JT["seed"] is None:
            _JT["seed"] = pd.read_csv(_SEED, dtype=str, keep_default_na=False)
        t = _JT["seed"].copy()
    for c in ("kategori", "label", "type_sap", "warna", "sni", "ket"):
        if c not in t.columns:
            t[c] = ""
    t = t.fillna("").astype(str)
    _JT.update(t=_t.time(), df=t, sni=set(t.loc[t["sni"].str.lower() == "ya", "label"]))
    return t.copy()


def _norm(x):
    return re.sub(r"\s+", " ", str(x)).strip().upper()


def label_untuk_sap(tipe, warna, tabel=None):
    """Jenis label untuk satu baris SAP. Return (label, ada_aturan): label '' = type itu memang tanpa label,
    ada_aturan False = type+warna belum terpetakan (masuk notifikasi admin)."""
    t = jenis_tabel() if tabel is None else tabel
    tp, wr = _norm(tipe), _norm(warna)
    cocok = t[t["type_sap"].map(_norm) == tp]
    for w in (wr, ""):
        c = cocok[cocok["warna"].map(_norm) == w]
        if len(c):
            return str(c.iloc[0]["label"]), True
    return "", False


def type_per_kategori():
    """{kategori: [label,...]} untuk pilihan di jendela input (berurutan seperti di tabel, tanpa duplikat, tanpa 'tanpa label')."""
    t = jenis_tabel()
    hasil = {k: [] for k in KATEGORI}
    for r in t.itertuples():
        if r.label and r.kategori in hasil and r.label not in hasil[r.kategori]:
            hasil[r.kategori].append(r.label)
    return hasil


def ket_label(lb):
    t = jenis_tabel()
    c = t[(t["label"] == lb) & (t["ket"] != "")]
    return str(c.iloc[0]["ket"]) if len(c) else ""


def punya_sni(lb):
    import time as _t
    if _JT["df"] is None or _t.time() - _JT["t"] >= 10:
        jenis_tabel()  # menyegarkan himpunan
    return lb in _JT["sni"]


def nama_sni(lb):
    return f"{SNI} {lb}"


def kategori_label(lb):
    if str(lb).startswith(SNI + " "):
        return SNI
    t = jenis_tabel()
    c = t[t["label"] == lb]
    return str(c.iloc[0]["kategori"]) if len(c) else kategori_dari_type(lb)


def kolom_lengkap(daftar):
    """Label terpilih -> kolom matriks: tiap label yang punya SNI diikuti kolom pendamping 'SNI <label>'."""
    hasil = []
    for lb in daftar:
        hasil.append(lb)
        if punya_sni(lb):
            hasil.append(nama_sni(lb))
    return hasil


def operator_daftar():
    """[(prn, nama)] operator yang bisa dipilih: karyawan yang menghasilkan (jenis PERIKSA atau belum diisi) dan tidak disilang.
    Bila tabel 'operator' (Daftar Operator, tahap berikutnya) sudah berisi, itu yang dipakai."""
    k = logic.info_karyawan()
    ro = data.baca("roster")
    silang = set(ro.loc[ro["status"] == "tidak", "prn"])
    daftar = data.baca("operator") if "operator" in _tabel_ada() else pd.DataFrame(columns=["prn"])
    if len(daftar):
        k = k[k["prn"].isin(set(daftar["prn"]))]
    else:
        k = k[k["jenis"].isin(["PERIKSA", ""]) & ~k["prn"].isin(silang)]
    k = k.assign(_n=k["nama_web"].where(k["nama_web"] != "", k["nama_sap"])).sort_values("_n")
    return list(zip(k["prn"], k["_n"]))


def _tabel_ada():
    try:
        from core.store import KOLOM as K
        return K
    except Exception:
        return {}


def tanggal_posting(prn, tgl, shift):
    """Pagi: posting di tanggal kerja. Sore: posting di hari kerja berikutnya menurut jadwal operator itu
    (Jumat sore, Sabtu-Minggu libur, jadi Senin)."""
    d0 = date.fromisoformat(tgl)
    if shift != "Sore":
        return tgl
    jad, cache = {}, {}
    for n in range(1, 8):
        d = d0 + timedelta(days=n)
        bulan = d.strftime("%Y-%m")
        if bulan not in cache:
            cache[bulan] = (logic.jadwal_peta(bulan), logic.hari_libur_default(bulan))
        jm, dflt = cache[bulan]
        if not logic.libur(prn, d.isoformat(), bulan, jm, dflt):
            return d.isoformat()
    return (d0 + timedelta(days=1)).isoformat()


def baca_hari(tgl, shift):
    d = data.baca("label_afkir")
    if "proses" not in d.columns:  # data sebelum baris Proses ada
        d["proses"] = ""
    return d[(d["tgl"] == tgl) & (d["shift"] == shift)].reset_index(drop=True)


def _int(x):
    try:
        return max(0, int(float(x or 0)))
    except (TypeError, ValueError):
        return 0


def simpan(tgl, shift, prn, nama, pabrik, meja, kolom, oleh, ganti_lama=None, catatan=""):
    """kolom = {type: {'lengket':n,'garis':n,'kotor':n}}. Satu baris per type.
    ganti_lama (opsional): (prn, pabrik, meja) kelompok lama yang diganti saat mengubah.
    Return pesan galat (str) bila ditolak, atau None bila tersimpan."""
    if not prn or not meja or not kolom:
        return "Pilih operator, meja, dan minimal satu type."
    pastikan = getattr(data.store(), "pastikan_bulan", None)
    if pastikan:
        pastikan(tgl[:7])  # bisa melempar BukuBulananBelumAda: dibiarkan naik agar ditampilkan admin
    ada = baca_hari(tgl, shift)
    if ganti_lama is None:
        dobel = ada[(ada["prn"] == prn) & (ada["pabrik"] == pabrik) & (ada["meja"] == str(meja)) & (ada["type"].isin(list(kolom)))]
        if len(dobel):
            return (f"Type {', '.join(sorted(set(dobel['type'])))} untuk {nama} di {nama_meja(pabrik, meja)} sudah tersimpan "
                    "pada tanggal dan shift ini. Ubah lewat tabel di bawah (tombol ✎).")
    waktu = datetime.now(data.WIB).strftime("%H:%M")
    posting = tanggal_posting(prn, tgl, shift)
    baris = []
    for t, v in kolom.items():
        l, g, k, pr = (_int(v.get(j)) for j in ("lengket", "garis", "kotor", "proses"))
        baris.append({"tgl": tgl, "shift": shift, "tgl_posting": posting, "waktu": waktu, "prn": prn, "nama": nama,
                      "pabrik": pabrik, "meja": str(meja), "kategori": kategori_label(t), "type": t,
                      "lengket": l, "garis": g, "kotor": k, "proses": pr, "total": l + g + k + pr, "oleh": oleh,
                      "induk": t[len(SNI) + 1:] if t.startswith(SNI + " ") else "", "catatan": (catatan or "").strip()})
    hapus = None
    lama = None
    if ganti_lama is not None:
        lp, lpab, lm = ganti_lama
        lama = ada[(ada["prn"] == lp) & (ada["pabrik"] == lpab) & (ada["meja"] == str(lm))]
        hapus = lama[KUNCI] if len(lama) else None
    try:  # riwayat perubahan (siapa, kapan, dari berapa ke berapa); gagal mencatat tidak boleh menggagalkan simpan
        _catat(tgl, shift, prn, pabrik, meja, baris, lama, oleh)
    except Exception:
        pass
    data.upsert("label_afkir", pd.DataFrame(baris, columns=KOLOM), KUNCI, hapus=hapus)
    data.catat_update("MONITORING LABEL")
    return None


def _ringkas(r):
    return f"Lengket {_int(r['lengket'])} · Garis {_int(r['garis'])} · Kotor {_int(r['kotor'])} · Proses {_int(r['proses'])}"


def _catat(tgl, shift, prn, pabrik, meja, baru, lama, oleh):
    from core import stok
    lama_map = {}
    if lama is not None and len(lama):
        lama_map = {r["type"]: r for _, r in lama.iterrows()}
    else:  # tambah type baru pada nama+meja+tanggal yang sama tidak menimpa; cek baris yang sudah ada
        pass
    for b in baru:
        kunci = f"{tgl}|{shift}|{prn}|{pabrik}|{meja}|{b['type']}"
        if b["type"] in lama_map:
            o = lama_map[b["type"]]
            if _ringkas(o) != _ringkas(b):
                stok.catat_riwayat("ubah label afkir", kunci, _ringkas(o), _ringkas(b), oleh, tgl)
        else:
            stok.catat_riwayat("input label afkir", kunci, "", _ringkas(b), oleh, tgl)
    for t, o in lama_map.items():
        if t not in {b["type"] for b in baru}:
            stok.catat_riwayat("hapus label afkir", f"{tgl}|{shift}|{prn}|{pabrik}|{meja}|{t}", _ringkas(o), "dihapus", oleh, tgl)


def riwayat_kelompok(tgl, shift, prn, pabrik, meja):
    from core import stok
    return stok.riwayat_daftar(f"{tgl}|{shift}|{prn}|{pabrik}|{meja}|", 20)


def hapus_baris(tgl, shift, prn, pabrik, meja, tipe, oleh=""):
    try:
        from core import stok
        ada = baca_hari(tgl, shift)
        x = ada[(ada["prn"] == prn) & (ada["pabrik"] == pabrik) & (ada["meja"] == str(meja)) & (ada["type"] == tipe)]
        if len(x):
            stok.catat_riwayat("hapus label afkir", f"{tgl}|{shift}|{prn}|{pabrik}|{meja}|{tipe}", _ringkas(x.iloc[0]), "dihapus", oleh, tgl)
    except Exception:
        pass
    h = pd.DataFrame([{"tgl": tgl, "shift": shift, "prn": prn, "pabrik": pabrik, "meja": str(meja), "type": tipe}])
    data.upsert("label_afkir", pd.DataFrame(columns=KOLOM), KUNCI, hapus=h)


def abaikan_hari(tgl, shift):
    d = data.baca("meja_abaikan")
    return d[(d["tgl"] == tgl) & (d["shift"] == shift)].reset_index(drop=True)


def meja_belum(tgl, shift):
    """{pabrik: [meja,...]} yang belum dicek (belum ada input label dan tidak diabaikan) pada tanggal+shift itu."""
    ada = baca_hari(tgl, shift)
    sudah = set(zip(ada["pabrik"], ada["meja"]))
    ab = abaikan_hari(tgl, shift)
    sudah |= set(zip(ab["pabrik"], ab["meja"]))
    return {p: [m for m in meja_daftar(p) if (p, m) not in sudah] for p in PABRIK}


def abaikan(tgl, shift, pabrik, meja, oleh):
    waktu = datetime.now(data.WIB).strftime("%H:%M")
    baru = pd.DataFrame([{"tgl": tgl, "shift": shift, "pabrik": pabrik, "meja": str(meja), "oleh": oleh, "waktu": waktu}])
    data.upsert("meja_abaikan", baru, ["tgl", "shift", "pabrik", "meja"])


def batal_abaikan(tgl, shift, pabrik, meja):
    h = pd.DataFrame([{"tgl": tgl, "shift": shift, "pabrik": pabrik, "meja": str(meja)}])
    data.upsert("meja_abaikan", pd.DataFrame(columns=["tgl", "shift", "pabrik", "meja", "oleh", "waktu"]),
                ["tgl", "shift", "pabrik", "meja"], hapus=h)


def operator_default():
    """Daftar bawaan (sebelum Daftar Operator pernah disimpan): [(prn, nama, kode)]."""
    k = logic.info_karyawan()
    ro = data.baca("roster")
    silang = set(ro.loc[ro["status"] == "tidak", "prn"])
    k = k[k["jenis"].isin(["PERIKSA", ""]) & ~k["prn"].isin(silang)]
    k = k.assign(_n=k["nama_web"].where(k["nama_web"] != "", k["nama_sap"])).sort_values("_n")
    return list(zip(k["prn"], k["_n"], k["kode_opr"]))


def operator_tersimpan():
    d = data.baca("operator")
    return list(d["prn"]) if len(d) else None


def operator_simpan(prn_list, oleh):
    """Ganti seluruh Daftar Operator dengan prn_list (urut sesuai daftar)."""
    from core.store import KOLOM
    waktu = datetime.now().strftime("%Y-%m-%d %H:%M")
    k = logic.info_karyawan().set_index("prn")
    baris = [{"prn": p, "kode_opr": str(k["kode_opr"].get(p, "")), "oleh": oleh, "waktu": waktu} for p in prn_list]
    df = pd.DataFrame(baris, columns=KOLOM["operator"])
    data.tulis("operator", df)
