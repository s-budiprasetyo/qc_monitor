"""Halaman admin (Welcome Admin QC TOTO). Jalankan: streamlit run app_admin.py"""
import base64
import difflib
import hmac
import os
from datetime import date

import pandas as pd
import streamlit as st

from core import calc, data, logic, parsers
from core.grid import jadwal_grid
from core.hub import hub

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]
FILE_INFO = ["FILE HASIL KERJA", "LEMBUR", "EVALUASI KARYAWAN", "ABSENSI", "JADWAL KERJA"]
PILIHAN_ABSEN = ["Sakit", "Ijin", "Cuti", "Dispen", "Resign", "Hapus catatan"]

st.set_page_config(page_title="Welcome Admin QC TOTO", page_icon="⚙️", layout="wide")


# ---------------------------------------------------------------- tampilan
_ASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


@st.cache_data(show_spinner=False)
def ikon(nama):
    """Ikon dari file Excel pengguna (folder assets) sebagai data-uri."""
    with open(os.path.join(_ASET, f"{nama}.png"), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def kepala(nama_ikon, judul):
    """Spanduk kuning ala Excel dengan ikon, di bagian atas tiap jendela."""
    st.markdown(f"<div class='kp'><img src='{ikon(nama_ikon)}'><span>{judul}</span></div>", unsafe_allow_html=True)


CSS = """
<style>
.block-container{max-width:1180px;padding-top:2.4rem}
h1.judul{text-align:center;font-weight:800;letter-spacing:.5px;margin:0 0 .6rem 0;padding:0}
.judul-update{font-size:2.7rem;font-weight:800;line-height:1.05;margin:.2rem 0 .4rem 0}
.ilus{background:#fff;border-radius:14px;padding:4px 0}
.ilus svg{height:430px;width:auto;display:block;margin-left:auto;margin-right:0}

/* spanduk kuning jendela (gaya file Excel) */
.kp{display:flex;align-items:center;gap:12px;background:#ffff00;border:2px solid #000;border-radius:6px;padding:6px 12px;margin:0 0 12px 0}
.kp img{height:42px;width:42px;object-fit:contain;background:#fff;border-radius:50%;border:2px solid #000}
.kp span{font-weight:800;font-size:1.15rem;letter-spacing:.4px;color:#000}
.st-key-hub{margin-top:0}
.st-key-lonceng button{border:none;background:transparent;font-size:1.7rem;padding:0 .3rem;box-shadow:none}
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


def sukses(pesan, nama_file=None, verifikasi=True):
    """Catat update, tampilkan jendela berhasil. Bila ada karyawan yang belum diverifikasi,
    jendela verifikasi (✕) otomatis terbuka setelah OK."""
    if nama_file:
        data.catat_update(nama_file)
    st.session_state["sukses"] = pesan
    if verifikasi and logic.belum_diverifikasi():
        st.session_state["verif"] = True
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
    kepala("awal", "DATA AWAL")
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
        sukses("DATA BERHASIL DI UPDATE: " + ", ".join(hasil))


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


# ---------------------------------------------------------------- verifikasi karyawan
@st.dialog("VERIFIKASI KARYAWAN", width="large")
def dlg_verif():
    kontrol_jendela("verif")
    kepala("awal", "VERIFIKASI DAFTAR PANTAU")
    u = logic.usulan_verifikasi()
    if u.empty:
        st.warning("Belum ada data karyawan. Upload data awal dulu.")
        return
    st.caption("Centang **✕ KELUARKAN** pada orang yang TIDAK boleh tampil di monitor (misalnya departemen lain). "
               "Usulan awal: yang tidak ada di file SAP sudah ditandai ✕; admin sendiri tidak. Ubah sesuai kebutuhan, "
               "lalu SIMPAN. Daftar ini dipakai di tabel monitor, Lembur, Absensi, dan Jadwal Kerja.")
    tabel = pd.DataFrame({"NAMA": u["nama"], "PRN": u["prn"],
                          "DI SAP": u["ada_sap"].map({True: "✔", False: "—"}),
                          "DI JADWAL": u["ada_jadwal"].map({True: "✔", False: "—"}),
                          "BARU": u["baru"].map({True: "baru", False: ""}),
                          "✕ KELUARKAN": u["silang"]})
    ed = st.data_editor(tabel, hide_index=True, width="stretch", height=460, key="verif_ed",
                        disabled=["NAMA", "PRN", "DI SAP", "DI JADWAL", "BARU"],
                        column_config={"✕ KELUARKAN": st.column_config.CheckboxColumn("✕ KELUARKAN", width="small")})
    n_x = int(ed["✕ KELUARKAN"].sum())
    st.write(f"**{len(ed) - n_x} orang tampil**, {n_x} dikeluarkan.")
    if st.button("SIMPAN", type="primary", key="verif_simpan"):
        roster = pd.DataFrame({"prn": ed["PRN"], "status": ["tidak" if x else "ya" for x in ed["✕ KELUARKAN"]]})
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
    for b in bulan_ada[-2:]:
        bentrok += [dict(m, bulan=b) for m in logic.masalah_bulan(b)]
    tanpa = pd.concat(tanpa) if tanpa else pd.DataFrame()
    if len(tanpa):
        ok = [str(o) != logic.OP_TANPA_TARGET and (g, t, o) not in kebal  # OP107 = catatan otomatis
              for g, t, o in zip(tanpa["grup"], tanpa["type"], tanpa["op"])]
        tanpa = tanpa[ok]
        tanpa = tanpa.groupby(["grup", "type", "op"]).size().reset_index(name="baris")
    return sorted(baru), tanpa, bentrok


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
belum_ada = data.baca("karyawan").empty or data.baca("target").empty
baru, tanpa, bentrok = ([], pd.DataFrame(), []) if belum_ada else cari_masalah()
jumlah = hitung_jumlah(baru, tanpa, bentrok) if not belum_ada else 0

pesan = st.session_state.pop("sukses", None)
if pesan:
    dlg_sukses(pesan)
elif st.session_state.pop("verif", False):
    dlg_verif()

st.markdown("<h1 class='judul'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)

atas1, atas2, atas3 = st.columns([1, 4, 2])
with atas1, st.container(key="lonceng"):
    if st.button("🔔" + (f" :red-badge[{jumlah}]" if jumlah else ""), key="bel"):
        dlg_lonceng(baru, tanpa, bentrok)
atas2.markdown("<div class='judul-update'>UPDATE DATA</div>", unsafe_allow_html=True)
with atas3, st.container(key="awal"):
    c1, c2 = st.columns([2, 1])
    if c1.button("Data awal", icon=":material/settings:", width="stretch"):
        st.session_state["max_awal"] = False
        dlg_awal()
    if c2.button("Keluar", width="stretch"):
        st.session_state["admin_ok"] = False
        st.rerun()

MENU = {"hasil": ("HASIL KERJA", dlg_hasil, "hasil", False),
        "lembur": ("LEMBUR", dlg_lembur, "lembur", False),
        "eval": ("EVALUASI KARYAWAN", None, "evaluasi", True),
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
