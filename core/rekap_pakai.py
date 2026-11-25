"""Laporan bulanan REKAPAN PEMAKAIAN LABEL QC & SK (format file 'REKAPAN PEMAKAIAN LABEL QC DAN SK 2026').
Satu baris per type label. Departemen: QC, SK, atau Gabungan (QC + SK dijumlah).

Kolom (huruf = kolom di Excel bulanan):
 G rencana produksi (QC = blok QC; SK = Firstfiring) · H stok bulan lalu (hitung aktual akhir bulan lalu) · I pengambilan (Input Label Bagus foreman)
 J pcs bagus SAP OP100 · K afkir proses = AA+AB+AC+AD (SAP M, LA, LB, F; hanya CW dan CE9) · L lengket · M kotor · N garis (input afkir foreman)
 O..S afkir pcs SAP per OP (Lokasi OP105 perbaikan, OP110 gerinda, OP115 cek ulang, OP120 TAP & TAD, OP107 setting CR; nilai kolom 'Afkir Total')
 T total rusak = K..S · U % afkir = T/J · X stok sistem = (H+I) - (J+K+L+M+N) · Y stok akhir (hitung aktual akhir bulan)
 AG..AM stok body akhir bulan per OP (file Stok Opname terakhir bulan itu); AF kirim ke packing dikosongkan.
Aturan tetap: baris CE7 = CE7 + semua warna; baris SNI = semua type CW kecuali CW52J (G, J, K, O..S dijumlah dari baris CW)."""
import json
import re
from pathlib import Path

import pandas as pd

from core import data, label, laporan, logic, rencana, sisabody

# (nama tampil di laporan, label internal aplikasi) sesuai urutan file REKAPAN
BARIS = [("CE6", "CE6"), ("CE9", "CE9"), ("CE7", "CE7"), ("PIV", "PIV"), ("HBE", "HBE"), ("BLUE", "B"), ("PB", "PB"), ("DR", "DR"), ("HF", "HF"),
         ("PP", "PP"), ("MA", "MA"), ("CW420J", "CW420J"), ("CW421J", "CW421J"), ("CW422J", "CW422J"), ("CW427J", "CW427J"), ("CW52J", "CW52J"),
         ("CW53J", "CW53J"), ("CW53PJ", "CW53PJ"), ("CW633J", "CW633J"), ("CW637J", "CW637J"), ("L38V1", "L38V1"), ("L521V1A", "L521V1A"),
         ("L521V3", "L521V3"), ("L529V1", "L529V1"), ("L568V3", "L568V3"), ("LW211CJ", "LW211CJ"), ("LW230J", "LW230J"), ("LW236CJ", "LW236CJ"),
         ("LW240CJ", "LW240CJ"), ("LW246J", "LW246J"), ("LW247CJ", "LW247CJ"), ("LW248JT1", "LW248JT1"), ("LW523NJ", "LW523NJ"),
         ("LW540J", "LW540J"), ("LW642CJ", "LW642CJ"), ("LW647CJ", "LW647CJ"), ("S161", "S161N"), ("S163", "S163N"), ("S211", "S211N"),
         ("SW420JP", "SW420IJP"), ("SW422JP", "SW422IJP"), ("SW427JP", "SW427IJP"), ("SW53JP", "SW53IJP"), ("SW633JP", "SW633IJP"),
         ("SW637JP", "SW637IJP"), ("U57M", "U57M")]
NAMA = [n for n, _ in BARIS]
INTERNAL = dict(BARIS)  # nama laporan -> label aplikasi
KE_NAMA = {v: k for k, v in INTERNAL.items()}  # label aplikasi -> nama laporan
WARNA = ["PIV", "HBE", "BLUE", "PB", "DR", "HF", "PP", "MA"]  # baris warna (label tambahan CE7)
KODE_WARNA = {"BLUE": "B"}  # kode di rencana/stok body: CE7#B
CW_SNI = [n for n in NAMA if n.startswith("CW") and n != "CW52J"]  # baris yang dijumlah ke SNI
SNI = "SNI"
OP_AFKIR = {"105": "O", "110": "P", "115": "Q", "120": "R", "107": "S"}
KOLOM_ANGKA = ["G", "H", "I", "J", "L", "M", "N", "O", "P", "Q", "R", "S", "AA", "AB", "AC", "AD", "Y", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"]
OP_BODY = {"AG": "op100", "AH": "op105", "AI": "op110", "AJ": "op115", "AK": "op120", "AL": "op107", "AM": "op166"}
_SAP_PROSES = {"AA": r"^SAP \| Afkir \(M\)", "AB": r"^SAP \| Afkir \(LA\)", "AC": r"^SAP \| Afkir \(LB\)", "AD": r"^SAP \| Afkir \(F\)"}
NAMA_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
RIWAYAT = Path(__file__).resolve().parent.parent / "assets" / "rekap_pakai_riwayat.json"


def bulan_sebelum(b):
    y, m = int(b[:4]), int(b[5:])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def _kosong():
    return pd.DataFrame(0, index=NAMA + [SNI], columns=KOLOM_ANGKA, dtype=float)


def _angka(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


def _kunci_rencana(k):
    return re.sub(r"\s*\([^)]*\)\s*$", "", str(k)).strip()


def _rencana(bulan, dept_kode):
    p = rencana.per_type(bulan, "QC" if dept_kode == "QC" else "SK-FF")
    out = {}
    for k, v in p.items():
        out[_kunci_rencana(k)] = out.get(_kunci_rencana(k), 0) + int(v)
    return out


def _sap(bulan):
    """DataFrame[dept, op, label, bagus, aftot, AA..AD] per baris SAP (Transaction Date = hari kerja)."""
    h = logic.hasil_bulan(bulan)
    kosong = pd.DataFrame(columns=["dept", "op", "label", "bagus", "aftot", "AA", "AB", "AC", "AD"])
    if h.empty:
        return kosong, False
    h = h.copy()
    col_tot = next((c for c in h.columns if re.match(r"^SAP \| Afkir Total", str(c).strip())), None)
    h["dept"] = ["SK" if "QCSK" in str(lk).upper().replace(" ", "") or str(g).upper() == "SK" else "QC" for lk, g in zip(h["lokasi"], h["grup"])]
    h["op"] = h["op"].astype(str).str.strip()
    h["bagus"] = _angka(h["SAP | Total"]) if "SAP | Total" in h.columns else 0
    h["aftot"] = _angka(h[col_tot]) if col_tot else 0
    for k, pola in _SAP_PROSES.items():
        kol = [c for c in h.columns if re.match(pola, str(c).strip())]
        h[k] = _angka(h[kol[0]]) if kol else 0
    warna = h["SAP | Warna"] if "SAP | Warna" in h.columns else ""
    tabel = label.jenis_tabel()
    h["_w"] = warna
    peta = {(t, w): label.label_untuk_sap(t, w, tabel)[0] for t, w in h[["type", "_w"]].drop_duplicates().itertuples(index=False)}
    h["label"] = [peta[(t, w)] for t, w in zip(h["type"], h["_w"])]
    h = h[h["label"] != ""]
    return h[["dept", "op", "label", "bagus", "aftot", "AA", "AB", "AC", "AD"]], col_tot is not None


def _tambah_nama(df, kolom, nama, nilai):
    if nama in df.index and nilai:
        df.loc[nama, kolom] += nilai


def _hitung_aktual(tgl, dept_kode):
    from core import rekap
    return rekap._hitungan(tgl, dept_kode)


def _tgl_hitung(akhir, awal=None):
    """Tanggal hitung aktual (label_hitung) terbaru pada atau sebelum `akhir` (dan >= `awal` bila diberikan); None bila tidak ada."""
    d = data.baca("label_hitung")
    if d.empty:
        return None
    t = sorted({x for x in d["tgl"].astype(str) if x <= akhir and (awal is None or x >= awal)})
    return t[-1] if t else None


def _isi_dept(bulan, dept_kode):
    """DataFrame (baris = NAMA + SNI, kolom = KOLOM_ANGKA) untuk satu departemen + catatan."""
    df, cat = _kosong(), []
    # G rencana
    plan = _rencana(bulan, dept_kode)
    if not plan:
        cat.append(f"Rencana produksi {dept_kode} bulan ini belum diupload.")
    for n in NAMA:
        df.loc[n, "G"] = plan.get(n, 0)
    for n in WARNA:
        df.loc[n, "G"] = plan.get("CE7#" + KODE_WARNA.get(n, n), 0)
    df.loc["CE7", "G"] = plan.get("CE7", 0) + df.loc[WARNA, "G"].sum()
    # H stok bulan lalu / Y stok akhir (hitung aktual)
    sebelum = bulan_sebelum(bulan)
    t_h = _tgl_hitung(sebelum + "-31", sebelum + "-01")
    if t_h:
        for lb, v in _hitung_aktual(t_h, dept_kode).items():
            if lb in KE_NAMA:
                df.loc[KE_NAMA[lb], "H"] = v
            elif lb == SNI:
                df.loc[SNI, "H"] = v
    else:
        cat.append(f"Stok bulan lalu ({NAMA_BULAN[int(sebelum[5:])]}): belum ada hasil hitung aktual akhir bulan.")
    t_y = _tgl_hitung(bulan + "-31", bulan + "-01")
    if t_y:
        for lb, v in _hitung_aktual(t_y, dept_kode).items():
            if lb in KE_NAMA:
                df.loc[KE_NAMA[lb], "Y"] = v
            elif lb == SNI:
                df.loc[SNI, "Y"] = v
    else:
        cat.append("Stok akhir: belum ada hasil hitung aktual di bulan ini.")
    # I pengambilan
    t = data.baca("label_terima")
    if len(t):
        t = t[t["tgl"].astype(str).str[:7] == bulan].copy()
        t["dept"] = t["dept"].replace("", "QC") if "dept" in t.columns else "QC"
        t = t[t["dept"] == dept_kode]
        t["jumlah"] = _angka(t["jumlah"])
        for lb, v in t.groupby("label")["jumlah"].sum().items():
            lb = SNI if label.adalah_sni(lb) else lb
            if lb in KE_NAMA:
                df.loc[KE_NAMA[lb], "I"] += v
            elif lb == SNI:
                df.loc[SNI, "I"] += v
    # L, M, N afkir label (input foreman)
    a = laporan.afkir(bulan)
    if len(a):
        a = a[a["bagian"] == ("QC SK" if dept_kode == "SK" else "QC")]
        for lb, g in a.groupby("label"):
            k = SNI if label.adalah_sni(lb) else KE_NAMA.get(lb)
            if k in df.index:
                df.loc[k, "L"] += g["lengket"].sum()
                df.loc[k, "M"] += g["kotor"].sum()
                df.loc[k, "N"] += g["garis"].sum()
    # J, AA..AD, O..S dari SAP (label berpasangan: warna -> CE7, CW -> SNI)
    s, ada_tot = _sap(bulan)
    if not ada_tot and len(s):
        cat.append("Kolom 'Afkir Total' tidak ditemukan di data SAP: O sampai S kosong.")
    s = s[s["dept"] == dept_kode]
    for r in s.itertuples():
        for lb in laporan.pasangan(r.label):
            k = SNI if lb == label.SNI else KE_NAMA.get(lb)
            if k not in df.index:
                continue
            if r.op == "100":
                df.loc[k, "J"] += r.bagus
                if laporan.proses_berlaku(lb) and lb != label.SNI:
                    for c in ("AA", "AB", "AC", "AD"):
                        df.loc[k, c] += getattr(r, c)
            elif r.op in OP_AFKIR:
                df.loc[k, OP_AFKIR[r.op]] += r.aftot
    # stok body akhir bulan (AG..AM)
    body, info, lengkap = sisabody.akhir_bulan(bulan, dept_kode)
    if not info:
        cat.append(f"Stok body akhir bulan ({dept_kode}) belum diupload.")
    elif not lengkap:
        cat.append(f"Stok body {dept_kode} yang tersimpan hanya kolom PERIKSA: upload ulang file akhir bulan agar OP105–OP166 terbaca.")
    for tp, ops in body.items():
        n = _nama_body(tp)
        for k in n:
            for kol, op in OP_BODY.items():
                df.loc[k, kol] += ops.get(op, 0)
    # SNI dijumlah dari baris CW (kecuali CW52J); CE7 ditambah semua warna
    for kol in ("G", "J", "O", "P", "Q", "R", "S", "AA", "AB", "AC", "AD"):
        df.loc[SNI, kol] = df.loc[CW_SNI, kol].sum()
    for kol in ("J", "O", "P", "Q", "R", "S", "AG", "AH", "AI", "AJ", "AK", "AL", "AM"):
        pass  # J, O..S: warna sudah ikut ke CE7 lewat label berpasangan; stok body: lihat _nama_body
    return df.round().astype(int), cat


def _nama_body(tp):
    """Type stok body -> baris laporan yang ikut bertambah (varian CE7 ikut menambah baris CE7)."""
    t = re.sub(r"\s*\(M\)\s*$", "", str(tp)).strip()
    t = {"SW53IJP": "SW53JP", "SW420IJP": "SW420JP", "SW422IJP": "SW422JP", "SW427IJP": "SW427JP", "SW633IJP": "SW633JP", "SW637IJP": "SW637JP",
         "S161N": "S161", "S163N": "S163", "S211N": "S211"}.get(t, t)
    if t.startswith("CE7#") and t != "CE7#W":
        w = t[4:]
        w = "BLUE" if w == "B" else w
        return [w, "CE7"] if w in WARNA else []
    return [t] if t in NAMA else []


def data_bulan(bulan, dept_pilih):
    """(DataFrame lengkap, catatan). dept_pilih: 'QC' | 'SK' | 'GAB'."""
    if dept_pilih == "GAB":
        a, ca = _isi_dept(bulan, "QC")
        b, cb = _isi_dept(bulan, "SK")
        return a + b, [f"QC: {x}" for x in ca] + [f"SK: {x}" for x in cb]
    return _isi_dept(bulan, dept_pilih)


def hitung(df):
    """Tambah kolom K, T, U, X (rumus laporan)."""
    d = df.copy()
    d["K"] = d[["AA", "AB", "AC", "AD"]].sum(axis=1)
    d["T"] = d[["K", "L", "M", "N", "O", "P", "Q", "R", "S"]].sum(axis=1)
    d["U"] = [t / j if j else 0 for t, j in zip(d["T"], d["J"])]
    d["X"] = (d["H"] + d["I"]) - (d["J"] + d[["K", "L", "M", "N"]].sum(axis=1))
    return d


def total(d):
    """Baris TOTAL = jumlah semua baris type (SNI tidak ikut)."""
    t = d.loc[NAMA].sum()
    t["U"] = t["T"] / t["J"] if t["J"] else 0
    return t


def riwayat():
    """Angka Januari–Oktober dari file REKAPAN lama (gabungan QC + SK): {'2026-01': {baris: {kolom: n}}}."""
    try:
        return json.loads(RIWAYAT.read_text(encoding="utf-8"))
    except Exception:
        return {}
