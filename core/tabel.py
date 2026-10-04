"""Tabel monitoring yang bisa diklik (kotak persen harian dan kolom RATA RATA)."""
import os
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "tabel"))
_komponen = components.declare_component("tabel_monitor", path=_DIR)


def tabel(html, key="tabel"):
    """Mengembalikan {k: 'h'|'r', p: prn, d: tanggal, n} saat sel diklik, atau None."""
    return _komponen(html=html, key=key, default=None)
