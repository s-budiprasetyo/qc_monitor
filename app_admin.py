"""Halaman admin (Welcome Admin QC TOTO). Jalankan: streamlit run app_admin.py"""
import difflib
import io
import time
from datetime import date, datetime

import pandas as pd
import streamlit as st

import halaman_foreman
from core import akses, calc, data, label, logic, parsers
from core.grid import jadwal_grid
from core.bulan import pilih_bulan
from core.hub import hub, roda
from core.store import BukuBulananBelumAda
from core.ui import gaya_global, gaya_responsif, ikon, kepala, kontrol_jendela

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]
FILE_INFO = ["FILE HASIL KERJA", "LEMBUR", "EVALUASI KARYAWAN", "ABSENSI", "JADWAL KERJA", "RIWAYAT GOOGLE SHEET"]
PILIHAN_ABSEN = ["Sakit", "Ijin", "Cuti", "Dispen", "Resign", "Hapus catatan"]

st.set_page_config(page_title="Welcome Admin QC TOTO", page_icon="⚙️", layout="wide")


# ---------------------------------------------------------------- tampilan
CSS = """
<style>
.block-container{max-width:1180px;padding-top:2.4rem}
h1.judul{text-align:center;font-weight:800;letter-spacing:.5px;margin:0 0 .6rem 0;padding:0}
.judul-update{font-size:2.7rem;font-weight:800;line-height:1.05;margin:.2rem 0 .4rem 0}
.ilus{background:#fff;border-radius:14px;padding:4px 0}
.ilus svg{height:430px;width:auto;display:block;margin-left:auto;margin-right:0}

.st-key-hub{margin-top:0}
.st-key-lonceng button{border:none;background:transparent;padding:.2rem .5rem;box-shadow:none;height:auto;min-height:0}
.st-key-lonceng button p{font-size:2.2rem !important;line-height:1.1}
.st-key-lonceng{width:fit-content}
button[data-testid="stBaseButton-secondary"]:not(.x){border-color:#00B0F0}
.st-key-awal button{font-size:.85rem}

button[data-testid="stBaseButton-primary"]{background:#00B0F0;border-color:#00B0F0;color:#fff;font-weight:600}
button[data-testid="stBaseButton-primary"]:hover{background:#0a86b5;border-color:#0a86b5;color:#fff}
button[data-testid="stBaseButton-primary"]:disabled{background:#cfe9f7;border-color:#cfe9f7;color:#fff}
h4.info{margin:1.4rem 0 .4rem 0;font-weight:700}
table.info{border-collapse:collapse;width:100%;font-size:13px}
table.info th,table.info td{border:1px solid #000;padding:5px 10px}
table.info th{text-align:center;font-weight:700;background:#fff;color:#000}
table.info td{background:#fff;color:#000}
table.info td.w{text-align:center}

</style>
"""


def pilihan_bulan():
    t, daftar = date.today(), []
    for k in range(-8, 3):
        n = t.year * 12 + t.month - 1 + k
        daftar.append(f"{n // 12}-{n % 12 + 1:02d}")
    return daftar, daftar.index(f"{t.year}-{t.month:02d}")


def nama_bulan(k):
    return f"{BULAN[int(k[5:]) - 1]} {k[:4]}"


_IKON_INFO = {"FILE HASIL KERJA": '<path d="M4 20h16M7 20v-9M12 20V5M17 20v-12"/>',
              "LEMBUR": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2"/>',
              "EVALUASI KARYAWAN": '<circle cx="12" cy="12" r="8.5"/><path d="M8 12.3l3 3 5-6"/>',
              "ABSENSI": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4M9 15l2 2 4-4"/>',
              "JADWAL KERJA": '<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4M8 14h2M12 14h2M8 17h2"/>',
              "RIWAYAT GOOGLE SHEET": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M5 9h14M5 15h14M11 9v12"/>'}
CSS_INFO = """
<style>
.inf{margin:1.4rem 0 .6rem}
.inf-h{display:flex;align-items:center;gap:.6rem;margin-bottom:.8rem}
.inf-h b{font-size:20px;font-weight:800;color:#0b3d91;letter-spacing:.4px}
.inf-h span{font-size:12px;color:#7b8fb0}
.inf-g{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.inf-k{background:#fff;border:1px solid #d6e4f8;border-radius:14px;padding:14px 16px;display:flex;gap:12px;align-items:center;box-shadow:0 2px 10px #2a5db00f}
.inf-i{flex:0 0 auto;width:42px;height:42px;border-radius:12px;background:#eaf3ff;color:#1a5fc8;display:flex;align-items:center;justify-content:center}
.inf-i svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.inf-t{min-width:0;flex:1}
.inf-n{font-size:11.5px;font-weight:800;color:#5b7399;letter-spacing:.6px}
.inf-r{font-size:16px;font-weight:800;color:#0b3d91;margin:1px 0}
.inf-w{font-size:12px;color:#7b8fb0}
.inf-d{flex:0 0 auto;width:10px;height:10px;border-radius:50%}
.d-ok{background:#1d9a54;box-shadow:0 0 0 3px #1d9a5426}.d-mid{background:#e8a317;box-shadow:0 0 0 3px #e8a31726}
.d-old{background:#d93025;box-shadow:0 0 0 3px #d9302526}.d-no{background:#b8c4d8;box-shadow:0 0 0 3px #b8c4d826}
.inf-s{margin-top:.9rem;display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:12.5px;color:#5b7399}
.inf-s a{background:#eef5ff;border:1px solid #cfe0f7;border-radius:999px;padding:3px 11px;color:#1a5fc8 !important;font-weight:700;text-decoration:none}
.inf-s a:hover{background:#dcebff}
.inf-l{display:flex;gap:14px;margin-top:.7rem;font-size:11.5px;color:#7b8fb0;flex-wrap:wrap}
.inf-l i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
@media (max-width:900px){.inf-g{grid-template-columns:repeat(2,1fr)}}
@media (max-width:560px){.inf-g{grid-template-columns:1fr}}
</style>
"""


def _html_info(log, buku):
    """Kartu 'terakhir update' per file: waktu relatif + penanda warna (hijau <=2 hari, kuning <=7, merah lebih lama)."""
    sekarang = datetime.now(data.WIB).replace(tzinfo=None)
    kartu = ""
    for n in FILE_INFO:
        w = str(log.get(n, "") or "").strip()
        rel, abs_, kelas = "Belum pernah", "Belum ada data", "d-no"
        try:
            t = datetime.strptime(w, "%H:%M, %d-%m-%Y")
            hari = (sekarang.date() - t.date()).days
            rel = "Hari ini" if hari <= 0 else ("Kemarin" if hari == 1 else f"{hari} hari lalu")
            abs_ = f"{t.strftime('%d-%m-%Y')} · pukul {t.strftime('%H:%M')}"
            kelas = "d-ok" if hari <= 2 else ("d-mid" if hari <= 7 else "d-old")
        except ValueError:
            pass
        ik = _IKON_INFO.get(n, _IKON_INFO["FILE HASIL KERJA"])
        kartu += (f"<div class='inf-k'><div class='inf-i'><svg viewBox='0 0 24 24'>{ik}</svg></div>"
                  f"<div class='inf-t'><div class='inf-n'>{n}</div><div class='inf-r'>{rel}</div><div class='inf-w'>{abs_}</div></div>"
                  f"<div class='inf-d {kelas}'></div></div>")
    sheet = ""
    if buku:
        sheet = ("<div class='inf-s'><b>Google Sheet bulanan:</b> "
                 + "".join(f"<a href='{b['url']}' target='_blank'>{b['nama']}</a>" for b in buku) + "</div>")
    legenda = ("<div class='inf-l'><span><i class='d-ok'></i>Terbaru (0–2 hari)</span><span><i class='d-mid'></i>3–7 hari</span>"
               "<span><i class='d-old'></i>Lebih dari 7 hari</span><span><i class='d-no'></i>Belum pernah</span></div>")
    return (CSS_INFO + "<div class='inf'><div class='inf-h'><b>Informasi Update</b><span>kapan tiap data terakhir diperbarui</span></div>"
            f"<div class='inf-g'>{kartu}</div>{sheet}{legenda}</div>")



# ---------------------------------------------------------------- jendela
@st.dialog("INFORMASI")
def dlg_sukses(pesan):
    st.markdown(f"<h4 style='text-align:center'>{pesan}</h4>", unsafe_allow_html=True)
    if st.button("OK", width="stretch"):
        st.rerun()


def sukses(pesan, nama_file=None, verifikasi=True):
    """Catat update, tampilkan jendela berhasil. Bila ada karyawan yang belum diverifikasi,
    jendela verifikasi (✕) otomatis terbuka setelah OK."""
    with st.spinner("Menyimpan ke Google Sheet… tunggu sebentar, jangan klik lagi."):
        if nama_file:
            data.catat_update(nama_file)
        if nama_file in (None, "FILE HASIL KERJA", "LEMBUR", "JADWAL KERJA"):
            try:  # riwayat di Google Sheet; kegagalan tidak boleh menggagalkan upload
                data.sinkron_riwayat()
            except Exception as e:
                pesan += f" (riwayat Google Sheet belum terbarui: {type(e).__name__})"
    for w in data.peringatan_store():
        pesan += f" ⚠ {w}"
    st.session_state["sukses"] = pesan
    if verifikasi and logic.belum_diverifikasi():
        st.session_state["verif"] = True
    if nama_file in ("FILE HASIL KERJA", "JADWAL KERJA", "ABSENSI"):
        st.session_state["bel_buka"] = True  # tampilkan notifikasi ketidaksesuaian bila ada
    st.rerun()


@st.dialog("UPLOAD FILE HASIL KERJA", width="large")
def dlg_hasil():
    kontrol_jendela("hasil")
    kepala("hasil", "UPLOAD FILE HASIL KERJA")
    st.session_state["_frag_hasil"] = True
    pilih = pilih_bulan("hasil", judul="PILIH BULAN")
    f = st.file_uploader("Drag file SAP (Catatan Periksa) ke sini, atau klik Browse files", type=["xlsx"])
    if f is None:
        return
    try:
        df, catatan = _baca_sap(f.getvalue())
    except Exception as e:
        st.error(f"File tidak bisa dibaca: {e}")
        return
    st.write(f"**{len(df)} baris**, tanggal {df['tgl'].min()} sampai {df['tgl'].max()}, "
             f"{df['nama_sap'].nunique()} karyawan.")
    for c in catatan:
        st.warning(c)
    lama = {t for b in df["tgl"].str[:7].unique() for t in data.baca(f"hasil_{b}")["tgl"]}
    baru_t, timpa = sorted(set(df["tgl"]) - lama), sorted(set(df["tgl"]) & lama)
    st.info(f"Tanggal yang **menimpa data lama** (dilengkapi, tidak dobel): {len(timpa)}"
            + (f" ({timpa[0][8:]}–{timpa[-1][8:]})" if timpa else "")
            + f". Tanggal **baru**: {len(baru_t)}"
            + (f" ({baru_t[0][8:]}–{baru_t[-1][8:]})" if baru_t else "") + ".")
    luar = (df["tgl"].str[:7] != pilih).sum()
    if luar == len(df):
        bln = ", ".join(sorted(df["tgl"].str[:7].unique()))
        st.info(f"Tanggal di file ada di bulan {bln}, berbeda dari bulan yang dipilih. Data tetap disimpan sesuai tanggalnya.")
    elif luar:
        st.warning(f"{luar} baris memiliki tanggal di luar bulan yang dipilih. Baris itu tetap disimpan "
                   "pada bulannya masing-masing.")
    if st.button("UPLOAD", type="primary"):
        with st.spinner("Menyimpan ke Google Sheet… tunggu sebentar, jangan klik lagi."):
            try:
                data.simpan_hasil(df)
            except BukuBulananBelumAda as e:
                st.error(str(e))
                return
            sukses("FILE BERHASIL DI UPDATE", "FILE HASIL KERJA")


@st.dialog("DATA AWAL", width="large")
def dlg_awal():
    kontrol_jendela("awal")
    kepala("awal", "DATA AWAL")
    st.write("Upload **DATA_KARYAWAN.xlsx** dan **PENCAPAIAN_KERJA_QC.xlsx**. Cukup sekali di awal; ulangi hanya "
             "bila ada karyawan baru atau target berubah. Boleh salah satu saja.")
    fk = st.file_uploader("DATA_KARYAWAN.xlsx", type=["xlsx"], key="fk")
    ft = st.file_uploader("PENCAPAIAN_KERJA_QC.xlsx", type=["xlsx"], key="ft")
    if st.button("SIMPAN", type="primary", disabled=not (fk or ft)):
        st.info("Menyimpan ke Google Sheet… tunggu sebentar, jangan klik lagi.")
        try:
            hasil = []
            if fk:
                k = parsers.baca_karyawan(fk)
                data.tulis("karyawan", k)
                if k["jenis"].ne("").any():  # daftar tampil mengikuti jenis pekerjaan di file
                    data.tulis("roster", pd.DataFrame({"prn": k["prn"], "status": [
                        "ya" if logic.tampil_default(j) else "tidak" for j in k["jenis"]]}))
                hasil.append(f"{len(k)} karyawan")
            if ft:
                t = parsers.baca_target(ft)
                data.tulis("target", t)
                hasil.append(f"{len(t)} baris target")
        except Exception as e:
            st.error(f"File tidak bisa dibaca: {e}")
            return
        sukses("DATA BERHASIL DI UPDATE: " + ", ".join(hasil))


@st.cache_data(show_spinner="Membaca file…", max_entries=4)
def _baca_sap(isi):
    return parsers.baca_sap(io.BytesIO(isi))


@st.cache_data(show_spinner="Membaca file…", max_entries=6)
def _baca_jadwal(isi, bulan):
    return parsers.baca_jadwal(io.BytesIO(isi), bulan)


def _tabel_kosong(kolom, n):
    return pd.DataFrame({c: [None] * n for c in kolom})


@st.dialog("UPDATE DATA KARYAWAN OVERTIME", width="large")
def dlg_lembur():
    kontrol_jendela("lembur")
    kepala("lembur", "UPDATE DATA KARYAWAN OVERTIME")
    nama, prns = logic.peta_nama_prn(), logic.karyawan_semua()
    if not prns:
        st.warning("Belum ada karyawan. Upload data awal dan file hasil kerja SAP dulu.")
        return
    by_nama = {nama.get(p) or f'PRN {p} (belum ada di data karyawan)': p for p in prns}
    tgl = st.date_input("PILIH TANGGAL", value=date.today(), format="DD/MM/YYYY", key="lembur_tgl")
    iso = tgl.strftime("%Y-%m-%d")
    lm = data.baca("lembur")
    lm = lm[lm["tgl"] == iso]
    awal = pd.DataFrame({"NAMA": [nama.get(p, p) for p in lm["prn"]],
                         "WAKTU (JAM)": [float(x) for x in lm["jam"]]})
    awal = pd.concat([awal, _tabel_kosong(["NAMA", "WAKTU (JAM)"], max(0, 9 - len(awal)))], ignore_index=True)
    st.caption("Baris bertambah otomatis: isi baris terakhir, lalu klik baris kosong berikutnya. "
               "Kosongkan nama atau jam untuk menghapus lembur seseorang di tanggal ini.")
    ed = st.data_editor(awal, key=f"lembur_{iso}", num_rows="dynamic", hide_index=True, width="stretch",
                        column_config={
                            "NAMA": st.column_config.SelectboxColumn("NAMA", options=list(by_nama), width="large"),
                            "WAKTU (JAM)": st.column_config.NumberColumn("WAKTU (JAM)", min_value=0.0, max_value=12.0,
                                                                         step=0.5, format="%.1f"),
                        })
    if st.button("SUBMIT", type="primary"):
        baru = {}
        for n, j in zip(ed["NAMA"], ed["WAKTU (JAM)"]):
            p = by_nama.get(n)
            if p and pd.notna(j) and float(j) > 0:
                baru[p] = {"prn": p, "tgl": iso, "jam": f"{float(j):g}"}
        data.upsert("lembur", pd.DataFrame(list(baru.values()), columns=["prn", "tgl", "jam"]),
                    ["prn", "tgl"], hapus=lm[["prn", "tgl"]])
        sukses("DATA BERHASIL DI UPDATE", "LEMBUR")


@st.dialog("UPDATE ABSENSI KARYAWAN", width="large")
def dlg_absensi():
    kontrol_jendela("absensi")
    kepala("absensi", "UPDATE ABSENSI KARYAWAN")
    nama, prns = logic.peta_nama_prn(), logic.karyawan_semua()
    if not prns:
        st.warning("Belum ada karyawan. Upload data awal dan file hasil kerja SAP dulu.")
        return
    by_nama = {nama.get(p) or f'PRN {p} (belum ada di data karyawan)': p for p in prns}
    hari_ini = st.date_input("PILIH TANGGAL (satu hari)", value=date.today(), format="DD/MM/YYYY", key="abs_tgl")
    tanggal = [hari_ini.strftime("%Y-%m-%d")]
    ada = data.baca("absensi")
    ada = ada[ada["tgl"] == tanggal[0]]
    if len(ada):
        st.markdown(f"**Sudah tercatat di tanggal ini ({len(ada)}):**")
        for r in ada.itertuples():
            c = st.columns([3, 1.4, 3, 1.2], vertical_alignment="center")
            c[0].write(nama.get(r.prn, r.prn))
            c[1].write(logic.NAMA_ABSEN.get(r.kode, r.kode))
            c[2].write(r.keterangan or "")
            if c[3].button("HAPUS", key=f"abh_{r.prn}_{r.tgl}"):
                with st.spinner("Menghapus…"):
                    data.upsert("absensi", pd.DataFrame(columns=["prn", "tgl", "kode", "keterangan", "waktu"]),
                                ["prn", "tgl"], hapus=pd.DataFrame([{"prn": r.prn, "tgl": r.tgl}]))
                st.session_state["hapus_ok"] = "absensi"
                st.rerun()
        st.divider()
    st.caption("Tambah catatan baru untuk tanggal ini. Resign berlaku mulai tanggal ini dan seterusnya.")
    ed = st.data_editor(_tabel_kosong(["NAMA", "ABSENSI", "KETERANGAN"], 5), key="abs_tabel", num_rows="dynamic",
                        hide_index=True, width="stretch",
                        column_config={
                            "NAMA": st.column_config.SelectboxColumn("NAMA", options=list(by_nama), width="large"),
                            "ABSENSI": st.column_config.SelectboxColumn("ABSENSI", options=PILIHAN_ABSEN),
                            "KETERANGAN": st.column_config.TextColumn("KETERANGAN", width="large"),
                        })
    if st.button("UPLOAD", type="primary"):
        baru, hapus, waktu = [], [], data.sekarang()
        for n, a, k in zip(ed["NAMA"], ed["ABSENSI"], ed["KETERANGAN"]):
            p = by_nama.get(n)
            if not p or not a:
                continue
            hari = tanggal[:1] if a == "Resign" else tanggal
            for t in hari:
                if a == "Hapus catatan":
                    hapus.append({"prn": p, "tgl": t})
                else:
                    baru.append({"prn": p, "tgl": t, "kode": logic.KODE_ABSEN[a],
                                 "keterangan": "" if pd.isna(k) else str(k), "waktu": waktu})
        data.upsert("absensi", pd.DataFrame(baru, columns=["prn", "tgl", "kode", "keterangan", "waktu"]),
                    ["prn", "tgl"], hapus=pd.DataFrame(hapus, columns=["prn", "tgl"]))
        sukses("DATA BERHASIL DI UPDATE", "ABSENSI")


def _jadwal_manual(bulan):
    kepala("jadwal2", "SETTING MANUAL JADWAL KERJA")
    prns, nama = logic.karyawan_semua(), logic.peta_nama_prn()
    if not prns:
        st.warning("Belum ada karyawan dari file SAP.")
    else:
        n, default, jm = logic.n_hari(bulan), logic.hari_libur_default(bulan), logic.jadwal_peta(bulan)
        state = {p: "".join("X" if logic.libur(p, f"{bulan}-{d:02d}", bulan, jm, default) else "O"
                            for d in range(1, n + 1)) for p in prns}
        st.caption("Klik sel untuk mengganti: O = masuk, X = libur. Awalnya Sabtu dan Minggu libur.")
        nilai = jadwal_grid([{"id": p, "nama": nama.get(p, p)} for p in prns], state, list(range(1, n + 1)),
                            [d for d, v in default.items() if v], f"{bulan}-{len(prns)}", f"grid_{bulan}")
        if st.button("UPLOAD", type="primary", key="jm_upload"):
            akhir = nilai if nilai is not None else state
            baris = [(p, f"{bulan}-{i + 1:02d}", c) for p, s in akhir.items() for i, c in enumerate(s)]
            data.upsert("jadwal_" + bulan, pd.DataFrame(baris, columns=["prn", "tgl", "status"]), ["prn", "tgl"])
            sukses("JADWAL KERJA BERHASIL DI UPDATE", "JADWAL KERJA")
    if st.button("← Kembali", key="jm_back"):
        st.session_state["jd_manual"] = False
        st.rerun(scope="fragment")


@st.dialog("JADWAL KERJA KARYAWAN", width="large")
def dlg_jadwal():
    kontrol_jendela("jadwal")
    if not st.session_state.get("jd_manual"):
        kepala("jadwal", "JADWAL KERJA KARYAWAN")
    st.session_state["_frag_jadwal"] = True
    bulan = pilih_bulan("jadwal", judul="PILIH BULAN")
    if st.session_state.get("jd_manual"):
        _jadwal_manual(bulan)
        return
    valid = set(data.baca("karyawan")["prn"])
    fq = st.file_uploader("► Upload Jadwal Kerja QC disini", type=["xlsx"], key="jd_qc")
    fs = st.file_uploader("► Upload Jadwal Kerja SK disini", type=["xlsx"], key="jd_sk")
    hasil = []
    labels = []
    for label, f in (("QC", fq), ("SK", fs)):
        if f is None:
            continue
        try:
            df, catatan = _baca_jadwal(f.getvalue(), bulan)
        except Exception as e:
            st.error(f"Jadwal {label}: {e}")
            return
        ok = df  # semua orang di jadwal dicatat sebagai riwayat, walau belum/tidak ada di SAP
        st.write(f"Jadwal {label}: **{ok['prn'].nunique()} karyawan** terbaca untuk {nama_bulan(bulan)}.")
        for c in catatan:
            st.warning(f"Jadwal {label}: {c}")
        asing = df["prn"].nunique() - df["prn"].isin(valid).groupby(df["prn"]).any().sum()
        if asing:
            st.info(f"{asing} orang di jadwal {label} belum ada di data karyawan. Tetap dicatat (tampil dengan nomor PRN) sampai data karyawan diperbarui.")
        hasil.append(ok)
        labels.append(label)
    a, b = st.columns(2)
    if a.button("UPLOAD", type="primary", disabled=not hasil, width="stretch"):
        baru = pd.concat(hasil, ignore_index=True)
        try:
            data.upsert("jadwal_" + bulan, baru, ["prn", "tgl"])
        except BukuBulananBelumAda as e:
            st.error(str(e))
            return
        bag = pd.concat([pd.DataFrame({"prn": sorted(set(o["prn"])), "bagian": lb})
                         for o, lb in zip(hasil, labels)], ignore_index=True)
        data.upsert("bagian", bag, ["prn"])
        sukses("JADWAL KERJA BERHASIL DI UPDATE", "JADWAL KERJA")
    if b.button("⚙ SETTING MANUAL", width="stretch"):
        st.session_state["jd_manual"] = True
        st.rerun(scope="fragment")


# ---------------------------------------------------------------- verifikasi karyawan
@st.dialog("VERIFIKASI KARYAWAN", width="large")
def dlg_verif():
    kontrol_jendela("verif")
    kepala("awal", "VERIFIKASI DAFTAR PANTAU")
    u = logic.usulan_verifikasi()
    if u.empty:
        st.warning("Belum ada data karyawan. Upload data awal dulu.")
        return
    st.caption("Semua karyawan sudah **tercentang ✔ (tampil)**. Cukup **hilangkan centang** pada orang yang TIDAK boleh "
               "tampil di monitor (jadi ✕), lalu SIMPAN. Yang tidak ada di file SAP (DI SAP: —) diurutkan paling atas. "
               "Daftar ini dipakai di tabel monitor, Lembur, Absensi, dan Jadwal Kerja.")
    tabel = pd.DataFrame({"NAMA": u["nama"], "PRN": u["prn"],
                          "DI SAP": u["ada_sap"].map({True: "✔", False: "—"}),
                          "DI JADWAL": u["ada_jadwal"].map({True: "✔", False: "—"}),
                          "JENIS": u["jenis"], "BARU": u["baru"].map({True: "baru", False: ""}),
                          "TAMPIL ✔ / ✕": ~u["silang"]})
    ed = st.data_editor(tabel, hide_index=True, width="stretch", height=460, key="verif_ed",
                        disabled=["NAMA", "PRN", "JENIS", "DI SAP", "DI JADWAL", "BARU"],
                        column_config={"TAMPIL ✔ / ✕": st.column_config.CheckboxColumn("TAMPIL ✔ / ✕", width="small")})
    n_x = int((~ed["TAMPIL ✔ / ✕"]).sum())
    st.write(f"**{len(ed) - n_x} orang tampil**, {n_x} dikeluarkan.")
    if st.button("SIMPAN", type="primary", key="verif_simpan"):
        roster = pd.DataFrame({"prn": ed["PRN"], "status": ["ya" if x else "tidak" for x in ed["TAMPIL ✔ / ✕"]]})
        data.tulis("roster", roster)
        sukses("DAFTAR PANTAU BERHASIL DI SIMPAN", verifikasi=False)


# ---------------------------------------------------------------- lonceng
def cari_masalah():
    karyawan, alias, target = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    abaikan = set(data.baca("abaikan")["nama_sap"])
    kebal = data.baca("target_abaikan")
    kebal = set(zip(kebal["grup"], kebal["type"], kebal["op"]))
    peta = calc.peta_nama(karyawan, alias)
    baru, tanpa, bentrok = set(), [], []
    bulan_ada = data.daftar_bulan()[-3:]
    for b in bulan_ada:
        h = data.baca(f"hasil_{b}")
        h = h[~h["nama_sap"].isin(abaikan)]
        baru |= set(h["nama_sap"]) - set(peta)
        tanpa.append(calc.hitung_harian(h.assign(prn=h["nama_sap"].map(peta)), target)[1])
    lihat = set()
    for b in bulan_ada[-2:]:
        for m in logic.masalah_bulan(b):
            if (m["prn"], m["tgl"]) not in lihat:
                lihat.add((m["prn"], m["tgl"]))
                bentrok.append(m)
    tanpa = pd.concat(tanpa) if tanpa else pd.DataFrame()
    if len(tanpa):
        ok = [str(o) != logic.OP_TANPA_TARGET and (g, t, o) not in kebal  # OP107 = catatan otomatis
              for g, t, o in zip(tanpa["grup"], tanpa["type"], tanpa["op"])]
        tanpa = tanpa[ok]
        tanpa = tanpa.groupby(["grup", "type", "op"]).size().reset_index(name="baris")
    return sorted(baru), tanpa, bentrok


@st.cache_data(ttl=180, show_spinner=False, max_entries=2)
def masalah_cache(versi_data):
    """Hitungan berat (pemeriksaan masalah) hanya diulang bila data berubah, bukan tiap klik."""
    return cari_masalah()


def cari_label_belum():
    """Pasangan type SAP + warna di hasil kerja 3 bulan terakhir yang belum punya aturan jenis label."""
    tabel, baris = label.jenis_tabel(), []
    for b in data.daftar_bulan()[-3:]:
        h = data.baca(f"hasil_{b}")
        if h.empty:
            continue
        wr = h["SAP | Warna"] if "SAP | Warna" in h.columns else pd.Series([""] * len(h), index=h.index)
        baris.append(pd.DataFrame({"type": h["type"], "warna": wr.astype(str)}))
    if not baris:
        return pd.DataFrame(columns=["type", "warna", "baris"])
    d = pd.concat(baris).groupby(["type", "warna"]).size().reset_index(name="baris")
    ok = [label.label_untuk_sap(t, w, tabel)[1] for t, w in zip(d["type"], d["warna"])]
    return d[[not x for x in ok]].reset_index(drop=True)


@st.cache_data(ttl=180, show_spinner=False, max_entries=2)
def label_belum_cache(versi_data):
    return cari_label_belum()


def hitung_jumlah(baru, tanpa, bentrok):
    return (len(baru) + (1 if len(tanpa) else 0) + (1 if bentrok else 0) + (1 if logic.belum_diverifikasi() else 0)
            + (1 if len(label_belum_cache(data.versi())) else 0))


@st.dialog("PUSAT NOTIFIKASI", width="large")
def dlg_lonceng(baru, tanpa, bentrok):
    kontrol_jendela("lonceng")
    kepala("lonceng", "PUSAT NOTIFIKASI")
    karyawan, alias = data.baca("karyawan"), data.baca("alias")
    if not hitung_jumlah(baru, tanpa, bentrok):
        st.success("Tidak ada masalah.")
        return
    pending = logic.belum_diverifikasi()
    if pending:
        st.markdown(f"**{len(pending)} karyawan belum diverifikasi** (tampil di monitor atau disilang ✕).")
        if st.button("Verifikasi sekarang", key="n_verif", type="primary"):
            st.session_state["verif"] = True
            st.rerun()
        st.divider()
    by_nama = dict(zip(karyawan["nama_sap"], karyawan["prn"]))
    for n in baru:
        st.markdown(f"**Nama SAP belum cocok:** {n}")
        saran = difflib.get_close_matches(n, list(by_nama), n=3, cutoff=0.4) or sorted(by_nama)
        pilih = st.selectbox("Pasangkan dengan", saran, key=f"p_{n}")
        a, b = st.columns(2)
        if a.button("Pasangkan", key=f"a_{n}"):
            data.tulis("alias", pd.concat([alias, pd.DataFrame([{"nama_sap": n, "prn": by_nama[pilih]}])],
                                          ignore_index=True))
            st.rerun()
        if b.button("Abaikan", key=f"b_{n}"):
            ab = data.baca("abaikan")
            data.tulis("abaikan", pd.concat([ab, pd.DataFrame([{"nama_sap": n}])], ignore_index=True))
            st.rerun()
        st.divider()
    if len(tanpa):
        st.markdown("**Target belum ada** (tidak ikut dihitung). Pilih tindakan tiap baris lalu klik TERAPKAN. "
                    "OP107 tidak muncul di sini: otomatis menjadi catatan \"mengerjakan OP107\".")
        tbl = pd.DataFrame({"GRUP": tanpa["grup"], "TYPE": tanpa["type"], "OP": tanpa["op"], "BARIS": tanpa["baris"],
                            "ISI TARGET": [None] * len(tanpa), "ABAIKAN": False, "HAPUS DATA": False})
        ed = st.data_editor(tbl, hide_index=True, width="stretch", key="tgt_ed",
                            disabled=["GRUP", "TYPE", "OP", "BARIS"],
                            column_config={"ISI TARGET": st.column_config.NumberColumn("ISI TARGET", min_value=1, step=1),
                                           "ABAIKAN": st.column_config.CheckboxColumn("ABAIKAN"),
                                           "HAPUS DATA": st.column_config.CheckboxColumn("HAPUS DATA")})
        st.caption("ISI TARGET: target per hari (8 jam), langsung dipakai menghitung. ABAIKAN: tidak muncul lagi di sini. "
                   "HAPUS DATA: baris hasil kerja itu dibuang dari data SAP.")
        if st.button("TERAPKAN", type="primary", key="tgt_ok"):
            isi, ign, hps = [], [], []
            for _, r in ed.iterrows():
                kunci = {"grup": r["GRUP"], "type": r["TYPE"], "op": r["OP"]}
                if r["HAPUS DATA"]:
                    hps.append(kunci)
                elif pd.notna(r["ISI TARGET"]):
                    isi.append({**kunci, "target": f"{float(r['ISI TARGET']):g}"})
                elif r["ABAIKAN"]:
                    ign.append(kunci)
            if isi:
                data.upsert("target", pd.DataFrame(isi, columns=["grup", "type", "op", "target"]), ["grup", "type", "op"])
            if ign:
                data.upsert("target_abaikan", pd.DataFrame(ign, columns=["grup", "type", "op"]), ["grup", "type", "op"])
            if hps:
                kh = {(k["grup"], k["type"], k["op"]) for k in hps}
                for b in data.daftar_bulan():
                    h = data.baca(f"hasil_{b}")
                    keep = [(g, t, o) not in kh for g, t, o in zip(h["grup"], h["type"], h["op"])]
                    if not all(keep):
                        data.tulis(f"hasil_{b}", h[keep])
            st.rerun()
        st.divider()
    belum_label = label_belum_cache(data.versi())
    if len(belum_label):
        st.markdown(f"**Type / warna belum punya jenis label ({len(belum_label)}).** Pilih label yang sesuai atau "
                    "\"TANPA LABEL\", lalu TERAPKAN. Type baru yang labelnya belum ada: tambahkan dulu di "
                    "*Jenis label* (bagian bawah halaman admin).")
        TANPA = "— TANPA LABEL —"
        opsi = [TANPA] + [x for v in label.type_per_kategori().values() for x in v]
        tb = pd.DataFrame({"TYPE": belum_label["type"], "WARNA": belum_label["warna"], "BARIS": belum_label["baris"],
                           "LABEL": [None] * len(belum_label)})
        ed = st.data_editor(tb, hide_index=True, width="stretch", key="lbl_ed", disabled=["TYPE", "WARNA", "BARIS"],
                            column_config={"LABEL": st.column_config.SelectboxColumn("LABEL", options=opsi)})
        if st.button("TERAPKAN", type="primary", key="lbl_ok"):
            jt, baru_baris = label.jenis_tabel(), []
            for _, r in ed.iterrows():
                if not r["LABEL"]:
                    continue
                lb = "" if r["LABEL"] == TANPA else r["LABEL"]
                ada = jt[jt["label"] == lb] if lb else jt.iloc[0:0]
                baru_baris.append({"kategori": ada.iloc[0]["kategori"] if len(ada) else "", "label": lb, "type_sap": r["TYPE"],
                                   "warna": r["WARNA"], "sni": "ya" if (len(ada) and (ada["sni"].str.lower() == "ya").any()) else "",
                                   "ket": ""})
            if baru_baris:
                data.tulis("jenis_label", pd.concat([jt, pd.DataFrame(baru_baris)], ignore_index=True))
            st.session_state["bel_buka"] = True
            st.rerun()
        st.divider()
    if bentrok:
        st.markdown(f"**Hasil kerja tidak sesuai jadwal atau absensi ({len(bentrok)} kasus).** Dicocokkan dengan "
                    "*hari kerja sebenarnya* (Transaction Date). Bila tanggal posting berbeda, pilih apakah hasilnya "
                    "masuk di tanggal kerja atau tetap di tanggal posting. "
                    "Pilih keputusan, lalu **TERAPKAN** (satu baris) atau **TERAPKAN SEMUA**.")
        PINDAH = "Hasil masuk tanggal kerja (jadwal jadi MASUK)"
        pil = {"libur": ["Ubah jadwal jadi MASUK", "Abaikan"],
               "libur_pindah": [PINDAH, "Tetap di tanggal posting"],
               "absen": ["Abaikan", "Hapus catatan absen"],
               "resign": ["Abaikan"]}
        lebar = [2.3, 1.3, 3.6, 2.3, 1.3]
        for c, t in zip(st.columns(lebar), ["NAMA", "TGL KERJA", "MASALAH", "KEPUTUSAN", ""]):
            c.markdown(f"**{t}**")
        pilihan = []
        for n, m in enumerate(bentrok):
            k = st.columns(lebar, vertical_alignment="center")
            k[0].write(m["nama"])
            k[1].write(m["tgl"])
            k[2].write(m["ket"])
            kep = k[3].selectbox("keputusan", pil[m["jenis"] + ("_pindah" if m["jenis"] == "libur" and m.get("beda") else "")], key=f"kep_{m['prn']}_{m['tgl']}", label_visibility="collapsed")
            pilihan.append((m, kep))
            if k[4].button("TERAPKAN", key=f"ok_{m['prn']}_{m['tgl']}"):
                _terapkan([(m, kep)])
        if st.button("TERAPKAN SEMUA", type="primary", key="ok_semua"):
            _terapkan(pilihan)


def _terapkan(daftar):
    """Jalankan keputusan admin untuk ketidaksesuaian jadwal/absensi, hitung ulang, lalu buka lagi lonceng."""
    ubah, hapus_abs, abaikan, pindah = {}, [], [], []
    for m, kep in daftar:
        if kep.startswith("Hasil masuk tanggal kerja"):
            pindah.append({"prn": m["prn"], "tgl": m["tgl"]})
            ubah.setdefault(m["bulan"], []).append({"prn": m["prn"], "tgl": m["tgl"], "status": "O"})
        elif kep == "Tetap di tanggal posting":
            abaikan.append({"prn": m["prn"], "tgl": m["tgl"]})
        elif kep == "Ubah jadwal jadi MASUK":
            ubah.setdefault(m["bulan"], []).append({"prn": m["prn"], "tgl": m["tgl"], "status": "O"})
        elif kep == "Hapus catatan absen":
            hapus_abs.append({"prn": m["prn"], "tgl": m["tgl"]})
        elif kep == "Abaikan":
            abaikan.append({"prn": m["prn"], "tgl": m["tgl"]})
    with st.spinner("Menerapkan keputusan…"):
        for bln, baris in ubah.items():
            data.upsert("jadwal_" + bln, pd.DataFrame(baris), ["prn", "tgl"])
        if pindah:
            data.upsert("pindah_hasil", pd.DataFrame(pindah), ["prn", "tgl"])
        if hapus_abs:
            data.upsert("absensi", pd.DataFrame(columns=["prn", "tgl", "kode", "keterangan", "waktu"]),
                        ["prn", "tgl"], hapus=pd.DataFrame(hapus_abs))
        if abaikan:
            data.upsert("masalah_abaikan", pd.DataFrame(abaikan), ["prn", "tgl"])
        if ubah:
            data.catat_update("JADWAL KERJA")
        try:
            data.sinkron_riwayat()
        except Exception:
            pass
    st.session_state["toast"] = f"{len(daftar)} keputusan diterapkan."
    st.session_state["bel_buka"] = True
    st.rerun()


@st.dialog("EVALUASI KARYAWAN", width="large")
def dlg_eval():
    kontrol_jendela("eval")
    kepala("evaluasi", "HALAMAN VERIFIKASI KARYAWAN")
    st.markdown("""<style>
[class*='st-key-evV_'] button{background:#1a9c3c !important;color:#fff !important;border:2px solid #000 !important;font-weight:800}
[class*='st-key-evX_'] button{background:#d50000 !important;color:#fff !important;border:2px solid #000 !important;font-weight:800}
[class*='st-key-evU_'] button{min-height:0;padding:0 .4rem}
[class*='st-key-evV_'] button,[class*='st-key-evX_'] button{min-width:2.2rem;padding:0 .5rem}
</style>""", unsafe_allow_html=True)
    semua = st.toggle("Tampilkan juga yang sudah diputuskan", key="ev_semua")
    antre = logic.antrean_evaluasi(semua)
    if not antre:
        st.info("Belum ada pengajuan alasan tidak target yang menunggu keputusan.")
        return
    st.caption("V = atasan menerima: target hari itu dikurangi sebesar waktu masalah. X = menolak: target 8 jam tetap, hasil tetap merah. "
               "Setelah dipilih, tombol lain hilang (klik 'ubah' untuk memilih ulang). Lalu tekan SUBMIT.")
    lebar = [2.2, 1.3, 1.0, 3.2, 0.8, 3.0]
    for c, t in zip(st.columns(lebar), ["NAMA", "TANGGAL", "% HASIL", "ALASAN", "MENIT", "KEPUTUSAN"]):
        c.markdown(f"**{t}**")
    pilih = {}
    for r in antre:
        kid = f"{r['prn']}_{r['tgl']}"
        sekarang_ = st.session_state.get(f"ev_{kid}", "?")
        if sekarang_ == "?":
            sekarang_ = r["status"] if r["status"] in ("V", "X") else None
        c = st.columns(lebar, vertical_alignment="center")
        c[0].write(r["nama"])
        c[1].write(f"{r['tgl'][8:]}-{r['tgl'][5:7]}-{r['tgl'][:4]}")
        c[2].write(f"{r['persen']:.1f}%".replace(".", ",") if r["persen"] is not None else "-")
        c[3].write(r["alasan"] or "–")
        c[4].write(r["menit"])
        with c[5]:
            k1, k2, k3 = st.columns([1, 1, 1], vertical_alignment="center", gap="small")
            if sekarang_ is None:
                if k1.button("V", key=f"evV_{kid}"):
                    st.session_state[f"ev_{kid}"] = "V"
                    st.rerun(scope="fragment")
                if k2.button("X", key=f"evX_{kid}"):
                    st.session_state[f"ev_{kid}"] = "X"
                    st.rerun(scope="fragment")
            else:
                warna = "#1a9c3c" if sekarang_ == "V" else "#d50000"
                k1.markdown(f"<span style='background:{warna};color:#fff;border:2px solid #000;border-radius:6px;padding:2px 12px;"
                            f"font-weight:800'>{sekarang_}</span>", unsafe_allow_html=True)
                if k2.button("ubah", key=f"evU_{kid}"):
                    st.session_state[f"ev_{kid}"] = None
                    st.rerun(scope="fragment")
                pilih[(r["prn"], r["tgl"])] = sekarang_
            with k3.popover("hapus"):
                st.write("Hapus pengajuan ini beserta foto? (Tidak bisa dibatalkan.)")
                if st.button("YA, HAPUS", key=f"evH_{kid}", type="primary"):
                    with st.spinner("Menghapus…"):
                        data.hapus_pengajuan(r["prn"], r["tgl"])
                    st.session_state["hapus_ok"] = "eval"
                    st.rerun()
    st.write("")
    ubah = {k: v for k, v in pilih.items() if v in ("V", "X")}
    if st.button(f"SUBMIT ({len(ubah)})", type="primary", width="stretch", disabled=not ubah):
        with st.spinner("Menyimpan keputusan…"):
            logic.simpan_keputusan(ubah)
            data.catat_update("EVALUASI KARYAWAN")
            try:
                data.sinkron_riwayat()
            except Exception:
                pass
        for k in list(st.session_state):
            if k.startswith("ev_") and k != "ev_semua":
                del st.session_state[k]
        st.session_state["sukses"] = "KEPUTUSAN BERHASIL DISIMPAN"
        st.rerun()



# ---------------------------------------------------------------- jenis label
_KOL_JL = {"kategori": "Kategori", "label": "Label", "type_sap": "Type SAP", "warna": "Warna SAP", "sni": "SNI", "ket": "Keterangan"}


def _jl_ke_tabel(df):
    """Tabel editor/Excel -> bentuk simpanan. Baris tanpa Type SAP dibuang; SNI jadi 'ya' atau kosong."""
    d = df.rename(columns={v: k for k, v in _KOL_JL.items()}).copy()
    for c in _KOL_JL:
        if c not in d.columns:
            d[c] = ""
    d = d[list(_KOL_JL)].fillna("")
    d["sni"] = d["sni"].map(lambda x: "ya" if str(x).strip().lower() in ("ya", "true", "1", "y", "sni") else "")
    d = d.astype(str).apply(lambda c: c.str.strip())
    d["type_sap"] = d["type_sap"].str.upper().str.replace(r"\s+", " ", regex=True)
    d["warna"] = d["warna"].str.upper()
    return d[d["type_sap"] != ""].reset_index(drop=True)


def kelola_jenis_label():
    st.caption("Pemetaan **Type SAP + Warna → Label**. Label ini yang muncul di jendela Input Label Afkir dan dipakai mencocokkan "
               "hasil SAP. *Warna SAP* kosong = berlaku untuk semua warna. *Label* kosong = type itu tidak punya label. "
               "*SNI* dicentang = label itu punya label SNI pendamping. Klik baris kosong paling bawah untuk menambah.")
    t = label.jenis_tabel()
    tampil = t.assign(sni=t["sni"].str.lower() == "ya").rename(columns=_KOL_JL)
    ed = st.data_editor(tampil, num_rows="dynamic", hide_index=True, width="stretch", key="jl_ed", height=380,
                        column_config={"Kategori": st.column_config.SelectboxColumn("Kategori", options=label.KATEGORI),
                                       "SNI": st.column_config.CheckboxColumn("SNI")})
    c1, c2 = st.columns(2)
    if c1.button("SIMPAN JENIS LABEL", type="primary", key="jl_simpan", width="stretch"):
        hasil = _jl_ke_tabel(ed)
        data.tulis("jenis_label", hasil)
        st.success(f"Tersimpan: {len(hasil)} baris, {len({x for x in hasil['label'] if x})} jenis label.")
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        t.rename(columns=_KOL_JL).to_excel(w, index=False, sheet_name="Jenis label")
    c2.download_button("Unduh Excel jenis label", buf.getvalue(), "jenis_label.xlsx", key="jl_unduh", width="stretch",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    f = st.file_uploader("Atau unggah Excel jenis label (kolom: Kategori, Label, Type SAP, Warna SAP, SNI, Keterangan)",
                         type=["xlsx"], key="jl_file")
    if f is not None:
        try:
            baru = _jl_ke_tabel(pd.read_excel(f, dtype=str))
        except Exception as e:
            st.error(f"File tidak bisa dibaca: {e}")
            return
        st.write(f"Terbaca **{len(baru)} baris**, {len({x for x in baru['label'] if x})} jenis label. Ini akan **menggantikan** tabel sekarang.")
        if st.button("GANTI TABEL DENGAN FILE INI", key="jl_ganti"):
            data.tulis("jenis_label", baru)
            st.success("Tabel jenis label diganti.")
            st.rerun()


# ---------------------------------------------------------------- halaman
def halaman_admin():
    akses.butuh(akses.ADMIN)
    st.markdown(CSS, unsafe_allow_html=True)
    gaya_global()
    gaya_responsif()
    akses.bilah(PG_FOREMAN, "Ke halaman Foreman")
    belum_ada = data.baca("karyawan").empty or data.baca("target").empty
    baru, tanpa, bentrok = ([], pd.DataFrame(), []) if belum_ada else masalah_cache(data.versi())
    jumlah = hitung_jumlah(baru, tanpa, bentrok) if not belum_ada else 0

    if st.session_state.get("toast"):
        st.toast(st.session_state.pop("toast"), icon="✅")
    pesan = st.session_state.pop("sukses", None)
    if pesan:
        dlg_sukses(pesan)
    elif st.session_state.pop("verif", False):
        dlg_verif()
    elif st.session_state.pop("bel_buka", False) and jumlah:
        dlg_lonceng(baru, tanpa, bentrok)
    elif not belum_ada and data.baca("roster").empty and not st.session_state.get("verif_ditawari"):
        st.session_state["verif_ditawari"] = True  # sekali per sesi: daftar pantau belum pernah diverifikasi
        dlg_verif()

    st.markdown("<h1 class='judul'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)

    atas1, atas2 = st.columns([1, 6])
    with atas1, st.container(key="lonceng"):
        if st.button("🔔" + (f" :red-badge[{jumlah}]" if jumlah else ""), key="bel"):
            dlg_lonceng(baru, tanpa, bentrok)
    with atas2, st.container(key="awal"):
        if st.button("Verifikasi", icon=":material/how_to_reg:"):
            st.session_state["max_verif"] = False
            dlg_verif()

    @st.dialog("BERHASIL")
    def dlg_hapus_ok(kembali):
        st.markdown("<h3 style='text-align:center;margin:1.2rem 0'>DATA BERHASIL DI HAPUS</h3>", unsafe_allow_html=True)
        if st.button("OK", type="primary", width="stretch"):
            st.session_state["buka_tes"] = {"id": kembali, "n": time.time()}  # kembali ke jendela asal
            st.rerun()


    if st.session_state.get("hapus_ok"):
        dlg_hapus_ok(st.session_state.pop("hapus_ok"))

    log = data.baca("update_log")
    log = dict(zip(log["nama_file"], log["waktu"]))

    def _terakhir(n):
        return "Terakhir: " + log[n] if log.get(n) else "Belum pernah"
    kar = data.baca("karyawan")
    jml_op = len(label.operator_daftar()) if not belum_ada else 0
    MENU = {"hasil": ("HASIL KERJA", "Upload file SAP (Catatan Periksa)", "bars", dlg_hasil, "Terakhir update", _terakhir("FILE HASIL KERJA")),
            "lembur": ("LEMBUR", "Input jam lembur karyawan", "clock", dlg_lembur, "Terakhir update", _terakhir("LEMBUR")),
            "absensi": ("ABSENSI", "Input sakit, ijin, cuti, dispen, resign", "calc", dlg_absensi, "Terakhir update", _terakhir("ABSENSI")),
            "jadwal": ("JADWAL KERJA", "Upload jadwal QC dan QC SK", "cal", dlg_jadwal, "Terakhir update", _terakhir("JADWAL KERJA")),
            "eval": ("EVALUASI", "Verifikasi alasan tidak target", "check", dlg_eval, "Terakhir update", _terakhir("EVALUASI KARYAWAN")),
            "awal": ("DATA AWAL", "Data karyawan dan target", "db", dlg_awal, "Status", f"{len(kar)} karyawan terdaftar"),
            "operator": ("DAFTAR OPERATOR", "Daftarkan operator untuk Input Label Afkir", "user", halaman_foreman.dlg_operator, "Status", f"{jml_op} operator"),
            "rencana": ("RENCANA PRODUKSI", "Rencana produksi per type", "doc", None, "Status", "Segera")}
    daftar = [{"id": k, "label": v[0], "sub": v[1], "icon": v[2], "status_label": v[4], "status": v[5], "disabled": v[3] is None}
              for k, v in MENU.items()]
    klik = roda(daftar, start=st.session_state.get("roda_id"), key="roda")
    klik = st.session_state.pop("buka_tes", None) or klik
    if klik and klik.get("n") != st.session_state.get("hub_n"):
        st.session_state["hub_n"] = klik.get("n")
        st.session_state["roda_id"] = klik["id"]
        fungsi = MENU[klik["id"]][3]
        if fungsi:
            st.session_state[f"max_{klik['id']}"] = False
            st.session_state["jd_manual"] = False
            if klik["id"] == "operator":
                st.session_state.pop("op_daftar", None)
            fungsi()

    if belum_ada:
        st.warning("Data karyawan dan target belum ada. Klik **Data awal** dan upload dua file Excel-nya.")
    buku = data.info_buku()
    st.markdown(_html_info(log, buku), unsafe_allow_html=True)
    if data.pakai_google_sheet():
        with st.expander("Hubungkan Google Sheet bulanan"):
            st.caption("Master (sheet_id di Secrets) tidak perlu diganti. Tiap bulan buat Google Sheet kosong, bagikan ke akun layanan "
                       "sebagai Editor, lalu tempel linknya di sini. Data bulan itu (hasil, jadwal, lembur, absensi, alasan + foto) tersimpan di sana.")
            bl_ini = datetime.now(data.WIB).strftime("%Y-%m")
            pilihan = [f"{th}-{bl:02d}" for th in (datetime.now(data.WIB).year - 1, datetime.now(data.WIB).year, datetime.now(data.WIB).year + 1) for bl in range(1, 13)]
            c1, c2 = st.columns([1, 3])
            bl_pilih = c1.selectbox("Bulan", pilihan, index=pilihan.index(bl_ini), key="hub_bulan")
            link = c2.text_input("Link Google Sheet bulan ini", key="hub_link", placeholder="https://docs.google.com/spreadsheets/d/…")
            if st.button("Hubungkan", key="hub_btn", disabled=not link.strip()):
                try:
                    st.success(f"Terhubung: {data.hubungkan_buku(bl_pilih, link)} → bulan {bl_pilih}. Data baru bulan itu disimpan di sana.")
                except ValueError as e:
                    st.error(str(e))
    with st.expander("Jenis label (tambah / ubah / unggah Excel)"):
        kelola_jenis_label()
    if data.pakai_google_sheet() and buku:
        with st.expander("Rapikan Sheet utama (pindahkan data bulan ke file bulanannya)"):
            st.caption("Alat ini AMAN: langkah Salin tidak menghapus apa pun; langkah Hapus hanya menghapus tab di Sheet utama yang "
                       "datanya sudah lengkap di file bulan. Sebelum menghapus, buat salinan Sheet utama di Google Drive.")
            bl_r = st.selectbox("Bulan", [b["bulan"] for b in buku], key="rp_bulan")
            if st.button("1. Periksa", key="rp_cek"):
                st.session_state["rp_hasil"] = (bl_r, data.rapikan("periksa", bl_r))
            hs = st.session_state.get("rp_hasil")
            if hs and hs[0] == bl_r:
                ket = {"aman": "✅ lengkap di file bulan (boleh dihapus dari master)", "salin": "⚠ belum lengkap di file bulan → klik Salin",
                       "kosong": "— tidak ada di master"}
                st.table(pd.DataFrame([{"Tabel": x["tabel"], "Baris di master": x["master"], "Baris di file bulan": x["buku"], "Status": ket[x["status"]]}
                                       for x in hs[1]]))
                if any(x["status"] == "salin" for x in hs[1]) and st.button("2. Salin yang belum ada ke file bulan", key="rp_salin"):
                    with st.spinner("Menyalin…"):
                        n = data.rapikan("salin", bl_r)
                    st.session_state["rp_hasil"] = (bl_r, data.rapikan("periksa", bl_r))
                    st.success(f"{n} tabel disalin. Klik Periksa lagi untuk memastikan.")
                    st.rerun()
                if any(x["status"] == "aman" for x in hs[1]):
                    oke = st.checkbox("Saya sudah membuat salinan Sheet utama di Google Drive", key="rp_oke")
                    if st.button("3. Hapus salinan lama di master", key="rp_hapus", disabled=not oke):
                        with st.spinner("Menghapus…"):
                            dihapus = data.rapikan("hapus", bl_r)
                        st.session_state.pop("rp_hasil", None)
                        st.success("Dihapus dari master: " + (", ".join(dihapus) or "tidak ada"))
    if data.pakai_google_sheet():
        with st.expander("Uji jejak Google Sheet"):
            st.caption("Menulis satu baris uji ke tab ALASAN TIDAK TARGET bulan ini untuk memastikan jejak email bisa tersimpan.")
            if st.button("Tulis baris uji", key="tes_jejak"):
                ok_, pesan_ = data.tes_jejak()
                (st.success if ok_ else st.error)(pesan_)


# ---------------------------------------------------------------- navigasi menurut peran
akses.gerbang()
_p = akses.peran()
PG_ADMIN = st.Page(halaman_admin, title="Upload Admin", url_path="upload-admin", icon=":material/upload_file:",
                   default=_p == akses.ADMIN)
PG_FOREMAN = st.Page(lambda: halaman_foreman.tampil(PG_ADMIN if _p == akses.ADMIN else None), title="Upload Foreman",
                     url_path="upload-foreman", icon=":material/fact_check:", default=_p == akses.FOREMAN)
# foreman hanya diberi halaman Foreman: halaman admin tidak terdaftar sama sekali untuk sesi itu
st.navigation([PG_ADMIN, PG_FOREMAN] if _p == akses.ADMIN else [PG_FOREMAN], position="hidden").run()
