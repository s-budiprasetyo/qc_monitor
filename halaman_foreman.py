"""Halaman Upload Foreman. Tahap 1: kerangka. Tahap 2 menambahkan jendela Monitoring Label dan notifikasi meja."""
import streamlit as st

from core import akses
from core.ui import gaya_global

CSS = """
<style>
.block-container{max-width:1180px;padding-top:1.6rem}
h1.judul-f{font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.6rem 0 1rem 0}
.kartu-f{background:#fff;border:1px solid #dde3ec;border-radius:14px;padding:16px 18px;margin-bottom:14px}
.btn-label{display:inline-flex;align-items:center;gap:10px;background:linear-gradient(135deg,#1a73e8,#0b3d91);color:#fff;
  font-weight:700;padding:14px 22px;border-radius:12px;font-size:15px;opacity:.55;cursor:not-allowed}
.btn-label svg{width:22px;height:22px;stroke:#fff;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
</style>
"""
IKON_LABEL = ('<svg viewBox="0 0 24 24"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/>'
              '<circle cx="7.5" cy="7.5" r="1.3"/></svg>')


def tampil(halaman_admin=None):
    akses.butuh(akses.ADMIN, akses.FOREMAN)
    st.markdown(CSS, unsafe_allow_html=True)
    gaya_global()
    akses.bilah(halaman_admin, "Ke halaman Admin")
    st.markdown("<h1 class='judul-f'>UPLOAD FOREMAN</h1>", unsafe_allow_html=True)
    st.markdown(f"<div class='kartu-f'><span class='btn-label'>{IKON_LABEL}MONITORING LABEL</span>"
                "<p style='margin:.7rem 0 0;color:#5b7399;font-size:13px'>Segera tersedia: input label afkir dan notifikasi meja "
                "yang belum dicek.</p></div>", unsafe_allow_html=True)
