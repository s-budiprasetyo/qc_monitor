"""Perhitungan persen hasil kerja. Semua aturan hitung ada di sini."""
import pandas as pd

MENIT_KERJA = 480  # 8 jam kerja


def peta_nama(karyawan, alias):
    """nama di SAP -> PRN (alias hasil kalibrasi menambah/menimpa)."""
    m = dict(zip(karyawan["nama_sap"], karyawan["prn"]))
    m.update(dict(zip(alias["nama_sap"], alias["prn"])))
    return m


def hitung_harian(hasil, target, penyesuaian=None):
    """hasil harus punya kolom prn. penyesuaian (opsional): prn, tgl, menit_masalah, jam_lembur.
    persen = jumlah(periksa / target tiap type) / ((480 - menit_masalah + 60 * jam_lembur) / 480) * 100
    Return (harian[prn, tgl, persen], baris_tanpa_target)."""
    t = target.copy()
    t["target"] = pd.to_numeric(t["target"])
    m = hasil.merge(t, on=["grup", "type", "op"], how="left")
    m["periksa"] = pd.to_numeric(m["periksa"])
    tanpa = m[m["target"].isna()]
    ada = m.dropna(subset=["target"]).copy()
    ada["rasio"] = ada["periksa"] / ada["target"]
    h = ada.groupby(["prn", "tgl"], as_index=False)["rasio"].sum()
    h["pembagi"] = 1.0
    if penyesuaian is not None and len(penyesuaian):
        p = penyesuaian.copy()
        for k in ("menit_masalah", "jam_lembur"):
            p[k] = pd.to_numeric(p[k], errors="coerce").fillna(0)
        h = h.merge(p, on=["prn", "tgl"], how="left").fillna({"menit_masalah": 0, "jam_lembur": 0})
        h["pembagi"] = (MENIT_KERJA - h["menit_masalah"] + 60 * h["jam_lembur"]) / MENIT_KERJA
    h["persen"] = h["rasio"] / h["pembagi"] * 100
    return h[["prn", "tgl", "persen"]], tanpa
