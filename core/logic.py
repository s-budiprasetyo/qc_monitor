"""Logika bulanan: karyawan yang tampil, status tiap hari, persen, rata-rata, dan pemeriksaan masalah."""
import calendar
import pandas as pd
from core import calc, data

KODE_ABSEN = {"Sakit": "S", "Ijin": "I", "Cuti": "CT", "Dispen": "D", "Resign": "R"}
NAMA_ABSEN = {v: k for k, v in KODE_ABSEN.items()}
OP_TANPA_TARGET = "107"  # memang tidak punya target: jadi catatan otomatis, bukan peringatan


def n_hari(bulan):
    return calendar.monthrange(int(bulan[:4]), int(bulan[5:]))[1]


def hari_libur_default(bulan):
    """Jadwal normal: Sabtu dan Minggu libur."""
    th, bl = int(bulan[:4]), int(bulan[5:])
    return {d: calendar.weekday(th, bl, d) >= 5 for d in range(1, n_hari(bulan) + 1)}


def peta_nama_prn():
    k = data.baca("karyawan")
    return dict(zip(k["prn"], k["nama_web"]))


def karyawan_sap(sampai_bulan=None):
    """PRN yang pernah muncul di file SAP (sesuai pemetaan nama)."""
    k, a = data.baca("karyawan"), data.baca("alias")
    peta = calc.peta_nama(k, a)
    hasil = set()
    for b in data.daftar_bulan():
        if sampai_bulan and b > sampai_bulan:
            continue
        h = data.baca(f"hasil_{b}")
        hasil |= {peta[n] for n in h["nama_sap"].unique() if n in peta}
    return hasil


def karyawan_dikenal(sampai_bulan=None):
    """Daftar pantau: karyawan yang sudah diverifikasi admin (status 'ya').
    Bila admin belum pernah verifikasi sama sekali, dipakai karyawan yang ada di file SAP."""
    r = data.baca("roster")
    nama = peta_nama_prn()
    hasil = set(r.loc[r["status"] == "ya", "prn"])
    if not hasil:  # belum diverifikasi (atau semua tersilang): jangan kosongkan daftar
        hasil = karyawan_sap(sampai_bulan) or set(data.baca("karyawan")["prn"])
    return sorted(hasil, key=lambda p: nama.get(p, p))


def prn_admin():
    """PRN milik admin (user di secrets cocok dengan user di data karyawan), supaya tidak tersilang otomatis."""
    try:
        import streamlit as st
        u = str(st.secrets["admin"]["user"]).lower()
    except Exception:
        return None
    k = data.baca("karyawan")
    cocok = k[k["user"].str.lower() == u]
    return cocok["prn"].iloc[0] if len(cocok) else None


def belum_diverifikasi():
    """PRN di data karyawan yang belum pernah diputuskan (belum ada di roster)."""
    k, r = data.baca("karyawan"), data.baca("roster")
    return [p for p in k["prn"] if p not in set(r["prn"])]


def usulan_verifikasi():
    """DataFrame usulan awal untuk dialog: prn, nama, ada_sap, ada_jadwal, silang (usulan)."""
    k, r = data.baca("karyawan"), data.baca("roster")
    putus = dict(zip(r["prn"], r["status"]))
    sap = karyawan_sap()
    ada_jadwal = set()
    for t in data.store().tables():
        if t.startswith("jadwal_"):
            ada_jadwal |= set(data.baca(t)["prn"])
    adm = prn_admin()
    baris = []
    for p, n in zip(k["prn"], k["nama_web"]):
        if p in putus:
            silang = putus[p] == "tidak"
        else:  # usulan awal: silang bila tidak ada di SAP (admin sendiri tidak disilang)
            silang = False  # semua ikut tampil; admin hanya mencentang ✕ pada yang tidak boleh
        baris.append({"prn": p, "nama": n, "ada_sap": p in sap, "ada_jadwal": p in ada_jadwal,
                      "baru": p not in putus, "silang": silang})
    return pd.DataFrame(baris).sort_values(["baru", "ada_sap", "nama"], ascending=[False, True, True]).reset_index(drop=True)


def catatan_otomatis(bulan):
    """Catatan otomatis dari operation yang memang tanpa target (OP107): tiap orang per hari.
    Return list dict(prn, nama, tgl, teks)."""
    k, a = data.baca("karyawan"), data.baca("alias")
    peta = calc.peta_nama(k, a)
    h = data.baca(f"hasil_{bulan}")
    h = h[h["op"].astype(str) == OP_TANPA_TARGET]
    nama = peta_nama_prn()
    out = []
    for n, t in sorted(set(zip(h["nama_sap"], h["tgl"])), key=lambda x: (x[1], x[0])):
        p = peta.get(n)
        if p:
            out.append(dict(prn=p, nama=nama.get(p, p), tgl=t, teks="mengerjakan OP107"))
    return out


def resign_dari():
    a = data.baca("absensi")
    a = a[a["kode"] == "R"]
    out = {}
    for p, t in zip(a["prn"], a["tgl"]):
        out[p] = min(t, out.get(p, t))
    return out


def jadwal_peta(bulan):
    j = data.baca(f"jadwal_{bulan}")
    return {(p, t): s for p, t, s in zip(j["prn"], j["tgl"], j["status"])}


def libur(prn, tgl, bulan, jadwal, default):
    s = jadwal.get((prn, tgl))
    if s is not None:
        return s == "X"
    return default[int(tgl[8:])]


def harian_bulan(bulan, hasil=None):
    """Return (harian[prn,tgl,persen], tanpa_target)."""
    k, a, t = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    if hasil is None:
        hasil = data.baca(f"hasil_{bulan}")
    peta = calc.peta_nama(k, a)
    hasil = hasil.assign(prn=hasil["nama_sap"].map(peta)).dropna(subset=["prn"])
    lembur = data.baca("lembur")
    lembur = lembur[lembur["tgl"].str.startswith(bulan)]
    adj = pd.DataFrame({"prn": lembur["prn"], "tgl": lembur["tgl"], "menit_masalah": "0",
                        "jam_lembur": lembur["jam"]})
    return calc.hitung_harian(hasil, t, adj)


def rekap_bulan(bulan):
    """Baris untuk tabel halaman utama. Tiap baris: prn, nama, hari{d: (jenis, nilai)}, rata."""
    nama = peta_nama_prn()
    harian, _ = harian_bulan(bulan)
    persen = {(p, t): v for p, t, v in zip(harian["prn"], harian["tgl"], harian["persen"])}
    abs_ = data.baca("absensi")
    abs_ = {(p, t): c for p, t, c in zip(abs_["prn"], abs_["tgl"], abs_["kode"])}
    rs = resign_dari()
    jadwal, default = jadwal_peta(bulan), hari_libur_default(bulan)
    awal = f"{bulan}-01"
    baris = []
    for prn in karyawan_dikenal(bulan):
        if prn in rs and rs[prn] < awal:
            continue  # sudah resign sebelum bulan ini
        hari, nilai = {}, []
        for d in range(1, n_hari(bulan) + 1):
            tgl = f"{bulan}-{d:02d}"
            if (prn, tgl) in persen:
                hari[d] = ("pct", persen[(prn, tgl)])
                nilai.append(persen[(prn, tgl)])
            elif prn in rs and tgl >= rs[prn]:
                hari[d] = ("abs", "R")
            elif (prn, tgl) in abs_:
                hari[d] = ("abs", abs_[(prn, tgl)])
            elif libur(prn, tgl, bulan, jadwal, default):
                hari[d] = ("libur", None)
        baris.append({"prn": prn, "nama": nama.get(prn, prn), "hari": hari,
                      "rata": sum(nilai) / len(nilai) if nilai else None})
    return baris


def masalah_bulan(bulan):
    """Peringatan untuk lonceng: hasil kerja SAP di hari libur, absen, atau setelah resign.
    Tiap item: dict(prn, nama, tgl, jenis, ket). jenis = libur | absen | resign."""
    nama = peta_nama_prn()
    harian, _ = harian_bulan(bulan)
    abs_ = data.baca("absensi")
    abs_ = {(p, t): c for p, t, c in zip(abs_["prn"], abs_["tgl"], abs_["kode"])}
    rs = resign_dari()
    jadwal, default = jadwal_peta(bulan), hari_libur_default(bulan)
    out = []
    for p, t in zip(harian["prn"], harian["tgl"]):
        n = nama.get(p, p)
        if p in rs and t >= rs[p]:
            out.append(dict(prn=p, nama=n, tgl=t, jenis="resign", ket="ada hasil kerja padahal tercatat resign"))
        elif (p, t) in abs_ and abs_[(p, t)] != "R":
            k = NAMA_ABSEN.get(abs_[(p, t)], abs_[(p, t)])
            out.append(dict(prn=p, nama=n, tgl=t, jenis="absen", ket=f"ada hasil kerja padahal tercatat {k}"))
        elif jadwal and libur(p, t, bulan, jadwal, default):
            out.append(dict(prn=p, nama=n, tgl=t, jenis="libur", ket="ada hasil kerja di hari libur menurut jadwal"))
    return sorted(out, key=lambda x: (x["tgl"], x["nama"]))
