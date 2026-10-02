"""Halaman admin (Welcome Admin QC TOTO). Jalankan: streamlit run app_admin.py"""
import difflib
import hmac
from datetime import date
import pandas as pd
import streamlit as st
from core import calc, data, parsers

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]
FILE_INFO = ["FILE HASIL KERJA", "LEMBUR", "EVALUASI KARYAWAN", "ABSENSI", "JADWAL KERJA"]

st.set_page_config(page_title="Welcome Admin QC TOTO", layout="wide")


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
        st.title("WELCOME ADMIN QC TOTO")
        with st.form("login"):
            u, p = st.text_input("User"), st.text_input("Password", type="password")
            if st.form_submit_button("Masuk"):
                if hmac.compare_digest(u, str(adm["user"])) and hmac.compare_digest(p, str(adm["password"])):
                    st.session_state["admin_ok"] = True
                    st.rerun()
                st.error("User atau password salah.")
        st.stop()


def pilihan_bulan():
    t, daftar = date.today(), []
    for k in range(-8, 2):
        n = t.year * 12 + t.month - 1 + k
        daftar.append(f"{n // 12}-{n % 12 + 1:02d}")
    return daftar, daftar.index(f"{t.year}-{t.month:02d}")


def cari_masalah():
    karyawan, alias, target = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    abaikan = set(data.baca("abaikan")["nama_sap"])
    peta = calc.peta_nama(karyawan, alias)
    baru, tanpa = set(), []
    for b in data.daftar_bulan()[-3:]:
        h = data.baca(f"hasil_{b}")
        h = h[~h["nama_sap"].isin(abaikan)]
        baru |= set(h["nama_sap"]) - set(peta)
        tanpa.append(calc.hitung_harian(h.assign(prn=h["nama_sap"].map(peta)), target)[1])
    tanpa = pd.concat(tanpa) if tanpa else pd.DataFrame()
    if len(tanpa):
        tanpa = tanpa.groupby(["grup", "type", "op"]).size().reset_index(name="baris")
    return sorted(baru), tanpa


@st.dialog("UPLOAD FILE HASIL KERJA", width="large")
def dlg_hasil():
    daftar, idx = pilihan_bulan()
    pilih = st.selectbox("PILIH BULAN", daftar, index=idx,
                         format_func=lambda k: f"{BULAN[int(k[5:]) - 1]} {k[:4]}")
    f = st.file_uploader("Drag file SAP (Catatan Periksa) ke sini, atau klik Browse files", type=["xlsx"])
    if f is None:
        return
    try:
        df, catatan = parsers.baca_sap(f)
    except Exception as e:
        st.error(f"File tidak bisa dibaca: {e}")
        return
    st.write(f"**{len(df)} baris**, tanggal {df['tgl'].min()} sampai {df['tgl'].max()}, "
             f"{df['nama_sap'].nunique()} karyawan.")
    for c in catatan:
        st.warning(c)
    luar = (df["tgl"].str[:7] != pilih).sum()
    if luar:
        st.warning(f"{luar} baris memiliki tanggal di luar bulan yang dipilih. Baris itu tetap disimpan "
                   "pada bulannya masing-masing.")
    if st.button("UPLOAD", type="primary"):
        data.simpan_hasil(df)
        data.catat_update("FILE HASIL KERJA")
        st.session_state["sukses"] = "FILE BERHASIL DI UPDATE"
        st.rerun()


@st.dialog("DATA AWAL", width="large")
def dlg_awal():
    st.write("Upload **DATA_KARYAWAN.xlsx** dan **PENCAPAIAN_KERJA_QC.xlsx**. Cukup sekali di awal, "
             "ulangi hanya bila ada karyawan baru atau target berubah. Boleh salah satu saja.")
    fk = st.file_uploader("DATA_KARYAWAN.xlsx", type=["xlsx"], key="fk")
    ft = st.file_uploader("PENCAPAIAN_KERJA_QC.xlsx", type=["xlsx"], key="ft")
    if st.button("SIMPAN", type="primary", disabled=not (fk or ft)):
        try:
            hasil = []
            if fk:
                k = parsers.baca_karyawan(fk)
                data.tulis("karyawan", k)
                hasil.append(f"{len(k)} karyawan")
            if ft:
                t = parsers.baca_target(ft)
                data.tulis("target", t)
                hasil.append(f"{len(t)} baris target")
        except Exception as e:
            st.error(f"File tidak bisa dibaca: {e}")
            return
        st.session_state["sukses"] = "DATA BERHASIL DI UPDATE: " + ", ".join(hasil)
        st.rerun()


@st.dialog("INFORMASI")
def dlg_sukses(pesan):
    st.markdown(f"<h4 style='text-align:center'>{pesan}</h4>", unsafe_allow_html=True)
    if st.button("OK", use_container_width=True):
        st.rerun()


def lonceng(baru, tanpa):
    karyawan, alias = data.baca("karyawan"), data.baca("alias")
    jumlah = len(baru) + (1 if len(tanpa) else 0)
    with st.popover(f"🔔 {jumlah}" if jumlah else "🔔"):
        if not jumlah:
            st.write("Tidak ada masalah.")
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
            st.markdown("**Target belum ada** (tidak ikut dihitung):")
            st.dataframe(tanpa, hide_index=True)


gerbang()
pesan = st.session_state.pop("sukses", None)
if pesan:
    dlg_sukses(pesan)

belum_ada = data.baca("karyawan").empty or data.baca("target").empty
baru, tanpa = ([], pd.DataFrame()) if belum_ada else cari_masalah()
st.markdown("<h1 style='text-align:center'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)
kiri, kanan = st.columns([1, 2])
with kiri:
    lonceng(baru, tanpa)
    st.markdown("## UPDATE DATA")
with kanan:
    if st.button("HASIL KERJA", use_container_width=True):
        dlg_hasil()
    for nama, tahap in (("LEMBUR", 2), ("EVALUASI KARYAWAN", 3), ("ABSENSI", 2), ("JADWAL KERJA", 2)):
        st.button(nama, disabled=True, help=f"Dibangun di tahap {tahap}", use_container_width=True)

if belum_ada:
    st.warning("Data karyawan dan target belum ada. Klik DATA AWAL dan upload dua file Excel-nya.")
if st.button("DATA AWAL (karyawan dan target)"):
    dlg_awal()

st.markdown("#### ► INFORMASI")
log = dict(zip(data.baca("update_log")["nama_file"], data.baca("update_log")["waktu"]))
st.table(pd.DataFrame({"NAMA FILE": FILE_INFO, "TERAKHIR UPDATE": [log.get(n, "-") for n in FILE_INFO]}))
