import streamlit as st

from core import akses
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))
st.markdown("<h1 style='color:#0b3d91;font-weight:800'>KOLABORASI LABEL</h1>", unsafe_allow_html=True)
st.info("Laporan gabungan % afkir label dan stok label akan dibuat setelah kedua laporan lain dipakai dan disepakati bentuknya.")
