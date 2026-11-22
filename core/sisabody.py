"""Sisa body (stok body harian QC TK, file 'Stok Opname <tgl> <PAGI/SORE>'): kolom PERIKSA (OP 100 siap periksa) per type.
Dipakai sebagai kolom SISA BODY pada rekap hitung label."""
import re
import pandas as pd
from core import data, rencana

KOLOM = ["tgl", "shift", "dept", "type", "jumlah", "file", "waktu"]
DEPT = {"QC": "QC TK", "SK-FF": "SK Firstfiring", "SK-RF": "SK Refiring"}
_SUFIKS = re.compile(r"\((?:P\d|HPC|BC|MESIN)\)|\s+(?:HPC|BC)$", re.I)


def kunci(nama):
    """'CE7#W (P2) HPC' -> 'CE7'; 'CW420J (Mesin)' -> 'CW420J (M)'; 'CW53J (P1)' -> 'CW53J'."""
    n = str(nama).strip()
    mesin = bool(re.search(r"\(mesin\)", n, re.I))
    for _ in range(3):
        n = _SUFIKS.sub("", n).strip()
    if n == "CE7#W":
        return "CE7"
    return f"{n} (M)" if mesin else n


def _angka(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


def baca_file(f, nama=""):
    """-> (tgl ISO, shift 'PAGI'/'SORE', DataFrame[type, jumlah])."""
    import openpyxl
    ws = openpyxl.load_workbook(f, data_only=True).worksheets[0]
    teks = " ".join(str(c.value) for r in ws.iter_rows(min_row=1, max_row=8) for c in r if isinstance(c.value, str))
    mt = re.search(r"TANGGAL\s*:\s*(\d{1,2})", teks, re.I)
    mb = re.search(r"(" + "|".join(rencana.BULAN) + r")\s+(20\d\d)", teks, re.I) or re.search(r"(" + "|".join(rencana.BULAN) + r")\D{0,3}(20\d\d)", nama, re.I)
    ms = re.search(r"\b(PAGI|SORE)\b", teks + " " + nama, re.I)
    if not (mt and mb and ms):
        raise ValueError("Tanggal / bulan / shift (PAGI atau SORE) tidak ditemukan di bagian atas file.")
    bln = [b.lower() for b in rencana.BULAN].index(mb.group(1).lower()) + 1
    tgl = f"{int(mb.group(2)):04d}-{bln:02d}-{int(mt.group(1)):02d}"
    kol = baris0 = None
    for r in range(1, 15):
        for c in ws[r]:
            if isinstance(c.value, str) and c.value.strip().upper() == "PERIKSA":
                kol, baris0 = c.column, r
    if kol is None:
        raise ValueError("Kolom PERIKSA tidak ditemukan.")
    rows = []
    for r in range(baris0 + 1, ws.max_row + 1):
        a, b = ws.cell(r, 1).value, ws.cell(r, 2).value
        if isinstance(a, str) and a.strip().upper().startswith(("TOTAL", "KETERANGAN")):
            break
        if not isinstance(b, str) or not b.strip():
            continue
        rows.append({"type": kunci(b), "jumlah": _angka(ws.cell(r, kol).value)})
    if not rows:
        raise ValueError("Tidak ada baris type.")
    d = pd.DataFrame(rows).groupby("type", sort=False, as_index=False).sum()
    d["jumlah"] = d["jumlah"].round().astype(int)
    return tgl, ms.group(1).upper(), d


def simpan(tgl, shift, d, nama_file, dept="QC"):
    b = pd.DataFrame({"tgl": tgl, "shift": shift, "dept": dept, "type": d["type"], "jumlah": d["jumlah"], "file": nama_file, "waktu": data.sekarang()})
    lama = _baca()
    hapus = lama[(lama["tgl"] == tgl) & (lama["shift"] == shift) & (lama["dept"] == dept)] if len(lama) else None
    data.upsert("sisa_body", b[KOLOM], ["tgl", "shift", "dept", "type"], hapus=hapus[["tgl", "shift", "dept", "type"]] if hapus is not None and len(hapus) else None)


def _baca():
    d = data.baca("sisa_body").copy()
    if len(d):
        if "dept" not in d.columns:
            d["dept"] = ""
        d["dept"] = d["dept"].replace("", "QC")  # data lama (sebelum ada SK) = QC TK
    return d


def daftar(dept=None):
    """DataFrame[tgl, shift, dept, file, waktu, jumlah(total), type(jml)] terbaru dulu."""
    d = _baca()
    if d.empty:
        return d
    if dept:
        d = d[d["dept"] == dept]
        if d.empty:
            return d
    d["jumlah"] = pd.to_numeric(d["jumlah"], errors="coerce").fillna(0)
    g = d.groupby(["tgl", "shift", "dept"], as_index=False).agg(file=("file", "first"), waktu=("waktu", "first"), jumlah=("jumlah", "sum"), type=("type", "count"))
    g["u"] = g["shift"].map({"PAGI": 0, "SORE": 1})
    return g.sort_values(["tgl", "u"], ascending=False).drop(columns="u")


def untuk(tgl, dept="QC"):
    """({type: jumlah}, (tgl_file, shift)) dari file stok body `dept` terbaru pada atau sebelum `tgl`; ({}, None) bila tidak ada."""
    g = daftar(dept)
    if g.empty:
        return {}, None
    g = g[g["tgl"] <= tgl]
    if g.empty:
        return {}, None
    t, s = g.iloc[0]["tgl"], g.iloc[0]["shift"]
    d = _baca()
    d = d[(d["tgl"] == t) & (d["shift"] == s) & (d["dept"] == dept)].copy()
    d["jumlah"] = pd.to_numeric(d["jumlah"], errors="coerce").fillna(0).astype(int)
    return d.groupby("type")["jumlah"].sum().to_dict(), (t, s)
