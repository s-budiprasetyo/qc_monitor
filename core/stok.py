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
from datetime import date, datetime, timedelta

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
    """Semua label yang punya stok: label biasa + satu label SNI, berurutan seperti tabel jenis label."""
    t = label.jenis_tabel()
    hasil = []
    for lb in t["label"]:
        if lb and lb not in hasil:
            hasil.append(lb)
    if label.SNI not in hasil and any(label.punya_sni(x) for x in hasil):
        hasil.append(label.SNI)
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


PRN_FOREMAN = "FOREMAN"  # penanda baris label_meja yang diinput/dikoreksi foreman (bukan operator)


def meja_cek(tgl, pabrik, meja):
    """Label diterima satu meja pada satu tanggal, satu baris per type:
    DataFrame[label, jumlah (total semua input + koreksi), oleh (pengisi terakhir), foreman (True bila pengisi terakhir foreman), jam, n]."""
    kol = ["label", "jumlah", "oleh", "foreman", "jam", "n"]
    d = data.baca("label_meja")
    if d.empty:
        return pd.DataFrame(columns=kol)
    d = d[(d["tgl"] == tgl) & (d["pabrik"] == pabrik) & (d["meja"].astype(str) == str(meja))].copy()
    if d.empty:
        return pd.DataFrame(columns=kol)
    d["jumlah"] = d["jumlah"].map(_int)
    d = d.sort_values("waktu")
    baris = []
    for lb, g in d.groupby("label", sort=False):
        t = g.iloc[-1]
        baris.append({"label": lb, "jumlah": int(g["jumlah"].sum()), "oleh": (t["nama"] or t["oleh"] or "").strip(),
                      "foreman": str(t["prn"]) == PRN_FOREMAN, "jam": str(t["waktu"])[:5], "n": len(g)})
    out = pd.DataFrame(baris, columns=kol)
    return out.set_index("label").loc[urut_label(set(out["label"]))].reset_index()


def meja_cek_simpan(tgl, pabrik, meja, target, oleh):
    """target = {label: jumlah akhir}. Selisih terhadap total tercatat disimpan sebagai baris koreksi foreman (jumlah bisa minus);
    input asli operator tidak dihapus. Return (jumlah type berubah, pesan galat atau None)."""
    if not pabrik or not meja:
        return 0, "Pabrik dan nomor meja wajib dipilih."
    if str(tgl) > hari_ini():
        return 0, "Tanggal tidak boleh lebih dari hari ini."
    if any(_int(v) < 0 for v in target.values()):
        return 0, "Jumlah tidak boleh di bawah 0."
    cur = meja_cek(tgl, pabrik, meja)
    ada = dict(zip(cur["label"], cur["jumlah"]))
    waktu = _waktu()
    baris, riwayat = [], []
    for lb, v in target.items():
        delta = _int(v) - ada.get(lb, 0)
        if not delta:
            continue
        baris.append({"id": f"{_id()}-{len(baris)}", "tgl": tgl, "waktu": waktu, "prn": PRN_FOREMAN, "nama": oleh, "pabrik": pabrik,
                      "meja": str(meja), "label": lb, "jumlah": delta, "oleh": oleh})
        riwayat.append({"waktu": datetime.now(data.WIB).strftime("%Y-%m-%d %H:%M:%S"), "tgl": tgl, "oleh": oleh, "jenis": "koreksi label meja",
                        "kunci": f"{tgl}|{pabrik}|{meja}|{lb}", "sebelum": str(ada.get(lb, 0)), "sesudah": str(_int(v))})
    if not baris:
        return 0, None
    data.upsert("label_meja", pd.DataFrame(baris, columns=["id", "tgl", "waktu", "prn", "nama", "pabrik", "meja", "label", "jumlah", "oleh"]), ["id"])
    data.upsert("label_riwayat", pd.DataFrame(riwayat, columns=["waktu", "tgl", "oleh", "jenis", "kunci", "sebelum", "sesudah"]), ["waktu", "kunci", "jenis"])
    data.catat_update("STOK LABEL")
    _bersih()
    return len(baris), None


def meja_terima_hapus(id_, oleh):
    d = data.baca("label_meja")
    x = d[d["id"] == id_]
    if x.empty:
        return
    r = x.iloc[0]
    data.upsert("label_meja", pd.DataFrame(columns=list(d.columns)), ["id"], hapus=pd.DataFrame([{"id": id_}]))
    catat_riwayat("hapus label diterima", f"{r['tgl']}|{r['prn']}|{r['pabrik']}|{r['meja']}|{r['label']}", f"{_int(r['jumlah'])}", "dihapus", oleh, r["tgl"])
    _bersih()


def meja_terima_koreksi(id_, label_baru, jumlah, pabrik, meja, prn, nama, oleh):
    """Perbaiki satu entri 'label diterima' di meja (karyawan salah ketik type/jumlah/meja/nama). Return galat (str) atau None."""
    d = data.baca("label_meja")
    x = d[d["id"] == id_]
    if x.empty:
        return "Entri tidak ditemukan."
    if not label_baru or not pabrik or not meja:
        return "Type, pabrik, dan meja wajib diisi."
    if _int(jumlah) == 0:
        return "Jumlah tidak boleh 0 (gunakan Hapus bila entri memang salah)."
    r = x.iloc[0].to_dict()
    sebelum = f"{r['label']} {_int(r['jumlah'])} @ {r['pabrik']}|{r['meja']} ({r.get('nama', '')})"
    r.update({"label": label_baru, "jumlah": str(_int(jumlah)), "pabrik": pabrik, "meja": str(meja), "prn": prn, "nama": nama})
    data.upsert("label_meja", pd.DataFrame([r], columns=list(d.columns)), ["id"])
    sesudah = f"{label_baru} {_int(jumlah)} @ {pabrik}|{meja} ({nama})"
    catat_riwayat("koreksi label diterima", f"{r['tgl']}|{id_}", sebelum, sesudah, oleh, r["tgl"])
    data.catat_update("STOK LABEL")
    _bersih()
    return None


def _ringkas_saldo(tgl=None):
    s, _ = saldo(tgl)
    return {k: v for k, v in s.items() if v}


def selisih_saldo(sebelum, sesudah):
    """Daftar [(lokasi, label, sebelum, sesudah)] yang saldonya berubah."""
    out = []
    for k in sorted(set(sebelum) | set(sesudah)):
        a, b = sebelum.get(k, 0), sesudah.get(k, 0)
        if a != b:
            out.append((k[0], k[1], a, b))
    return out


def timpa_opname(tgl, lokasi_daftar, label_daftar):
    """Hasil ADJUST opname bertanggal >= tgl yang menimpa saldo (lokasi, label) tertentu -> koreksi sebelum tanggal itu tidak mengubah stok sesudahnya.
    Return [(tgl_opname, lokasi, label, aktual)]."""
    h = data.baca("label_hitung")
    if h.empty:
        return []
    if "lokasi" not in h.columns:
        h["lokasi"] = ""
    h["lokasi"] = h["lokasi"].replace("", FOREMAN)
    h = h[(h["adjust"] == "ya") & (h["tgl"] >= tgl) & h["lokasi"].isin(list(lokasi_daftar)) & h["label"].isin(list(label_daftar))]
    h = h.sort_values(["tgl", "waktu"]).drop_duplicates(["tgl", "lokasi", "label"], keep="last")
    return [(r.tgl, r.lokasi, r.label, _int(r.aktual)) for r in h.itertuples()]


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
        a = a[(a["prn"] == prn) & (a["tgl"] == tgl)]
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


def opname_info(tgl, lokasi):
    """(oleh, jam 'HH:MM', sudah_adjust) hitungan tersimpan satu lokasi pada tanggal itu; None bila belum pernah."""
    d = data.baca("label_hitung")
    if d.empty:
        return None
    d = d.copy()
    if "lokasi" not in d.columns:
        d["lokasi"] = ""
    d["lokasi"] = d["lokasi"].replace("", FOREMAN)
    d = d[(d["tgl"] == tgl) & (d["lokasi"] == lokasi)]
    if d.empty:
        return None
    d = d.sort_values("waktu")
    t = d.iloc[-1]
    return str(t.get("oleh", "")), str(t["waktu"])[:5], bool((d.drop_duplicates("label", keep="last")["adjust"] == "ya").all())


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
    """Jadikan hasil hitung (aktual) sebagai stok awal: semua lokasi yang dihitung pada tanggal itu (atau lokasi_daftar). Return jumlah lokasi.
    Semua lokasi ditulis SEKALIGUS (satu kali tulis per tabel) supaya cepat walau puluhan meja."""
    status = opname_status(tgl)
    pilih = [lk for lk in (lokasi_daftar or list(status)) if lk in status]
    if not pilih:
        return 0
    d = data.baca("label_hitung").copy()
    if "lokasi" not in d.columns:
        d["lokasi"] = ""
    d["lokasi"] = d["lokasi"].replace("", FOREMAN)
    d = d[(d["tgl"] == tgl) & (d["lokasi"].isin(pilih))].sort_values(["tgl", "waktu"]).drop_duplicates(["lokasi", "label"], keep="last")
    if d.empty:
        return 0
    now = datetime.now(data.WIB)
    waktu = now.strftime("%H:%M:%S.%f")
    baris, riwayat, n = [], [], 0
    for lk in pilih:
        g = d[d["lokasi"] == lk]
        if g.empty:
            continue
        n += 1
        for r in g.itertuples():
            baris.append({"tgl": tgl, "waktu": f"{waktu}-{len(baris):04d}", "label": r.label, "aktual": _int(r.aktual), "sistem": _int(r.sistem),
                          "adjust": "ya", "oleh": oleh, "lokasi": lk})
        riwayat.append({"waktu": now.strftime("%Y-%m-%d %H:%M:%S"), "tgl": tgl, "oleh": oleh, "jenis": "adjust stok opname", "kunci": f"{tgl}|{lk}",
                        "sebelum": "", "sesudah": ", ".join(f"{r.label}={_int(r.aktual)}" for r in g.itertuples() if r.label != KOSONG)[:300]})
    data.upsert("label_hitung", pd.DataFrame(baris, columns=["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh", "lokasi"]),
                ["tgl", "waktu", "label", "lokasi"])
    data.upsert("label_riwayat", pd.DataFrame(riwayat, columns=["waktu", "tgl", "oleh", "jenis", "kunci", "sebelum", "sesudah"]),
                ["waktu", "kunci", "jenis"])
    data.catat_update("STOK LABEL")
    _bersih()
    return n


def opname_koreksi(tgl, lokasi, perubahan, oleh):
    """Ubah jumlah hitung aktual type tertentu pada opname tanggal tgl di satu lokasi. perubahan = {label: aktual_baru}.
    Semua baris hitung (sebelum maupun sesudah ADJUST) untuk type itu diubah; type yang belum ada ditambahkan. Return galat (str) atau None."""
    perubahan = {lb: _int(a) for lb, a in perubahan.items() if lb}
    if not perubahan:
        return "Tidak ada perubahan."
    if any(a < 0 for a in perubahan.values()):
        return "Jumlah aktual tidak boleh negatif."
    d = data.baca("label_hitung")
    if "lokasi" not in d.columns:
        d["lokasi"] = ""
    lk = d["lokasi"].replace("", FOREMAN)
    sudah = opname_status(tgl).get(lokasi)
    if sudah is None:
        return "Opname lokasi itu pada tanggal tersebut tidak ditemukan."
    ubah, baru, sebelum, sesudah = [], [], [], []
    waktu = datetime.now(data.WIB).strftime("%H:%M:%S.%f")
    for i, (lb, a) in enumerate(sorted(perubahan.items())):
        m = (d["tgl"] == tgl) & (lk == lokasi) & (d["label"] == lb)
        if m.any():
            lama = _int(d[m].sort_values("waktu").iloc[-1]["aktual"])
            if lama == a:
                continue
            x = d[m].copy()
            x["aktual"] = str(a)
            ubah.append(x)
            sebelum.append(f"{lb}={lama}")
        else:
            sx = stok_lokasi(lokasi, tgl).get(lb, 0)
            baru.append({"tgl": tgl, "waktu": f"{waktu}-{i:02d}", "label": lb, "aktual": str(a), "sistem": str(sx),
                         "adjust": "ya" if sudah else "", "oleh": oleh, "lokasi": lokasi})
            sebelum.append(f"{lb}=(belum ada)")
        sesudah.append(f"{lb}={a}")
    if not sesudah:
        return "Tidak ada jumlah yang berubah."
    kol = list(d.columns)
    bagian = ubah + ([pd.DataFrame(baru, columns=kol)] if baru else [])
    data.upsert("label_hitung", pd.concat(bagian, ignore_index=True)[kol], ["tgl", "waktu", "label", "lokasi"])
    catat_riwayat("koreksi stok opname", f"{tgl}|{lokasi}", ", ".join(sebelum)[:300], ", ".join(sesudah)[:300], oleh, tgl)
    data.catat_update("STOK LABEL")
    _bersih()
    return None


# ---------------------------------------------------------------- notifikasi stok minus (butuh persetujuan foreman)
def _id_notif(tgl, lk, lb, prn=""):
    return f"{tgl}|{lk}|{lb}"


def notif_stok(sampai=None):
    """Meja QC yang saldo type labelnya MINUS di akhir hari karena pemakaian (pcs bagus SAP + afkir) hari itu, setelah ADJUST opname hari itu.
    'ambil_meja'  = ada meja QC lain yang masih punya type itu (diambil dari meja lain tanpa Pindah Label);
    'dari_foreman'= tidak ada meja yang punya stok (diambil dari Foreman tanpa tercatat).
    Return daftar dict(id, tgl, jenis, lokasi, label, prn, nama, kurang, sumber[(lokasi, stok)], foreman). Yang sudah diputuskan foreman tidak ikut."""
    sampai = sampai or hari_ini()
    ev, _t = _ledger_c(sampai)
    sudah = data.baca("label_notif")
    putus = set(sudah["id"]) if len(sudah) else set()
    sal, out, pakai = defaultdict(int), [], {}
    i, n = 0, len(ev)
    while i < n and ev[i][0] <= sampai:
        tgl = ev[i][0]
        pakai = defaultdict(lambda: [0, {}])  # (lokasi, label) -> [pemakaian hari itu, {(prn, nama): pcs SAP}]
        while i < n and ev[i][0] == tgl:
            _t0, o, jenis, lk, lb, v, *k = ev[i]
            i += 1
            if o == 4:  # sapu SK: bukan urusan notifikasi QC
                _terap(sal, jenis, lk, lb, v)
                continue
            if jenis == "tambah" and k and v < 0 and k[0][0] in ("SAP", "AFKIR", "PM_PAKAI") and not adalah_foreman(lk) and dept_lokasi(lk) == "QC":
                pk = pakai[(lk, lb)]
                pk[0] += -v
                if k[0][0] == "SAP":
                    kk = (k[0][3] if len(k[0]) > 3 else "", k[0][1])
                    pk[1][kk] = pk[1].get(kk, 0) + -v
            _terap(sal, jenis, lk, lb, v)
        for (lk, lb), (tot, siapa) in pakai.items():
            bal = sal.get((lk, lb), 0)
            kurang = min(-bal, tot) if bal < 0 else 0
            nid = _id_notif(tgl, lk, lb)
            if kurang <= 0 or nid in putus:
                continue
            prn, nama = max(siapa, key=siapa.get) if siapa else ("", "")
            sumber = sorted(((l2, s_) for (l2, b2), s_ in sal.items() if b2 == lb and s_ > 0 and l2 != lk and not adalah_foreman(l2) and dept_lokasi(l2) == "QC"),
                            key=lambda x: -x[1])
            out.append({"id": nid, "tgl": tgl, "jenis": "ambil_meja" if sumber else "dari_foreman", "lokasi": lk, "label": lb, "prn": prn,
                        "nama": nama, "kurang": int(kurang), "sumber": sumber, "foreman": int(sal.get((FOREMAN, lb), 0))})
    return out


def notif_putuskan(nid, status, oleh):
    """Catat keputusan foreman (abaikan) supaya notifikasi itu tidak muncul lagi."""
    tgl = nid.split("|", 1)[0]
    d = pd.DataFrame([{"id": nid, "tgl": tgl, "oleh": oleh, "waktu": datetime.now(data.WIB).strftime("%Y-%m-%d %H:%M:%S"), "status": status}],
                     columns=["id", "tgl", "oleh", "waktu", "status"])
    data.upsert("label_notif", d, ["id"])
    data.catat_update("STOK LABEL")
    _bersih()


def notif_setujui(n, jumlah, asal, oleh):
    """Setujui notifikasi n (dict dari notif_stok). ambil_meja: catat pemindahan meja asal -> meja ini sejumlah `jumlah` (sisa tetap di meja ini).
    dari_foreman: catat label diterima meja ini dari Foreman sejumlah `jumlah`. Return galat (str) atau None."""
    jumlah = _int(jumlah)
    if jumlah <= 0:
        return "Jumlah harus lebih dari 0."
    pabrik, meja = n["lokasi"].split("|", 1)
    if n["jenis"] == "ambil_meja":
        if not asal or "|" not in asal:
            return "Pilih meja asal label."
        ap, am = asal.split("|", 1)
        g = pindah_simpan(n["tgl"], ap, am, (pabrik, meja), [(n["label"], jumlah)], oleh, n["prn"])
    else:
        g = meja_terima_simpan(n["tgl"], n["prn"] or PRN_FOREMAN, n["nama"], pabrik, meja, [(n["label"], jumlah)], oleh)
    if g:
        return g
    catat_riwayat("setujui notifikasi stok", n["id"], "", f"{n['jenis']} {n['label']} {jumlah}" + (f" dari {asal}" if asal else ""), oleh, n["tgl"])
    return None


def adjust_terakhir(dept=None):
    """Adjust stok opname terakhir untuk dept (QC | SK | None): {'tgl': tanggal hitung, 'waktu': kapan diproses, 'oleh', 'lokasi': [..]} atau None."""
    r = data.baca("label_riwayat")
    if r.empty:
        return None
    r = r[r["jenis"] == "adjust stok opname"].copy()
    if r.empty:
        return None
    r["lk"] = r["kunci"].astype(str).str.split("|", n=1).str[1].fillna("")
    r = r[[dept_cocok(lk, dept) for lk in r["lk"]]]
    if r.empty:
        return None
    t = r.sort_values(["tgl", "waktu"]).iloc[-1]["tgl"]
    r = r[r["tgl"] == t]
    w = r["waktu"].max()
    x = r[r["waktu"].str[:16] == w[:16]]
    return {"tgl": t, "waktu": w, "oleh": x.iloc[0]["oleh"], "lokasi": list(x["lk"])}


def adjust_cek(dept):
    """Cek apakah hasil ADJUST terakhir sudah jadi stok sistem. -> (info, DataFrame[label, aktual, sistem, ok], belum_adjust[lokasi]) atau (None, None, [])."""
    info = adjust_terakhir(dept)
    if not info:
        return None, None, []
    tgl = info["tgl"]
    sal, _ = saldo(tgl)
    akt = defaultdict(int)
    sis = defaultdict(int)
    for lk in info["lokasi"]:
        for lb, (a, _sx) in opname_baris(tgl, lk).items():
            akt[lb] += a
        for (l2, lb), nn in sal.items():
            if l2 == lk:
                sis[lb] += nn
    baris = [{"label": lb, "aktual": akt.get(lb, 0), "sistem": sis.get(lb, 0), "ok": akt.get(lb, 0) == sis.get(lb, 0)}
             for lb in urut_label(set(akt) | {k for k, v in sis.items() if v})]
    belum = [lk for lk, sdh in opname_status(tgl).items() if dept_cocok(lk, dept) and not sdh]
    return info, pd.DataFrame(baris, columns=["label", "aktual", "sistem", "ok"]), belum


def opname_tanggal():
    """Tanggal-tanggal opname yang ada (terbaru dulu)."""
    d = data.baca("label_hitung")
    return sorted(set(d["tgl"]), reverse=True) if len(d) else []


# ---------------------------------------------------------------- hitung saldo
def _pemakaian(sampai):
    """Pcs bagus SAP harian: DataFrame[tgl, prn, label, bagus, nama] (mulai MULAI s/d sampai)."""
    out = []
    for b in pd.period_range(MULAI[:7], sampai[:7], freq="M"):
        t = laporan.tabel(str(b), op100=True)
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
            peta[(r.prn, r.tgl)] = lok(r.pabrik, str(r.meja))
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


def _ledger(sampai, abaikan=None):
    """Daftar kejadian stok terurut (tgl, urutan, jenis, lokasi, label, nilai) dan pemakaian SAP yang belum terpetakan ke meja."""
    data.muat(["label_terima", "label_distribusi", "label_meja", "label_pindah", "label_kosong", "label_hitung", "label_afkir", "label_pindahmeja",
               "karyawan", "alias"] + [f"hasil_{b}" for b in pd.period_range(MULAI[:7], sampai[:7], freq="M")])
    ev = []  # (tgl, urutan, jenis, lokasi, label, nilai)
    for r in data.baca("label_terima").itertuples():
        ev.append((r.tgl, 1, "tambah", foreman_dept(getattr(r, "dept", "") or "QC"), r.label, _int(r.jumlah), ("TERIMA", r.oleh, "label diterima dari packing")))
    for r in data.baca("label_distribusi").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", foreman_dept(r.dari), r.label, -n, ("DISTR_KELUAR", r.oleh, f"distribusi ke {r.ke}")))
        ev.append((r.tgl, 1, "tambah", foreman_dept(r.ke), r.label, n, ("DISTR_MASUK", r.oleh, f"distribusi dari {r.dari}")))
    for r in data.baca("label_meja").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", foreman_dept(dept_pabrik(r.pabrik)), r.label, -n, ("KIRIM_MEJA", r.oleh, f"keluar ke {lok_nama(lok(r.pabrik, str(r.meja)))} ({r.nama})")))
        ev.append((r.tgl, 1, "tambah", lok(r.pabrik, str(r.meja)), r.label, n, ("TERIMA_MEJA", r.nama or r.oleh, "label diterima di meja")))
    for r in data.baca("label_pindah").itertuples():
        n = _int(r.jumlah)
        ke = foreman_dept(dept_pabrik(r.dari_pabrik)) if not r.ke_pabrik else lok(r.ke_pabrik, str(r.ke_meja))
        ev.append((r.tgl, 1, "tambah", lok(r.dari_pabrik, str(r.dari_meja)), r.label, -n, ("PINDAH_KELUAR", r.oleh, f"dipindah ke {lok_nama(ke)}")))
        ev.append((r.tgl, 1, "tambah", ke, r.label, n, ("PINDAH_MASUK", r.oleh, f"dipindah dari {lok_nama(lok(r.dari_pabrik, str(r.dari_meja)))}")))
    for r in data.baca("label_kosong").itertuples():
        ev.append((r.tgl, 0, "reset", r.pabrik, "", 0, ("RESET", getattr(r, "oleh", ""), "meja dikosongkan")))
    h = data.baca("label_hitung")
    if len(h):
        h = h[h["adjust"] == "ya"].copy()
        if "lokasi" not in h.columns:
            h["lokasi"] = ""
        for r in h.sort_values(["tgl", "waktu"]).itertuples():
            ev.append((r.tgl, 3, "set", r.lokasi or FOREMAN, r.label, _int(r.aktual), ("SET", r.oleh, "hasil hitung aktual (ADJUST)")))
    pem = _pemakaian(sampai)
    peta = _peta_meja()
    # afkir: dibebankan ke meja tempat afkir itu diinput (setiap baris input foreman punya pabrik dan meja sendiri)
    a = data.baca("label_afkir")
    if len(a):
        for r in a.itertuples():
            n = sum(_int(getattr(r, j)) for j in laporan.JENIS)
            tg = r.tgl
            if n and MULAI <= tg <= sampai:
                ev.append((tg, 2, "tambah", lok(r.pabrik, str(r.meja)), r.type, -n, ("AFKIR", r.nama, f"label afkir (input {r.oleh})")))
    # Pindah meja: pemakaian di meja lama (hasil isian sisa fisik), koreksi bila sisa fisik > stok sistem, dan label yang dibawa
    pakai = defaultdict(int)  # (prn, tgl, label) -> pemakaian yang sudah dibebankan ke meja lama
    for r in data.baca("label_pindahmeja").itertuples():
        if not r.label:
            continue
        dari = lok(r.dari_pabrik, str(r.dari_meja))
        ke = lok(r.ke_pabrik, str(r.ke_meja))
        used, bawa, kor = _int(r.bagus), _int(getattr(r, "bawa", 0)), _int(getattr(r, "koreksi", 0))
        if used:
            ev.append((r.tgl, 2, "tambah", dari, r.label, -used, ("PM_PAKAI", r.nama, "pcs bagus di meja lama (pindah meja)")))
            pakai[(r.prn, r.tgl, r.label)] += used
        if kor:
            ev.append((r.tgl, 2, "tambah", dari, r.label, kor, ("PM_KOREKSI", r.nama, "koreksi sisa fisik saat pindah meja")))
        if bawa:
            ev.append((r.tgl, 2, "tambah", dari, r.label, -bawa, ("PM_KELUAR", r.nama, f"dibawa ke {lok_nama(ke)}")))
            ev.append((r.tgl, 2, "tambah", ke, r.label, bawa, ("PM_MASUK", r.nama, f"dibawa dari {lok_nama(dari)}")))
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
                ev.append((r.tgl, 2, "tambah", lk, r.label, -int(sisa), ("SAP", r.nama, "pcs bagus SAP", r.prn)))
    ev = [e for e in ev if e[0] >= MULAI]  # catatan uji sebelum tanggal mulai tidak ikut dihitung
    ev.sort(key=lambda e: (e[0], e[1]))
    ev = _sapu_sk(ev)
    return ev, pd.DataFrame(tanpa, columns=["tgl", "prn", "nama", "label", "n"])


def _sapu_sk(ev):
    """SK tidak punya stok sisa di meja: selesai kerja, sisa label (atau kekurangannya) tiap meja SK otomatis kembali ke Foreman SK.
    Disisipkan sebagai kejadian di akhir tiap hari yang ada kejadiannya (urutan 4). QC tidak disentuh."""
    sal, out, i, n = defaultdict(int), list(ev), 0, len(ev)
    while i < n:
        tgl = ev[i][0]
        while i < n and ev[i][0] == tgl:
            e = ev[i]
            _terap(sal, e[2], e[3], e[4], e[5])
            i += 1
        for (lk, lb), v in sorted(sal.items()):
            if v and not adalah_foreman(lk) and dept_lokasi(lk) == "SK":
                out.append((tgl, 4, "tambah", lk, lb, -v, ("SAPU_KELUAR", "sistem", "sisa meja SK kembali ke Foreman SK")))
                out.append((tgl, 4, "tambah", FOREMAN_SK, lb, v, ("SAPU_MASUK", "sistem", f"sisa dari {lok_nama(lk)} (SK)")))
                sal[(lk, lb)] = 0
                sal[(FOREMAN_SK, lb)] += v
    out.sort(key=lambda e: (e[0], e[1]))
    return out


def _ledger_c(sampai):
    """_ledger yang di-memo 20 detik (dipakai tampilan harian dan rincian)."""
    if time.time() - _memo["t"] > 20:
        _memo["d"] = {}
        _memo["t"] = time.time()
    k = ("ledger", sampai)
    if k not in _memo["d"]:
        _memo["d"][k] = _ledger(sampai)
    return _memo["d"][k]


def _terap(sal, jenis, lk, lb, v):
    if jenis == "reset":
        for k in [k for k in sal if k[0].startswith(lk + "|")]:
            sal[k] = 0
    elif jenis == "set":
        sal[(lk, lb)] = v
    else:
        sal[(lk, lb)] += v


def saldo(sampai=None, abaikan=None):
    """({(lokasi, label): saldo}, DataFrame pemakaian tanpa meja) sampai akhir hari `sampai`."""
    sampai = sampai or hari_ini()
    if time.time() - _memo["t"] > 20:
        _memo["d"] = {}
        _memo["t"] = time.time()
    if abaikan is None and sampai in _memo["d"]:
        return _memo["d"][sampai]
    ev, tanpa = _ledger(sampai, abaikan)
    sal = defaultdict(int)
    for tgl, _o, jenis, lk, lb, v, *_k in ev:
        if tgl > sampai:
            break
        _terap(sal, jenis, lk, lb, v)
    hasil = (dict(sal), pd.DataFrame(tanpa, columns=["tgl", "prn", "nama", "label", "n"]))
    if abaikan is None:
        _memo["d"][sampai] = hasil
    return hasil


def harian(bulan):
    """Stok akhir TIAP HARI (setelah pemakaian) dalam bulan 'YYYY-MM' sampai hari ini, dari satu kali penelusuran kejadian.
    Return (saldo {tgl: {(lokasi, label): n}}, adjust {tgl: {(lokasi, label): (sistem_sebelum, aktual)}}, aktif {tgl yang ada pemakaian SAP/afkir})."""
    kunci = ("harian", bulan)
    if time.time() - _memo["t"] > 20:
        _memo["d"] = {}
        _memo["t"] = time.time()
    if kunci in _memo["d"]:
        return _memo["d"][kunci]
    p = pd.Period(bulan, freq="M")
    akhir = min(p.end_time.date().isoformat(), hari_ini())
    hari = [d.date().isoformat() for d in pd.date_range(p.start_time.date(), akhir)]
    hasil, adj, aktif = {}, defaultdict(dict), set()
    if hari:
        ev, tanpa = _ledger_c(hari_ini())
        aktif |= set(tanpa["tgl"]) if len(tanpa) else set()
        sal, i = defaultdict(int), 0
        for tgl, _o, jenis, lk, lb, v, *k in ev:
            if tgl > akhir:
                break
            while i < len(hari) and hari[i] < tgl:
                hasil[hari[i]] = dict(sal)
                i += 1
            if jenis == "set":
                adj[tgl][(lk, lb)] = (sal.get((lk, lb), 0), v)
            if k and k[0][0] in ("SAP", "AFKIR", "PM_PAKAI", "SET"):
                aktif.add(tgl)
            _terap(sal, jenis, lk, lb, v)
        while i < len(hari):
            hasil[hari[i]] = dict(sal)
            i += 1
    out = (hasil, dict(adj), aktif)
    _memo["d"][kunci] = out
    return out


_GRUP = {"TERIMA": "MASUK", "TERIMA_MEJA": "MASUK", "PINDAH_MASUK": "MASUK", "DISTR_MASUK": "MASUK", "PM_MASUK": "MASUK",
         "KIRIM_MEJA": "KELUAR", "PINDAH_KELUAR": "KELUAR", "DISTR_KELUAR": "KELUAR", "PM_KELUAR": "KELUAR",
         "SAPU_MASUK": "MASUK", "SAPU_KELUAR": "KELUAR",
         "SAP": "SAP", "PM_PAKAI": "SAP", "AFKIR": "AFKIR", "SET": "KOREKSI", "PM_KOREKSI": "KOREKSI", "RESET": "KOREKSI"}
GRUP = ["MASUK", "KELUAR", "SAP", "AFKIR", "KOREKSI"]


def rincian(tgl, lb):
    """Telusur satu type label pada satu hari: stok awal (akhir hari sebelumnya) per lokasi, kejadian hari itu (masuk, keluar, pemakaian SAP,
    afkir, koreksi/ADJUST) beserta karyawannya, dan stok akhir. Return dict(awal, akhir, kejadian[(lokasi, grup, nama, info, jumlah)], tanpa)."""
    ev, tanpa = _ledger_c(hari_ini())
    sal, awal, kej = defaultdict(int), None, []
    for tg, _o, jenis, lk, l2, v, *k in ev:
        if tg > tgl:
            break
        if tg == tgl and awal is None:
            awal = {kk: vv for kk, vv in sal.items() if kk[1] == lb}
        if tg == tgl:
            kat, nama, info = k[0][:3] if k else ("", "", "")
            if jenis == "reset":
                for kk in [kk for kk in sal if kk[0].startswith(lk + "|") and kk[1] == lb and sal[kk]]:
                    kej.append((kk[0], "KOREKSI", nama, info, -sal[kk]))
            elif l2 == lb:
                kej.append((lk, _GRUP.get(kat, "KOREKSI"), nama, info, (v - sal.get((lk, l2), 0)) if jenis == "set" else v))
        _terap(sal, jenis, lk, l2, v)
    akhir = {kk: vv for kk, vv in sal.items() if kk[1] == lb}
    if awal is None:
        awal = dict(akhir)
    tp = tanpa[(tanpa["tgl"] == tgl) & (tanpa["label"] == lb)] if len(tanpa) else tanpa
    return {"awal": awal, "akhir": akhir, "kejadian": kej, "tanpa": tp}


def pic_meja(tgl, hari_mundur=14):
    """{lokasi meja: [nama operator]}: operator yang memegang meja itu pada tanggal tgl = alamat terakhirnya (maks hari_mundur hari ke belakang).
    Bila alamat itu bukan dari tanggal tgl sendiri, nama diberi tanggalnya, mis. 'BUDI (21/11)'."""
    nama = {}
    for tb in ("label_afkir", "label_meja", "label_pindahmeja"):
        d = data.baca(tb)
        if len(d) and "nama" in d.columns:
            for p_, n_ in zip(d["prn"], d["nama"]):
                if n_:
                    nama[p_] = n_
    batas = (date.fromisoformat(tgl) - timedelta(days=hari_mundur)).isoformat()
    terakhir = {}  # prn -> (tanggal, lokasi)
    for (prn, t), lk in _peta_meja().items():
        if batas <= t <= tgl and (prn not in terakhir or t > terakhir[prn][0]):
            terakhir[prn] = (t, lk)
    out = defaultdict(list)
    for prn, (t, lk) in sorted(terakhir.items(), key=lambda x: nama.get(x[0], x[0])):
        n_ = nama.get(prn) or prn
        out[lk].append(n_ if t == tgl else f"{n_} ({t[8:]}/{t[5:7]})")
    return dict(out)


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
