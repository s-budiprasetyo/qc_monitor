"""Hub admin: gambar roda gigi + dokumen buatan pengguna, jalur sirkuit menekuk ke tombol-tombol."""
import os
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "hub"))
_komponen = components.declare_component("hub_admin", path=_DIR)


def hub(items, key="hub"):
    """items: [{id,label,icon(data-uri),disabled,badge}] (5 tombol). Mengembalikan {id,n} saat diklik."""
    return _komponen(items=items, key=key, default=None)
