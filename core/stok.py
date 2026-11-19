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
FOREMAN = "FOREMAN"


def lok(pabrik, meja):
    return f"{pabrik}|{meja}"


def lok_nama(lk):
    if not lk or lk == FOREMAN:
        return "Foreman (stok utama)"
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
def terima_simpan(tgl, baris, oleh):
    """baris = [(label, jumlah)]. Satu baris per input. Masuk stok FOREMAN."""
    waktu = _waktu()
    d = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb, "jumlah": int(n), "oleh": oleh} for lb, n in baris if lb and _int(n) > 0],
                    columns=["tgl", "waktu", "label", "jumlah", "oleh"])
    if len(d):
        d["waktu"] = [f"{waktu}.{i}" for i in range(len(d))]
        data.upsert("label_terima", d, ["tgl", "waktu", "label"])
        data.catat_update("STOK LABEL")
        _bersih()
    return len(d)


def terima_hapus(tgl, waktu, lb, oleh=""):
    h = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb}])
    data.upsert("label_terima", pd.DataFrame(columns=["tgl", "waktu", "label", "jumlah", "oleh"]), ["tgl", "waktu", "label"], hapus=h)
    catat_riwayat("hapus label bagus", f"{tgl}|{lb}", "", "dihapus", oleh, tgl)
    _bersih()


def terima_daftar(bulan=None):
    d = data.baca("label_terima")
    if d.empty:
        return d
    d = d.copy()
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
    """ke = FOREMAN atau (pabrik, meja). baris = [(label, jumlah)]. Return galat (str) atau None."""
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
    waktu = _waktu()
    d = pd.DataFrame([{"tgl": tgl, "waktu": f"{waktu}.{i}", "label": lb, "aktual": int(a), "sistem": int(sx),
                       "adjust": "ya" if adjust else "", "oleh": oleh, "lokasi": lokasi} for i, (lb, a, sx) in enumerate(baris) if lb],
                    columns=["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh", "lokasi"])
    if len(d):
        data.upsert("label_hitung", d, ["tgl", "waktu", "label"])
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


# ---------------------------------------------------------------- hitung saldo
def _pemakaian(sampai):
    """Pemakaian harian dari SAP + afkir: DataFrame[tgl, prn, label, n] (mulai MULAI s/d sampai)."""
    out = []
    for b in pd.period_range(MULAI[:7], sampai[:7], freq="M"):
        t = laporan.tabel(str(b))
        if t.empty:
            continue
        t = t[(t["tgl"] >= MULAI) & (t["tgl"] <= sampai)]
        if t.empty:
            continue
        t = t.copy()
        t["n"] = pd.to_numeric(t["bagus"], errors="coerce").fillna(0) + sum(pd.to_numeric(t[j], errors="coerce").fillna(0) for j in laporan.JENIS)
        out.append(t[["tgl", "prn", "label", "n", "nama"]])
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=["tgl", "prn", "label", "n", "nama"])


def _peta_meja():
    """(prn, tgl) -> lokasi meja tempat operator bekerja hari itu."""
    peta = {}
    a = data.baca("label_afkir")
    if len(a):
        for r in a.sort_values(["tgl", "waktu"]).itertuples():
            peta[(r.prn, r.tgl_posting)] = lok(r.pabrik, str(r.meja))
            peta[(r.prn, r.tgl)] = peta.get((r.prn, r.tgl), lok(r.pabrik, str(r.meja)))
    m = data.baca("label_meja")
    if len(m):
        for r in m.sort_values(["tgl", "waktu"]).itertuples():
            peta[(r.prn, r.tgl)] = lok(r.pabrik, str(r.meja))  # penerimaan label menang (alamat eksplisit)
    return peta


def saldo(sampai=None):
    """({(lokasi, label): saldo}, DataFrame pemakaian tanpa meja) sampai akhir hari `sampai`."""
    sampai = sampai or hari_ini()
    if time.time() - _memo["t"] > 20:
        _memo["d"] = {}
        _memo["t"] = time.time()
    if sampai in _memo["d"]:
        return _memo["d"][sampai]
    ev = []  # (tgl, urutan, jenis, lokasi, label, nilai)
    for r in data.baca("label_terima").itertuples():
        ev.append((r.tgl, 1, "tambah", FOREMAN, r.label, _int(r.jumlah)))
    for r in data.baca("label_meja").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", FOREMAN, r.label, -n))
        ev.append((r.tgl, 1, "tambah", lok(r.pabrik, str(r.meja)), r.label, n))
    for r in data.baca("label_pindah").itertuples():
        n = _int(r.jumlah)
        ev.append((r.tgl, 1, "tambah", lok(r.dari_pabrik, str(r.dari_meja)), r.label, -n))
        ke = FOREMAN if not r.ke_pabrik else lok(r.ke_pabrik, str(r.ke_meja))
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
    tanpa = []
    for r in pem.itertuples():
        lk = peta.get((r.prn, r.tgl))
        if lk is None or r.n <= 0:
            if r.n > 0:
                tanpa.append({"tgl": r.tgl, "prn": r.prn, "nama": r.nama, "label": r.label, "n": int(r.n)})
            continue
        ev.append((r.tgl, 2, "tambah", lk, r.label, -int(r.n)))
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
    _memo["d"][sampai] = hasil
    return hasil


def stok_lokasi(lokasi, sampai=None):
    """{label: saldo} satu lokasi (foreman atau meja); hanya label yang saldonya bukan 0."""
    sal, _ = saldo(sampai)
    return {lb: n for (lk, lb), n in sal.items() if lk == lokasi and n != 0}


def stok_meja(pabrik, meja, sampai=None):
    return stok_lokasi(lok(pabrik, str(meja)), sampai)


def stok_foreman(sampai=None):
    return stok_lokasi(FOREMAN, sampai)


def urut_label(daftar):
    ur = {lb: i for i, lb in enumerate(semua_label())}
    return sorted(daftar, key=lambda x: (ur.get(x, 9999), x))


def stok_semua(sampai=None):
    """DataFrame[label, foreman, meja, total] — total stok per label."""
    sal, _ = saldo(sampai)
    fm, mj = defaultdict(int), defaultdict(int)
    for (lk, lb), n in sal.items():
        (fm if lk == FOREMAN else mj)[lb] += n
    semua = set(fm) | set(mj)
    baris = [{"label": lb, "foreman": fm.get(lb, 0), "meja": mj.get(lb, 0), "total": fm.get(lb, 0) + mj.get(lb, 0)} for lb in urut_label(semua)]
    return pd.DataFrame(baris, columns=["label", "foreman", "meja", "total"])


def stok_per_meja(sampai=None):
    """DataFrame[pabrik, meja, label, stok] untuk semua meja yang punya saldo."""
    sal, _ = saldo(sampai)
    baris = []
    for (lk, lb), n in sal.items():
        if lk == FOREMAN or n == 0:
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


def excel_stok(total, per_meja, sampai):
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
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
