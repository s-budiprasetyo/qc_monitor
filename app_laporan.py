"""Aplikasi laporan (app ke-3): hanya melihat dan mengunduh Excel. Login admin atau foreman (user/password sama dengan app lain).
Tidak ada input data di sini."""
import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from core import akses, data, laporan
from core.ui import gaya_global

st.set_page_config(page_title="Laporan QC TOTO", page_icon="📊", layout="wide")

CSS = """
<style>
.block-container{max-width:1180px;padding-top:1.6rem}
h1.judul-l{font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.6rem 0 .2rem 0}
.sub-l{color:#5b7399;font-size:14px;margin-bottom:1rem}
table.lp{border-collapse:collapse;width:100%;font-size:13px;background:#fff}
table.lp th{background:#1a5fc8;color:#fff;text-align:center;padding:7px 8px;font-size:12px;border:1px solid #b8c7dd}
table.lp td{padding:6px 8px;border:1px solid #d6e0ef;text-align:right}
table.lp td.t{text-align:left}
table.lp td.m{background:#fde2e2;color:#c00000;font-weight:800}
table.lp tr.sni td{background:#fff7ec}
.sx2{overflow-x:auto}
.st-key-unduh button{background:linear-gradient(135deg,#1a73e8,#0b3d91);color:#fff;border:0;font-weight:800;border-radius:10px;padding:.6rem 1.4rem}
@media (max-width:640px){h1.judul-l{font-size:1.7rem}}
</style>
"""
NAMA_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def _bln(k):
    return f"{NAMA_BULAN[int(k[5:])]} {k[:4]}"


def _pct(x):
    return "-" if pd.isna(x) else f"{x * 100:.2f}%".replace(".", ",")


def _html(df, dengan_tgl):
    kol = (["tgl"] if dengan_tgl else []) + ["nama", "label", "bagus", "lengket", "garis", "kotor", "proses", "afkir",
                                              "%lengket", "%garis", "%kotor", "%proses", "%afkir"]
    judul = {"tgl": "TANGGAL", "nama": "NAMA", "label": "LABEL", "bagus": "PCS BAGUS", "lengket": "LENGKET", "garis": "GARIS",
             "kotor": "KOTOR", "proses": "PROSES", "afkir": "TOTAL AFKIR", "%lengket": "% LENGKET", "%garis": "% GARIS",
             "%kotor": "% KOTOR", "%proses": "% PROSES", "%afkir": "% TOTAL"}
    h = "<div class='sx2'><table class='lp'><tr>" + "".join(f"<th>{judul[c]}</th>" for c in kol) + "</tr>"
    for r in df.to_dict("records"):
        sni = str(r["label"]).startswith("SNI ")
        h += "<tr class='sni'>" if sni else "<tr>"
        for c in kol:
            v = r[c]
            if c in ("tgl", "nama", "label"):
                h += f"<td class='t'>{html.escape(str(v))}</td>"
            elif c.startswith("%"):
                merah = c == "%kotor" and not pd.isna(v) and v > laporan.BATAS_KOTOR
                h += f"<td class='m'>{_pct(v)}</td>" if merah else f"<td>{_pct(v)}</td>"
            else:
                h += f"<td>{int(v):,}</td>".replace(",", ".")
        h += "</tr>"
    return h + "</table></div>"


def halaman():
    akses.butuh(akses.ADMIN, akses.FOREMAN)
    st.markdown(CSS, unsafe_allow_html=True)
    gaya_global()
    akses.bilah()
    st.markdown("<h1 class='judul-l'>LAPORAN % LABEL AFKIR</h1>"
                "<div class='sub-l'>Afkir label (input foreman) ÷ pcs bagus SAP, per karyawan dan label. Hanya lihat dan unduh Excel.</div>",
                unsafe_allow_html=True)
    ada = sorted(set(data.daftar_bulan()), reverse=True)
    if not ada:
        st.info("Belum ada data hasil kerja dari SAP.")
        return
    a, b, c = st.columns([1.4, 1.2, 1.4], vertical_alignment="bottom")
    bulan = a.selectbox("Bulan", ada, format_func=_bln, key="lp_bulan")
    bagian = b.segmented_control("Bagian", ["QC", "QC SK"], default="QC", key="lp_bagian") or "QC"
    mode = c.segmented_control("Laporan", ["Harian", "Bulanan"], default="Harian", key="lp_mode") or "Harian"
    with st.spinner("Menghitung…"):
        df = laporan.tabel(bulan)
    df = df[df["bagian"] == bagian]
    if df.empty:
        st.info(f"Belum ada input label afkir {bagian} untuk {_bln(bulan)}.")
        return
    if mode == "Harian":
        hari = sorted(df["tgl"].unique(), reverse=True)
        tgl = st.selectbox("Tanggal (posting)", hari, key="lp_tgl")
        d = laporan.tambah_persen(df[df["tgl"] == tgl])
        st.markdown(_html(d, False), unsafe_allow_html=True)
        isi = laporan.excel_harian(df[df["tgl"] == tgl], f"{bagian} · {tgl}")
        nama_file = f"label_afkir_{bagian.replace(' ', '')}_{tgl}.xlsx"
    else:
        d = laporan.tambah_persen(laporan.bulanan(df))
        st.markdown(_html(d, False), unsafe_allow_html=True)
        isi = laporan.excel_bulanan(df, f"{bagian} · {_bln(bulan)}")
        nama_file = f"label_afkir_{bagian.replace(' ', '')}_{bulan}.xlsx"
    st.write("")
    with st.container(key="unduh"):
        st.download_button("⬇  UNDUH EXCEL", isi, file_name=nama_file,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Kotor di atas 0,5% berwarna merah. Baris oranye = label SNI (pembagi: pcs bagus label induknya). "
               "Tanda '-' = tidak ada pcs bagus SAP untuk label itu pada hari itu.")


akses.gerbang()
halaman()
