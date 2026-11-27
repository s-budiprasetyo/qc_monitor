"""Laporan AFKIR LABEL (pcs): type label x tanggal. Pilihan pabrik dan jenis afkir; klik angka -> siapa yang mengafkirkan."""
import calendar
import io

import pandas as pd
import streamlit as st

from core import akses, laporan, stok
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))

NAMA_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
st.markdown("""
<style>
.block-container{max-width:1240px}
.lp-judul{font-size:2rem;font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.2rem 0 0}
.lp-sub{color:#5b7399;font-size:14px;margin-bottom:.9rem}
@media (max-width:700px){.lp-judul{font-size:1.5rem}}
</style>
""", unsafe_allow_html=True)
st.markdown("<div class='lp-judul'>AFKIR LABEL</div><div class='lp-sub'>Jumlah label yang diafkirkan per type label dan tanggal kerja, dalam pcs. "
            "Klik angka untuk melihat siapa yang mengafkirkan.</div>", unsafe_allow_html=True)

hari = pd.Timestamp.now(tz="Asia/Jakarta")
daftar = [str(b) for b in pd.period_range("2026-11", hari.strftime("%Y-%m"), freq="M")][::-1]
bulan = st.selectbox("Bulan", daftar, format_func=lambda k: f"{NAMA_BULAN[int(k[5:])]} {k[:4]}", key="kt_bln")
PAB = ["Pabrik 1", "Pabrik 2", "SK", "Gabungan"]
pab = st.segmented_control("Pabrik", PAB, default="Gabungan", key="kt_pab", label_visibility="collapsed") or "Gabungan"
JN = {"Label Kotor": "kotor", "Label Lengket": "lengket", "Label Garis": "garis", "Proses": "proses", "Total": "total"}
pil = st.segmented_control("Tampilkan", list(JN), default="Label Kotor", key="kt_jenis", label_visibility="collapsed") or "Label Kotor"
kol = JN[pil]
NJ = {"lengket": "Lengket", "garis": "Garis", "kotor": "Kotor", "proses": "Proses"}


def _f(v):
    return f"{int(v):,}".replace(",", ".")


@st.cache_data(ttl=60, show_spinner=False)
def _muat(b):
    t = laporan.tabel(b)
    if t.empty:
        return t
    peta = stok._peta_meja()
    idx = stok._idx_meja(peta)

    def _p(r):
        lk = stok._meja_operator(peta, idx, r.prn, r.tgl, 3650)
        if lk:
            return stok._lok_pisah(lk)[0]
        return "QC SK" if r.bagian == "QC SK" else ""
    t = t.copy()
    t["pabrik"] = [_p(r) for r in t.itertuples()]
    t["total"] = t[["lengket", "garis", "kotor", "proses"]].sum(axis=1)
    return t[t["total"] > 0]


df = _muat(bulan)
if pab != "Gabungan":
    df = df[df["pabrik"] == ("QC SK" if pab == "SK" else pab)] if len(df) else df
if df.empty or int(df[kol].sum()) == 0:
    st.info("Belum ada afkir untuk pilihan ini.")
    st.stop()
d = df[df[kol] > 0]
jml = calendar.monthrange(int(bulan[:4]), int(bulan[5:]))[1]
tipe = sorted(d["label"].unique(), key=lambda x: (str(x) == "SNI", str(x)))
pv = d.pivot_table(index="label", columns="tgl", values=kol, aggfunc="sum", fill_value=0).reindex(tipe, fill_value=0)
angka = pd.DataFrame({str(i): [int(pv.loc[t].get(f"{bulan}-{i:02d}", 0)) for t in tipe] for i in range(1, jml + 1)}, index=tipe)
angka["TOTAL"] = angka.sum(axis=1)
angka.loc["TOTAL"] = angka.sum()
baris = list(angka.index)
tam = angka.map(lambda v: "" if v == 0 else _f(v))
tam.insert(0, "TYPE", baris)
st.caption("Kolom = tanggal kerja. Angka bisa diklik." + (" Pada tabel Total, rincian menampilkan jenis afkirnya." if kol == "total" else ""))


def _gaya(x):
    g = pd.DataFrame("", index=x.index, columns=x.columns)
    g["TYPE"] = "font-weight:800;color:#0b3d91"
    g["TOTAL"] = "font-weight:800;background-color:#eef4ff"
    g.iloc[-1, :] = "font-weight:800;background-color:#eef4ff"
    return g


ev = st.dataframe(tam.style.apply(_gaya, axis=None), hide_index=True, width="stretch", height=min(48 + 35 * len(tam), 640),
                  on_select="rerun", selection_mode="single-cell", key="kt_grid",
                  column_config={"TYPE": st.column_config.TextColumn("TYPE", pinned=True, width="small"),
                                 **{str(i): st.column_config.TextColumn(str(i), alignment="right", width=52) for i in range(1, jml + 1)},
                                 "TOTAL": st.column_config.TextColumn("TOTAL", alignment="right", width="small")})


@st.dialog("RINCIAN AFKIR LABEL", width="large")
def _rinci(tp, tg):
    sub = d if kol != "total" else df
    judul = f"{tp if tp != 'TOTAL' else 'Semua type'} · " + (f"{tg[8:]}-{tg[5:7]}-{tg[:4]}" if tg else f"{NAMA_BULAN[int(bulan[5:])]} {bulan[:4]}")
    st.markdown(f"<div style='font-size:1.25rem;font-weight:800;color:#0b3d91'>{judul}</div><div style='color:#5b7399'>{pil} · {pab}</div>", unsafe_allow_html=True)
    if tp != "TOTAL":
        sub = sub[sub["label"] == tp]
    if tg:
        sub = sub[sub["tgl"] == tg]
    if kol == "total":
        j = pd.DataFrame({"JENIS AFKIR": [NJ[k] for k in NJ], "PCS": [int(sub[k].sum()) for k in NJ]})
        j = j[j["PCS"] > 0]
        j.loc[len(j)] = ["TOTAL", int(j["PCS"].sum())]
        st.dataframe(j.assign(PCS=j["PCS"].map(_f)), hide_index=True, width="stretch",
                     column_config={"PCS": st.column_config.TextColumn("PCS", alignment="right")})
        st.caption("Untuk melihat nama karyawannya, pilih jenis afkirnya (Label Kotor / Lengket / Garis / Proses).")
        return
    g = sub.groupby(["nama"] + (["label"] if tp == "TOTAL" else []) + (["tgl"] if not tg else []))[kol].sum().reset_index()
    g = g[g[kol] > 0].sort_values(kol, ascending=False)
    g = g.rename(columns={"nama": "KARYAWAN", "label": "TYPE", "tgl": "TANGGAL", kol: "PCS"})
    if "TANGGAL" in g:
        g["TANGGAL"] = g["TANGGAL"].str[8:] + "-" + g["TANGGAL"].str[5:7]
    tot = int(g["PCS"].sum())
    g["PCS"] = g["PCS"].map(_f)
    st.dataframe(g, hide_index=True, width="stretch", height=min(62 + 36 * len(g), 480),
                 column_config={"PCS": st.column_config.TextColumn("PCS", alignment="right", width="small")})
    st.caption(f"Total {_f(tot)} pcs oleh {len(g)} baris karyawan.")


sel = (ev.selection.cells if ev and ev.selection else None) or []
if sel:
    bar, nm = sel[0]
    if nm != "TYPE" and bar is not None and int(bar) < len(baris):
        tp = baris[int(bar)]
        tg = None if nm == "TOTAL" else f"{bulan}-{int(nm):02d}"
        tanda = (bulan, pab, kol, tp, tg)
        if st.session_state.get("kt_buka") != tanda:
            st.session_state["kt_buka"] = tanda
            _rinci(tp, tg)
        elif st.button("🔍 Buka rincian pilihan ini", key="kt_lagi"):
            _rinci(tp, tg)
st.caption(f"{'Jumlah' if kol == 'total' else 'Total ' + pil.lower()}: {_f(d[kol].sum()) if kol != 'total' else _f(df['total'].sum())} pcs. Label SNI dihitung sebagai type tersendiri. "
           "Afkir proses diambil dari SAP bila belum diinput foreman. Karyawan tanpa alamat meja tidak masuk tabel Pabrik 1/2/SK, hanya Gabungan.")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    angka.reset_index().rename(columns={"index": "TYPE", "label": "TYPE"}).to_excel(w, index=False, sheet_name="Afkir label pcs")
st.download_button("⬇ Unduh Excel", buf.getvalue(), file_name=f"afkir_label_{kol}_{pab}_{bulan}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
