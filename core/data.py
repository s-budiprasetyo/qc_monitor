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


TTL = 60  # detik; tulis() menghapus tembolok tabel yang diubah


def baca(nama):
    c, sekarang_ = _tembolok(), time.time()
    if nama in c and sekarang_ - c[nama][0] < TTL:
        return c[nama][1].copy()
    df = store().read(nama)
    if nama.startswith("hasil_") and "trx" not in df.columns:  # data lama sebelum kolom trx ada
        df["trx"] = df["tgl"]
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
    c["_v"] = c.get("_v", 0) + 1
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
    """Tulis ulang tab 'HASIL KERJA KARYAWAN' di Google Sheet dari seluruh data: tiap bulan yang punya Google Sheet
    sendiri ke bukunya, sisanya ke Sheet utama. Bulan yang isinya tidak berubah dilewati. Aman dipanggil berulang."""
    import hashlib
    from core import logic
    df = logic.laporan_riwayat()
    st_, c = store(), _tembolok()
    bln = df["TANGGAL TAMPIL"].astype(str).str[:7] if len(df) else pd.Series([], dtype=str)
    punya = {b for b in bln.unique() if getattr(st_, "bulan_punya_buku", lambda x: False)(b)}
    bagian = [(b, df[bln == b]) for b in sorted(punya)] + [(None, df[~bln.isin(punya)])]
    for b, d_ in bagian:
        kunci = f"_hash_{b}"
        h = hashlib.md5(d_.to_csv(index=False).encode()).hexdigest()
        if c.get(kunci) == h:
            continue
        if b is None:
            st_.write_laporan("HASIL KERJA KARYAWAN", d_)
        else:
            st_.write_laporan("HASIL KERJA KARYAWAN", d_, bulan=b)
        c[kunci] = h
    catat_update("RIWAYAT GOOGLE SHEET")
    return len(df)


def info_buku():
    """Daftar Google Sheet bulanan (untuk tampilan admin): list dict(bulan, nama, url)."""
    st_ = store()
    if not hasattr(st_, "daftar_buku"):
        return []
    try:
        return [dict(bulan=x["bulan"], nama=x["nama"], url=f"https://docs.google.com/spreadsheets/d/{x['sheet_id']}")
                for x in st_.daftar_buku()]
    except Exception:
        return []


def peringatan_store():
    """Pesan masalah dari penyimpanan (mis. gagal membuat Google Sheet bulan baru); dibaca lalu dikosongkan."""
    p = getattr(store(), "peringatan", None)
    if not p:
        return []
    out = list(p)
    p.clear()
    return out


def catat_alasan(email, nama, tgl_tidak_target, alasan, menit=""):
    """Tambah satu baris ke tab 'ALASAN TIDAK TARGET' (jejak, tidak bisa ditimpa)."""
    w = datetime.now(WIB)
    store().tambah_baris("ALASAN TIDAK TARGET", KOLOM_ALASAN,
                         [w.strftime("%H:%M:%S"), w.strftime("%Y-%m-%d"), email, nama, tgl_tidak_target, alasan, menit],
                         bulan=str(tgl_tidak_target)[:7])


def versi():
    """Naik tiap ada data yang ditulis; dipakai sebagai kunci cache hitungan berat."""
    return _tembolok().get("_v", 0)


# ---------------------------------------------------------------- alasan tidak target (Tahap 3)
def kecilkan_foto(isi, batas=42000):
    """Foto jadi JPEG kecil (teks base64 <= batas karakter) supaya muat di satu sel Google Sheet."""
    import base64
    import io
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(isi))).convert("RGB")
    for sisi, mutu in ((480, 60), (400, 55), (320, 50), (240, 45), (160, 40)):
        k = im.copy()
        k.thumbnail((sisi, sisi))
        b = io.BytesIO()
        k.save(b, "JPEG", quality=mutu, optimize=True)
        teks = base64.b64encode(b.getvalue()).decode()
        if len(teks) <= batas:
            return teks
    return teks


def pengajuan_ada(prn, tgl):
    p = baca("pengajuan")
    return bool(((p["prn"] == prn) & (p["tgl"] == tgl)).any())


def alasan_hari(prn, tgl):
    """Alasan yang pernah diajukan untuk satu orang satu hari: list dict(masalah, menit, foto)."""
    al = baca("alasan")
    al = al[(al["prn"] == prn) & (al["tgl"] == tgl)].copy()
    al["no"] = pd.to_numeric(al["no"], errors="coerce")
    return [dict(masalah=r.masalah, menit=int(float(r.menit or 0)), foto=r.foto) for r in al.sort_values("no").itertuples()]


def simpan_alasan(prn, nama, tgl, items, email=""):
    """items: list dict(masalah, menit, foto=bytes|None, foto_lama=id|''). Pengajuan ulang untuk hari yang sama menggantikan
    isi lama dan status kembali 'menunggu' (jadi notifikasi baru untuk atasan). Tiap pengajuan tetap dijejak di tab
    'ALASAN TIDAK TARGET'."""
    if not email:  # belum verifikasi Google: jejak memakai user login karyawan
        k = baca("karyawan")
        u = k.loc[k["prn"] == prn, "user"]
        email = f"(tanpa Google) {u.iloc[0]}" if len(u) else "(tanpa Google)"
    revisi = pengajuan_ada(prn, tgl)
    lama = {f"{prn}|{tgl}|{n}": r["foto"] for n, r in enumerate(alasan_hari(prn, tgl), 1)}
    foto_lama = baca("foto_alasan")
    foto_lama = dict(zip(foto_lama["id"], foto_lama["data"]))
    baris, fotos = [], []
    for n, it in enumerate(items, 1):
        fid = ""
        if it.get("foto"):
            fid = f"{prn}|{tgl}|{n}"
            fotos.append({"id": fid, "data": kecilkan_foto(it["foto"])})
        elif it.get("foto_lama") and it["foto_lama"] in foto_lama:
            fid = f"{prn}|{tgl}|{n}"
            fotos.append({"id": fid, "data": foto_lama[it["foto_lama"]]})
        baris.append({"prn": prn, "tgl": tgl, "no": str(n), "masalah": it["masalah"],
                      "menit": str(int(it["menit"])), "foto": fid})
    total = sum(int(it["menit"]) for it in items)
    # hapus isi lama hari ini (termasuk baris nomor tinggi yang tidak dipakai lagi), lalu tulis yang baru
    al = baca("alasan")
    tulis("alasan", pd.concat([al[~((al["prn"] == prn) & (al["tgl"] == tgl))], pd.DataFrame(baris)], ignore_index=True))
    ft = baca("foto_alasan")
    ft = ft[~ft["id"].str.startswith(f"{prn}|{tgl}|")]
    tulis("foto_alasan", pd.concat([ft, pd.DataFrame(fotos, columns=["id", "data"])], ignore_index=True))
    upsert("pengajuan", pd.DataFrame([{"prn": prn, "tgl": tgl, "menit": str(total), "status": "menunggu",
                                       "waktu": sekarang(), "email": email}]), ["prn", "tgl"])
    try:
        catat_alasan(email, nama, tgl,
                     ("[REVISI] " if revisi else "") +
                     "; ".join(f"{it['masalah']} ({int(it['menit'])} mnt)" for it in items), str(total))
    except Exception:
        pass
    return True


def hapus_pengajuan(prn, tgl):
    """Hapus total satu pengajuan alasan (pengajuan, alasan, foto). Jejak di tab ALASAN TIDAK TARGET tidak diubah."""
    for nama, kunci in (("pengajuan", None), ("alasan", None)):
        t = baca(nama)
        tulis(nama, t[~((t["prn"] == prn) & (t["tgl"] == tgl))])
    ft = baca("foto_alasan")
    tulis("foto_alasan", ft[~ft["id"].str.startswith(f"{prn}|{tgl}|")])
    try:  # jejak di tab Google Sheet ikut dihapus
        k = baca("karyawan")
        nama = k.loc[k["prn"] == prn, "nama_web"]
        if len(nama):
            store().hapus_baris("ALASAN TIDAK TARGET", {"NAMA": nama.iloc[0], "TANGGAL TIDAK TARGET": tgl}, bulan=tgl[:7])
    except Exception:
        pass


def foto_alasan(fid):
    f = baca("foto_alasan")
    x = f.loc[f["id"] == fid, "data"]
    return x.iloc[0] if len(x) else None


def kegiatan_hari(prn, tgl):
    k = baca("kegiatan")
    x = k[(k["prn"] == prn) & (k["tgl"] == tgl)]
    return x.iloc[0]["teks"] if len(x) else ""


def simpan_kegiatan(prn, nama, tgl, teks, email=""):
    """Catatan kegiatan lain hari itu (tanpa hasil pcs). Teks kosong = hapus catatan. Dijejak di tab ALASAN TIDAK TARGET."""
    teks = teks.strip()
    if not email:
        k = baca("karyawan")
        u = k.loc[k["prn"] == prn, "user"]
        email = f"(tanpa Google) {u.iloc[0]}" if len(u) else "(tanpa Google)"
    if not teks:
        k = baca("kegiatan")
        tulis("kegiatan", k[~((k["prn"] == prn) & (k["tgl"] == tgl))])
        return
    upsert("kegiatan", pd.DataFrame([{"prn": prn, "tgl": tgl, "teks": teks, "waktu": sekarang(), "email": email}]), ["prn", "tgl"])
    try:
        catat_alasan(email, nama, tgl, "[KEGIATAN LAIN] " + teks, "")
    except Exception:
        pass
