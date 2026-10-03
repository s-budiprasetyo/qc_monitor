"""Jembatan Streamlit ke penyimpanan: cache baca, simpan hasil, catatan update."""
from datetime import datetime, timedelta, timezone
import pandas as pd
import streamlit as st
from core.store import buat_store

WIB = timezone(timedelta(hours=7))


@st.cache_resource
def store():
    try:
        rahasia = dict(st.secrets)
    except Exception:
        rahasia = {}
    return buat_store(rahasia)


@st.cache_data(ttl=60, show_spinner=False)
def baca(nama):
    return store().read(nama)


@st.cache_data(ttl=60, show_spinner=False)
def daftar_bulan():
    return sorted(t[6:] for t in store().tables() if t.startswith("hasil_"))


def tulis(nama, df):
    store().write(nama, df)
    baca.clear()
    daftar_bulan.clear()


def simpan_hasil(df):
    """Simpan per bulan Posting Date. Tanggal yang sama ditimpa, tanggal lain tetap aman."""
    df = df.assign(bulan=df["tgl"].str[:7])
    for bulan, bagian in df.groupby("bulan"):
        nama = f"hasil_{bulan}"
        lama = store().read(nama)
        lama = lama[~lama["tgl"].isin(set(bagian["tgl"]))]
        baru = pd.concat([lama, bagian.drop(columns="bulan")], ignore_index=True)
        tulis(nama, baru.sort_values(["tgl", "nama_sap"]))


def catat_update(nama_file):
    log = store().read("update_log")
    log = log[log["nama_file"] != nama_file]
    sekarang = datetime.now(WIB).strftime("%H:%M, %d-%m-%Y")
    tulis("update_log", pd.concat([log, pd.DataFrame([{"nama_file": nama_file, "waktu": sekarang}])],
                                  ignore_index=True))
