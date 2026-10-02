"""Isi awal data karyawan dan target ke penyimpanan (jalankan sekali dari komputer sendiri).
Pemakaian: python seed.py DATA_KARYAWAN.xlsx PENCAPAIAN_KERJA_QC.xlsx
File asli jangan dimasukkan ke GitHub; password disimpan sebagai hash."""
import os
import sys
import tomllib
from core import parsers
from core.store import buat_store

if len(sys.argv) != 3:
    sys.exit(__doc__)
rahasia = {}
if os.path.exists(".streamlit/secrets.toml"):
    with open(".streamlit/secrets.toml", "rb") as f:
        rahasia = tomllib.load(f)
s = buat_store(rahasia)
k, t = parsers.baca_karyawan(sys.argv[1]), parsers.baca_target(sys.argv[2])
s.write("karyawan", k)
s.write("target", t)
print(f"Karyawan: {len(k)} baris, target: {len(t)} baris, disimpan ke {type(s).__name__}.")
