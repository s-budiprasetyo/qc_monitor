"""Halaman admin (Welcome Admin QC TOTO). Jalankan: streamlit run app_admin.py"""
import difflib
import io
import hmac
from datetime import date

import pandas as pd
import streamlit as st

from core import calc, data, logic, parsers
from core.grid import jadwal_grid
from core.hub import hub
from core.ui import ikon, kepala, kontrol_jendela

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


# ---------------------------------------------------------------- gerbang admin
def gerbang():
    """Hanya admin: akun Google yang terdaftar (bila login Google aktif) + user dan password."""
    try:
        adm = st.secrets.get("admin")
    except Exception:  # file secrets belum ada
        adm = None
    if not adm:
        st.error("Pengaturan [admin] belum ada di secrets. Halaman admin dikunci.")
        st.stop()
    if "auth" in st.secrets:  # login Google aktif
        if not st.user.is_logged_in:
            st.title("WELCOME ADMIN QC TOTO")
            st.button("Masuk dengan Google", on_click=st.login)
            st.stop()
        if st.user.email.lower() not in [e.lower() for e in adm.get("emails", [])]:
            st.error("Akun ini tidak punya akses admin.")
            st.button("Keluar", on_click=st.logout)
            st.stop()
    if not st.session_state.get("admin_ok"):
        st.markdown("<h1 class='judul'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)
        with st.form("login"):
            u, p = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                if hmac.compare_digest(u.encode(), str(adm["user"]).encode()) and hmac.compare_digest(p.encode(), str(adm["password"]).encode()):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                st.error("User atau password salah.")
        st.stop()


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
    daftar, idx = pilihan_bulan()
    pilih = st.selectbox("PILIH BULAN", daftar, index=idx, format_func=nama_bulan)
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
            data.simpan_hasil(df)
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
    nama, prns = logic.peta_nama_prn(), logic.karyawan_dikenal()
    if not prns:
        st.warning("Belum ada karyawan. Upload data awal dan file hasil kerja SAP dulu.")
        return
    by_nama = {nama.get(p, p): p for p in prns}
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
    nama, prns = logic.peta_nama_prn(), logic.karyawan_dikenal()
    if not prns:
        st.warning("Belum ada karyawan. Upload data awal dan file hasil kerja SAP dulu.")
        return
    by_nama = {nama.get(p, p): p for p in prns}
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
                data.upsert("absensi", pd.DataFrame(columns=["prn", "tgl", "kode", "keterangan", "waktu"]),
                            ["prn", "tgl"], hapus=pd.DataFrame([{"prn": r.prn, "tgl": r.tgl}]))
                try:
                    data.sinkron_riwayat()
                except Exception:
                    pass
                st.rerun(scope="fragment")
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
    prns, nama = logic.karyawan_dikenal(), logic.peta_nama_prn()
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
    daftar, idx = pilihan_bulan()
    bulan = st.selectbox("PILIH BULAN", daftar, index=idx, format_func=nama_bulan, key="jd_bulan")
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
        ok = df[df["prn"].isin(valid)]
        st.write(f"Jadwal {label}: **{ok['prn'].nunique()} karyawan** terbaca untuk {nama_bulan(bulan)}.")
        for c in catatan:
            st.warning(f"Jadwal {label}: {c}")
        lewat = df["prn"].nunique() - ok["prn"].nunique()
        if lewat:
            st.info(f"{lewat} orang di jadwal {label} tidak ada di data karyawan dan diabaikan.")
        hasil.append(ok)
        labels.append(label)
    a, b = st.columns(2)
    if a.button("UPLOAD", type="primary", disabled=not hasil, width="stretch"):
        baru = pd.concat(hasil, ignore_index=True)
        data.upsert("jadwal_" + bulan, baru, ["prn", "tgl"])
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


def hitung_jumlah(baru, tanpa, bentrok):
    return len(baru) + (1 if len(tanpa) else 0) + (1 if bentrok else 0) + (1 if logic.belum_diverifikasi() else 0)


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
                    data.hapus_pengajuan(r["prn"], r["tgl"])
                    try:
                        data.sinkron_riwayat()
                    except Exception:
                        pass
                    st.rerun(scope="fragment")
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



# ---------------------------------------------------------------- halaman
gerbang()
st.markdown(CSS, unsafe_allow_html=True)
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

atas1, atas2, atas3 = st.columns([1, 3, 3])
with atas1, st.container(key="lonceng"):
    if st.button("🔔" + (f" :red-badge[{jumlah}]" if jumlah else ""), key="bel"):
        dlg_lonceng(baru, tanpa, bentrok)
atas2.markdown("<div class='judul-update'>UPDATE DATA</div>", unsafe_allow_html=True)
with atas3, st.container(key="awal"):
    c0, c1, c2 = st.columns([1.3, 1.2, 1])
    if c0.button("Verifikasi", icon=":material/how_to_reg:", width="stretch"):
        st.session_state["max_verif"] = False
        dlg_verif()
    if c1.button("Data awal", icon=":material/settings:", width="stretch"):
        st.session_state["max_awal"] = False
        dlg_awal()
    if c2.button("Keluar", width="stretch"):
        st.session_state["admin_ok"] = False
        st.rerun()

MENU = {"hasil": ("HASIL KERJA", dlg_hasil, "hasil", False),
        "lembur": ("LEMBUR", dlg_lembur, "lembur", False),
        "eval": ("EVALUASI KARYAWAN", dlg_eval, "evaluasi", False),
        "absensi": ("ABSENSI", dlg_absensi, "absensi", False),
        "jadwal": ("JADWAL KERJA", dlg_jadwal, "jadwal", False)}
klik = hub([{"id": k, "label": v[0], "icon": ikon(v[2]), "disabled": v[3]} for k, v in MENU.items()], key="hub")
klik = klik or st.session_state.pop("buka_tes", None)
if klik and klik.get("n") != st.session_state.get("hub_n"):
    st.session_state["hub_n"] = klik.get("n")
    _, fungsi, _, mati = MENU[klik["id"]]
    if fungsi and not mati:
        st.session_state[f"max_{klik['id']}"] = False
        st.session_state["jd_manual"] = False
        fungsi()

if belum_ada:
    st.warning("Data karyawan dan target belum ada. Klik **Data awal** dan upload dua file Excel-nya.")
log = data.baca("update_log")
log = dict(zip(log["nama_file"], log["waktu"]))
baris = "".join(f"<tr><td>{n}</td><td class='w'>{log.get(n, '-')}</td></tr>" for n in FILE_INFO)
st.markdown("<h4 class='info'>► INFORMASI</h4><table class='info'><tr><th>NAMA FILE</th>"
            f"<th>TERAKHIR UPDATE</th></tr>{baris}</table>", unsafe_allow_html=True)
