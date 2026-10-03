"""Halaman admin (Welcome Admin QC TOTO). Jalankan: streamlit run app_admin.py"""
import difflib
import hmac
import math
from datetime import date

import pandas as pd
import streamlit as st

from core import calc, data, logic, parsers
from core.grid import jadwal_grid

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]
FILE_INFO = ["FILE HASIL KERJA", "LEMBUR", "EVALUASI KARYAWAN", "ABSENSI", "JADWAL KERJA"]
PILIHAN_ABSEN = ["Sakit", "Ijin", "Cuti", "Dispen", "Resign", "Hapus catatan"]

st.set_page_config(page_title="Welcome Admin QC TOTO", page_icon="⚙️", layout="wide")


# ---------------------------------------------------------------- tampilan
def _gear_path(cx, cy, r_out, r_in, teeth):
    pts, step = [], 2 * math.pi / teeth
    for i in range(teeth):
        a = i * step
        for ang, r in ((a - .28 * step, r_in), (a - .15 * step, r_out), (a + .15 * step, r_out), (a + .28 * step, r_in)):
            pts.append(f"{cx + r * math.cos(ang):.1f},{cy + r * math.sin(ang):.1f}")
    return "M" + " L".join(pts) + "Z"


ILUSTRASI = f"""
<div class="ilus"><svg viewBox="0 0 352 440" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Update data">
  <path d="{_gear_path(236, 150, 104, 86, 12)}" fill="#243b73"/>
  <circle cx="236" cy="150" r="42" fill="#fff"/>
  <circle cx="236" cy="150" r="30" fill="none" stroke="#243b73" stroke-width="10"/>
  <path d="M46 112 H238 V400 H94 L46 352 Z" fill="#2c4a8f" stroke="#fff" stroke-width="6"/>
  <path d="M24 134 H216 V420 H72 L24 372 Z" fill="#243b73" stroke="#fff" stroke-width="6"/>
  <g fill="#fff">
    <rect x="56" y="168" width="136" height="10" rx="5"/><rect x="56" y="204" width="136" height="10" rx="5"/>
    <rect x="56" y="240" width="136" height="10" rx="5"/><rect x="56" y="276" width="136" height="10" rx="5"/>
    <rect x="56" y="312" width="136" height="10" rx="5"/><rect x="56" y="348" width="90" height="10" rx="5"/>
  </g>
  <path d="M160 318 H198 V364 H228 L179 432 L130 364 H160 Z" fill="#2f9fdd" stroke="#fff" stroke-width="5" stroke-linejoin="round"/>
</svg></div>
"""

CSS = """
<style>
.block-container{max-width:1180px;padding-top:2.4rem}
h1.judul{text-align:center;font-weight:800;letter-spacing:.5px;margin:0 0 .6rem 0;padding:0}
.judul-update{font-size:2.7rem;font-weight:800;line-height:1.05;margin:.2rem 0 .4rem 0}
.ilus{background:#fff;border-radius:14px;padding:4px 0}
.ilus svg{height:430px;width:auto;display:block;margin-left:auto;margin-right:0}

/* tombol menu: garis biru, teks biru, bertingkat dengan simpul seperti gambar */
.st-key-menu{margin-top:96px;gap:16px}
.st-key-menu button{background:#fff;border:1px solid #1ba1e2;color:#1ba1e2;border-radius:10px;
  height:46px;font-weight:600;letter-spacing:.4px}
.st-key-menu button:hover{background:#e8f6fd;border-color:#0f86c2;color:#0f86c2}
.st-key-menu button:disabled{opacity:.6;background:#fff}
.st-key-m1,.st-key-m2,.st-key-m3,.st-key-m4,.st-key-m5{position:relative}
.st-key-m1::before,.st-key-m2::before,.st-key-m3::before,.st-key-m4::before,.st-key-m5::before{
  content:"";position:absolute;top:50%;height:4px;margin-top:-2px;background:#243b73;left:calc(-1 * var(--m) - 14px);width:calc(var(--m) + 14px - 10px)}
.st-key-m1::after,.st-key-m2::after,.st-key-m3::after,.st-key-m4::after,.st-key-m5::after{
  content:"";position:absolute;top:50%;left:-26px;width:22px;height:22px;margin-top:-11px;border-radius:50%;background:#243b73}
.st-key-m1,.st-key-m2,.st-key-m3,.st-key-m4,.st-key-m5{width:290px}
.st-key-m1{--m:70px;margin-left:70px}.st-key-m2{--m:112px;margin-left:112px}.st-key-m3{--m:155px;margin-left:155px}
.st-key-m4{--m:112px;margin-left:112px}.st-key-m5{--m:70px;margin-left:70px}

.st-key-lonceng button{border:none;background:transparent;font-size:1.7rem;padding:0 .3rem;box-shadow:none}
.st-key-lonceng{width:fit-content}
.st-key-awal button{font-size:.85rem}

button[data-testid="stBaseButton-primary"]{background:#1ba1e2;border-color:#1ba1e2;color:#fff;font-weight:600}
button[data-testid="stBaseButton-primary"]:hover{background:#0f86c2;border-color:#0f86c2;color:#fff}
button[data-testid="stBaseButton-primary"]:disabled{background:#cfe9f7;border-color:#cfe9f7;color:#fff}
h4.info{margin:1.4rem 0 .4rem 0;font-weight:700}
table.info{border-collapse:collapse;width:100%;font-size:13px}
table.info th,table.info td{border:1px solid #000;padding:5px 10px}
table.info th{text-align:center;font-weight:700;background:#fff;color:#000}
table.info td{background:#fff;color:#000}
table.info td.w{text-align:center}

@media (max-width: 900px){
  .st-key-menu{margin-top:12px}
  .st-key-m1,.st-key-m2,.st-key-m3,.st-key-m4,.st-key-m5{width:100%}
  .st-key-m1,.st-key-m2,.st-key-m3,.st-key-m4,.st-key-m5{margin-left:0}
  .st-key-m1::before,.st-key-m2::before,.st-key-m3::before,.st-key-m4::before,.st-key-m5::before,
  .st-key-m1::after,.st-key-m2::after,.st-key-m3::after,.st-key-m4::after,.st-key-m5::after{display:none}
  .ilus svg{height:260px;margin:0 auto}
}
</style>
"""


def kontrol_jendela(nama):
    """Tombol perbesar/kecilkan jendela. Tombol tutup (X) bawaan dialog; tidak ada minimize."""
    kunci = f"max_{nama}"
    besar = st.session_state.get(kunci, False)
    if besar:
        st.markdown("<style>div[data-testid='stDialog'] div[role='dialog']"
                    "{width:96vw !important;max-width:96vw !important;}</style>", unsafe_allow_html=True)
    _, kanan = st.columns([5, 1])
    kanan.button("❐ Kecilkan" if besar else "⛶ Perbesar", key=f"tb_{kunci}", width="stretch",
                 on_click=lambda: st.session_state.update({kunci: not besar}))


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


def sukses(pesan, nama_file):
    data.catat_update(nama_file)
    st.session_state["sukses"] = pesan
    st.rerun()


@st.dialog("UPLOAD FILE HASIL KERJA", width="large")
def dlg_hasil():
    kontrol_jendela("hasil")
    daftar, idx = pilihan_bulan()
    pilih = st.selectbox("PILIH BULAN", daftar, index=idx, format_func=nama_bulan)
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
        sukses("FILE BERHASIL DI UPDATE", "FILE HASIL KERJA")


@st.dialog("DATA AWAL", width="large")
def dlg_awal():
    kontrol_jendela("awal")
    st.write("Upload **DATA_KARYAWAN.xlsx** dan **PENCAPAIAN_KERJA_QC.xlsx**. Cukup sekali di awal; ulangi hanya "
             "bila ada karyawan baru atau target berubah. Boleh salah satu saja.")
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


def _tabel_kosong(kolom, n):
    return pd.DataFrame({c: [None] * n for c in kolom})


@st.dialog("UPDATE DATA KARYAWAN OVERTIME", width="large")
def dlg_lembur():
    kontrol_jendela("lembur")
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
    nama, prns = logic.peta_nama_prn(), logic.karyawan_dikenal()
    if not prns:
        st.warning("Belum ada karyawan. Upload data awal dan file hasil kerja SAP dulu.")
        return
    by_nama = {nama.get(p, p): p for p in prns}
    rentang = st.date_input("PILIH TANGGAL (satu hari, atau pilih tanggal awal dan akhir)",
                            value=(date.today(),), format="DD/MM/YYYY", key="abs_tgl")
    mulai = rentang[0]
    akhir = rentang[1] if len(rentang) > 1 else rentang[0]
    tanggal = [d.strftime("%Y-%m-%d") for d in pd.date_range(mulai, akhir)][:62]
    st.caption(f"{len(tanggal)} hari: {tanggal[0]} sampai {tanggal[-1]}. Resign berlaku mulai tanggal awal dan seterusnya. "
               "Pilih 'Hapus catatan' untuk membatalkan catatan yang sudah ada.")
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
    st.markdown("#### SETTING MANUAL JADWAL KERJA")
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
    daftar, idx = pilihan_bulan()
    bulan = st.selectbox("PILIH BULAN", daftar, index=idx, format_func=nama_bulan, key="jd_bulan")
    if st.session_state.get("jd_manual"):
        _jadwal_manual(bulan)
        return
    valid = set(data.baca("karyawan")["prn"])
    fq = st.file_uploader("► Upload Jadwal Kerja QC disini", type=["xlsx"], key="jd_qc")
    fs = st.file_uploader("► Upload Jadwal Kerja SK disini", type=["xlsx"], key="jd_sk")
    hasil = []
    for label, f in (("QC", fq), ("SK", fs)):
        if f is None:
            continue
        try:
            df, catatan = parsers.baca_jadwal(f, bulan)
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
    a, b = st.columns(2)
    if a.button("UPLOAD", type="primary", disabled=not hasil, width="stretch"):
        baru = pd.concat(hasil, ignore_index=True)
        data.upsert("jadwal_" + bulan, baru, ["prn", "tgl"])
        sukses("JADWAL KERJA BERHASIL DI UPDATE", "JADWAL KERJA")
    if b.button("⚙ SETTING MANUAL", width="stretch"):
        st.session_state["jd_manual"] = True
        st.rerun(scope="fragment")


# ---------------------------------------------------------------- lonceng
def cari_masalah():
    karyawan, alias, target = data.baca("karyawan"), data.baca("alias"), data.baca("target")
    abaikan = set(data.baca("abaikan")["nama_sap"])
    peta = calc.peta_nama(karyawan, alias)
    baru, tanpa, bentrok = set(), [], []
    bulan_ada = data.daftar_bulan()[-3:]
    for b in bulan_ada:
        h = data.baca(f"hasil_{b}")
        h = h[~h["nama_sap"].isin(abaikan)]
        baru |= set(h["nama_sap"]) - set(peta)
        tanpa.append(calc.hitung_harian(h.assign(prn=h["nama_sap"].map(peta)), target)[1])
    for b in bulan_ada[-2:]:
        bentrok += [dict(m, bulan=b) for m in logic.masalah_bulan(b)]
    tanpa = pd.concat(tanpa) if tanpa else pd.DataFrame()
    if len(tanpa):
        tanpa = tanpa.groupby(["grup", "type", "op"]).size().reset_index(name="baris")
    return sorted(baru), tanpa, bentrok


def lonceng(baru, tanpa, bentrok):
    karyawan, alias = data.baca("karyawan"), data.baca("alias")
    jumlah = len(baru) + (1 if len(tanpa) else 0) + (1 if bentrok else 0)
    with st.container(key="lonceng"):
        pop = st.popover("🔔" + (f" :red-badge[{jumlah}]" if jumlah else ""))
    with pop:
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
            st.dataframe(tanpa, hide_index=True, width="stretch")
        if bentrok:
            st.markdown(f"**Hasil kerja tidak sesuai jadwal atau absensi** ({len(bentrok)} kasus). "
                        "Hasil SAP tetap dipakai dan ditampilkan.")
            st.dataframe(pd.DataFrame(bentrok)[["nama", "tgl", "ket"]].rename(
                columns={"nama": "NAMA", "tgl": "TANGGAL", "ket": "KETERANGAN"}), hide_index=True, width="stretch")
            lib = [m for m in bentrok if m["jenis"] == "libur"]
            if lib and st.button(f"Jadikan {len(lib)} hari itu hari masuk di jadwal", key="fix_libur"):
                for bln in sorted({m["bulan"] for m in lib}):
                    sub = pd.DataFrame([{"prn": m["prn"], "tgl": m["tgl"], "status": "O"} for m in lib
                                        if m["bulan"] == bln])
                    data.upsert("jadwal_" + bln, sub, ["prn", "tgl"])
                data.catat_update("JADWAL KERJA")
                st.rerun()


# ---------------------------------------------------------------- halaman
gerbang()
st.markdown(CSS, unsafe_allow_html=True)
pesan = st.session_state.pop("sukses", None)
if pesan:
    dlg_sukses(pesan)

belum_ada = data.baca("karyawan").empty or data.baca("target").empty
baru, tanpa, bentrok = ([], pd.DataFrame(), []) if belum_ada else cari_masalah()

st.markdown("<h1 class='judul'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)

kiri, kanan = st.columns([0.62, 1.38], gap="small")
with kiri:
    lonceng(baru, tanpa, bentrok)
    st.markdown("<div class='judul-update'>UPDATE DATA</div>", unsafe_allow_html=True)
    st.markdown(ILUSTRASI, unsafe_allow_html=True)
    with st.container(key="awal"):
        c1, c2 = st.columns([2, 1])
        if c1.button("⚙ Data awal", width="stretch"):
            st.session_state["max_awal"] = False
            dlg_awal()
        if c2.button("Keluar", width="stretch"):
            st.session_state["admin_ok"] = False
            st.rerun()

MENU = [("HASIL KERJA", dlg_hasil, "max_hasil", False),
        ("LEMBUR", dlg_lembur, "max_lembur", False),
        ("EVALUASI KARYAWAN", None, "max_evaluasi", True),
        ("ABSENSI", dlg_absensi, "max_absensi", False),
        ("JADWAL KERJA", dlg_jadwal, "max_jadwal", False)]
with kanan:
    with st.container(key="menu"):
        for i, (label, fungsi, kunci_max, mati) in enumerate(MENU, 1):
            with st.container(key=f"m{i}"):
                if st.button(label, key=f"btn_{i}", width="stretch", disabled=mati,
                             help="Segera hadir (tahap berikutnya)" if mati else None):
                    st.session_state[kunci_max] = False
                    if label == "JADWAL KERJA":
                        st.session_state["jd_manual"] = False
                    fungsi()
    if belum_ada:
        st.warning("Data karyawan dan target belum ada. Klik **Data awal** dan upload dua file Excel-nya.")
    log = data.baca("update_log")
    log = dict(zip(log["nama_file"], log["waktu"]))
    baris = "".join(f"<tr><td>{n}</td><td class='w'>{log.get(n, '-')}</td></tr>" for n in FILE_INFO)
    st.markdown("<h4 class='info'>► INFORMASI</h4><table class='info'><tr><th>NAMA FILE</th>"
                f"<th>TERAKHIR UPDATE</th></tr>{baris}</table>", unsafe_allow_html=True)
