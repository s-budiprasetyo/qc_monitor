"""Monitoring stok label: stok sistem = stok awal + diterima - pcs bagus - afkir, dibandingkan hitungan aktual foreman."""
import html
from datetime import datetime

import pandas as pd
import streamlit as st

from core import akses, data, stok
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))

st.markdown("""
<style>
.block-container{max-width:1240px}
.lp-judul{font-size:2rem;font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.2rem 0 0}
.lp-sub{color:#5b7399;font-size:14px;margin-bottom:.9rem}
.kpi{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:.4rem 0 1rem}
.kpi div.k{background:#fff;border:1px solid #d6e4f8;border-radius:14px;padding:12px 16px;box-shadow:0 2px 10px #2a5db00f}
.kpi small{display:block;font-size:11.5px;font-weight:800;color:#5b7399;letter-spacing:.6px}
.kpi b{display:block;font-size:22px;color:#0b3d91;margin:2px 0}
.kpi span{font-size:12.5px;color:#7b8fb0}
.peringatan{background:#fff7e0;border:1px solid #f0d88a;border-radius:12px;padding:10px 14px;font-size:13px;color:#6b5200;margin-bottom:.8rem}
@media (max-width:700px){.kpi{grid-template-columns:1fr}.lp-judul{font-size:1.5rem}}
</style>
""", unsafe_allow_html=True)


def _n(x):
    return "" if pd.isna(x) else f"{int(x):,}".replace(",", ".")


hari_ini = datetime.now(data.WIB).date()
st.markdown("<div class='lp-judul'>STOK LABEL</div><div class='lp-sub'>Stok sistem = stok awal + diterima − pcs bagus SAP − label afkir. "
            "Hitungan aktual dan penerimaan diinput foreman di halaman Foreman → Input Label.</div>", unsafe_allow_html=True)
c1, c2 = st.columns([1.3, 2.7], vertical_alignment="bottom")
tgl = c1.date_input("Stok per tanggal (akhir hari)", value=hari_ini, min_value=datetime.strptime(stok.MULAI, "%Y-%m-%d").date(),
                    max_value=hari_ini, format="DD/MM/YYYY", key="st_tgl")
with st.spinner("Menghitung stok…"):
    d = stok.stok_laporan(tgl.strftime("%Y-%m-%d"))
d = d[(d[["awal", "diterima", "bagus", "afkir"]].abs().sum(axis=1) > 0) | d["aktual"].notna()].reset_index(drop=True)
if d.empty:
    st.info("Belum ada penerimaan, pemakaian, atau hitungan label.")
    st.stop()
if not (d["tgl_awal"] != "").any():
    st.markdown("<div class='peringatan'>⚠ Stok awal belum diinput (dianggap 0 sejak "
                f"{stok.MULAI[8:]}-{stok.MULAI[5:7]}-{stok.MULAI[:4]}), jadi stok sistem bisa minus. "
                "Foreman: Input Label → Stok Label → hitung, Simpan, Lihat Selisih, lalu ADJUST.</div>", unsafe_allow_html=True)
minus = int((d["sistem"] < 0).sum())
sel = d[d["aktual"].notna()]
terakhir = sel["tgl_hitung"].max() if len(sel) else ""
st.markdown(f"<div class='kpi'><div class='k'><small>LABEL AKTIF</small><b>{len(d)}</b><span>ada pergerakan atau hitungan</span></div>"
            f"<div class='k'><small>STOK SISTEM MINUS</small><b style='color:{'#b3261e' if minus else '#1d6f2f'}'>{minus}</b><span>label</span></div>"
            f"<div class='k'><small>HITUNGAN TERAKHIR</small><b>{(terakhir[8:] + '-' + terakhir[5:7]) if terakhir else '-'}</b><span>{len(sel)} label pernah dihitung</span></div></div>",
            unsafe_allow_html=True)

tampil = pd.DataFrame({
    "Label": d["label"], "Stok awal": d["awal"], "Diterima": d["diterima"], "Pcs bagus": d["bagus"], "Afkir": d["afkir"],
    "Stok sistem": d["sistem"], "Aktual (hitung)": d["aktual"],
    "Tgl hitung": d["tgl_hitung"].map(lambda t: f"{t[8:]}-{t[5:7]}" if t else ""),
    "Selisih": d["sel_hitung"]})


def _fmt(v, tanda=False):
    if pd.isna(v):
        return ""
    t = f"{int(v):+,}" if tanda else f"{int(v):,}"
    return t.replace(",", ".")


_num = tampil.copy()
for k in ["Stok awal", "Diterima", "Pcs bagus", "Afkir", "Stok sistem", "Aktual (hitung)"]:
    tampil[k] = _num[k].map(_fmt)
tampil["Selisih"] = _num["Selisih"].map(lambda v: _fmt(v, True))


def _warna(col):
    if col.name == "Stok sistem":
        return ["color:#b3261e;font-weight:800" if v < 0 else "font-weight:800;color:#0b3d91" for v in _num["Stok sistem"]]
    if col.name == "Selisih":
        return ["" if pd.isna(v) or v == 0 else ("color:#b3261e;font-weight:700" if v < 0 else "color:#1d6f2f;font-weight:700") for v in _num["Selisih"]]
    return [""] * len(col)


st.dataframe(tampil.style.apply(_warna), hide_index=True, width="stretch", height=min(80 + 36 * len(tampil), 680),
             column_config={k: st.column_config.TextColumn(k, alignment="right") for k in
                            ["Stok awal", "Diterima", "Pcs bagus", "Afkir", "Stok sistem", "Aktual (hitung)", "Selisih"]})
st.caption("Selisih = aktual − stok sistem saat label itu dihitung. Label yang di-ADJUST memakai angka aktual sebagai stok awal baru.")
st.download_button("⬇ Unduh Excel", stok.excel_stok(d.assign(aktual=d["aktual"]).rename(columns={}), tgl.strftime("%d-%m-%Y")),
                   file_name=f"stok_label_{tgl.strftime('%Y-%m-%d')}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
