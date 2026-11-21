"""Stok label: dua jenis stok yang dijumlahkan.

  1. Stok FOREMAN (stok utama): bertambah dari Input Label Bagus (label dari packing), berkurang saat operator menerima label,
     bertambah lagi bila stok meja dikembalikan ke foreman.
  2. Stok MEJA (satu saldo per meja per label): bertambah saat operator menerima label / stok dipindah masuk,
     berkurang oleh pemakaian (pcs bagus SAP + semua kategori afkir) dan oleh pemindahan keluar.

Label SNI punya stok sendiri (diterima dan dipindah terpisah dari type induknya).
Pemakaian operator dibebankan ke meja tempat dia bekerja pada hari itu (dari penerimaan label atau input label afkir).
Tombol Kosongkan Label Meja mereset semua meja satu pabrik menjadi 0 mulai awal tanggal tombol ditekan.
Hasil hitung dengan ADJUST mengganti saldo lokasi itu (foreman / satu meja) di akhir tanggal hitung."""
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime

import pandas as pd

from core import data, label, laporan

MULAI = os.environ.get("QC_MULAI_STOK", "2026-11-19")  # semua stok 0 mulai tanggal ini (pemakaian sebelum tanggal ini diabaikan)
FOREMAN = "FOREMAN"        # stok Foreman QC (Pabrik 1 dan Pabrik 2)
FOREMAN_SK = "FOREMAN SK"  # stok Foreman SK (pabrik QC SK); data lama tanpa keterangan = QC
DEPT = {"QC": ["Pabrik 1", "Pabrik 2"], "SK": ["QC SK"]}


def dept_pabrik(pabrik):
    return "SK" if pabrik == "QC SK" else "QC"


def foreman_dept(dept):
    return FOREMAN_SK if dept == "SK" else FOREMAN


def adalah_foreman(lk):
    return lk in (FOREMAN, FOREMAN_SK)


def dept_lokasi(lk):
    if lk == FOREMAN_SK:
        return "SK"
    if lk == FOREMAN:
        return "QC"
    return dept_pabrik(lk.split("|", 1)[0])


def dept_cocok(lk, dept):
    return not dept or dept_lokasi(lk) == dept


def lok(pabrik, meja):
    return f"{pabrik}|{meja}"


def lok_nama(lk):
    if lk == FOREMAN_SK:
        return "Foreman SK"
    if not lk or lk == FOREMAN:
        return "Foreman QC"
    p, m = lk.split("|", 1)
    return f"Meja {m} · {p}"


def _lok_pisah(lk):
    p, m = lk.split("|", 1)
    return p, m


def semua_label():
    """Semua label yang punya stok: label biasa + pendamping SNI-nya, berurutan seperti tabel jenis label."""
    t = label.jenis_tabel()
    hasil = []
    for lb in t["label"]:
        if lb and lb not in hasil:
            hasil.append(lb)
            if label.punya_sni(lb):
                hasil.append(label.nama_sni(lb))
    return hasil


def _int(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def _id():
    return datetime.now(data.WIB).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]


def _waktu():
    return datetime.now(data.WIB).strftime("%H:%M:%S")


def hari_ini():
    return datetime.now(data.WIB).strftime("%Y-%m-%d")


_memo = {"t": 0.0, "v": 0, "d": {}}
_versi = [0]


def _bersih():
    _versi[0] += 1
    _memo["d"] = {}


# ---------------------------------------------------------------- riwayat
def catat_riwayat(jenis, kunci, sebelum, sesudah, oleh, tgl=""):
    d = pd.DataFrame([{"waktu": datetime.now(data.WIB).strftime("%Y-%m-%d %H:%M:%S"), "tgl": tgl, "oleh": oleh, "jenis": jenis,
                       "kunci": kunci, "sebelum": sebelum, "sesudah": sesudah}], columns=["waktu", "tgl", "oleh", "jenis", "kunci", "sebelum", "sesudah"])
    data.upsert("label_riwayat", d, ["waktu", "kunci", "jenis"])


def riwayat_daftar(kunci_awal="", batas=30):
    d = data.baca("label_riwayat")
    if d.empty:
        return d
    if kunci_awal:
        d = d[d["kunci"].astype(str).str.startswith(kunci_awal)]
    return d.sort_values("waktu", ascending=False).head(batas).reset_index(drop=True)


# ---------------------------------------------------------------- 1. label diterima foreman (dari packing)
def terima_simpan(tgl, baris, oleh, dept="QC"):
    """baris = [(label, jumlah)]. Satu baris per input. Masuk stok Foreman departemen itu (QC | SK)."""
    waktu = _waktu()
    d = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb, "jumlah": int(n), "oleh": oleh, "dept": dept} for lb, n in baris if lb and _int(n) > 0],
                    columns=["tgl", "waktu", "label", "jumlah", "oleh", "dept"])
    if len(d):
        d["waktu"] = [f"{waktu}.{i}" for i in range(len(d))]
        data.upsert("label_terima", d, ["tgl", "waktu", "label", "dept"])
        data.catat_update("STOK LABEL")
        _bersih()
    return len(d)


def terima_hapus(tgl, waktu, lb, oleh=""):
    h = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb}])
    data.upsert("label_terima", pd.DataFrame(columns=["tgl", "waktu", "label", "jumlah", "oleh", "dept"]), ["tgl", "waktu", "label"], hapus=h)
    catat_riwayat("hapus label bagus", f"{tgl}|{lb}", "", "dihapus", oleh, tgl)
    _bersih()


def terima_daftar(bulan=None, dept=None):
    d = data.baca("label_terima")
    if d.empty:
        return d
    d = d.copy()
    if "dept" not in d.columns:
        d["dept"] = ""
    d["dept"] = d["dept"].replace("", "QC")
    if dept:
        d = d[d["dept"] == dept]
    d["jumlah"] = d["jumlah"].map(_int)
    if bulan:
        d = d[d["tgl"].astype(str).str[:7] == bulan]
    return d.sort_values(["tgl", "waktu"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- 2. label diterima operator (foreman -> meja)
def meja_terima_daftar(prn=None, tgl=None):
    d = data.baca("label_meja")
    if d.empty:
        return d
    d = d.copy()
    d["jumlah"] = d["jumlah"].map(_int)
    if prn:
        d = d[d["prn"] == prn]
    if tgl:
        d = d[d["tgl"] == tgl]
    return d.sort_values(["tgl", "waktu"], ascending=False).reset_index(drop=True)


def meja_terima_simpan(tgl, prn, nama, pabrik, meja, baris, oleh):
    """baris = [(label, jumlah)]. Return pesan galat (str) atau None bila tersimpan."""
    if not pabrik or not meja:
        return "Pabrik dan nomor meja wajib dipilih."
    baris = [(lb, _int(n)) for lb, n in baris if lb and _int(n) > 0]
    if not baris:
        return "Isi minimal satu type label dengan jumlah lebih dari 0."
    if str(tgl) > hari_ini():
        return "Tanggal tidak boleh lebih dari hari ini."
    waktu = _waktu()
    d = pd.DataFrame([{"id": _id(), "tgl": tgl, "waktu": waktu, "prn": prn, "nama": nama, "pabrik": pabrik, "meja": str(meja),
                       "label": lb, "jumlah": n, "oleh": oleh} for lb, n in baris], columns=["id", "tgl", "waktu", "prn", "nama", "pabrik", "meja", "label", "jumlah", "oleh"])
    d["id"] = [f"{x}-{i}" for i, x in enumerate(d["id"])]
    data.upsert("label_meja", d, ["id"])
    data.catat_update("STOK LABEL")
    _bersih()
    return None


def meja_terima_hapus(id_, oleh):
    d = data.baca("label_meja")
    x = d[d["id"] == id_]
    if x.empty:
        return
    r = x.iloc[0]
    data.upsert("label_meja", pd.DataFrame(columns=list(d.columns)), ["id"], hapus=pd.DataFrame([{"id": id_}]))
    catat_riwayat("hapus label diterima", f"{r['tgl']}|{r['prn']}|{r['pabrik']}|{r['meja']}|{r['label']}", f"{_int(r['jumlah'])}", "dihapus", oleh, r["tgl"])
    _bersih()


def meja_terakhir(prn, sampai=None):
    """(pabrik, meja) terakhir operator itu (dari penerimaan label atau input label afkir) sebelum/sampai tanggal."""
    sampai = sampai or hari_ini()
    d = data.baca("label_meja")
    cand = []
    if len(d):
        d = d[(d["prn"] == prn) & (d["tgl"] <= sampai)]
        cand += [(r.tgl, r.waktu, r.pabrik, str(r.meja)) for r in d.itertuples()]
    a = data.baca("label_afkir")
    if len(a):
        a = a[(a["prn"] == prn) & (a["tgl"] <= sampai)]
        cand += [(r.tgl, r.waktu, r.pabrik, str(r.meja)) for r in a.itertuples()]
    if not cand:
        return None, None
    c = sorted(cand)[-1]
    return c[2], c[3]


# ---------------------------------------------------------------- 3. pemindahan stok
def pindah_simpan(tgl, dari_pabrik, dari_meja, ke, baris, oleh, prn=""):
    """ke = FOREMAN (kembali ke Foreman departemen meja asal) atau (pabrik, meja). baris = [(label, jumlah)]. Return galat (str) atau None."""
    if not dari_pabrik or not dari_meja:
        return "Meja asal belum dipilih."
    if ke != FOREMAN and (not ke or not ke[0] or not ke[1]):
        return "Alamat pindah wajib dilengkapi (foreman, atau pabrik dan meja tujuan)."
    if ke != FOREMAN and (ke[0], str(ke[1])) == (dari_pabrik, str(dari_meja)):
        return "Meja tujuan tidak boleh sama dengan meja asal."
    baris = [(lb, _int(n)) for lb, n in baris if lb and _int(n) > 0]
    if not baris:
        return "Isi jumlah yang dipindahkan (lebih dari 0) untuk minimal satu type."
    stok_asal = stok_meja(dari_pabrik, dari_meja, tgl)
    for lb, n in baris:
        if n > stok_asal.get(lb, 0):
            return f"Jumlah {lb} yang dipindahkan ({n}) melebihi stok di meja asal ({stok_asal.get(lb, 0)})."
    kp, km = ("", "") if ke == FOREMAN else (ke[0], str(ke[1]))
    waktu = _waktu()
    d = pd.DataFrame([{"id": f"{_id()}-{i}", "tgl": tgl, "waktu": waktu, "dari_pabrik": dari_pabrik, "dari_meja": str(dari_meja),
                       "ke_pabrik": kp, "ke_meja": km, "label": lb, "jumlah": n, "oleh": oleh, "prn": prn} for i, (lb, n) in enumerate(baris)],
                    columns=["id", "tgl", "waktu", "dari_pabrik", "dari_meja", "ke_pabrik", "ke_meja", "label", "jumlah", "oleh", "prn"])
    data.upsert("label_pindah", d, ["id"])
    data.catat_update("STOK LABEL")
    _bersih()
    return None


def pindah_daftar(prn=None, tgl=None):
    d = data.baca("label_pindah")
    if d.empty:
        return d
    d = d.copy()
    d["jumlah"] = d["jumlah"].map(_int)
    if prn:
        d = d[d["prn"] == prn]
    if tgl:
        d = d[d["tgl"] == tgl]
    return d.sort_values(["tgl", "waktu"], ascending=False).reset_index(drop=True)


def pindah_hapus(id_, oleh):
    d = data.baca("label_pindah")
    x = d[d["id"] == id_]
    if x.empty:
        return
    r = x.iloc[0]
    data.upsert("label_pindah", pd.DataFrame(columns=list(d.columns)), ["id"], hapus=pd.DataFrame([{"id": id_}]))
    catat_riwayat("hapus pemindahan", f"{r['tgl']}|{r['dari_pabrik']}|{r['dari_meja']}|{r['label']}", f"{_int(r['jumlah'])}", "dihapus", oleh, r["tgl"])
    _bersih()


# ---------------------------------------------------------------- 3a. distribusi / pinjam label antar foreman (QC <-> SK)
def distribusi_simpan(tgl, dari, ke, baris, oleh, ket=""):
    """dari, ke = 'QC' | 'SK'. baris = [(label, jumlah)]. Return galat (str) atau None."""
    if dari not in DEPT or ke not in DEPT or dari == ke:
        return "Pilih foreman asal dan foreman tujuan yang berbeda (QC / SK)."
    baris = [(lb, _int(n)) for lb, n in baris if lb and _int(n) > 0]
    if not baris:
        return "Isi minimal satu type label dengan jumlah lebih dari 0."
    if str(tgl) > hari_ini():
        return "Tanggal tidak boleh lebih dari hari ini."
    waktu = _waktu()
    d = pd.DataFrame([{"id": f"{_id()}-{i}", "tgl": tgl, "waktu": waktu, "dari": dari, "ke": ke, "label": lb, "jumlah": n, "oleh": oleh, "ket": ket}
                      for i, (lb, n) in enumerate(baris)], columns=["id", "tgl", "waktu", "dari", "ke", "label", "jumlah", "oleh", "ket"])
    data.upsert("label_distribusi", d, ["id"])
    catat_riwayat("distribusi foreman", f"{tgl}|{dari}>{ke}", "", ", ".join(f"{lb} {n}" for lb, n in baris)[:300], oleh, tgl)
    data.catat_update("STOK LABEL")
    _bersih()
    return None


def distribusi_daftar(batas=40):
    d = data.baca("label_distribusi")
    if d.empty:
        return d
    d = d.copy()
    d["jumlah"] = d["jumlah"].map(_int)
    return d.sort_values(["tgl", "waktu"], ascending=False).head(batas).reset_index(drop=True)


def distribusi_hapus(id_, oleh):
    d = data.baca("label_distribusi")
    x = d[d["id"] == id_]
    if x.empty:
        return
    r = x.iloc[0]
    data.upsert("label_distribusi", pd.DataFrame(columns=list(d.columns)), ["id"], hapus=pd.DataFrame([{"id": id_}]))
    catat_riwayat("hapus distribusi foreman", f"{r['tgl']}|{r['dari']}>{r['ke']}|{r['label']}", f"{_int(r['jumlah'])}", "dihapus", oleh, r["tgl"])
    _bersih()


# ---------------------------------------------------------------- 3b. operator pindah meja
def pindahmeja_simpan(tgl, prn, nama, dari, ke, baris, oleh):
    """dari/ke = (pabrik, meja). baris = [(label, sisa_fisik_di_meja_lama, dibawa_ke_meja_baru)].
    Pemakaian di meja lama = stok sistem (tanpa pcs bagus SAP operator ini hari itu) - sisa fisik. Sisa yang tidak dibawa tinggal di meja lama.
    Return galat (str) atau None."""
    if not dari or not dari[0] or not dari[1]:
        return "Meja saat ini wajib dipilih."
    if not ke or not ke[0] or not ke[1]:
        return "Meja selanjutnya wajib dipilih (pabrik dan nomor meja)."
    if (dari[0], str(dari[1])) == (ke[0], str(ke[1])):
        return "Meja selanjutnya tidak boleh sama dengan meja saat ini."
    if str(tgl) > hari_ini():
        return "Tanggal tidak boleh lebih dari hari ini."
    awal = stok_lokasi(lok(*dari), tgl, abaikan=(prn, tgl))
    waktu = _waktu()
    rows = []
    ring = []
    for i, (lb, sisa, bawa) in enumerate(baris):
        if not lb or sisa is None:
            continue
        sisa, bawa = _int(sisa), _int(bawa)
        if sisa < 0 or bawa < 0:
            return f"Jumlah {lb} tidak boleh minus."
        if bawa > sisa:
            return f"Label {lb} yang dibawa ({bawa}) melebihi sisa di meja ({sisa})."
        s0 = awal.get(lb, 0)
        rows.append({"id": f"{_id()}-{i}", "tgl": tgl, "waktu": waktu, "prn": prn, "nama": nama, "dari_pabrik": dari[0], "dari_meja": str(dari[1]),
                     "ke_pabrik": ke[0], "ke_meja": str(ke[1]), "label": lb, "bagus": max(0, s0 - sisa), "oleh": oleh,
                     "sisa": sisa, "bawa": bawa, "koreksi": max(0, sisa - s0)})
        ring.append(f"{lb} sisa {sisa} bawa {bawa}")
    if not rows:  # tidak ada label yang diisi: tetap catat perpindahannya
        rows.append({"id": f"{_id()}-0", "tgl": tgl, "waktu": waktu, "prn": prn, "nama": nama, "dari_pabrik": dari[0], "dari_meja": str(dari[1]),
                     "ke_pabrik": ke[0], "ke_meja": str(ke[1]), "label": "", "bagus": 0, "oleh": oleh, "sisa": 0, "bawa": 0, "koreksi": 0})
    kol = ["id", "tgl", "waktu", "prn", "nama", "dari_pabrik", "dari_meja", "ke_pabrik", "ke_meja", "label", "bagus", "oleh", "sisa", "bawa", "koreksi"]
    data.upsert("label_pindahmeja", pd.DataFrame(rows, columns=kol), ["id"])
    catat_riwayat("pindah meja", f"{tgl}|{prn}|{dari[0]}|{dari[1]}", lok_nama(lok(*dari)), (lok_nama(lok(*ke)) + " · " + "; ".join(ring))[:300], oleh, tgl)
    data.catat_update("STOK LABEL")
    _bersih()
    return None


def pindahmeja_daftar(prn=None, tgl=None):
    d = data.baca("label_pindahmeja")
    if d.empty:
        return d
    d = d.copy()
    for k in ("bagus", "sisa", "bawa", "koreksi"):
        if k not in d.columns:
            d[k] = 0
        d[k] = d[k].map(_int)
    if prn:
        d = d[d["prn"] == prn]
    if tgl:
        d = d[d["tgl"] == tgl]
    return d.sort_values(["tgl", "waktu"]).reset_index(drop=True)


def pindahmeja_hapus(waktu, tgl, prn, oleh):
    d = data.baca("label_pindahmeja")
    x = d[(d["waktu"] == waktu) & (d["tgl"] == tgl) & (d["prn"] == prn)]
    if x.empty:
        return
    r = x.iloc[0]
    data.upsert("label_pindahmeja", pd.DataFrame(columns=list(d.columns)), ["id"], hapus=x[["id"]])
    catat_riwayat("hapus pindah meja", f"{tgl}|{prn}|{r['dari_pabrik']}|{r['dari_meja']}", "", "dihapus", oleh, tgl)
    _bersih()


def afkir_hari(prn, tgl):
    """{(pabrik, meja, label): jumlah afkir} operator itu pada tanggal (input foreman, semua kategori)."""
    a = data.baca("label_afkir")
    out = defaultdict(int)
    if len(a):
        a = a[(a["prn"] == prn) & ((a["tgl"] == tgl) | (a["tgl_posting"] == tgl))]
        for r in a.itertuples():
            out[(r.pabrik, str(r.meja), r.type)] += sum(_int(getattr(r, j)) for j in laporan.JENIS)
    return dict(out)


# ---------------------------------------------------------------- 4. kosongkan label meja
def kosongkan(tgl, pabrik, oleh):
    if pabrik not in label.PABRIK:
        return "Pilih pabrik."
    d = pd.DataFrame([{"id": _id(), "tgl": tgl, "waktu": _waktu(), "pabrik": pabrik, "oleh": oleh}], columns=["id", "tgl", "waktu", "pabrik", "oleh"])
    data.upsert("label_kosong", d, ["id"])
    catat_riwayat("kosongkan label meja", f"{tgl}|{pabrik}", "", "semua meja jadi 0", oleh, tgl)
    data.catat_update("STOK LABEL")
    _bersih()
    return None


# ---------------------------------------------------------------- 5. hitung aktual (per lokasi)
def hitung_simpan(tgl, baris, oleh, adjust=False, lokasi=FOREMAN):
    """baris = [(label, aktual, sistem)]. adjust=True: aktual jadi saldo baru lokasi itu (akhir hari tgl)."""
    waktu = datetime.now(data.WIB).strftime("%H:%M:%S.%f")
    d = pd.DataFrame([{"tgl": tgl, "waktu": f"{waktu}-{i:02d}", "label": lb, "aktual": int(a), "sistem": int(sx),
                       "adjust": "ya" if adjust else "", "oleh": oleh, "lokasi": lokasi} for i, (lb, a, sx) in enumerate(baris) if lb],
                    columns=["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh", "lokasi"])
    if len(d):
        data.upsert("label_hitung", d, ["tgl", "waktu", "label", "lokasi"])
        data.catat_update("STOK LABEL")
        _bersih()
    return len(d)


def hitung_terakhir(tgl=None, lokasi=FOREMAN):
    """Hasil hitung terbaru per label untuk satu lokasi (yang bertanggal tgl bila diberikan)."""
    kol = ["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh", "lokasi"]
    d = data.baca("label_hitung")
    if d.empty:
        return pd.DataFrame(columns=kol)
    d = d.copy()
    if "lokasi" not in d.columns:
        d["lokasi"] = ""
    d["lokasi"] = d["lokasi"].replace("", FOREMAN)
    d = d[d["lokasi"] == lokasi]
    d["aktual"] = d["aktual"].map(_int)
    d["sistem"] = d["sistem"].map(_int)
    if tgl:
        d = d[d["tgl"] == tgl]
    return d.sort_values(["tgl", "waktu"]).drop_duplicates("label", keep="last").reset_index(drop=True)


# ---------------------------------------------------------------- 5b. stok opname (hitung fisik berkala)
KOSONG = "(kosong)"  # penanda "lokasi ini sudah dihitung dan kosong"


def opname_status(tgl):
    """{lokasi: True bila hasil hitung terakhir lokasi itu sudah di-ADJUST} untuk semua lokasi yang dihitung pada tanggal itu."""
    d = data.baca("label_hitung")
    if d.empty:
        return {}
    d = d[d["tgl"] == tgl].copy()
    if d.empty:
        return {}
    if "lokasi" not in d.columns:
        d["lokasi"] = ""
    d["lokasi"] = d["lokasi"].replace("", FOREMAN)
    out = {}
    for lk, g in d.groupby("lokasi"):
        g = g.sort_values("waktu")
        out[lk] = (g.drop_duplicates("label", keep="last")["adjust"] == "ya").all()
    return out


def opname_baris(tgl, lokasi):
    """{label: (aktual, sistem)} hasil hitung terbaru satu lokasi pada tanggal itu (penanda kosong tidak ikut)."""
    h = hitung_terakhir(tgl, lokasi)
    return {r.label: (r.aktual, r.sistem) for r in h.itertuples() if r.label != KOSONG}


def opname_simpan(tgl, lokasi, aktual, oleh):
    """aktual = {label: jumlah}. Label yang punya stok sistem tetapi tidak diisi dianggap 0. Lokasi kosong tetap tercatat sudah dihitung."""
    sudah = opname_status(tgl).get(lokasi)
    lama = opname_baris(tgl, lokasi)
    sis = stok_lokasi(lokasi, tgl)
    baris = {}
    for lb in set(sis) | set(lama) | set(aktual):
        a = _int(aktual.get(lb, 0))
        sx = lama[lb][1] if (sudah and lb in lama) else sis.get(lb, 0)
        baris[lb] = (a, sx)
    rows = [(lb, a, sx) for lb, (a, sx) in baris.items()]
    if not rows:
        rows = [(KOSONG, 0, 0)]
    return hitung_simpan(tgl, rows, oleh, adjust=False, lokasi=lokasi)


def opname_adjust(tgl, oleh, lokasi_daftar=None):
    """Jadikan hasil hitung (aktual) sebagai stok awal: semua lokasi yang dihitung pada tanggal itu (atau lokasi_daftar). Return jumlah lokasi."""
    status = opname_status(tgl)
    n = 0
    for lk in (lokasi_daftar or list(status)):
        if lk not in status:
            continue
        h = hitung_terakhir(tgl, lk)
        if h.empty:
            continue
        hitung_simpan(tgl, [(r.label, r.aktual, r.sistem) for r in h.itertuples()], oleh, adjust=True, lokasi=lk)
        catat_riwayat("adjust stok opname", f"{tgl}|{lk}", "", ", ".join(f"{r.label}={r.aktual}" for r in h.itertuples() if r.label != KOSONG)[:300], oleh, tgl)
        n += 1
    return n


def opname_tanggal():
    """Tanggal-tanggal opname yang ada (terbaru dulu)."""
    d = data.baca("label_hitung")
    return sorted(set(d["tgl"]), reverse=True) if len(d) else []


# ---------------------------------------------------------------- hitung saldo
def _pemakaian(sampai):
    """Pcs bagus SAP harian: DataFrame[tgl, prn, label, bagus, nama] (mulai MULAI s/d sampai)."""
    out = []
    for b in pd.period_range(MULAI[:7], sampai[:7], freq="M"):
        t = laporan.tabel(str(b))
        if t.empty:
            continue
        t = t[(t["tgl"] >= MULAI) & (t["tgl"] <= sampai)]
        if t.empty:
            continue
        t = t.copy()
        out.append(t[["tgl", "prn", "label", "bagus", "nama"]])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["tgl", "prn", "label", "bagus", "nama"])


def _peta_meja():
    """(prn, tgl) -> lokasi meja tempat operator bekerja hari itu."""
    peta = {}
    a = data.baca("label_afkir")
    if len(a):
        for r in a.sort_values(["tgl", "waktu"]).itertuples():
            peta[(r.prn, r.tgl_posting)] = lok(r.pabrik, str(r.meja))
            peta[(r.prn, r.tgl)] = peta.get((r.prn, r.tgl), lok(r.pabrik, str(r.meja)))
    ev = []  # alamat eksplisit: label diterima di meja, atau operator pindah meja (yang terakhir menang)
    m = data.baca("label_meja")
    if len(m):
        ev += [(r.tgl, r.waktu, r.prn, lok(r.pabrik, str(r.meja))) for r in m.itertuples()]
    p = data.baca("label_pindahmeja")
    if len(p):
        ev += [(r.tgl, r.waktu, r.prn, lok(r.ke_pabrik, str(r.ke_meja))) for r in p.itertuples()]
    for tgl, _w, prn, lokasi in sorted(ev, key=lambda e: (e[0], e[1])):
        peta[(prn, tgl)] = lokasi
    return peta


def saldo(sampai=None, abaikan=None):
    """({(lokasi, label): saldo}, DataFrame pemakaian tanpa meja) sampai akhir hari `sampai`."""
    sampai = sampai or hari_ini()
    if time.time() - _memo["t"] > 20:
        _memo["d"] = {}
        _memo["t"] = time.time()
    if abaikan is None and sampai in _memo["d"]:
        return _memo["d"][sampai]
    ev = []  # (tgl, urutan, jenis, lokasi, label, nilai)
    for r in data.baca("label_terima").itertuples():
        ev.append((r.tgl, 1, "tambah", foreman_dept(getattr(r, "dept", "") or "QC"), r.label, _int(r.jumlah)))
    for r in data.baca("label_distribusi").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", foreman_dept(r.dari), r.label, -n))
        ev.append((r.tgl, 1, "tambah", foreman_dept(r.ke), r.label, n))
    for r in data.baca("label_meja").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", foreman_dept(dept_pabrik(r.pabrik)), r.label, -n))
        ev.append((r.tgl, 1, "tambah", lok(r.pabrik, str(r.meja)), r.label, n))
    for r in data.baca("label_pindah").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", lok(r.dari_pabrik, str(r.dari_meja)), r.label, -n))
        ke = foreman_dept(dept_pabrik(r.dari_pabrik)) if not r.ke_pabrik else lok(r.ke_pabrik, str(r.ke_meja))
        ev.append((r.tgl, 1, "tambah", ke, r.label, n))
    for r in data.baca("label_kosong").itertuples():
        ev.append((r.tgl, 0, "reset", r.pabrik, "", 0))
    h = data.baca("label_hitung")
    if len(h):
        h = h[h["adjust"] == "ya"].copy()
        if "lokasi" not in h.columns:
            h["lokasi"] = ""
        for r in h.sort_values(["tgl", "waktu"]).itertuples():
            ev.append((r.tgl, 3, "set", r.lokasi or FOREMAN, r.label, _int(r.aktual)))
    pem = _pemakaian(sampai)
    peta = _peta_meja()
    # afkir: dibebankan ke meja tempat afkir itu diinput (setiap baris input foreman punya pabrik dan meja sendiri)
    a = data.baca("label_afkir")
    if len(a):
        for r in a.itertuples():
            n = sum(_int(getattr(r, j)) for j in laporan.JENIS)
            tg = r.tgl_posting or r.tgl
            if n and MULAI <= tg <= sampai:
                ev.append((tg, 2, "tambah", lok(r.pabrik, str(r.meja)), r.type, -n))
    # Pindah meja: pemakaian di meja lama (hasil isian sisa fisik), koreksi bila sisa fisik > stok sistem, dan label yang dibawa
    pakai = defaultdict(int)  # (prn, tgl, label) -> pemakaian yang sudah dibebankan ke meja lama
    for r in data.baca("label_pindahmeja").itertuples():
        if not r.label:
            continue
        dari = lok(r.dari_pabrik, str(r.dari_meja))
        ke = lok(r.ke_pabrik, str(r.ke_meja))
        used, bawa, kor = _int(r.bagus), _int(getattr(r, "bawa", 0)), _int(getattr(r, "koreksi", 0))
        if used:
            ev.append((r.tgl, 2, "tambah", dari, r.label, -used))
            pakai[(r.prn, r.tgl, r.label)] += used
        if kor:
            ev.append((r.tgl, 2, "tambah", dari, r.label, kor))
        if bawa:
            ev.append((r.tgl, 2, "tambah", dari, r.label, -bawa))
            ev.append((r.tgl, 2, "tambah", ke, r.label, bawa))
    # pcs bagus SAP: per (operator, hari, label); sisanya (di luar pemakaian meja lama) dibebankan ke meja terakhir operator itu hari itu
    tanpa = []
    for r in pem.itertuples():
        bagus = _int(r.bagus)
        if bagus <= 0 or abaikan == (r.prn, r.tgl):
            continue
        sisa = bagus - pakai.get((r.prn, r.tgl, r.label), 0)
        if sisa > 0:
            lk = peta.get((r.prn, r.tgl))
            if lk is None:
                tanpa.append({"tgl": r.tgl, "prn": r.prn, "nama": r.nama, "label": r.label, "n": int(sisa)})
            else:
                ev.append((r.tgl, 2, "tambah", lk, r.label, -int(sisa)))
    ev = [e for e in ev if e[0] >= MULAI]  # catatan uji sebelum tanggal mulai tidak ikut dihitung
    ev.sort(key=lambda e: (e[0], e[1]))
    sal = defaultdict(int)
    for tgl, _o, jenis, lk, lb, v in ev:
        if tgl > sampai:
            break
        if jenis == "reset":
            for k in [k for k in sal if k[0].startswith(lk + "|")]:
                sal[k] = 0
        elif jenis == "set":
            sal[(lk, lb)] = v
        else:
            sal[(lk, lb)] += v
    hasil = (dict(sal), pd.DataFrame(tanpa, columns=["tgl", "prn", "nama", "label", "n"]))
    if abaikan is None:
        _memo["d"][sampai] = hasil
    return hasil


def stok_lokasi(lokasi, sampai=None, abaikan=None):
    """{label: saldo} satu lokasi (foreman atau meja); hanya label yang saldonya bukan 0. abaikan=(prn, tgl): tanpa pcs bagus SAP operator itu hari itu."""
    sal, _ = saldo(sampai, abaikan)
    return {lb: n for (lk, lb), n in sal.items() if lk == lokasi and n != 0}


def stok_meja(pabrik, meja, sampai=None):
    return stok_lokasi(lok(pabrik, str(meja)), sampai)


def stok_foreman(sampai=None, dept="QC"):
    return stok_lokasi(foreman_dept(dept), sampai)


def urut_label(daftar):
    ur = {lb: i for i, lb in enumerate(semua_label())}
    return sorted(daftar, key=lambda x: (ur.get(x, 9999), x))


def stok_semua(sampai=None, dept=None):
    """DataFrame[label, foreman, meja, total] — total stok per label. dept = QC | SK | None (gabungan)."""
    sal, _ = saldo(sampai)
    fm, mj = defaultdict(int), defaultdict(int)
    for (lk, lb), n in sal.items():
        if not dept_cocok(lk, dept):
            continue
        (fm if adalah_foreman(lk) else mj)[lb] += n
    semua = {lb for lb in set(fm) | set(mj) if fm.get(lb, 0) or mj.get(lb, 0)}
    baris = [{"label": lb, "foreman": fm.get(lb, 0), "meja": mj.get(lb, 0), "total": fm.get(lb, 0) + mj.get(lb, 0)} for lb in urut_label(semua)]
    return pd.DataFrame(baris, columns=["label", "foreman", "meja", "total"])


def stok_per_meja(sampai=None, dept=None):
    """DataFrame[pabrik, meja, label, stok] untuk semua meja yang punya saldo."""
    sal, _ = saldo(sampai)
    baris = []
    for (lk, lb), n in sal.items():
        if adalah_foreman(lk) or n == 0 or not dept_cocok(lk, dept):
            continue
        p, m = _lok_pisah(lk)
        baris.append({"pabrik": p, "meja": int(m) if str(m).isdigit() else m, "label": lb, "stok": n})
    d = pd.DataFrame(baris, columns=["pabrik", "meja", "label", "stok"])
    if d.empty:
        return d
    po = {p: i for i, p in enumerate(label.PABRIK)}
    d["_p"] = d["pabrik"].map(po)
    d["_l"] = d["label"].map({lb: i for i, lb in enumerate(semua_label())}).fillna(9999)
    return d.sort_values(["_p", "meja", "_l"]).drop(columns=["_p", "_l"]).reset_index(drop=True)


def stok_sebaran(sampai=None, dept=None):
    """DataFrame[label, lokasi, nama, stok, dept]: satu baris per (label, lokasi) — untuk 'CW53J ada di mana saja'. Foreman di urutan pertama."""
    sal, _ = saldo(sampai)
    baris = []
    for (lk, lb), n in sal.items():
        if n == 0 or not dept_cocok(lk, dept):
            continue
        baris.append({"label": lb, "lokasi": lk, "nama": lok_nama(lk), "stok": n, "dept": dept_lokasi(lk)})
    d = pd.DataFrame(baris, columns=["label", "lokasi", "nama", "stok", "dept"])
    if d.empty:
        return d
    po = {p: i for i, p in enumerate(label.PABRIK)}

    def _u(lk):
        if adalah_foreman(lk):
            return (0 if lk == FOREMAN else 1, 0, 0)
        p, m = _lok_pisah(lk)
        return (2, po.get(p, 99), int(m) if str(m).isdigit() else 999)
    d["_u"] = d["lokasi"].map(_u)
    d["_l"] = d["label"].map({lb: i for i, lb in enumerate(semua_label())}).fillna(9999)
    return d.sort_values(["_l", "_u"]).drop(columns=["_u", "_l"]).reset_index(drop=True)


def excel_stok(total, per_meja, sampai, sebaran=None):
    """Excel stok: total per label (kolom Total = Foreman + Meja, rumus) dan detail per meja."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    sisi = Side(style="thin", color="B8C7DD")
    gar = Border(left=sisi, right=sisi, top=sisi, bottom=sisi)

    def kepala(ws, baris, judul, lebar):
        for i, t in enumerate(judul, 1):
            c = ws.cell(baris, i, t)
            c.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
            c.fill = PatternFill("solid", fgColor="1A5FC8")
            c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            c.border = gar
            ws.column_dimensions[chr(64 + i)].width = lebar[i - 1]
        ws.row_dimensions[baris].height = 30

    wb = Workbook()
    ws = wb.active
    ws.title = "Stok label"
    ws["A1"] = f"MONITORING STOK LABEL — per {sampai}"
    ws["A1"].font = Font(name="Arial", bold=True, size=13, color="0B3D91")
    ws["A2"] = "Total = stok foreman + stok di meja. Stok meja = diterima operator − pcs bagus SAP − label afkir (semua kategori) ± pemindahan."
    ws["A2"].font = Font(name="Arial", italic=True, size=9, color="5B7399")
    kepala(ws, 4, ["LABEL", "STOK FOREMAN", "STOK DI MEJA", "TOTAL"], [20, 16, 16, 16])
    for r, x in enumerate(total.itertuples(), 5):
        for i, v in enumerate([x.label, x.foreman, x.meja, f"=B{r}+C{r}"], 1):
            c = ws.cell(r, i, v)
            c.font = Font(name="Arial", size=10)
            c.border = gar
            if i > 1:
                c.number_format = "#,##0;[Red]-#,##0"
    ws.freeze_panes = "B5"
    w2 = wb.create_sheet("Per meja")
    kepala(w2, 1, ["PABRIK", "MEJA", "LABEL", "STOK"], [14, 10, 20, 14])
    for r, x in enumerate(per_meja.itertuples(), 2):
        for i, v in enumerate([x.pabrik, x.meja, x.label, x.stok], 1):
            c = w2.cell(r, i, v)
            c.font = Font(name="Arial", size=10)
            c.border = gar
            if i == 4:
                c.number_format = "#,##0;[Red]-#,##0"
    w2.freeze_panes = "A2"
    if sebaran is not None and len(sebaran):
        w3 = wb.create_sheet("Di mana saja")
        kepala(w3, 1, ["LABEL", "LOKASI", "DEPARTEMEN", "STOK"], [20, 26, 14, 14])
        for r, x in enumerate(sebaran.itertuples(), 2):
            for i, v in enumerate([x.label, x.nama, x.dept, x.stok], 1):
                c = w3.cell(r, i, v)
                c.font = Font(name="Arial", size=10)
                c.border = gar
                if i == 4:
                    c.number_format = "#,##0;[Red]-#,##0"
        w3.freeze_panes = "A2"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
