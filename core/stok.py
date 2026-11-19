"""Stok label. Per label (semua pabrik digabung).

stok sistem (akhir hari D) = stok awal + diterima - pemakaian, dengan
  pemakaian harian = pcs bagus SAP + label afkir (label SNI: pcs bagus type induknya + afkir SNI-nya).
Stok awal per label = hasil hitung terakhir yang di-ADJUST (aktual, akhir hari hitung); belum ada = 0 dan
perhitungan mulai dari MULAI. Pergerakan dihitung setelah hari adjust (tanggal > hari adjust)."""
from datetime import datetime

import pandas as pd

from core import data, label, laporan

import os
MULAI = os.environ.get("QC_MULAI_STOK", "2026-11-01")   # stok awal 0 mulai tanggal ini (sampai ada hasil hitung yang di-adjust)


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


# ---------------------------------------------------------------- terima
def terima_simpan(tgl, baris, oleh):
    """baris = [(label, jumlah)]. Satu baris per input."""
    waktu = datetime.now(data.WIB).strftime("%H:%M:%S")
    d = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb, "jumlah": int(n), "oleh": oleh} for lb, n in baris if lb and _int(n) > 0],
                    columns=["tgl", "waktu", "label", "jumlah", "oleh"])
    if len(d):
        # waktu dibuat unik per baris supaya kunci tidak bentrok
        d["waktu"] = [f"{waktu}.{i}" for i in range(len(d))]
        data.upsert("label_terima", d, ["tgl", "waktu", "label"])
        data.catat_update("STOK LABEL")
    return len(d)


def terima_hapus(tgl, waktu, lb):
    h = pd.DataFrame([{"tgl": tgl, "waktu": waktu, "label": lb}])
    data.upsert("label_terima", pd.DataFrame(columns=["tgl", "waktu", "label", "jumlah", "oleh"]), ["tgl", "waktu", "label"], hapus=h)


def terima_daftar(bulan=None):
    d = data.baca("label_terima")
    if d.empty:
        return d
    d = d.copy()
    d["jumlah"] = d["jumlah"].map(_int)
    if bulan:
        d = d[d["tgl"].astype(str).str[:7] == bulan]
    return d.sort_values(["tgl", "waktu"], ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- hitung aktual
def hitung_simpan(tgl, baris, oleh, adjust=False):
    """baris = [(label, aktual, sistem)]. adjust=True: aktual jadi stok awal baru label itu."""
    waktu = datetime.now(data.WIB).strftime("%H:%M:%S")
    d = pd.DataFrame([{"tgl": tgl, "waktu": f"{waktu}.{i}", "label": lb, "aktual": int(a), "sistem": int(sx),
                       "adjust": "ya" if adjust else "", "oleh": oleh} for i, (lb, a, sx) in enumerate(baris) if lb],
                    columns=["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh"])
    if len(d):
        data.upsert("label_hitung", d, ["tgl", "waktu", "label"])
        data.catat_update("STOK LABEL")
    return len(d)


def hitung_terakhir(tgl=None):
    """Hasil hitung terbaru per label (yang bertanggal tgl bila diberikan, selain itu seluruhnya)."""
    d = data.baca("label_hitung")
    if d.empty:
        return pd.DataFrame(columns=["tgl", "waktu", "label", "aktual", "sistem", "adjust", "oleh"])
    d = d.copy()
    d["aktual"] = d["aktual"].map(_int)
    d["sistem"] = d["sistem"].map(_int)
    if tgl:
        d = d[d["tgl"] == tgl]
    return d.sort_values(["tgl", "waktu"]).drop_duplicates("label", keep="last").reset_index(drop=True)


# ---------------------------------------------------------------- hitung stok sistem
def _pergerakan(sampai):
    """DataFrames harian: bagus[label,tgl,n], afkir[label,tgl,n] dari MULAI s/d sampai (tanggal posting)."""
    bulan = pd.period_range(MULAI[:7], sampai[:7], freq="M")
    bag = []
    for b in bulan:
        pb = laporan.pcs_bagus(str(b))
        if len(pb):
            bag.append(pb.groupby(["label", "tgl"], as_index=False)[["bagus", "proses"]].sum())
    bagus = pd.concat(bag, ignore_index=True) if bag else pd.DataFrame(columns=["label", "tgl", "bagus"])
    pro = bagus.groupby(["label", "tgl"], as_index=False)["proses"].sum().rename(columns={"proses": "n"}) if "proses" in bagus.columns else None
    bagus = bagus.drop(columns=["proses"], errors="ignore")
    if pro is not None and len(pro):  # label SNI pendamping: Proses sama dengan type induknya
        pro = pd.concat([pro] + [pro[pro["label"] == lb].assign(label=label.nama_sni(lb)) for lb in set(pro["label"]) if label.punya_sni(lb)], ignore_index=True)
    # pcs bagus label SNI = pcs bagus type induknya
    sni = [(lb, label.nama_sni(lb)) for lb in set(bagus["label"]) if label.punya_sni(lb)]
    tambahan = [bagus[bagus["label"] == lb].assign(label=ns) for lb, ns in sni]
    bagus = pd.concat([bagus] + tambahan, ignore_index=True) if tambahan else bagus
    a = data.baca("label_afkir")
    if len(a):
        a = a.copy()
        for c in ("lengket", "garis", "kotor", "proses"):
            a[c] = pd.to_numeric(a[c] if c in a.columns else 0, errors="coerce").fillna(0)
        # Proses type closet CW otomatis dari SAP (di bawah); input manual hanya dipakai untuk type lain
        a["n"] = a["lengket"] + a["garis"] + a["kotor"] + a["proses"].where(~a["type"].map(laporan.proses_berlaku), 0)
        afkir = a.groupby(["type", "tgl_posting"], as_index=False)["n"].sum().rename(columns={"type": "label", "tgl_posting": "tgl"})
    else:
        afkir = pd.DataFrame(columns=["label", "tgl", "n"])
    if pro is not None and len(pro):
        afkir = pd.concat([afkir, pro[pro["n"] > 0]], ignore_index=True).groupby(["label", "tgl"], as_index=False)["n"].sum()
    return bagus, afkir


def stok_sistem(sampai=None):
    """DataFrame[label, awal, diterima, bagus, afkir, sistem, tgl_awal]; sampai = 'YYYY-MM-DD' (default hari ini)."""
    sampai = sampai or datetime.now(data.WIB).strftime("%Y-%m-%d")
    bagus, afkir = _pergerakan(sampai)
    ter = terima_daftar()
    h = data.baca("label_hitung")
    adj = {}
    if len(h):
        h = h[h["adjust"] == "ya"].copy()
        h["aktual"] = h["aktual"].map(_int)
        for r in h.sort_values(["tgl", "waktu"]).itertuples():
            adj[r.label] = (r.tgl, r.aktual)
    baris = []
    for lb in semua_label():
        tgl0, awal = adj.get(lb, (None, 0))

        def jml(df, kol):
            if df.empty or lb not in set(df["label"]):
                return 0
            x = df[(df["label"] == lb) & (df["tgl"] <= sampai) & (df["tgl"] >= MULAI)]
            if tgl0:
                x = x[x["tgl"] > tgl0]
            return int(pd.to_numeric(x[kol], errors="coerce").fillna(0).sum())
        t_, b_, a_ = jml(ter, "jumlah"), jml(bagus, "bagus"), jml(afkir, "n")
        baris.append({"label": lb, "awal": awal, "diterima": t_, "bagus": b_, "afkir": a_, "sistem": awal + t_ - b_ - a_, "tgl_awal": tgl0 or ""})
    return pd.DataFrame(baris)


def excel_stok(df, sampai):
    """Excel stok: kolom Stok sistem berupa rumus = awal + diterima - bagus - afkir."""
    import io

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    wb = Workbook()
    ws = wb.active
    ws.title = "Stok label"
    ws["A1"] = f"MONITORING STOK LABEL — per {sampai}"
    ws["A1"].font = Font(name="Arial", bold=True, size=13, color="0B3D91")
    ws["A2"] = "Stok sistem = stok awal + diterima − pcs bagus SAP − label afkir. Stok awal 0 sampai ada hitungan yang di-adjust."
    ws["A2"].font = Font(name="Arial", italic=True, size=9, color="5B7399")
    judul = ["LABEL", "STOK AWAL", "DITERIMA", "PCS BAGUS (SAP)", "AFKIR", "STOK SISTEM", "HITUNG AKTUAL", "TGL HITUNG", "SELISIH"]
    sisi = Side(style="thin", color="B8C7DD")
    gar = Border(left=sisi, right=sisi, top=sisi, bottom=sisi)
    for i, t in enumerate(judul, 1):
        c = ws.cell(4, i, t)
        c.font = Font(name="Arial", bold=True, color="FFFFFF", size=10)
        c.fill = PatternFill("solid", fgColor="1A5FC8")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = gar
    for r, x in enumerate(df.itertuples(), 5):
        vals = [x.label, x.awal, x.diterima, x.bagus, x.afkir, f"=B{r}+C{r}-D{r}-E{r}",
                x.aktual if x.tgl_hitung else None, x.tgl_hitung or None, f'=IF(G{r}="","",G{r}-F{r})' if x.tgl_hitung else None]
        for i, v in enumerate(vals, 1):
            c = ws.cell(r, i, v)
            c.font = Font(name="Arial", size=10)
            c.border = gar
            if 2 <= i <= 7 or i == 9:
                c.number_format = "#,##0;[Red]-#,##0"
    ws.freeze_panes = "B5"
    ws.column_dimensions["A"].width = 18
    for col in "BCDEFGHI":
        ws.column_dimensions[col].width = 16
    ws.row_dimensions[4].height = 32
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def stok_laporan(sampai=None):
    """stok_sistem + hitungan terakhir per label (aktual, tgl_hitung, sel_hitung = aktual - sistem saat dihitung)."""
    d = stok_sistem(sampai)
    h = hitung_terakhir()
    if len(h):
        ak = {r.label: (r.aktual, r.tgl, r.aktual - r.sistem) for r in h.itertuples()}
    else:
        ak = {}
    d["aktual"] = [ak.get(lb, (None, "", None))[0] for lb in d["label"]]
    d["tgl_hitung"] = [ak.get(lb, (None, "", None))[1] for lb in d["label"]]
    d["sel_hitung"] = [ak.get(lb, (None, "", None))[2] for lb in d["label"]]
    return d
