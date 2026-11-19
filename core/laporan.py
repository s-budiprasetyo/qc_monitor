"""Laporan % label afkir: afkir (input foreman) dibagi pcs bagus SAP (kolom Total) per karyawan, per label, per hari.

- Hari = Tanggal Posting (sama dengan tanggal di SAP).
- Pcs bagus label = jumlah 'Total' SAP karyawan itu pada hari itu untuk type (+warna) yang dipetakan ke label itu.
- Label SNI (pendamping): pembagi = pcs bagus label induknya (kolom `induk`), bukan nol dan bukan miliknya sendiri.
- Bagian: 'QC SK' bila meja di pabrik QC SK, selain itu 'QC'.
- Kotor di atas 0,5% ditandai merah."""
import io
import re

import pandas as pd

from core import calc, data, label, logic

JENIS = [j[0] if isinstance(j, (tuple, list)) else j for j in label.JENIS]  # lengket, garis, kotor, proses
BATAS_KOTOR = 0.005
KOLOM = ["tgl", "bagian", "prn", "nama", "label", "bagus", "lengket", "garis", "kotor", "proses", "induk", "catatan"]


PROSES_SAP = ["SAP | Afkir (M) - Berubah", "SAP | Afkir (LA) - Bocor Udara", "SAP | Afkir (LB) - Bocor Air", "SAP | Afkir (F) - Kurang Lancar"]


def proses_berlaku(lb):
    """Afkir Proses (otomatis dari SAP: M + LA + LB + F) hanya untuk type closet CW. CE6, CE7 (termasuk warna) dan CE9 tidak.
    Label SNI pendamping memakai nilai Proses type induknya."""
    t = str(lb).upper()
    return t[4:].startswith("CW") if t.startswith("SNI ") else t.startswith("CW")


def _angka(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


_memo = {}


def pcs_bagus(bulan):
    """Versi cepat (disimpan 60 detik) dari _pcs_bagus: dipakai dialog input yang sering memanggilnya."""
    import time
    t = _memo.get(bulan)
    if t and time.time() - t[0] < 60:
        return t[1]
    d = _pcs_bagus(bulan)
    _memo[bulan] = (time.time(), d)
    return d


def sap_hari(prn, tgl_posting):
    """{label: proses_sap} untuk semua type yang dikerjakan karyawan itu pada tanggal posting (dari SAP)."""
    if not prn or not tgl_posting:
        return {}
    b = pcs_bagus(str(tgl_posting)[:7])
    m = b[(b["prn"] == prn) & (b["tgl"] == tgl_posting)]
    return {lb: int(p) for lb, p in zip(m["label"], m["proses"])}


def _pcs_bagus(bulan):
    """DataFrame[prn, tgl, label, bagus]: jumlah Total SAP per karyawan/hari/label (hasil efektif, tanggal posting)."""
    h = logic.hasil_bulan(bulan)
    if h.empty or "prn" not in h.columns:
        return pd.DataFrame(columns=["prn", "tgl", "label", "bagus", "proses", "nama", "bagian"])
    h = h.copy()
    kp = [c for c in h.columns if re.match(r"^SAP \| Afkir \((M|LA|LB|F)\)", str(c).strip())]
    h["_p"] = sum(_angka(h[c]) for c in kp) if kp else 0
    h["_w"] = h["SAP | Warna"] if "SAP | Warna" in h.columns else ""
    h["_b"] = _angka(h["SAP | Total"]) if "SAP | Total" in h.columns else 0
    tabel = label.jenis_tabel()
    peta = {(t, w): label.label_untuk_sap(t, w, tabel)[0] for t, w in h[["type", "_w"]].drop_duplicates().itertuples(index=False)}
    h["label"] = [peta[(t, w)] for t, w in zip(h["type"], h["_w"])]
    h = h[(h["label"] != "") & h["prn"].notna()]
    g = h.groupby(["prn", "tgl", "label"], as_index=False)[["_b", "_p"]].sum().rename(columns={"_b": "bagus", "_p": "proses"})
    g["proses"] = [int(p) if proses_berlaku(lb) else 0 for p, lb in zip(g["proses"], g["label"])]
    info = h.groupby("prn").agg(nama=("nama_sap", "first"), bagian=("grup", lambda x: "QC SK" if (x == "SK").any() else "QC"))
    g["nama"] = g["prn"].map(info["nama"])
    g["bagian"] = g["prn"].map(info["bagian"])
    return g


def proses_sap(prn, tgl_posting, lb):
    """Afkir Proses otomatis (M + LA + LB + F dari SAP) untuk satu karyawan, tanggal posting, dan label. 0 bila tidak berlaku."""
    if not prn or not tgl_posting or not proses_berlaku(lb):
        return 0
    b = pcs_bagus(str(tgl_posting)[:7])
    induk = str(lb)[4:] if str(lb).startswith("SNI ") else lb
    m = b[(b["prn"] == prn) & (b["tgl"] == tgl_posting) & (b["label"] == induk)]
    return int(m["proses"].sum()) if len(m) else 0


def afkir(bulan):
    """DataFrame[tgl, bagian, prn, nama, label, induk, lengket, garis, kotor, proses] untuk Tanggal Posting di bulan itu."""
    d = data.baca("label_afkir")
    if d.empty:
        return pd.DataFrame(columns=KOLOM[:2] + ["prn", "nama", "label", "induk"] + JENIS)
    if "proses" not in d.columns:
        d["proses"] = ""
    if "induk" not in d.columns:
        d["induk"] = ""
    d = d[d["tgl_posting"].astype(str).str[:7] == bulan].copy()
    for j in JENIS:
        d[j] = _angka(d[j]).astype(int)
    d["bagian"] = d["pabrik"].map(lambda p: "QC SK" if p == "QC SK" else "QC")
    if "catatan" not in d.columns:
        d["catatan"] = ""
    d["catatan"] = d["catatan"].fillna("")
    d = d.drop(columns=["tgl"]).rename(columns={"tgl_posting": "tgl", "type": "label"})
    g = d.groupby(["tgl", "prn", "nama", "label", "induk"], as_index=False).agg(
        {**{j: "sum" for j in JENIS}, "bagian": lambda s: "QC SK" if (s == "QC SK").any() else "QC",
         "catatan": lambda s: "; ".join(dict.fromkeys(x.strip() for x in s if str(x).strip()))})
    return g


def tabel(bulan):
    """Satu baris per (hari, karyawan, label) dengan pcs bagus SAP. Label SNI memakai pcs bagus label induknya.
    Karyawan/hari/label yang ada di SAP tetapi belum diinput afkirnya tetap muncul dengan afkir 0 (-> 0%)."""
    a = afkir(bulan)
    b = pcs_bagus(bulan)
    if a.empty and b.empty:
        return pd.DataFrame(columns=KOLOM)
    ada = {(p, t, lb) for p, t, lb in zip(a["prn"], a["tgl"], a["label"])}
    n_input = len(a)
    baru = []
    for p, t, lb, nm, bg in zip(b["prn"], b["tgl"], b["label"], b["nama"], b["bagian"]):
        for nama_lb, induk in [(lb, "")] + ([(label.nama_sni(lb), lb)] if label.punya_sni(lb) else []):
            if (p, t, nama_lb) not in ada:
                baru.append({"tgl": t, "bagian": bg, "prn": p, "nama": nm, "label": nama_lb, "induk": induk, "catatan": "",
                             **{j: 0 for j in JENIS}})
    if baru:
        a = pd.concat([a, pd.DataFrame(baru)], ignore_index=True)
    # nama & bagian ikut data SAP agar satu karyawan = satu baris
    info = b.drop_duplicates("prn").set_index("prn")
    a["nama"] = [info["nama"].get(p, n) for p, n in zip(a["prn"], a["nama"])]
    a["bagian"] = [info["bagian"].get(p, g) for p, g in zip(a["prn"], a["bagian"])]
    peta = {(p, t, lb): v for p, t, lb, v in zip(b["prn"], b["tgl"], b["label"], b["bagus"])}
    pro = {(p, t, lb): v for p, t, lb, v in zip(b["prn"], b["tgl"], b["label"], b["proses"])}
    # Proses: nilai hasil input foreman dipakai apa adanya (terisi otomatis dari SAP, boleh diubah); baris tanpa input memakai SAP
    sudah = [i < n_input for i in range(len(a))]
    a["proses"] = [v if ok else (pro.get((p, t, (ind or lb)), 0) if proses_berlaku(lb) else 0)
                   for ok, p, t, lb, ind, v in zip(sudah, a["prn"], a["tgl"], a["label"], a["induk"], a["proses"])]
    a["bagus"] = [peta.get((p, t, (ind or lb)), 0) for p, t, lb, ind in zip(a["prn"], a["tgl"], a["label"], a["induk"])]
    a["bagus"] = a["bagus"].astype(int)
    return a.sort_values(["bagian", "nama", "tgl", "label"])[KOLOM].reset_index(drop=True)


def ringkas_harian(df):
    """Satu baris per (bagian, prn, nama, tgl): total afkir, pcs bagus total (label SNI tidak dihitung dobel), kotor, %.
    % total = jumlah afkir total / jumlah pcs bagus total hari itu."""
    if df.empty:
        return pd.DataFrame(columns=["bagian", "prn", "nama", "tgl", "afkir", "bagus", "kotor", "pct", "pct_kotor"])
    d = df.copy()
    d["afkir"] = d["kotor"]  # % label afkir hanya kategori Kotor
    d["bagus_utama"] = d["bagus"]  # pcs bagus semua baris label (SNI pendamping ikut dihitung)
    g = d.groupby(["bagian", "prn", "nama", "tgl"], as_index=False).agg(afkir=("afkir", "sum"), bagus=("bagus_utama", "sum"), kotor=("kotor", "sum"))
    b = g["bagus"].where(g["bagus"] > 0)
    g["pct"] = g["afkir"] / b
    g["pct_kotor"] = g["kotor"] / b
    return g


def ringkas_bulan(rh):
    """Satu baris per operator untuk sebulan (rata-rata tertimbang: total kotor / total pcs bagus)."""
    if rh.empty:
        return rh
    g = rh.groupby(["bagian", "prn", "nama"], as_index=False)[["afkir", "bagus", "kotor"]].sum()
    b = g["bagus"].where(g["bagus"] > 0)
    g["pct"] = g["afkir"] / b
    g["pct_kotor"] = g["kotor"] / b
    return g


def tambah_persen(df):
    """Kolom % (pecahan, 0.01 = 1%) dan total afkir. Pcs bagus 0 -> kosong (NaN)."""
    d = df.copy()
    d["afkir"] = d[JENIS].sum(axis=1)
    b = d["bagus"].where(d["bagus"] > 0)
    for j in JENIS + ["afkir"]:
        d["%" + j] = d[j] / b
    return d


def bulanan(df):
    """Jumlahkan per karyawan + label sepanjang bulan."""
    if df.empty:
        return df
    g = df.groupby(["bagian", "prn", "nama", "label"], as_index=False)[["bagus"] + JENIS].sum()
    return g.sort_values(["bagian", "nama", "label"]).reset_index(drop=True)


# ---------------------------------------------------------------- Excel
def _tulis_sheet(ws, df, judul, kolom_awal=("bagian", "nama", "label"), dengan_tgl=False):
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter as L
    nama = {"tgl": "TANGGAL", "bagian": "BAGIAN", "nama": "NAMA", "label": "LABEL", "bagus": "PCS BAGUS (SAP)",
            "lengket": "LENGKET", "garis": "GARIS", "kotor": "KOTOR", "proses": "PROSES"}
    awal = (["tgl"] if dengan_tgl else []) + list(kolom_awal)
    kol = awal + ["bagus"] + JENIS
    ws["A1"] = judul
    ws["A1"].font = Font(name="Arial", bold=True, size=13, color="0B3D91")
    ws["A2"] = ("% label afkir = afkir Kotor ÷ pcs bagus SAP (kolom Total). Label SNI dibagi pcs bagus label induknya. "
                "Di atas 0,5% diberi warna merah. Lengket, Garis, Proses hanya informasi.")
    ws["A2"].font = Font(name="Arial", italic=True, size=9, color="5B7399")
    h = 4
    tebal = Side(style="thin", color="B8C7DD")
    garis = Border(left=tebal, right=tebal, top=tebal, bottom=tebal)
    judul_kol = [nama[c] for c in kol] + ["% LABEL AFKIR (KOTOR)"]
    for i, t in enumerate(judul_kol, 1):
        c = ws.cell(h, i, t)
        c.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor="1A5FC8")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = garis
    n = len(kol)
    ib = kol.index("bagus") + 1
    ij = [kol.index(j) + 1 for j in JENIS]
    ik = ij[JENIS.index("kotor")]
    ip = n + 1
    for r, row in enumerate(df[kol].itertuples(index=False), h + 1):
        for i, v in enumerate(row, 1):
            c = ws.cell(r, i, v)
            c.font = Font(name="Arial", size=10)
            c.border = garis
            if kol[i - 1] in ["bagus"] + JENIS:
                c.number_format = "#,##0"
        c = ws.cell(r, ip, f'=IF(${L(ib)}{r}>0,{L(ik)}{r}/${L(ib)}{r},"")')
        c.number_format = "0.00%"
        c.font = Font(name="Arial", size=10, bold=True)
        c.border = garis
    akhir = h + len(df)
    if len(df):
        from openpyxl.formatting.rule import FormulaRule
        kot = L(ip)
        ws.conditional_formatting.add(f"{kot}{h + 1}:{kot}{akhir}", FormulaRule(
            formula=[f'AND(ISNUMBER({kot}{h + 1}),{kot}{h + 1}>{BATAS_KOTOR})'],
            font=Font(name="Arial", color="C00000", bold=True), fill=PatternFill("solid", bgColor="FDE2E2")))
    ws.freeze_panes = ws.cell(h + 1, len(awal) + 1)
    for i in range(1, ip + 1):
        ws.column_dimensions[L(i)].width = 32 if kol[i - 1:i] == ["nama"] else (14 if i <= n else 20)
    ws.row_dimensions[h].height = 32


def excel_harian(df_hari, tgl):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Harian"
    _tulis_sheet(ws, df_hari, f"% LABEL AFKIR HARIAN — {tgl}")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def excel_bulanan(df_bulan, bulan):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Ringkasan bulan"
    _tulis_sheet(ws, bulanan(df_bulan), f"% LABEL AFKIR BULANAN — {bulan}")
    ws2 = wb.create_sheet("Per hari")
    _tulis_sheet(ws2, df_bulan, f"% LABEL AFKIR PER HARI — {bulan}", dengan_tgl=True)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
