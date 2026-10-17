"""Grafik spiral/histogram pencapaian (khusus admin): bagian grafik bisa diklik."""
import os
import streamlit.components.v1 as components

_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "components", "grafik"))
_komponen = components.declare_component("grafik_pencapaian", path=_DIR)

KELAS = [("<60%", "<60%", None, 60, "#d73027"), ("60–<70%", "60-70", 60, 70, "#fc8d59"), ("70–<80%", "70-80", 70, 80, "#fee08b"),
         ("80–<90%", "80-90", 80, 90, "#e0f09a"), ("90–<100%", "90-100", 90, 100, "#91cf60"), ("≥100%", "≥100%", 100, None, "#1a9850")]


def kelas_anggota(pasangan):
    """pasangan: [(idx, nama, nilai)] -> 6 daftar anggota per kelas (dipilah dengan nilai asli, bukan pembulatan)."""
    hasil = [[] for _ in KELAS]
    for p in pasangan:
        v = p[2]
        for i, (_, _, lo, hi, _) in enumerate(KELAS):
            if (lo is None or v >= lo) and (hi is None or v < hi):
                hasil[i].append(p)
                break
    return hasil


def data_grafik(pasangan, judul, sub):
    anggota = kelas_anggota(pasangan)
    return {"judul": judul, "sub": sub, "kelas": [
        {"label": k[0], "sing": k[1], "warna": k[4], "jumlah": len(a)} for k, a in zip(KELAS, anggota)]}


def grafik(harian, bulanan, key="grafik"):
    return _komponen(harian=harian, bulanan=bulanan, key=key, default=None)
