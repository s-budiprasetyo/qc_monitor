"""Tabel monitoring yang bisa diklik (kotak persen harian dan kolom RATA RATA)."""
import os
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "tabel"))
_komponen = components.declare_component("tabel_monitor", path=_DIR)


def tabel(html, key="tabel", nama_file="monitoring.png", kal=None, mode="", bulan_label=""):
    """Mengembalikan {k: 'h'|'r', p: prn, d: tanggal, n} saat sel diklik, atau None."""
    return _komponen(html=html, nama_file=nama_file, kal=kal or [], mode=mode, bulan_label=bulan_label, key=key, default=None)
