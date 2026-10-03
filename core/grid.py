"""Komponen grid O/X untuk Setting Manual Jadwal Kerja (klik sel untuk mengganti masuk/libur)."""
import os
import streamlit.components.v1 as components

_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "grid")
_komponen = components.declare_component("jadwal_grid", path=os.path.normpath(_DIR))


def jadwal_grid(rows, state, days, weekend, reset_token, key):
    """rows: [{id, nama}], state: {id: 'OOXX...'}. Mengembalikan state terbaru (dict) setelah ada klik,
    atau None bila belum ada perubahan."""
    return _komponen(rows=rows, state=state, days=days, weekend=weekend,
                     reset_token=reset_token, key=key, default=None)
