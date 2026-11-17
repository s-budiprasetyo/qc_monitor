"""Monitoring Label (foreman): meja, kategori/type, tanggal posting dari jadwal, simpan/ubah/hapus, notifikasi meja."""
import re
from datetime import date, datetime, timedelta

import pandas as pd

from core import data, logic

PABRIK = {"Pabrik 1": 21, "Pabrik 2": 19, "QC SK": 5}  # jumlah meja per pabrik (total 45)
SHIFT = ["Pagi", "Sore"]  # SAP: Shift B = Pagi, C = Sore
KATEGORI = ["Closet", "Lavatory", "Tangki", "Urinal", "Aksesoris"]
JENIS = [("lengket", "Lengket"), ("garis", "Garis"), ("kotor", "Kotor")]
KOLOM = ["tgl", "shift", "tgl_posting", "waktu", "prn", "nama", "pabrik", "meja", "kategori", "type",
         "lengket", "garis", "kotor", "total", "oleh"]
KUNCI = ["tgl", "shift", "prn", "pabrik", "meja", "type"]
BATAS_KOTOR = 0.5  # persen dari jumlah periksa (dipakai laporan tahap berikutnya)


def hari_ini():
    return datetime.now(data.WIB).date()


def meja_daftar(pabrik):
    return [str(i) for i in range(1, PABRIK[pabrik] + 1)]


def nama_meja(pabrik, meja):
    return f"Meja {meja} · {pabrik}"


def kategori_dari_type(t):
    """Aturan awalan type: CW/CE = Closet, L/LW = Lavatory, SW/S+angka = Tangki, U = Urinal, selain itu Aksesoris."""
    t = str(t).strip().upper()
    if re.match(r"^(CW|CE)", t):
        return "Closet"
    if re.match(r"^L", t):
        return "Lavatory"
    if t.startswith("SW") or re.match(r"^S\d", t):
        return "Tangki"
    if re.match(r"^U", t):
        return "Urinal"
    return "Aksesoris"


def type_per_kategori():
    """{kategori: [type,...]} dari data target (PENCAPAIAN KERJA QC); jadi daftar pilihan type."""
    t = data.baca("target")
    hasil = {k: [] for k in KATEGORI}
    for x in sorted({str(v).strip() for v in t["type"] if str(v).strip()}):
        hasil[kategori_dari_type(x)].append(x)
    return hasil


def operator_daftar():
    """[(prn, nama)] operator yang bisa dipilih: karyawan yang menghasilkan (jenis PERIKSA atau belum diisi) dan tidak disilang.
    Bila tabel 'operator' (Daftar Operator, tahap berikutnya) sudah berisi, itu yang dipakai."""
    k = logic.info_karyawan()
    ro = data.baca("roster")
    silang = set(ro.loc[ro["status"] == "tidak", "prn"])
    daftar = data.baca("operator") if "operator" in _tabel_ada() else pd.DataFrame(columns=["prn"])
    if len(daftar):
        k = k[k["prn"].isin(set(daftar["prn"]))]
    else:
        k = k[k["jenis"].isin(["PERIKSA", ""]) & ~k["prn"].isin(silang)]
    k = k.assign(_n=k["nama_web"].where(k["nama_web"] != "", k["nama_sap"])).sort_values("_n")
    return list(zip(k["prn"], k["_n"]))


def _tabel_ada():
    try:
        from core.store import KOLOM as K
        return K
    except Exception:
        return {}


def tanggal_posting(prn, tgl, shift):
    """Pagi: posting di tanggal kerja. Sore: posting di hari kerja berikutnya menurut jadwal operator itu
    (Jumat sore, Sabtu-Minggu libur, jadi Senin)."""
    d0 = date.fromisoformat(tgl)
    if shift != "Sore":
        return tgl
    jad, cache = {}, {}
    for n in range(1, 8):
        d = d0 + timedelta(days=n)
        bulan = d.strftime("%Y-%m")
        if bulan not in cache:
            cache[bulan] = (logic.jadwal_peta(bulan), logic.hari_libur_default(bulan))
        jm, dflt = cache[bulan]
        if not logic.libur(prn, d.isoformat(), bulan, jm, dflt):
            return d.isoformat()
    return (d0 + timedelta(days=1)).isoformat()


def baca_hari(tgl, shift):
    d = data.baca("label_afkir")
    return d[(d["tgl"] == tgl) & (d["shift"] == shift)].reset_index(drop=True)


def _int(x):
    try:
        return max(0, int(x or 0))
    except (TypeError, ValueError):
        return 0


def simpan(tgl, shift, prn, nama, pabrik, meja, kolom, oleh, ganti_lama=None):
    """kolom = {type: {'lengket':n,'garis':n,'kotor':n}}. Satu baris per type.
    ganti_lama (opsional): (prn, pabrik, meja) kelompok lama yang diganti saat mengubah.
    Return pesan galat (str) bila ditolak, atau None bila tersimpan."""
    if not prn or not meja or not kolom:
        return "Pilih operator, meja, dan minimal satu type."
    pastikan = getattr(data.store(), "pastikan_bulan", None)
    if pastikan:
        pastikan(tgl[:7])  # bisa melempar BukuBulananBelumAda: dibiarkan naik agar ditampilkan admin
    ada = baca_hari(tgl, shift)
    if ganti_lama is None:
        dobel = ada[(ada["prn"] == prn) & (ada["pabrik"] == pabrik) & (ada["meja"] == str(meja)) & (ada["type"].isin(list(kolom)))]
        if len(dobel):
            return (f"Type {', '.join(sorted(set(dobel['type'])))} untuk {nama} di {nama_meja(pabrik, meja)} sudah tersimpan "
                    "pada tanggal dan shift ini. Ubah lewat tabel di bawah (tombol ✎).")
    waktu = datetime.now(data.WIB).strftime("%H:%M")
    posting = tanggal_posting(prn, tgl, shift)
    baris = []
    for t, v in kolom.items():
        l, g, k = _int(v.get("lengket")), _int(v.get("garis")), _int(v.get("kotor"))
        baris.append({"tgl": tgl, "shift": shift, "tgl_posting": posting, "waktu": waktu, "prn": prn, "nama": nama,
                      "pabrik": pabrik, "meja": str(meja), "kategori": kategori_dari_type(t), "type": t,
                      "lengket": l, "garis": g, "kotor": k, "total": l + g + k, "oleh": oleh})
    hapus = None
    if ganti_lama is not None:
        lp, lpab, lm = ganti_lama
        lama = ada[(ada["prn"] == lp) & (ada["pabrik"] == lpab) & (ada["meja"] == str(lm))]
        hapus = lama[KUNCI] if len(lama) else None
    data.upsert("label_afkir", pd.DataFrame(baris, columns=KOLOM), KUNCI, hapus=hapus)
    data.catat_update("MONITORING LABEL")
    return None


def hapus_baris(tgl, shift, prn, pabrik, meja, tipe):
    h = pd.DataFrame([{"tgl": tgl, "shift": shift, "prn": prn, "pabrik": pabrik, "meja": str(meja), "type": tipe}])
    data.upsert("label_afkir", pd.DataFrame(columns=KOLOM), KUNCI, hapus=h)


def abaikan_hari(tgl, shift):
    d = data.baca("meja_abaikan")
    return d[(d["tgl"] == tgl) & (d["shift"] == shift)].reset_index(drop=True)


def meja_belum(tgl, shift):
    """{pabrik: [meja,...]} yang belum dicek (belum ada input label dan tidak diabaikan) pada tanggal+shift itu."""
    ada = baca_hari(tgl, shift)
    sudah = set(zip(ada["pabrik"], ada["meja"]))
    ab = abaikan_hari(tgl, shift)
    sudah |= set(zip(ab["pabrik"], ab["meja"]))
    return {p: [m for m in meja_daftar(p) if (p, m) not in sudah] for p in PABRIK}


def abaikan(tgl, shift, pabrik, meja, oleh):
    waktu = datetime.now(data.WIB).strftime("%H:%M")
    baru = pd.DataFrame([{"tgl": tgl, "shift": shift, "pabrik": pabrik, "meja": str(meja), "oleh": oleh, "waktu": waktu}])
    data.upsert("meja_abaikan", baru, ["tgl", "shift", "pabrik", "meja"])


def batal_abaikan(tgl, shift, pabrik, meja):
    h = pd.DataFrame([{"tgl": tgl, "shift": shift, "pabrik": pabrik, "meja": str(meja)}])
    data.upsert("meja_abaikan", pd.DataFrame(columns=["tgl", "shift", "pabrik", "meja", "oleh", "waktu"]),
                ["tgl", "shift", "pabrik", "meja"], hapus=h)
