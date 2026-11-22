"""Excel 'REKAP HITUNG LABEL' (format 10._REKAP_HITUNG_LABEL_OKTOBER26): sheet per departemen (QC TK, SK) + sheet INPUT.
JUMLAH LABEL = hasil hitung aktual (SUMIF dari INPUT), SISA LABEL = B-C, PB LABEL = E+C-B."""
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from core import label, rencana, sisabody, stok

URUTAN = ["CE6", "CE7", "CE9", "CW52J", "CW53J", "CW53PJ", "CW420J", "CW421J", "CW633J", "CW637J", "CW702J", "L38", "L38V1", "L521V1A",
          "L529V1", "L568V3", "LW211CJ", "LW230J", "LW236CJ", "LW240CJ", "LW246J", "LW247CJ", "LW248JT1", "LW540J", "LW642CJ", "LW647CJ",
          "SW53JP", "SW420JP", "SW633JP", "SW637JP", "SW784JP", "U57M", "SW53CRJP", "SW420CRJP", "SW633CRJP", "SW637CRJP", "SW784CRJP",
          "U104ST", "A100", "S163N", "S211N", "X003", "X004", "S161", "CW422J", "L521V3", "SW422JP", "LW523NJ", "CW420J (M)", "CW427J",
          "CW427J (M)", "SW427JP", "SW427CRJP", "CE7#HBE", "CE7#PIV", "CE7#B", "CE7#PB", "CE7#HF", "CE7#DR", "CE7#MA", "CE7#PP", "SNI"]
VARIAN = URUTAN[URUTAN.index("CE7#HBE"):URUTAN.index("CE7#PP") + 1]
BARIS_AWAL, BARIS_AKHIR = 4, 90  # 87 baris type/SPARE
TGL_INPUT_MAKS = 401
F = "Arial"
TIPIS = Side(style="thin", color="999999")
KOTAK = Border(left=TIPIS, right=TIPIS, top=TIPIS, bottom=TIPIS)
BULAN_ID = rencana.BULAN


def _kunci(lb):
    return "SNI" if str(lb).startswith(label.SNI + " ") else lb


def _hitungan(tgl, dept):
    """{type rekap: jumlah aktual} gabungan semua lokasi dept yang dihitung pada tanggal opname."""
    out = {}
    for lk in stok.opname_status(tgl):
        if not stok.dept_cocok(lk, dept):
            continue
        for lb, (a, _sx) in stok.opname_baris(tgl, lk).items():
            k = _kunci(lb)
            out[k] = out.get(k, 0) + int(a)
    return out


def _sheet(ws, judul, dept, kol_in, hit, plan, baris_nama, sisa=None, sni_cw=False, plan_rf=None):
    sisa = sisa or {}
    ws["A1"] = judul
    ws["A1"].font = Font(name=F, bold=True, size=16)
    for i, h in enumerate(["TYPE", "JUMLAH LABEL", "SISA BODY", "SISA LABEL", "RENCANA PRODUKSI", "PB LABEL"], start=1):
        c = ws.cell(2, i, h)
        c.font = Font(name=F, bold=True)
        c.fill = PatternFill("solid", fgColor="D9E1F2")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = KOTAK
    ws["B3"] = f'=INPUT!{kol_in[0]}3&" "&INPUT!{kol_in[1]}3'
    ws["B3"].font = Font(name=F, italic=True, size=9)
    tk, jm = kol_in[2], kol_in[3]
    for i, nama in enumerate(baris_nama):
        r = BARIS_AWAL + i
        ws.cell(r, 1, nama)
        ws.cell(r, 2, f"=SUMIF(INPUT!${tk}$3:${tk}${TGL_INPUT_MAKS},A{r},INPUT!${jm}$3:${jm}${TGL_INPUT_MAKS})")
        ws.cell(r, 4, f"=+B{r}-C{r}")
        if nama == "CE7":
            ws.cell(r, 3, f"={int(sisa.get('CE7', 0))}+SUM(C{BARIS_AWAL + baris_nama.index('CE7#HBE')}:C{BARIS_AWAL + baris_nama.index('CE7#PP')})")
            ws.cell(r, 5, f"={int(plan.get('CE7', 0))}+SUM(E{BARIS_AWAL + baris_nama.index('CE7#HBE')}:E{BARIS_AWAL + baris_nama.index('CE7#PP')})")
        elif nama == "SNI" and sni_cw and sisa:  # sisa body SNI = jumlah semua type CW kecuali CW52J
            cw = [BARIS_AWAL + baris_nama.index(k) for k in baris_nama if k.startswith("CW") and k != "CW52J"]
            ws.cell(r, 3, "=" + "+".join(f"C{x}" for x in cw))
            ws.cell(r, 5, None)
        else:
            if sisa.get(nama):
                ws.cell(r, 3, int(sisa[nama]))
            ws.cell(r, 5, int(plan[nama]) if plan.get(nama) else None)
        ws.cell(r, 6, f"=E{r}+C{r}-B{r}" if not nama.startswith("SPARE") else None)
        if plan_rf is not None and plan_rf.get(nama):
            ws.cell(r, 8, int(plan_rf[nama]))
            ws.cell(r, 8).font = Font(name=F, color="0000FF")
            ws.cell(r, 8).number_format = "#,##0"
        for cc in range(1, 7):
            c = ws.cell(r, cc)
            c.font = Font(name=F, bold=(cc == 1), color=("0000FF" if cc in (3, 5) else "000000"))
            c.border = KOTAK
            if cc > 1:
                c.number_format = "#,##0;[Red]-#,##0;-"
    if plan_rf is not None:
        ws["H2"] = "RENCANA RF"
        ws["H2"].font = Font(name=F, bold=True)
        ws["H2"].fill = PatternFill("solid", fgColor="D9E1F2")
        ws["H2"].border = KOTAK
        ws["E2"] = "RENCANA PRODUKSI (FF)"
        ws.column_dimensions["H"].width = 13
    rs = BARIS_AKHIR + 1
    ws.cell(rs, 1, "SUM")
    for col in "BDF":
        ws[f"{col}{rs}"] = f"=SUM({col}{BARIS_AWAL}:{col}{BARIS_AKHIR})"
    # SISA BODY & RENCANA type CE7 sudah memuat jumlah varian CE7#… (baris 57-64), jadi varian tidak dihitung dua kali di SUM
    v0, v1 = BARIS_AWAL + baris_nama.index("CE7#HBE"), BARIS_AWAL + baris_nama.index("CE7#PP")
    ws[f"C{rs}"] = f"=SUM(C{BARIS_AWAL}:C{BARIS_AKHIR})-SUM(C{v0}:C{v1})" + (f"-C{BARIS_AWAL + baris_nama.index('SNI')}" if sni_cw and sisa else "")  # SNI = subset CW
    ws[f"E{rs}"] = f"=SUM(E{BARIS_AWAL}:E{BARIS_AKHIR})-SUM(E{v0}:E{v1})"
    for cc in range(1, 7):
        c = ws.cell(rs, cc)
        c.font = Font(name=F, bold=True)
        c.fill = PatternFill("solid", fgColor="FFF2CC")
        c.border = KOTAK
        if cc > 1:
            c.number_format = "#,##0;[Red]-#,##0;-"
    for col, w in zip("ABCDEF", (18.6, 15, 12, 13, 18, 13)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "B3"


def bulan_rencana(tgl):
    """Rekap label akhir bulan N memakai rencana produksi bulan N+1 (hitung 31 Okt -> rencana November)."""
    y, m = int(tgl[:4]), int(tgl[5:7])
    return f"{y + (m == 12)}-{m % 12 + 1:02d}"


def buat(tgl, bulan_plan=None, wb=None):
    """Sheet rekap untuk hasil hitung tanggal `tgl` (YYYY-MM-DD), ditambahkan ke `wb` (atau workbook baru).
    Rencana diambil dari `bulan_plan` (default: bulan sesudah tanggal hitung)."""
    bulan_plan = bulan_plan or bulan_rencana(tgl)
    plan_qc = rencana.per_type(bulan_plan, "QC")
    plan_sk = rencana.per_type(bulan_plan, "SK-FF")
    plan_rf = rencana.per_type(bulan_plan, "SK-RF")
    sisa_ff, info_ff = sisabody.untuk(tgl, "SK-FF")
    sisa_rf, info_rf = sisabody.untuk(tgl, "SK-RF")
    sisa_sk = {k: sisa_ff.get(k, 0) + sisa_rf.get(k, 0) for k in set(sisa_ff) | set(sisa_rf)}
    hit = {d: _hitungan(tgl, d) for d in ("QC", "SK")}
    # type di luar daftar baku -> baris SPARE (urut nama)
    sisa_qc, sisa_info = sisabody.untuk(tgl)

    def _nama_baris(h, p, sb=None):
        sb = sb or {}
        tambah = sorted({k for k in list(h) + list(p) + list(sb) if k not in URUTAN and (h.get(k) or p.get(k) or sb.get(k))})
        spare = [f"SPARE{n}" for n in range(25, 0, -1)]
        baris = list(URUTAN) + spare
        for k, sp in zip(tambah, spare):
            baris[baris.index(sp)] = k
        return baris
    nm = {"QC": _nama_baris(hit["QC"], plan_qc, sisa_qc), "SK": _nama_baris(hit["SK"], {**plan_rf, **plan_sk}, sisa_sk)}
    if wb is None:
        wb = Workbook()
        ws_qc = wb.active
    else:
        ws_qc = wb.create_sheet()
    ws_sk, ws_in = wb.create_sheet(), wb.create_sheet("INPUT")
    ws_qc.title, ws_sk.title = "REKAP HITUNG LABEL QC", "REKAP HITUNG LABEL SK"
    _sheet(ws_qc, "REKAP HITUNG LABEL QC TK", "QC", ("A", "B", "C", "D"), hit["QC"], plan_qc, nm["QC"], sisa_qc, True)
    _sheet(ws_sk, "REKAP HITUNG LABEL QC SK", "SK", ("F", "G", "H", "I"), hit["SK"], plan_sk, nm["SK"], sisa_sk, False, plan_rf)
    # INPUT
    y, m, d = int(tgl[:4]), int(tgl[5:7]), int(tgl[8:10])
    bln = f"{BULAN_ID[m - 1]} {y}"
    ws_in["A1"], ws_in["F1"] = "QC TK", "QC SK"
    for col, h in zip("ABCD", ("TGL", "BULAN", "TYPE", "JUMLAH")):
        ws_in[f"{col}2"] = h
    for col, h in zip("FGHI", ("TGL", "BULAN", "TYPE", "JUMLAH")):
        ws_in[f"{col}2"] = h
    for cc in ws_in["A1:I2"]:
        for c in cc:
            c.font = Font(name=F, bold=True)
    for (c0, dept) in (("A", "QC"), ("F", "SK")):
        cols = [chr(ord(c0) + i) for i in range(4)]
        for i, (k, v) in enumerate(sorted(hit[dept].items(), key=lambda kv: (URUTAN.index(kv[0]) if kv[0] in URUTAN else 999, kv[0]))):
            r = 3 + i
            ws_in[f"{cols[0]}{r}"], ws_in[f"{cols[1]}{r}"], ws_in[f"{cols[2]}{r}"], ws_in[f"{cols[3]}{r}"] = d, bln, k, v
            for cc in cols:
                ws_in[f"{cc}{r}"].font = Font(name=F, color="0000FF")
    for col, w in zip("ABCDEFGHI", (7, 15, 16, 10, 3, 7, 15, 16, 10)):
        ws_in.column_dimensions[col].width = w
    # ringkasan TK + SK (seperti H91:J91 di file asli)
    ws_qc["H90"], ws_qc["I90"], ws_qc["J90"] = "TOTAL TK+SK", "SNI", "NON SNI"
    ws_qc["H91"] = "=+B91+'REKAP HITUNG LABEL SK'!B91"
    nom_sni = BARIS_AWAL + nm["QC"].index("SNI")
    nom_sni_sk = BARIS_AWAL + nm["SK"].index("SNI")
    ws_qc["I91"] = f"=+B{nom_sni}+'REKAP HITUNG LABEL SK'!B{nom_sni_sk}"
    ws_qc["J91"] = "=+H91-I91"
    for c in ("H90", "I90", "J90", "H91", "I91", "J91"):
        ws_qc[c].font = Font(name=F, bold=True)
        ws_qc[c].number_format = "#,##0"
    ws_qc["A93"] = (f"Hitungan aktual per {d} {bln}. Rencana produksi: {rencana.nama_bulan(bulan_plan)} (blok QUALITY CONTROL). "
                    + (f"Sisa body: file stok body {int(sisa_info[0][8:10])} {BULAN_ID[int(sisa_info[0][5:7]) - 1]} {sisa_info[0][:4]} {sisa_info[1]} (kolom PERIKSA)."
                     if sisa_info else "Sisa body belum diupload (menu Stok Body di admin); kolom biru bisa diisi manual.") + ("" if plan_qc else " RENCANA BELUM DIUPLOAD untuk bulan ini (menu Rencana Produksi di admin)."))
    ket = []
    for nmx, inf in (("Firstfiring", info_ff), ("Refiring", info_rf)):
        ket.append(f"SK {nmx}: " + (f"{int(inf[0][8:10])} {BULAN_ID[int(inf[0][5:7]) - 1]} {inf[1]}" if inf else "belum diupload"))
    ws_qc["A94"] = "Sisa body SK = " + "; ".join(ket) + ". Rencana SK: FF di kolom E, RF di kolom H."
    ws_qc["A94"].font = Font(name=F, italic=True, size=9)
    ws_qc["A93"].font = Font(name=F, italic=True, size=9)
    return wb


def bytes_rekap(tgl, bulan_plan=None, wb=None):
    buf = io.BytesIO()
    buat(tgl, bulan_plan, wb).save(buf)
    return buf.getvalue()
