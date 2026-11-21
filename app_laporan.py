"""Aplikasi laporan (app ke-3): hanya melihat dan mengunduh Excel. Login admin atau foreman (user/password sama dengan app lain).
Menu grup LABEL: % Afkir Label, Afkir Kotor (pcs), Stok Label, Kolaborasi (segera). Tidak ada input data di sini."""
import streamlit as st

from core import akses

st.set_page_config(page_title="Laporan QC TOTO", page_icon="📊", layout="wide")

akses.gerbang()

halaman = st.navigation(
    {"LABEL": [
        st.Page("halaman_lap_afkir.py", title="% Afkir Label", icon=":material/percent:", url_path="afkir", default=True),
        st.Page("halaman_lap_kotor.py", title="Afkir Kotor (pcs)", icon=":material/delete_sweep:", url_path="kotor"),
        st.Page("halaman_lap_stok.py", title="Stok Label", icon=":material/inventory_2:", url_path="stok"),
        st.Page("halaman_lap_kolab.py", title="Kolaborasi", icon=":material/join_inner:", url_path="kolaborasi"),
    ]},
    position="top",
)
halaman.run()
