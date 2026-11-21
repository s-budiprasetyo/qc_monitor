"""Rencana produksi bulanan (file 'Draft Rencana Produksi' per pabrik). Hanya blok RENCANA PRODUKSI QUALITY CONTROL
yang dibaca; blok departemen lain (Forming, Dry Body, Glazing) diabaikan. Disimpan per (bulan, pabrik, dept)."""
import re
import pandas as pd
from core import data

KOLOM_HARI = ["bulan", "pabrik", "dept", "type", "tgl", "jumlah"]
KOLOM = ["bulan", "pabrik", "dept", "type", "periksa", "bagus", "file", "waktu"]
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def bulan_dari_nama(nama):
    """'..._November_2026_...' -> '2026-11' (None bila tidak ditemukan)."""
    m = re.search(r"(" + "|".join(BULAN) + r")\D{0,3}(20\d\d)", str(nama), re.I)
    if not m:
        return None
    return f"{m.group(2)}-{[b.lower() for b in BULAN].index(m.group(1).lower()) + 1:02d}"


def nama_bulan(ym):
    try:
        return f"{BULAN[int(ym[5:7]) - 1]} {ym[:4]}"
    except Exception:
        return str(ym)


def kunci_type(t, mesin=""):
    """Nama type di rencana -> nama baris/label di rekap. CE7#W = label CE7; kolom M = 'CW420J (M)'."""
    t = str(t).strip()
    if t == "CE7#W":
        return "CE7"
    if str(mesin).strip().upper() == "M" and not t.endswith("(M)"):
        return f"{t} (M)"
    return t


def _angka(v):
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else 0.0


BLOK = {"QC": ("QUALITY CONTROL", "PERIKSA"), "KAMA": ("GLAZING", "GLAZUR")}  # KAMA = blok GLAZING (hasil glazur masuk kama/bakar)
NAMA_DEPT = {"QC": "QC", "KAMA": "KAMA"}


def _blok(ws, dept):
    """Satu blok departemen -> (total[type, periksa, bagus], harian[type, tgl, jumlah], forming[])."""
    judul, kolom_total = BLOK[dept]
    col0 = None
    for c in ws[3]:
        if isinstance(c.value, str) and judul in c.value.upper() and "RENCANA PRODUKSI" in c.value.upper():
            col0 = c.column
            break
    if col0 is None:
        raise ValueError(f"Blok 'RENCANA PRODUKSI {judul}' tidak ditemukan di baris 3.")
    cp = cb = None
    hari = {}
    for c in ws[10]:
        if c.column < col0:
            continue
        v = c.value
        if isinstance(v, (int, float)) and not isinstance(v, bool) and not cp and 1 <= int(v) <= 31:
            hari[c.column] = int(v)
        elif isinstance(v, str):
            u = v.strip().upper()
            if u == kolom_total:
                cp = c.column
            elif u == "BAGUS" and cp and not cb:
                cb = c.column
        if cb:
            break
    if cp is None or cb is None or not hari:
        raise ValueError(f"Kolom tanggal / {kolom_total} / BAGUS pada blok {judul} tidak ditemukan.")
    forming, tot, har = [], [], []
    akhir = ws.max_row
    for r in range(11, ws.max_row + 1):  # data berakhir di baris GRAND TOTAL (kolom A); di bawahnya hanya catatan
        a = ws.cell(r, 1).value
        if isinstance(a, str) and a.strip().upper().startswith("GRAND TOTAL"):
            akhir = r - 1
            break
    for r in range(11, akhir + 1):
        t = ws.cell(r, col0).value
        if not isinstance(t, str) or not t.strip():
            continue
        t = t.strip()
        u = t.upper()
        m = re.match(r"FORMING\s+(\d+)", u)
        if m:
            forming.append(int(m.group(1)))
            continue
        if u.startswith("GRAND TOTAL PC0"):
            break
        if u.startswith(("TOTAL", "GRAND TOTAL", "HAL")):
            continue
        k = kunci_type(t, ws.cell(r, col0 + 1).value) if dept == "QC" else kunci_type(t if t != "CE7#W" else "CE7", ws.cell(r, col0 + 1).value)
        tot.append({"type": k, "periksa": _angka(ws.cell(r, cp).value), "bagus": _angka(ws.cell(r, cb).value)})
        for c, d in hari.items():
            v = _angka(ws.cell(r, c).value)
            if v:
                har.append({"type": k, "tgl": d, "jumlah": v})
    if not tot:
        raise ValueError(f"Tidak ada baris type pada blok {judul}.")
    d = pd.DataFrame(tot).groupby("type", sort=False, as_index=False).sum()
    d["periksa"] = d["periksa"].round().astype(int)
    d["bagus"] = d["bagus"].round().astype(int)
    h = pd.DataFrame(har, columns=["type", "tgl", "jumlah"])
    if len(h):
        h = h.groupby(["type", "tgl"], as_index=False).sum()
        h["jumlah"] = h["jumlah"].round().astype(int)
    return d, h, forming


def baca_file(f):
    """-> (pabrik, {dept: (total, harian)}, peringatan[]). Pabrik dikenali dari nomor FORMING (1-4 = P1, 5-8 = P2).
    Blok QC (PERIKSA) dan KAMA (GLAZUR) dibaca; Forming & Dry Body diabaikan."""
    import openpyxl
    wb = openpyxl.load_workbook(f, data_only=True)
    if "Renc Produksi" not in wb.sheetnames:
        raise ValueError("Sheet 'Renc Produksi' tidak ditemukan. Pastikan ini file Draft Rencana Produksi.")
    ws = wb["Renc Produksi"]
    out, forming = {}, []
    for dept in BLOK:
        d, h, fm = _blok(ws, dept)
        out[dept] = (d, h)
        forming = forming or fm
    pabrik = "2" if forming and min(forming) >= 5 else "1"
    return pabrik, out, []


def simpan(bulan, pabrik, hasil, nama_file):
    """hasil = {dept: (total, harian)} dari baca_file. Data lama (bulan, pabrik, dept) diganti."""
    for dept, (d, h) in hasil.items():
        b = pd.DataFrame({"bulan": bulan, "pabrik": str(pabrik), "dept": dept, "type": d["type"], "periksa": d["periksa"],
                          "bagus": d["bagus"], "file": nama_file, "waktu": data.sekarang()})
        _ganti("rencana_qc", b[KOLOM], bulan, pabrik, dept, ["bulan", "pabrik", "dept", "type"])
        hh = pd.DataFrame({"bulan": bulan, "pabrik": str(pabrik), "dept": dept, "type": h["type"], "tgl": h["tgl"], "jumlah": h["jumlah"]})
        _ganti("rencana_harian", hh[KOLOM_HARI], bulan, pabrik, dept, ["bulan", "pabrik", "dept", "type", "tgl"])


def _ganti(tabel, baru, bulan, pabrik, dept, kunci):
    lama = data.baca(tabel)
    hapus = lama[(lama["bulan"] == bulan) & (lama["pabrik"].astype(str) == str(pabrik)) & (lama["dept"] == dept)] if len(lama) else None
    data.upsert(tabel, baru, kunci, hapus=hapus[kunci] if hapus is not None and len(hapus) else None)


def harian(bulan, dept="QC"):
    """DataFrame[pabrik, type, tgl, jumlah] untuk bulan & dept."""
    d = data.baca("rencana_harian")
    if d.empty:
        return d
    d = d[(d["bulan"] == bulan) & (d["dept"] == dept)].copy()
    d["tgl"] = pd.to_numeric(d["tgl"], errors="coerce").fillna(0).astype(int)
    d["jumlah"] = pd.to_numeric(d["jumlah"], errors="coerce").fillna(0).astype(int)
    return d


def ada():
    d = data.baca("rencana_qc")
    return d


def per_type(bulan, dept="QC"):
    """{type: periksa} gabungan semua pabrik untuk bulan itu."""
    d = data.baca("rencana_qc")
    if d.empty:
        return {}
    d = d[(d["bulan"] == bulan) & (d["dept"] == dept)].copy()
    d["periksa"] = pd.to_numeric(d["periksa"], errors="coerce").fillna(0)
    return d.groupby("type")["periksa"].sum().astype(int).to_dict()


def bulan_tersedia():
    d = data.baca("rencana_qc")
    return sorted(set(d["bulan"])) if len(d) else []
