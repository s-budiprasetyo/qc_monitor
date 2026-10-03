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


def sekarang():
    return datetime.now(WIB).strftime("%H:%M, %d-%m-%Y")


def catat_update(nama_file):
    log = store().read("update_log")
    log = log[log["nama_file"] != nama_file]
    tulis("update_log", pd.concat([log, pd.DataFrame([{"nama_file": nama_file, "waktu": sekarang()}])],
                                  ignore_index=True))


def upsert(nama, baru, kunci, hapus=None):
    """Gabungkan baris baru ke tabel: baris lama dengan kunci yang sama diganti.
    hapus (opsional): DataFrame berisi kolom kunci yang barisnya dihapus dari tabel."""
    lama = store().read(nama)
    if hapus is not None and len(hapus):
        k = set(map(tuple, hapus[kunci].astype(str).values))
        lama = lama[[tuple(r) not in k for r in lama[kunci].astype(str).values]]
    if len(baru):
        k = set(map(tuple, baru[kunci].astype(str).values))
        lama = lama[[tuple(r) not in k for r in lama[kunci].astype(str).values]]
        lama = pd.concat([lama, baru], ignore_index=True)
    tulis(nama, lama)
