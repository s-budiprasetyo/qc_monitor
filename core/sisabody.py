"""Sisa body (stok body harian QC TK, file 'Stok Opname <tgl> <PAGI/SORE>'): kolom PERIKSA (OP 100 siap periksa) per type.
Dipakai sebagai kolom SISA BODY pada rekap hitung label."""
import re
import pandas as pd
from core import data, rencana

EKSTRA = ["pl", "perbaikan", "cek_ulang", "gerinda", "tdk_set", "tap", "kirim"]  # kolom stok body per OP (laporan pemakaian label)
KOLOM = ["tgl", "shift", "dept", "type", "jumlah", "file", "waktu"] + EKSTRA
_HEADER = {"PL": "pl", "PERBAIKAN": "perbaikan", "CEK ULANG": "cek_ulang", "GERINDA": "gerinda", "TAP": "tap", "KIRIM": "kirim",
           "TDK SET CR": "tdk_set", "TIDAK SET CR": "tdk_set", "TDK SET": "tdk_set", "TIDAK SET": "tdk_set"}
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
    kol_x = {}
    for r in range(1, 15):
        for c in ws[r]:
            if isinstance(c.value, str):
                h = re.sub(r"\s+", " ", c.value.strip().upper())
                if h == "PERIKSA":
                    kol, baris0 = c.column, r
                elif h in _HEADER and _HEADER[h] not in kol_x:
                    kol_x[_HEADER[h]] = c.column
    if kol is None:
        raise ValueError("Kolom PERIKSA tidak ditemukan.")
    rows = []
    for r in range(baris0 + 1, ws.max_row + 1):
        a, b = ws.cell(r, 1).value, ws.cell(r, 2).value
        if isinstance(a, str) and a.strip().upper().startswith(("TOTAL", "KETERANGAN")):
            break
        if not isinstance(b, str) or not b.strip():
            continue
        rows.append({"type": kunci(b), "jumlah": _angka(ws.cell(r, kol).value),
                     **{k: _angka(ws.cell(r, c).value) for k, c in kol_x.items()}})
    if not rows:
        raise ValueError("Tidak ada baris type.")
    d = pd.DataFrame(rows).groupby("type", sort=False, as_index=False).sum()
    for k in ["jumlah"] + EKSTRA:
        d[k] = d[k].round().astype(int) if k in d.columns else 0
    return tgl, ms.group(1).upper(), d


def simpan(tgl, shift, d, nama_file, dept="QC"):
    b = pd.DataFrame({"tgl": tgl, "shift": shift, "dept": dept, "type": d["type"], "jumlah": d["jumlah"], "file": nama_file, "waktu": data.sekarang(),
                      **{k: (d[k] if k in d.columns else 0) for k in EKSTRA}})
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


def akhir_bulan(bulan, dept_kode):
    """Stok body akhir bulan per OP: file terbaru (tanggal lalu shift SORE>PAGI) pada atau sebelum akhir bulan.
    dept_kode: 'QC' atau 'SK' (SK = Firstfiring + Refiring). Return ({type: {op: n}}, info [(dept, tgl, shift)], lengkap)
    op: op100 (PERIKSA+PL), op105, op110, op115, op120, op107, op166. lengkap False = file lama (hanya kolom PERIKSA tersimpan)."""
    akhir = f"{bulan}-31"
    out, info, lengkap = {}, [], True
    for dept in (["QC"] if dept_kode == "QC" else ["SK-FF", "SK-RF"]):
        g = daftar(dept)
        if g.empty:
            continue
        g = g[g["tgl"] <= akhir]
        g = g[g["tgl"].str[:7] == bulan] if (g["tgl"].str[:7] == bulan).any() else g.iloc[0:0]
        if g.empty:
            continue
        t, s = g.iloc[0]["tgl"], g.iloc[0]["shift"]
        info.append((dept, t, s))
        d = _baca()
        d = d[(d["tgl"] == t) & (d["shift"] == s) & (d["dept"] == dept)].copy()
        if not all(c in d.columns for c in EKSTRA) or not d[EKSTRA].astype(str).apply(lambda s: s.str.strip().ne("")).any().any():
            lengkap = False  # file lama: hanya kolom PERIKSA yang tersimpan
        for k in ["jumlah"] + EKSTRA:
            d[k] = pd.to_numeric(d[k], errors="coerce").fillna(0).astype(int) if k in d.columns else 0
        for r in d.itertuples():
            x = out.setdefault(r.type, {})
            for op, v in (("op100", r.jumlah + r.pl), ("op105", r.perbaikan), ("op110", r.gerinda), ("op115", r.cek_ulang),
                          ("op120", r.tap), ("op107", r.tdk_set), ("op166", r.kirim)):
                x[op] = x.get(op, 0) + int(v)
    return out, info, lengkap
