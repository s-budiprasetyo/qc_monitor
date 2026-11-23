"""Laporan label afkir KOTOR dalam pcs: karyawan x type label (bukan persen). Untuk monitoring atasan."""
import calendar
import io

import pandas as pd
import streamlit as st

from core import akses, laporan
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
st.markdown("<div class='lp-judul'>AFKIR LABEL KOTOR (PCS)</div><div class='lp-sub'>Jumlah label kotor yang diafkirkan tiap karyawan per type label, "
            "dalam pcs (bukan persen). Berdasarkan Tanggal Posting.</div>", unsafe_allow_html=True)

hari = pd.Timestamp.now(tz="Asia/Jakarta")
bulan_ini = hari.strftime("%Y-%m")
daftar = [str(b) for b in pd.period_range("2026-11", bulan_ini, freq="M")][::-1]
c1, c2 = st.columns([1.4, 2], vertical_alignment="bottom")
bulan = c1.selectbox("Bulan", daftar, format_func=lambda k: f"{NAMA_BULAN[int(k[5:])]} {k[:4]}", key="kt_bln")
bag = c2.segmented_control("Bagian", ["QC", "SK", "Gabungan QC + SK"], default="QC", key="kt_bag", label_visibility="collapsed") or "QC"


@st.cache_data(ttl=60, show_spinner=False)
def _muat(b):
    return laporan.afkir(b)


df = _muat(bulan)
if bag != "Gabungan QC + SK":
    df = df[df["bagian"] == ("QC SK" if bag == "SK" else "QC")]
th, bl = int(bulan[:4]), int(bulan[5:])
akhir = calendar.monthrange(th, bl)[1]
tg = st.date_input("Rentang tanggal posting", value=(pd.Timestamp(f"{bulan}-01").date(), pd.Timestamp(f"{bulan}-{akhir:02d}").date()),
                   min_value=pd.Timestamp(f"{bulan}-01").date(), max_value=pd.Timestamp(f"{bulan}-{akhir:02d}").date(), format="DD/MM/YYYY", key="kt_tgl")
if isinstance(tg, (tuple, list)) and len(tg) == 2:
    df = df[(df["tgl"] >= tg[0].strftime("%Y-%m-%d")) & (df["tgl"] <= tg[1].strftime("%Y-%m-%d"))]
if df.empty or int(df["kotor"].sum()) == 0:
    st.info("Belum ada label kotor yang diafkirkan pada periode ini.")
    st.stop()
mode = st.segmented_control("Tampilan", ["Karyawan × Type", "Per karyawan (total)", "Per type (total)"], default="Karyawan × Type", key="kt_mode", label_visibility="collapsed") or "Karyawan × Type"
d = df[df["kotor"] > 0]


def _f(v):
    return f"{int(v):,}".replace(",", ".")


if mode == "Karyawan × Type":
    pv = d.pivot_table(index="nama", columns="label", values="kotor", aggfunc="sum", fill_value=0)
    pv = pv[sorted(pv.columns, key=lambda x: (str(x) == "SNI", str(x)))]
    pv["TOTAL"] = pv.sum(axis=1)
    pv = pv.sort_values("TOTAL", ascending=False)
    pv.loc["TOTAL"] = pv.sum()
    tam = pv.map(lambda v: "" if v == 0 else _f(v))
    st.dataframe(tam, width="stretch", height=min(45 + 36 * len(tam), 700),
                 column_config={c: st.column_config.TextColumn(c, alignment="right") for c in tam.columns})
    hasil = pv.reset_index().rename(columns={"nama": "KARYAWAN"})
elif mode == "Per karyawan (total)":
    g = d.groupby("nama")["kotor"].sum().sort_values(ascending=False).reset_index()
    g.columns = ["KARYAWAN", "LABEL KOTOR (PCS)"]
    st.dataframe(g.assign(**{"LABEL KOTOR (PCS)": g["LABEL KOTOR (PCS)"].map(_f)}), hide_index=True, width="stretch",
                 column_config={"LABEL KOTOR (PCS)": st.column_config.TextColumn("LABEL KOTOR (PCS)", alignment="right")})
    hasil = g
else:
    g = d.groupby("label")["kotor"].sum().sort_values(ascending=False).reset_index()
    g.columns = ["TYPE LABEL", "LABEL KOTOR (PCS)"]
    st.dataframe(g.assign(**{"LABEL KOTOR (PCS)": g["LABEL KOTOR (PCS)"].map(_f)}), hide_index=True, width="stretch",
                 column_config={"LABEL KOTOR (PCS)": st.column_config.TextColumn("LABEL KOTOR (PCS)", alignment="right")})
    hasil = g
st.caption(f"Total label kotor diafkirkan: {_f(d['kotor'].sum())} pcs. Label SNI dihitung sebagai type tersendiri.")
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine="openpyxl") as w:
    hasil.to_excel(w, index=False, sheet_name="Afkir kotor pcs")
st.download_button("⬇ Unduh Excel", buf.getvalue(), file_name=f"afkir_kotor_pcs_{bag[:3].strip()}_{bulan}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
