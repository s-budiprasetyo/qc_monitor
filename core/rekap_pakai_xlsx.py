"""Excel laporan REKAPAN PEMAKAIAN LABEL: satu sheet per bulan (format file REKAPAN) + sheet REKAPAN PER BULAN.
Rumus tetap hidup: K, T, U, X, TOTAL, baris CE7 (CE7 + warna), baris SNI (jumlah CW kecuali CW52J), H = Y bulan sebelumnya,
dan REKAPAN PER BULAN menunjuk ke TOTAL tiap sheet bulan."""
import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L

from core import data, rekap_pakai as R

F = "Arial"
TIPIS = Side(style="thin", color="888888")
KOTAK = Border(left=TIPIS, right=TIPIS, top=TIPIS, bottom=TIPIS)
BIRU = PatternFill("solid", fgColor="D9E1F2")
KUNING = PatternFill("solid", fgColor="FFF2CC")
NF = '#,##0;-#,##0;"-"'
BARIS0 = 11
BARIS_TOTAL = BARIS0 + len(R.NAMA)  # 57
BARIS_SNI = BARIS_TOTAL + 2  # 59
BARIS_Y = BARIS_SNI + 2  # 61
NAMA_SHEET = [n.upper() for n in R.NAMA_BULAN[1:]]
JUDUL = {"QC": "QUALITY CONTROL TK", "SK": "QUALITY CONTROL SK", "GAB": "QUALITY CONTROL TK & SK"}
KOL_PLAIN = ["I", "L", "M", "N", "Y", "AA", "AB", "AC", "AD", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"]
KOL_JUMLAH_CE7 = ["G", "J", "O", "P", "Q", "R", "S", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"]  # CE7 = CE7 + semua warna
KOL_JUMLAH_SNI = ["G", "J", "O", "P", "Q", "R", "S", "AA", "AB", "AC", "AD"]  # SNI = jumlah CW (kecuali CW52J)
KOL_TOTAL = ["G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "Y", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"]


def _sel(ws, ref, nilai=None, tebal=False, biru=False, nf=None, rata=None, isi=None, kotak=True, ukuran=10, bungkus=False):
    c = ws[ref]
    if nilai is not None:
        c.value = nilai
    c.font = Font(name=F, bold=tebal, color="0000FF" if biru else "000000", size=ukuran)
    if nf:
        c.number_format = nf
    if rata or bungkus:
        c.alignment = Alignment(horizontal=rata, vertical="center", wrap_text=bungkus)
    if isi:
        c.fill = isi
    if kotak:
        c.border = KOTAK
    return c


def _kepala(ws, bulan, dept):
    nm = R.NAMA_BULAN[int(bulan[5:])]
    ws["E1"] = "PT. SURYA PERTIWI NUSANTARA"
    ws["E1"].font = Font(name=F, bold=True, size=12)
    ws["E2"] = f"LAPORAN MONITORING\nPENGGUNAAN LABEL\n{JUDUL[dept]}"
    ws["E2"].font = Font(name=F, bold=True, size=12)
    ws["E2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws["O2"] = f"Gresik, {datetime.now(data.WIB).day:02d} {R.NAMA_BULAN[datetime.now(data.WIB).month]} {datetime.now(data.WIB).year}"
    for ref, t in (("O3", "Dibuat,"), ("Q3", "Diperiksa,"), ("T3", "Disetujui,"), ("O6", "Foreman"), ("Q6", "Supervisor")):
        ws[ref] = t
        ws[ref].font = Font(name=F, size=10)
    ws["E7"] = f"BULAN : {nm.upper()} {bulan[:4]}"
    ws["E7"].font = Font(name=F, bold=True, size=11)
    sebelum = R.NAMA_BULAN[int(R.bulan_sebelum(bulan)[5:])].upper()
    judul = {"E8": "NO", "F8": "TYPE", "G8": "RENCANA PRODUKSI", "H8": f"STOK {sebelum}", "I8": "PENGAMBILAN (BKB)", "J8": "PEMAKAIAN LABEL",
             "T8": "TOTAL RUSAK", "U8": "PRESENTASE AFKIR (%)", "X8": "STOK SISTEM", "Y8": f"STOK AKHIR {nm.upper()}", "AA8": "AFKIR PROSES",
             "AF8": "KIRIM KE PACKING (OP166)", "AG8": "STOK BODY AKHIR BULAN",
             "J9": "BAGUS OP100", "K9": "AFKIR LABEL", "O9": "AFKIR LABEL PROSES (DALAM BAGUS OP100)",
             "K10": "PROSES OP100 (M, LA, LB, F)", "L10": "LENGKET", "M10": "KOTOR", "N10": "GARIS", "O10": "PERBAIKAN", "P10": "GERINDA",
             "Q10": "CEK ULANG", "R10": "TAP & TAD", "S10": "SETTING CR", "AA10": "M", "AB10": "LA", "AC10": "LB", "AD10": "F",
             "AG9": "OP100", "AH9": "OP105", "AI9": "OP110", "AJ9": "OP115", "AK9": "OP120", "AL9": "OP107", "AM9": "OP166"}
    for ref, t in judul.items():
        ws[ref] = t
    for rng in ("E8:E10", "F8:F10", "G8:G10", "H8:H10", "I8:I10", "J8:S8", "T8:T10", "U8:U10", "X8:X10", "Y8:Y10", "AA8:AD9", "AF8:AF10", "AG8:AM8",
                "K9:N9", "O9:S9", "J9:J10", "AG9:AG9"):
        try:
            ws.merge_cells(rng)
        except Exception:
            pass
    for r in range(8, 11):
        for ci in list(range(5, 22)) + list(range(24, 26)) + list(range(27, 31)) + list(range(32, 40)):
            _sel(ws, f"{L(ci)}{r}", tebal=True, isi=BIRU, rata="center", bungkus=True, ukuran=9)
    ws.row_dimensions[8].height = 30
    ws.row_dimensions[10].height = 30


def _baris(ws, bulan, dept, df, prev_sheet, riwayat_nilai=None):
    """Tulis tabel data. df: DataFrame hasil R.data_bulan (nilai dasar); riwayat_nilai: dict baris->kolom (angka lama, nilai biasa)."""
    r_of = {n: BARIS0 + i for i, n in enumerate(R.NAMA)}
    r_ce7, r_w0, r_w1 = r_of["CE7"], r_of["PIV"], r_of["MA"]
    cw_rows = [r_of[n] for n in R.CW_SNI]
    cw_ref = lambda c: "=SUM(" + f"{c}{cw_rows[0]}:{c}{cw_rows[3]},{c}{cw_rows[4]}:{c}{cw_rows[-1]}" + ")"  # CW420J..CW427J, CW53J..CW637J
    for n in R.NAMA + [R.SNI]:
        r = r_of.get(n, BARIS_SNI)
        v = df.loc[n] if riwayat_nilai is None else {c: riwayat_nilai.get(n, {}).get(c, 0) for c in R.KOLOM_ANGKA}
        if n != R.SNI:
            _sel(ws, f"E{r}", R.NAMA.index(n) + 1, rata="center")
        else:
            _sel(ws, f"E{r}", 47, rata="center")
        _sel(ws, f"F{r}", n, tebal=(n in ("CE7", "SNI")))
        # kolom nilai
        for c in ["G", "I", "J", "L", "M", "N", "O", "P", "Q", "R", "S", "Y", "AA", "AB", "AC", "AD", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"]:
            nilai = int(v[c])
            if riwayat_nilai is None and n == "CE7" and c in KOL_JUMLAH_CE7:
                basis = nilai - int(df.loc[R.WARNA, c].sum())
                nilai = f"={basis}+SUM({c}{r_w0}:{c}{r_w1})"
            elif n == R.SNI and c in KOL_JUMLAH_SNI and riwayat_nilai is None:
                nilai = cw_ref(c)
            _sel(ws, f"{c}{r}", nilai, biru=not isinstance(nilai, str), nf=NF)
        # H
        if prev_sheet:
            _sel(ws, f"H{r}", f"='{prev_sheet}'!Y{r}", nf=NF)
        else:
            _sel(ws, f"H{r}", int(v["H"]), biru=True, nf=NF)
        if n == R.SNI:
            _sel(ws, f"K{r}", f"=SUM(K{cw_rows[0]}:K{cw_rows[3]},K{cw_rows[4]}:K{cw_rows[-1]})", nf=NF)
        else:
            _sel(ws, f"K{r}", f"=SUM(AA{r}:AD{r})", nf=NF)
        _sel(ws, f"T{r}", f"=SUM(K{r}:S{r})", nf=NF)
        _sel(ws, f"U{r}", f"=IFERROR(T{r}/J{r},0)", nf="0.0%")
        _sel(ws, f"X{r}", f"=(H{r}+I{r})-(J{r}+SUM(K{r}:N{r}))" if n != R.SNI else f"=(H{r}+I{r}-J{r})", nf=NF)
        _sel(ws, f"AF{r}", None, nf=NF)
        if n == "CE7":
            _sel(ws, f"F{r}", n, tebal=True, isi=KUNING)
    # TOTAL
    rt = BARIS_TOTAL
    _sel(ws, f"E{rt}", "TOTAL", tebal=True, isi=KUNING)
    ws.merge_cells(f"E{rt}:F{rt}")
    for c in KOL_TOTAL:
        _sel(ws, f"{c}{rt}", f"=SUM({c}{BARIS0}:{c}{rt - 1})", tebal=True, isi=KUNING, nf=NF)
    _sel(ws, f"U{rt}", f"=IFERROR(T{rt}/J{rt},0)", tebal=True, isi=KUNING, nf="0.0%")
    _sel(ws, f"Y{BARIS_Y}", f"=SUM(Y{BARIS0}:Y{BARIS_SNI})", tebal=True, nf=NF, kotak=False)


def _lebar(ws):
    ws.column_dimensions["A"].width = 2
    for c in "BCD":
        ws.column_dimensions[c].width = 1.5
    ws.column_dimensions["E"].width = 5
    ws.column_dimensions["F"].width = 12
    for ci in range(7, 40):
        ws.column_dimensions[L(ci)].width = 11
    for c in ("V", "W", "Z", "AE"):
        ws.column_dimensions[c].width = 2
    ws.freeze_panes = "G11"
    ws.sheet_view.zoomScale = 90


def _sheet_bulan(wb, bulan, dept, prev_sheet, riwayat):
    ws = wb.create_sheet(NAMA_SHEET[int(bulan[5:]) - 1])
    _kepala(ws, bulan, dept)
    if riwayat is not None:
        _baris(ws, bulan, dept, None, prev_sheet, riwayat)
        cat = ["Angka bulan ini dari file REKAPAN lama (gabungan QC + SK)."]
    else:
        df, cat = R.data_bulan(bulan, dept)
        _baris(ws, bulan, dept, df, prev_sheet)
    ws[f"E{BARIS_Y + 2}"] = "Catatan:"
    ws[f"E{BARIS_Y + 2}"].font = Font(name=F, bold=True, size=9)
    aturan = ["Baris CE7 = CE7 + semua warna; baris SNI = jumlah semua type CW kecuali CW52J.",
              "Stok sistem = (stok bulan lalu + pengambilan) - (pcs bagus OP100 + afkir proses + lengket + kotor + garis). Afkir OP105-OP120 sudah termasuk dalam bagus OP100.",
              "Kolom biru = angka dari aplikasi (nilai); hitam = rumus."] + cat
    for i, t in enumerate(aturan):
        ws[f"E{BARIS_Y + 3 + i}"] = t
        ws[f"E{BARIS_Y + 3 + i}"].font = Font(name=F, size=9, italic=True)
    _lebar(ws)
    return ws.title


def _rekapan(wb, tahun, ada):
    ws = wb.create_sheet("REKAPAN PER BULAN")
    ws["B1"] = "PT. SURYA PERTIWI NUSANTARA"
    ws["B1"].font = Font(name=F, bold=True, size=12)
    ws["B2"] = "LAPORAN MONITORING PENGGUNAAN LABEL QUALITY CONTROL TK & SK"
    ws["B2"].font = Font(name=F, bold=True, size=12)
    judul = ["NO", "BULAN", "RENCANA PRODUKSI", "STOK AWAL BULAN", "PENGAMBILAN (BKB)", "BAGUS OP100", "AFKIR PROSES", "LENGKET", "KOTOR", "GARIS",
             "PERBAIKAN", "GERINDA", "CEK ULANG", "TAP & TAD", "SETTING CR", "TOTAL RUSAK", "PRESENTASE AFKIR (%)"]
    asal = ["", "", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", ""]
    for i, t in enumerate(judul):
        _sel(ws, f"{L(2 + i)}8", t, tebal=True, isi=BIRU, rata="center", bungkus=True, ukuran=9)
    ws.row_dimensions[8].height = 36
    for m in range(1, 13):
        r = 10 + m
        _sel(ws, f"B{r}", m, rata="center")
        _sel(ws, f"C{r}", R.NAMA_BULAN[m].upper())
        sh = NAMA_SHEET[m - 1]
        for i, c in enumerate(asal):
            if not c:
                continue
            _sel(ws, f"{L(2 + i)}{r}", f"='{sh}'!{c}{BARIS_TOTAL}" if sh in ada else None, nf=NF)
        _sel(ws, f"R{r}", f"=IFERROR(Q{r}/G{r},0)" if sh in ada else None, nf="0.0%")
    _sel(ws, "B23", "TOTAL", tebal=True, isi=KUNING)
    ws.merge_cells("B23:C23")
    for i, c in enumerate(asal):
        if c:
            _sel(ws, f"{L(2 + i)}23", f"=SUM({L(2 + i)}11:{L(2 + i)}22)", tebal=True, isi=KUNING, nf=NF)
    _sel(ws, "R23", "=IFERROR(Q23/G23,0)", tebal=True, isi=KUNING, nf="0.0%")
    ws.column_dimensions["A"].width = 2
    ws.column_dimensions["B"].width = 6
    ws.column_dimensions["C"].width = 14
    for ci in range(4, 19):
        ws.column_dimensions[L(ci)].width = 13
    ws["B25"] = ("Stok awal bulan = jumlah stok awal semua baris sheet bulan itu. Persentase = total rusak ÷ bagus OP100. "
                 "Semua angka menunjuk ke baris TOTAL tiap sheet bulan.")
    ws["B25"].font = Font(name=F, size=9, italic=True)


def buat(bulan, dept, setahun=False):
    """Workbook: satu sheet bulan (setahun=False) atau semua bulan tahun itu + REKAPAN PER BULAN (setahun=True).
    Bulan sebelum aplikasi berjalan (Januari–Oktober) hanya ada untuk dept 'GAB' (dari file REKAPAN lama)."""
    wb = Workbook()
    wb.remove(wb.active)
    if not setahun:
        _sheet_bulan(wb, bulan, dept, None, None)
        return wb
    tahun = bulan[:4]
    riw = R.riwayat()
    ada, prev = set(), None
    for m in range(1, 13):
        b = f"{tahun}-{m:02d}"
        if b in riw and dept == "GAB":
            prev = _sheet_bulan(wb, b, dept, prev, riw[b])
        elif b in riw:
            continue  # bulan lama hanya tersedia gabungan
        else:
            prev = _sheet_bulan(wb, b, dept, prev, None)
        ada.add(prev)
    _rekapan(wb, tahun, ada)
    return wb


def bytes_xlsx(bulan, dept, setahun=False):
    buf = io.BytesIO()
    buat(bulan, dept, setahun).save(buf)
    return buf.getvalue()
