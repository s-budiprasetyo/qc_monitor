"""Jembatan Streamlit ke penyimpanan: cache baca, simpan hasil, catatan update."""
import time
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


@st.cache_resource
def _tembolok():
    return {}


TTL = 180  # detik; tulis() menghapus tembolok tabel yang diubah


def baca(nama):
    c, sekarang_ = _tembolok(), time.time()
    if nama in c and sekarang_ - c[nama][0] < TTL:
        return c[nama][1].copy()
    df = store().read(nama)
    c[nama] = (sekarang_, df)
    return df.copy()


def daftar_bulan():
    c, sekarang_ = _tembolok(), time.time()
    if "_bulan" in c and sekarang_ - c["_bulan"][0] < TTL:
        return list(c["_bulan"][1])
    hasil = sorted(t[6:] for t in store().tables() if t.startswith("hasil_"))
    c["_bulan"] = (sekarang_, hasil)
    return list(hasil)


def tulis(nama, df):
    store().write(nama, df)
    c = _tembolok()
    c.pop(nama, None)
    c.pop("_bulan", None)
    c[nama] = (time.time(), df.fillna("").astype(str).reset_index(drop=True))


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


def pakai_google_sheet():
    """True bila penyimpanan memakai Google Sheet (secrets lengkap); False = folder lokal sementara."""
    from core.store import SheetsStore
    return isinstance(store(), SheetsStore)


KOLOM_ALASAN = ["JAM", "TANGGAL POSTING", "EMAIL", "NAMA", "TANGGAL TIDAK TARGET", "ALASAN", "MENIT MASALAH"]


def sinkron_riwayat():
    """Tulis ulang tab 'HASIL KERJA KARYAWAN' di Google Sheet dari seluruh data. Aman dipanggil berulang."""
    from core import logic
    df = logic.laporan_riwayat()
    store().write_laporan("HASIL KERJA KARYAWAN", df)
    catat_update("RIWAYAT GOOGLE SHEET")
    return len(df)


def catat_alasan(email, nama, tgl_tidak_target, alasan, menit=""):
    """Tambah satu baris ke tab 'ALASAN TIDAK TARGET' (jejak, tidak bisa ditimpa)."""
    w = datetime.now(WIB)
    store().tambah_baris("ALASAN TIDAK TARGET", KOLOM_ALASAN,
                         [w.strftime("%H:%M:%S"), w.strftime("%Y-%m-%d"), email, nama, tgl_tidak_target, alasan, menit])
