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


JENIS_TAMPIL = ["PERIKSA", "PERBAIKAN", "GERINDA", "TAP/TAD", "FOREMAN"]  # urutan = urutan tampil
TIPE_URUT = ["CE7", "CLOSET", "LAVATORY", "TANGKI", "URINAL"]
BAGIAN_URUT = ["QC", "SK"]


def info_karyawan():
    """Data karyawan + kolom jenis, tipe, bagian (selalu ada, walau data lama belum punya)."""
    k = data.baca("karyawan")
    for c in ("jenis", "tipe"):
        if c not in k.columns:
            k[c] = ""
    b = data.baca("bagian")
    peta = dict(zip(b["prn"], b["bagian"]))
    k["bagian"] = k["prn"].map(peta).fillna("") .replace("", "QC")
    return k.fillna("")


def tampil_default(jenis):
    """Yang tampil di monitor: hanya yang bekerja menghasilkan. Jenis kosong (data lama) = tampil."""
    return jenis == "" or jenis in JENIS_TAMPIL


def kunci_urut(bagian, jenis, tipe, nama):
    def pos(daftar, v):
        return daftar.index(v) if v in daftar else len(daftar)
    return (pos(BAGIAN_URUT, bagian), pos(JENIS_TAMPIL, jenis), pos(TIPE_URUT, tipe), nama)


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
    k = info_karyawan().set_index("prn")
    def kunci(p):
        if p in k.index:
            r = k.loc[p]
            return kunci_urut(r["bagian"], r["jenis"], r["tipe"], nama.get(p, p))
        return kunci_urut("", "", "", nama.get(p, p))
    return sorted(hasil, key=kunci)


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
    k, r = info_karyawan(), data.baca("roster")
    putus = dict(zip(r["prn"], r["status"]))
    jenis = dict(zip(k["prn"], k["jenis"]))
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
            silang = not tampil_default(jenis.get(p, ""))  # yang tidak menghasilkan (supervisor, admin, dll) ✕
        baris.append({"prn": p, "nama": n, "jenis": jenis.get(p, ""), "ada_sap": p in sap, "ada_jadwal": p in ada_jadwal,
                      "baru": p not in putus, "silang": silang})
    return pd.DataFrame(baris).sort_values(["baru", "ada_sap", "nama"], ascending=[False, True, True]).reset_index(drop=True)


def catatan_otomatis(bulan):
    """Catatan otomatis dari operation yang memang tanpa target (OP107): tiap orang per hari.
    Return list dict(prn, nama, tgl, teks)."""
    k, a = data.baca("karyawan"), data.baca("alias")
    peta = calc.peta_nama(k, a)
    h = hasil_bulan(bulan)
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


INTI = ["tgl", "nama_sap", "type", "lokasi", "grup", "op", "periksa", "trx"]


def hasil_pindah():
    """(prn, tanggal kerja) yang oleh admin dipindahkan ke tanggal kerja sebenarnya (bukan tanggal posting)."""
    t = data.baca("pindah_hasil")
    return set(zip(t["prn"], t["tgl"]))


def hasil_bulan(bulan):
    """Hasil kerja efektif untuk satu bulan: tanggal = Posting Date, kecuali baris yang dipindahkan admin ke
    tanggal kerja (Transaction Date). Baris dari bulan tetangga ikut bila dipindahkan ke bulan ini."""
    k, a = data.baca("karyawan"), data.baca("alias")
    peta = calc.peta_nama(k, a)
    th, bl = int(bulan[:4]), int(bulan[5:])
    tetangga = [f"{th + (bl - 1 + d) // 12}-{(bl - 1 + d) % 12 + 1:02d}" for d in (-1, 0, 1)]
    ada = set(data.daftar_bulan())
    bagian = [data.baca(f"hasil_{b}") for b in tetangga if b in ada]
    if not bagian:
        return data.baca(f"hasil_{bulan}")
    h = pd.concat(bagian, ignore_index=True).fillna("")
    h["prn"] = h["nama_sap"].map(peta)
    pindah = hasil_pindah()
    if pindah:
        m = [(p, t) in pindah for p, t in zip(h["prn"], h["trx"])]
        h.loc[m, "tgl"] = h.loc[m, "trx"]
    return h[h["tgl"].str[:7] == bulan].reset_index(drop=True)


def menit_diterima():
    """{(prn,tgl): menit} untuk pengajuan yang diterima atasan (V): target hari itu dikurangi sebesar menit ini."""
    p = data.baca("pengajuan")
    p = p[p["status"] == "V"]
    return {(a, b): float(pd.to_numeric(m, errors="coerce") or 0) for a, b, m in zip(p["prn"], p["tgl"], p["menit"])}


def harian_bulan(bulan, hasil=None, dengan_masalah=True):
    """Return (harian[prn,tgl,persen], tanpa_target). dengan_masalah=False: abaikan pengurangan menit dari pengajuan V."""
    k, a, t = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    if hasil is None:
        hasil = hasil_bulan(bulan)
    peta = calc.peta_nama(k, a)
    hasil = hasil[INTI].assign(prn=hasil["nama_sap"].map(peta)).dropna(subset=["prn"])
    lembur = data.baca("lembur")
    lembur = lembur[lembur["tgl"].str.startswith(bulan)]
    adj = pd.DataFrame({"prn": lembur["prn"], "tgl": lembur["tgl"], "menit_masalah": "0",
                        "jam_lembur": lembur["jam"]})
    if dengan_masalah:
        mn = [(p, d, m) for (p, d), m in menit_diterima().items() if d.startswith(bulan)]
        if mn:
            adj = pd.concat([adj, pd.DataFrame({"prn": [x[0] for x in mn], "tgl": [x[1] for x in mn],
                                                "menit_masalah": [str(x[2]) for x in mn], "jam_lembur": "0"})],
                            ignore_index=True)
    if len(adj):
        adj["menit_masalah"] = pd.to_numeric(adj["menit_masalah"], errors="coerce").fillna(0)
        adj["jam_lembur"] = pd.to_numeric(adj["jam_lembur"], errors="coerce").fillna(0)
        adj = adj.groupby(["prn", "tgl"], as_index=False)[["menit_masalah", "jam_lembur"]].sum()
    return calc.hitung_harian(hasil, t, adj)


def detail_hari(bulan, prn, tgl):
    """Rincian satu orang satu hari: list dict(type, op, periksa, target, pct) dan persen total (None bila tak ada target)."""
    k, a, t = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    peta = calc.peta_nama(k, a)
    h = hasil_bulan(bulan)
    h = h[(h["tgl"] == tgl) & (h["nama_sap"].map(peta) == prn)]
    t = t.assign(target=pd.to_numeric(t["target"], errors="coerce"))
    m = h.merge(t, on=["grup", "type", "op"], how="left")
    baris = []
    for r in m.itertuples():
        per = pd.to_numeric(r.periksa, errors="coerce")
        ada = pd.notna(r.target) and r.target > 0
        baris.append(dict(type=r.type, op=str(r.op), periksa=float(per) if pd.notna(per) else 0.0,
                          target=float(r.target) if ada else None,
                          pct=float(per) / r.target * 100 if ada and pd.notna(per) else None))
    baris.sort(key=lambda x: (x["type"], x["op"]))
    harian, _ = harian_bulan(bulan)
    v = harian[(harian["prn"] == prn) & (harian["tgl"] == tgl)]["persen"]
    return baris, (float(v.iloc[0]) if len(v) else None)


def tidak_target(bulan, prn=None):
    """Hari dengan persen < 100 (dibulatkan) + alasan yang diposting. Status V/X TIDAK disertakan (privasi)."""
    harian, _ = harian_bulan(bulan)
    harian = harian[harian["tgl"].str.startswith(bulan)]
    if prn:
        harian = harian[harian["prn"] == prn]
    al = data.baca("alasan")
    out = []
    for p, d, v in sorted(zip(harian["prn"], harian["tgl"], harian["persen"]), key=lambda x: (x[0], x[1])):
        if round(v) >= 100:
            continue
        a = al[(al["prn"] == p) & (al["tgl"] == d)].sort_values("no")
        out.append(dict(prn=p, tgl=d, persen=v,
                        alasan=[dict(masalah=r.masalah, menit=r.menit, foto=r.foto) for r in a.itertuples()]))
    return out


def absen_bulan(bulan, prn):
    a = data.baca("absensi")
    a = a[(a["prn"] == prn) & (a["tgl"].str.startswith(bulan))].sort_values("tgl")
    return [dict(tgl=t, kode=c, ket=k) for t, c, k in zip(a["tgl"], a["kode"], a["keterangan"])]


def antrean_evaluasi(semua=False):
    """Pengajuan untuk atasan (semua=False: hanya yang menunggu). Persen = nilai asli tanpa pengurangan menit."""
    p = data.baca("pengajuan")
    if not semua:
        p = p[p["status"] == "menunggu"]
    nama, al = peta_nama_prn(), data.baca("alasan")
    asli, out = {}, []
    for r in p.sort_values(["tgl", "prn"]).itertuples():
        b = r.tgl[:7]
        if b not in asli:
            h, _ = harian_bulan(b, dengan_masalah=False)
            asli[b] = {(x, y): z for x, y, z in zip(h["prn"], h["tgl"], h["persen"])}
        a = al[(al["prn"] == r.prn) & (al["tgl"] == r.tgl)].sort_values("no")
        out.append(dict(prn=r.prn, nama=nama.get(r.prn, r.prn), tgl=r.tgl, persen=asli[b].get((r.prn, r.tgl)),
                        menit=r.menit, status=r.status,
                        alasan="; ".join(f"{x.masalah} ({x.menit} mnt)" for x in a.itertuples())))
    return out


def simpan_keputusan(keputusan):
    """keputusan: {(prn,tgl): 'V'|'X'}. Mengubah status pengajuan."""
    p = data.baca("pengajuan")
    for (a, b), v in keputusan.items():
        p.loc[(p["prn"] == a) & (p["tgl"] == b), "status"] = v
    data.tulis("pengajuan", p)


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
    h = h[h["trx"] != ""]
    posting = {}
    for p, t, d in zip(h["prn"], h["trx"], h["tgl"]):
        posting[(p, t)] = min(d, posting.get((p, t), d))
    abs_ = data.baca("absensi")
    abs_ = {(p, t): c for p, t, c in zip(abs_["prn"], abs_["tgl"], abs_["kode"])}
    rs = resign_dari()
    ab = data.baca("masalah_abaikan")
    abaikan = set(zip(ab["prn"], ab["tgl"])) | hasil_pindah()
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
        elif (jadwal and libur(p, t, bln, jadwal, default)) or (d != t and calendar.weekday(int(t[:4]), int(t[5:7]), int(t[8:])) >= 5):
            ket, jenis = "bekerja di hari libur menurut jadwal", "libur"
        else:
            continue
        out.append(dict(prn=p, nama=n, tgl=t, tgl_posting=d, bulan=bln, jenis=jenis, ket=ket + tambah,
                        beda=d != t))
    return out


HITUNG = ["TANGGAL TAMPIL", "TANGGAL KERJA (TRX)", "NAMA TAMPIL", "PRN", "TARGET", "% TYPE", "% HARIAN", "STATUS", "KETERANGAN", "TAMPIL DI MONITOR"]


def laporan_riwayat():
    """Riwayat hasil kerja semua bulan: SEMUA kolom SAP asli + kolom hitungan, satu baris per baris SAP.
    Hanya karyawan di daftar pantau; nama yang belum cocok tetap ditulis (status NAMA BELUM COCOK)."""
    k, a, t = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    peta, nama, tampil = calc.peta_nama(k, a), peta_nama_prn(), set(karyawan_dikenal())
    pindah = hasil_pindah()
    t = t.assign(target=pd.to_numeric(t["target"], errors="coerce"))
    bagian, mentah = [], []
    for b in data.daftar_bulan():
        h = data.baca(f"hasil_{b}").fillna("")
        if h.empty:
            continue
        h["prn"] = h["nama_sap"].map(peta)
        h = h.copy()
        if h.empty:
            continue
        h["tgl_posting"] = h["tgl"]
        m = [(p, x) in pindah for p, x in zip(h["prn"], h["trx"])]
        h.loc[m, "tgl"] = h.loc[m, "trx"]
        harian, _ = harian_bulan(b)
        pers = {(p, d): v for p, d, v in zip(harian["prn"], harian["tgl"], harian["persen"])}
        mm = h.merge(t, on=["grup", "type", "op"], how="left")
        mm["periksa"] = pd.to_numeric(mm["periksa"], errors="coerce")
        hitung = []
        for r in mm.itertuples():
            ada = pd.notna(r.target)
            hari = pers.get((r.prn, r.tgl))
            if pd.isna(r.prn):
                status = "NAMA BELUM COCOK"
            elif not ada:
                status = "TANPA TARGET (OP107)" if str(r.op) == OP_TANPA_TARGET else "TANPA TARGET"
            elif hari is None:
                status = "TANPA TARGET"
            else:
                status = "TARGET" if round(hari) >= 100 else "TIDAK TARGET"
            ket = ""
            if r.trx and r.trx != r.tgl_posting:
                ket = "dipindah ke tanggal kerja" if r.tgl == r.trx else "tanggal posting beda dengan tanggal kerja"
            hitung.append([r.tgl, r.trx, nama.get(r.prn, "") if pd.notna(r.prn) else "",
                           r.prn if pd.notna(r.prn) else "", float(r.target) if ada else "",
                           round(r.periksa / r.target * 100, 1) if ada and pd.notna(r.periksa) else "",
                           round(hari, 1) if hari is not None and pd.notna(r.prn) else "", status, ket,
                           "ya" if r.prn in tampil else "tidak"])
        hitung = pd.DataFrame(hitung, columns=HITUNG)
        bagian.append(hitung)
        mentah.append(mm[[c for c in mm.columns if c.startswith("SAP | ")]].fillna("").reset_index(drop=True))
    if not bagian:
        return pd.DataFrame(columns=HITUNG)
    sap = pd.concat(mentah, ignore_index=True).fillna("")
    hit = pd.concat(bagian, ignore_index=True)
    df = pd.concat([hit, sap], axis=1)
    df = df.sort_values(["TANGGAL TAMPIL", "NAMA TAMPIL"], kind="stable").reset_index(drop=True)
    df.columns = [c[6:] if c.startswith("SAP | ") else c for c in df.columns]
    return df
