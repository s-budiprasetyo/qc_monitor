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
    """Ketidaksesuaian untuk lonceng: orang yang menghasilkan pekerjaan pada HARI KERJA SEBENARNYA (Transaction Date)
    yang menurut jadwal libur, tercatat absen, atau sudah resign. Tampilan tabel tetap memakai Posting Date.
    Tiap item: dict(prn, nama, tgl, tgl_posting, bulan, jenis, ket). jenis = libur | absen | resign.
    Yang sudah diputuskan 'abaikan' oleh admin tidak muncul lagi."""
    nama, tampil = peta_nama_prn(), set(karyawan_dikenal())
    k, a = data.baca("karyawan"), data.baca("alias")
    peta = calc.peta_nama(k, a)
    h = data.baca(f"hasil_{bulan}")
    h = h.assign(prn=h["nama_sap"].map(peta)).dropna(subset=["prn"])
    h = h[h["prn"].isin(tampil)]
    posting = {}
    for p, t, d in zip(h["prn"], h["trx"], h["tgl"]):
        posting[(p, t)] = min(d, posting.get((p, t), d))
    abs_ = data.baca("absensi")
    abs_ = {(p, t): c for p, t, c in zip(abs_["prn"], abs_["tgl"], abs_["kode"])}
    rs = resign_dari()
    ab = data.baca("masalah_abaikan")
    abaikan = set(zip(ab["prn"], ab["tgl"]))
    cache, out = {}, []
    for (p, t), d in sorted(posting.items(), key=lambda x: (x[0][1], nama.get(x[0][0], ""))):
        if (p, t) in abaikan:
            continue
        bln = t[:7]
        if bln not in cache:
            cache[bln] = (jadwal_peta(bln), hari_libur_default(bln))
        jadwal, default = cache[bln]
        n = nama.get(p, p)
        tambah = f" (hasilnya tercatat di tanggal posting {d[8:]}-{d[5:7]})" if d != t else ""
        if p in rs and t >= rs[p]:
            ket, jenis = "ada hasil kerja padahal tercatat resign", "resign"
        elif (p, t) in abs_ and abs_[(p, t)] != "R":
            ket, jenis = f"ada hasil kerja padahal tercatat {NAMA_ABSEN.get(abs_[(p, t)], abs_[(p, t)])}", "absen"
        elif jadwal and libur(p, t, bln, jadwal, default):
            ket, jenis = "bekerja di hari libur menurut jadwal", "libur"
        else:
            continue
        out.append(dict(prn=p, nama=n, tgl=t, tgl_posting=d, bulan=bln, jenis=jenis, ket=ket + tambah))
    return out


KOLOM_RIWAYAT = ["TANGGAL", "NAMA", "PRN", "TYPE", "OPERATION", "PERIKSA", "TARGET", "% TYPE", "% HARIAN", "STATUS"]


def laporan_riwayat():
    """Riwayat hasil kerja semua bulan, satu baris per orang per hari per type, lengkap dengan status target.
    Hanya karyawan yang ada di daftar pantau."""
    k, a, t = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    peta, nama, tampil = calc.peta_nama(k, a), peta_nama_prn(), set(karyawan_dikenal())
    t = t.assign(target=pd.to_numeric(t["target"], errors="coerce"))
    baris = []
    for b in data.daftar_bulan():
        h = data.baca(f"hasil_{b}")
        h = h.assign(prn=h["nama_sap"].map(peta)).dropna(subset=["prn"])
        h = h[h["prn"].isin(tampil)]
        if h.empty:
            continue
        harian, _ = harian_bulan(b)
        pers = {(p, d): v for p, d, v in zip(harian["prn"], harian["tgl"], harian["persen"])}
        m = h.merge(t, on=["grup", "type", "op"], how="left")
        m["periksa"] = pd.to_numeric(m["periksa"], errors="coerce")
        for r in m.itertuples():
            ada = pd.notna(r.target)
            hari = pers.get((r.prn, r.tgl))
            if not ada:
                status = "TANPA TARGET (OP107)" if str(r.op) == OP_TANPA_TARGET else "TANPA TARGET"
            elif hari is None:
                status = "TANPA TARGET"
            else:
                status = "TARGET" if round(hari) >= 100 else "TIDAK TARGET"
            baris.append([r.tgl, nama.get(r.prn, r.prn), r.prn, r.type, str(r.op),
                          float(r.periksa) if pd.notna(r.periksa) else "",
                          float(r.target) if ada else "",
                          round(r.periksa / r.target * 100, 1) if ada and pd.notna(r.periksa) else "",
                          round(hari, 1) if hari is not None else "", status])
    df = pd.DataFrame(baris, columns=KOLOM_RIWAYAT)
    return df.sort_values(["TANGGAL", "NAMA", "TYPE"]).reset_index(drop=True)
