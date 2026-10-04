"""Pemilih bulan gaya gulir (roda): bulan dan tahun digulir atas-bawah, lalu tombol OK."""
import os
from datetime import date

import streamlit as st
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "bulan"))
_komponen = components.declare_component("pemilih_bulan", path=_DIR)
_BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
          "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]


def pilih_bulan(kunci, awal=None, tersedia=None, judul="BULAN"):
    """Tombol berisi bulan terpilih; diklik membuka roda bulan/tahun. Return 'YYYY-MM'.
    tersedia: daftar 'YYYY-MM' yang boleh dipilih (None = bebas, tahun sekitar hari ini)."""
    sk = f"pb_{kunci}"
    if sk not in st.session_state:
        st.session_state[sk] = awal or (tersedia[-1] if tersedia else date.today().strftime("%Y-%m"))
    cur = st.session_state[sk]
    if tersedia:
        tahun = sorted({t[:4] for t in tersedia} | {cur[:4]})
    else:
        y = date.today().year
        tahun = [str(i) for i in range(y - 3, y + 2)]
    st.caption(judul)
    with st.popover(f"{_BULAN[int(cur[5:]) - 1]} {cur[:4]}  ▾", width="stretch"):
        r = _komponen(nilai=cur, tersedia=tersedia, tahun=tahun, key=f"cmp_{kunci}", default=None)
        if r and r.get("n") != st.session_state.get(f"{sk}_n"):
            st.session_state[f"{sk}_n"] = r["n"]
            if r["v"] != cur:
                st.session_state[sk] = r["v"]
                st.rerun(scope="fragment" if st.session_state.get("_frag_" + kunci) else "app")
    return st.session_state[sk]
