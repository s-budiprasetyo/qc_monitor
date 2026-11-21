"""Hub admin: gambar roda gigi + dokumen buatan pengguna, jalur sirkuit menekuk ke tombol-tombol."""
import os
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "hub"))
_komponen = components.declare_component("hub_admin", path=_DIR)


def hub(items, key="hub"):
    """items: [{id,label,icon(data-uri),disabled,badge}] (5 tombol). Mengembalikan {id,n} saat diklik."""
    return _komponen(items=items, key=key, default=None)


_RODA = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "roda"))
_komponen_roda = components.declare_component("roda_admin", path=_RODA)


def roda(items, start=None, key="roda", judul1="UPLOAD", judul2="DATA", hud=False):
    """Roda gigi berputar. items: [{id,label,sub,icon,status_label,status,disabled}]. Mengembalikan {id,n} saat BUKA diklik."""
    return _komponen_roda(items=items, start=start, key=key, judul1=judul1, judul2=judul2, hud=hud, default=None)
