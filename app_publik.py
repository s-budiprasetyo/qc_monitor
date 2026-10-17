"""Halaman utama (umum): Monitoring Hasil Kerja Karyawan. Jalankan: streamlit run app_publik.py"""
import base64
import calendar
import hmac
import html

import altair as alt
import pandas as pd
import streamlit as st

from core import data, logic, parsers
from core.bulan import pilih_bulan
from core.tabel import tabel
from core.grafik import KELAS, data_grafik, grafik, kelas_anggota
from core.ui import gaya_global, gaya_responsif, kepala_pub, kontrol_jendela_pub

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

st.set_page_config(page_title="Monitoring Hasil Kerja Karyawan", layout="wide")

if st.query_params.get("privasi") is not None:  # halaman kebijakan privasi (dipakai di konfigurasi login Google)
    st.title("Kebijakan Privasi — Monitoring QC TOTO")
    st.markdown("""
Aplikasi **Monitoring QC TOTO** dipakai internal oleh karyawan bagian QC untuk melihat hasil kerja harian dan
menyampaikan alasan bila hasil kerja belum mencapai target.

**Data yang kami baca.** Saat karyawan memilih *Verifikasi dengan Google*, aplikasi hanya membaca **alamat email**
(dan nama profil dasar) dari akun Google tersebut. Tidak ada akses ke Gmail, Drive, kontak, atau data Google lain.

**Untuk apa.** Alamat email dicatat bersama alasan tidak target atau catatan kegiatan yang diposting, sebagai jejak
siapa yang menulis dan kapan.

**Penyimpanan.** Data disimpan di Google Sheet milik pengelola aplikasi dan hanya dapat dibuka oleh pengelola.
Data tidak dijual, tidak dibagikan, dan tidak dipakai untuk iklan.

**Penghapusan.** Karyawan dapat meminta data postingnya dihapus dengan menghubungi pengelola aplikasi
(salis_budi_prasetyo@student.umaha.ac.id).

Terakhir diperbarui: Oktober 2026.
""")
    st.stop()
st.markdown("""<style>
h1.judul{text-align:center;font-weight:800;margin:0 0 .8rem 0}
.wrap{overflow-x:auto}
table.t{border-collapse:collapse;width:100%;font-size:12px;text-align:center}
table.t th,table.t td{border:1px solid #000;padding:3px 1px;white-space:nowrap;height:30px;color:#000;background:#fff}
table.t td.n,table.t th.n{text-align:left;padding-left:4px}
table.t th.we{background:#ffff00;color:#e00000}
table.t td.lb{background:#f4c2dd}
table.t td.ab{background:#ffff00}
.v{display:inline-block;border:2px solid #000;border-radius:6px;padding:1px 3px;font-weight:600;background:#fff}
.v.kd{background:#ffff00;min-width:20px;font-size:14px;font-weight:800}
.v.kg{box-sizing:border-box;position:relative;background:#fff;width:22px;height:22px;padding:0;vertical-align:middle}
.v.kg:after{content:'';position:absolute;left:50%;top:50%;width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;background:#1a73e8}
.v.kg.ada:after{width:14px;height:14px;margin:-7px 0 0 -7px}
.m{color:#e00000}
.ket{font-size:12px;margin-top:6px}
table.d{border-collapse:collapse;width:100%;font-size:14px;text-align:center}
table.d th,table.d td{border:1px solid #000;padding:5px 8px;color:#000;background:#fff}
table.d th{background:#ffff00}table.d td.l{text-align:left}
table.d tr.tot td{font-weight:800;background:#f2f2f2}
.id{font-size:15px;margin:4px 0 8px 0;color:#000}
.ket span{display:inline-block;width:12px;height:12px;border:1px solid #000;margin:0 4px 0 12px;vertical-align:-1px}
</style>""", unsafe_allow_html=True)


def nama_bulan(kode):
    return f"{BULAN[int(kode[5:]) - 1]} {kode[:4]}"


def kotak(v, desimal=0, klik=""):
    # merah bila angka yang tampil masih di bawah 100%
    teks = f"{v:.{desimal}f}".replace(".", ",") + "%"
    return f"<span class='v k{' m' if round(v, desimal) < 100 else ''}' {klik}>{teks}</span>" if klik else \
        f"<span class='v{' m' if round(v, desimal) < 100 else ''}'>{teks}</span>"


def sel(jenis, nilai, prn, d):
    if jenis == "pct":
        attr = f"data-k='h' data-p='{html.escape(prn)}' data-d='{bulan}-{d:02d}'"
        return f"<td>{kotak(nilai, 0, klik=attr)}</td>"
    if jenis == "abs":
        return f"<td class='ab'><span class='v kd'>{html.escape(nilai)}</span></td>"
    if jenis == "libur":
        return "<td class='lb'></td>"
    attr = f"data-k='k' data-p='{html.escape(prn)}' data-d='{bulan}-{d:02d}'"
    ada = " ada" if jenis == "keg" else ""  # ada catatan = lingkaran biru gelap di dalam tombol; kosong = tombol kosong
    return f"<td><span class='v kg k{ada}' {attr}></span></td>"  # kosong: bisa diklik untuk mencatat kegiatan lain


def tabel_html(baris, tahun, bln):
    # tanggal sesudah data SAP terakhir yang diposting disembunyikan (belum ada nilainya)
    n_hari = hari_akhir(baris, tahun, bln)
    h = "<table class='t'><tr><th class='n'>NAMA</th>"
    for d in range(1, n_hari + 1):
        h += f"<th class='{'we' if calendar.weekday(tahun, bln, d) >= 5 else ''}'>{d}</th>"
    h += "<th>RATA RATA</th></tr>"
    for i, b in enumerate(baris):  # PRN tidak ditaruh di halaman: sel memakai nomor baris, dipetakan lagi di server
        h += f"<tr><td class='n'>{html.escape(b['nama'])}</td>"
        for d in range(1, n_hari + 1):
            jenis, nilai = b["hari"].get(d, (None, None))
            h += sel(jenis, nilai, str(i), d)
        rata = kotak(b["rata"], 1, klik=f"data-k='r' data-p='{i}'") if b["rata"] is not None else ""
        h += f"<td>{rata}</td></tr>"
    return h + "</table>"


def hari_akhir(baris, tahun, bln):
    ada = [d for b in baris for d, (j, v) in b["hari"].items() if j == "pct" or (j == "abs" and v != "R")]
    return max(ada) if ada else calendar.monthrange(tahun, bln)[1]


def kalender_data(baris, tahun, bln, boleh_idx):
    """Kalender bulanan per orang (tampilan smartphone). Hanya untuk baris yang boleh dilihat si pengguna."""
    n_hari, hasil = hari_akhir(baris, tahun, bln), []
    for i in boleh_idx:
        b = baris[i]
        c = "<div class='c off'></div>" * calendar.weekday(tahun, bln, 1)
        for d in range(1, calendar.monthrange(tahun, bln)[1] + 1):
            tg = f"{tahun}-{bln:02d}-{d:02d}"
            dt = f"<i class='dt'>{d}</i>"
            if d > n_hari:
                c += f"<div class='c off'>{dt}</div>"
                continue
            jenis, nilai = b["hari"].get(d, (None, None))
            if jenis == "pct":
                m = " m" if round(nilai) < 100 else ""
                c += (f"<div class='c'>{dt}<span class='b k{m}' data-k='h' data-p='{i}' data-d='{tg}'>"
                      f"{angka(nilai)}%</span></div>")
            elif jenis == "abs":
                c += f"<div class='c ab'>{dt}<span class='b y'>{html.escape(nilai)}</span></div>"
            elif jenis == "libur":
                c += f"<div class='c lb'>{dt}</div>"
            else:
                ada = " ada" if jenis == "keg" else ""
                c += f"<div class='c'>{dt}<span class='b kg k{ada}' data-k='k' data-p='{i}' data-d='{tg}'></span></div>"
        rata = b["rata"]
        hasil.append({"i": i, "nama": b["nama"], "rata": f"{angka(rata, 1)}%" if rata is not None else "",
                      "rm": rata is not None and round(rata, 1) < 100, "cells": c})
    return hasil


gaya_global()
gaya_responsif()
st.markdown("<h1 class='judul'>MONITORING HASIL KERJA KARYAWAN</h1>", unsafe_allow_html=True)
opsi = data.daftar_bulan()
if not opsi:
    if not data.pakai_google_sheet():
        st.error("Aplikasi ini belum terhubung ke Google Sheet: **sheet_id** dan **[gcp_service_account]** belum ada di "
                 "Secrets app ini (Manage app → Settings → Secrets). Isi sama persis dengan Secrets app admin.")
        st.stop()
    st.info("Belum ada data hasil kerja. Admin perlu mengupload file SAP terlebih dahulu.")
    with st.expander("Info koneksi (untuk admin)", expanded=True):
        try:
            sh = data.store().sh
            st.write(f"Terhubung ke Google Sheet: **{sh.title}**")
            st.write("Tab yang terbaca:", ", ".join(w.title for w in sh.worksheets()) or "(kosong)")
        except Exception as e:
            st.error(f"Gagal membaca Google Sheet: {type(e).__name__}: {e}")
        if st.button("Muat ulang data"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()
    st.stop()

def tgl_id(t):
    return f"{t[8:]}-{t[5:7]}-{t[:4]}"


def angka(v, d=0):
    return f"{v:.{d}f}".replace(".", ",")


def email_google():
    try:
        if "auth" in st.secrets and st.user.is_logged_in:
            return str(st.user.email)
    except Exception:
        pass
    return ""


def perlu_google():
    """True bila login Google sudah dipasang di app ini tetapi pengguna belum verifikasi (wajib untuk memposting alasan)."""
    try:
        return "auth" in st.secrets and not st.user.is_logged_in
    except Exception:
        return False


def boleh(prn):
    return bool(st.session_state.get("adm")) or st.session_state.get("me") == prn


def img_foto(fid):
    b64 = data.foto_alasan(fid)
    return base64.b64decode(b64) if b64 else None


def tombol_kembali():
    d = st.session_state.get("dari_kelas")
    if d and st.button("← Kembali ke daftar kelas", key="kembali_kelas"):
        st.session_state["buka"] = ("kelas",) + tuple(d)
        st.rerun()


@st.dialog("LOGIN")
def dlg_login():
    kontrol_jendela_pub("login")
    kepala_pub("login", "LOGIN KARYAWAN")
    google_ok, perlu = "", False
    if "auth" in st.secrets:  # langkah 1: akun Google terverifikasi (email dicatat otomatis di setiap posting)
        try:
            if st.user.is_logged_in:
                google_ok = str(st.user.email)
                st.success(f"Langkah 1 selesai. Akun Google terverifikasi: {google_ok}")
            else:
                perlu = True
                st.info("Langkah 1: verifikasi akun Google di perangkat ini (cukup sekali; emailnya otomatis tercatat "
                        "saat kamu memposting). Setelah kembali ke halaman ini, tekan LOGIN lagi untuk langkah 2.")
                st.button("Verifikasi dengan Google", on_click=st.login, width="stretch", type="primary")
        except Exception:
            pass
    with st.form("form_login"):
        u = st.text_input("User", placeholder="mis. QC-NAMA", disabled=perlu)
        p = st.text_input("Password", type="password", disabled=perlu)
        ok = st.form_submit_button("MASUK", type="primary", width="stretch", disabled=perlu)
    if ok:
        if st.session_state.get("gagal", 0) >= 5:
            st.error("Terlalu banyak percobaan salah. Muat ulang halaman untuk mencoba lagi.")
            return
        k = data.baca("karyawan")
        c = k[k["user"].str.strip().str.upper() == u.strip().upper()]
        if len(c) and u.strip() and hmac.compare_digest(parsers.hash_pw(p), str(c.iloc[0]["pass_hash"])):
            prn = c.iloc[0]["prn"]
            st.session_state.update({"me": prn, "me_nama": c.iloc[0]["nama_web"], "adm": prn == logic.prn_admin(), "gagal": 0})
            st.rerun()
        st.session_state["gagal"] = st.session_state.get("gagal", 0) + 1
        st.error("User atau password salah.")


@st.dialog("HASIL KERJA", width="large")
def dlg_hari(bln, prn, tgl):
    kontrol_jendela_pub("hari")
    kepala_pub("hasil", "HASIL KERJA HARIAN")
    tombol_kembali()
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>TANGGAL</b>: {tgl_id(tgl)} &nbsp;&nbsp; <b>NAMA</b>: {html.escape(nama)}</div>", unsafe_allow_html=True)
    rinci, total = logic.detail_hari(bln, prn, tgl)
    h = "<div style='overflow-x:auto'><table class='d'><tr><th>TYPE</th><th>WARNA</th><th>PABRIK</th><th>FORMING</th><th>OPERATION</th><th>PERIKSA</th><th>TARGET</th><th>% HASIL KERJA</th></tr>"
    for r in rinci:
        h += (f"<tr><td class='l'>{html.escape(r['type'])}</td><td>{html.escape(r['warna']) or '-'}</td>"
              f"<td>{html.escape(r['pabrik']) or '-'}</td><td>{html.escape(r['forming']) or '-'}</td><td>OP{html.escape(r['op'])}</td><td>{angka(r['periksa'])}</td>"
              f"<td>{angka(r['target']) if r['target'] else '-'}</td>"
              f"<td>{kotak(r['pct'], 1) if r['pct'] is not None else '-'}</td></tr>")
    h += f"<tr class='tot'><td colspan='7' class='l'>% TOTAL</td><td>{kotak(total, 1) if total is not None else '-'}</td></tr></table></div>"
    st.markdown(f"<div class='sx'>{h}</div>", unsafe_allow_html=True)
    ada = data.pengajuan_ada(prn, tgl)
    if ada:
        st.markdown("**ALASAN TIDAK TARGET YANG SUDAH DIAJUKAN**")
        for r in data.alasan_hari(prn, tgl):
            c = st.columns([5, 1.5, 1.2], vertical_alignment="center")
            c[0].write(r["masalah"])
            c[1].write(f"{r['menit']} menit")
            if r["foto"]:
                with c[2].popover("📷"):
                    st.image(img_foto(r["foto"]))
    if ada or (total is not None and round(total) < 100):
        st.write("")
        if st.button("EDIT ALASAN" if ada else "Alasan tidak target", type="primary", width="stretch"):
            st.session_state["buka"] = ("notes", bln, prn, tgl)
            st.rerun()


@st.dialog("NOTES", width="large")
def dlg_notes(bln, prn, tgl):
    kontrol_jendela_pub("notes")
    kepala_pub("notes", "NOTES — ALASAN TIDAK TARGET")
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>TANGGAL</b>: {tgl_id(tgl)} &nbsp;&nbsp; <b>NAMA</b>: {html.escape(nama)}</div>",
                unsafe_allow_html=True)
    lama = data.alasan_hari(prn, tgl)
    st.caption("Isi masalah yang membuat hasil kerja tidak mencapai target (maksimal 5), lengkap dengan waktu yang "
               "terpakai dan foto bila ada." + (" Kamu sedang mengedit pengajuan sebelumnya; setelah diajukan ulang, "
                                                "atasan akan menerima notifikasi baru." if lama else ""))
    for c, t in zip(st.columns([5, 1.6, 2.4]), ["MASALAH", "WAKTU (MENIT)", "FOTO"]):
        c.markdown(f"**{t}**")
    items = []
    for i in range(5):
        l = lama[i] if i < len(lama) else {"masalah": "", "menit": 0, "foto": ""}
        with st.container(key=f"nt_{i}"):
          c = st.columns([5, 1.6, 2.4], vertical_alignment="center")
          m = c[0].text_input("masalah", key=f"nm_{tgl}_{i}", value=l["masalah"], label_visibility="collapsed",
                              placeholder=f"Masalah {i + 1}", max_chars=200)
          w = c[1].number_input("menit", key=f"nw_{tgl}_{i}", value=int(l["menit"]), min_value=0, max_value=480, step=5,
                                label_visibility="collapsed")
          f = c[2].file_uploader("foto", key=f"nf_{tgl}_{i}", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
          if l["foto"] and not f:
              c[2].caption("📷 foto tersimpan (unggah lagi untuk mengganti)")
          items.append((m.strip(), int(w), f, l["foto"]))
    isi = [x for x in items if x[0]]
    total = sum(x[1] for x in isi)
    st.markdown(f"**Total waktu bermasalah: {total} menit**")
    if perlu_google():
        st.warning("Untuk memposting, akun Google kamu harus terverifikasi supaya emailnya tercatat sebagai jejak digital.")
        st.button("Verifikasi dengan Google", on_click=st.login, width="stretch", key="g_notes")
    if st.button("AJUKAN ULANG KE ATASAN" if lama else "AJUKAN KE ATASAN", type="primary", width="stretch",
                 disabled=perlu_google()):
        if not isi:
            st.error("Isi minimal satu masalah.")
        elif any(x[1] <= 0 for x in isi):
            st.error("Isi waktu (menit) untuk setiap masalah yang ditulis.")
        elif total > 480:
            st.error("Total waktu tidak boleh lebih dari 480 menit (8 jam).")
        else:
            with st.spinner("Menyimpan…"):
                data.simpan_alasan(prn, nama, tgl, [dict(masalah=m, menit=w, foto=f.getvalue() if f else None,
                                                         foto_lama="" if f else fl) for m, w, f, fl in isi],
                                   email_google())
            st.session_state["galat_jejak"] = data.galat_jejak()
            st.session_state["buka"] = ("terima",)
            st.rerun()


@st.dialog("KEGIATAN HARI INI", width="large")
def dlg_kegiatan(bln, prn, tgl):
    kontrol_jendela_pub("keg")
    kepala_pub("kegiatan", "KEGIATAN HARI INI")
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>TANGGAL</b>: {tgl_id(tgl)} &nbsp;&nbsp; <b>NAMA</b>: {html.escape(nama)}</div>",
                unsafe_allow_html=True)
    lama = data.kegiatan_hari(prn, tgl)
    st.caption("Tidak ada hasil pcs di hari ini. Tulis kegiatan yang kamu kerjakan (mis. membersihkan area, membantu "
               "angkat body). Kosongkan lalu SUBMIT untuk menghapus catatan." if lama else
               "Tidak ada hasil pcs di hari ini. Tulis kegiatan yang kamu kerjakan (mis. membersihkan area, membantu "
               "angkat body), lalu SUBMIT.")
    teks = st.text_area("Kegiatan", value=lama, max_chars=300, height=120, label_visibility="collapsed",
                        placeholder="Kegiatan hari ini…")
    if perlu_google():
        st.warning("Untuk menyimpan, akun Google kamu harus terverifikasi supaya emailnya tercatat sebagai jejak digital.")
        st.button("Verifikasi dengan Google", on_click=st.login, width="stretch", key="g_keg")
    if st.button("SUBMIT", type="primary", width="stretch", disabled=perlu_google() or (not teks.strip() and not lama)):
        with st.spinner("Menyimpan…"):
            data.simpan_kegiatan(prn, nama, tgl, teks, email_google())
            st.session_state["galat_jejak"] = data.galat_jejak()
            rekap.clear()
        st.session_state["buka"] = ("terima", "Kegiatan kamu sudah tersimpan." if teks.strip() else "Catatan kegiatan dihapus.")
        st.rerun()


@st.dialog("TERIMA KASIH")
def dlg_terima(pesan="Alasan kamu sudah diajukan ke atasan."):
    kontrol_jendela_pub("terima")
    kepala_pub("terima", "TERIMA KASIH")
    st.markdown(f"<p style='text-align:center'>{html.escape(pesan)}</p>", unsafe_allow_html=True)
    g = st.session_state.pop("galat_jejak", "")
    if g:
        st.warning("Data tersimpan, tetapi jejak email gagal ditulis ke Google Sheet. Beri tahu admin. Rincian: " + g)
    if st.button("OK", width="stretch", type="primary"):
        st.rerun()


@st.dialog("REKAP BULANAN", width="large")
def dlg_rata(bln, prn):
    kontrol_jendela_pub("rata")
    kepala_pub("rekap", "REKAP BULANAN")
    tombol_kembali()
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>NAMA</b>: {html.escape(nama)} "
                f"&nbsp;&nbsp; <b>BULAN</b>: {nama_bulan(bln)}</div>", unsafe_allow_html=True)
    harian, _ = logic.harian_bulan(bln)
    harian = harian[(harian["prn"] == prn) & (harian["tgl"].str.startswith(bln))].sort_values("tgl")
    absen = logic.absen_bulan(bln, prn)
    n_hari = calendar.monthrange(int(bln[:4]), int(bln[5:]))[1]
    abs_tgl = {int(x["tgl"][8:]): logic.NAMA_ABSEN.get(x["kode"], x["kode"]).upper() for x in absen if x["kode"] != "R"}
    nilai = {int(t[8:]): v for t, v in zip(harian["tgl"], harian["persen"]) if int(t[8:]) not in abs_tgl}
    hari = sorted(set(nilai) | set(abs_tgl))  # hanya tanggal yang ada isinya (libur tidak ditampilkan)
    if not hari:
        st.caption("Belum ada data bulan ini.")
    else:
        df = pd.DataFrame({"Tanggal": hari, "Persen": [nilai.get(d) for d in hari]})  # absen = kosong (garis putus)
        df["Label"] = [f"{round(v)}%" if pd.notna(v) else "" for v in df["Persen"]]
        df["Merah"] = [pd.notna(v) and round(v) < 100 for v in df["Persen"]]
        # angka yang nilainya berdekatan dengan tetangganya bergantian di atas/bawah titik (tetap sejajar dengan tanggal)
        pos, prev_v, prev_pos = [], None, "a"
        for v in df["Persen"]:
            if pd.isna(v):
                pos.append("a")
                prev_v = None
                continue
            pos.append("a")  # semua angka persen berada di atas titiknya
        df["Pos"] = pos
        atas = max(120, int(max([v for v in nilai.values()] + [100]) // 20 + 1) * 20)
        ab = pd.DataFrame({"Tanggal": list(abs_tgl), "Kode": list(abs_tgl.values()), "a": 0, "b": atas}) if abs_tgl else None

        def buat(fs, sumbu, lebar=None):
            """sumbu='penuh' (desktop) | 'isi' (bagian yang digeser, tanpa angka sumbu Y) | 'y' (hanya sumbu Y, tetap di kiri)"""
            hitam = dict(labelColor="#000", domainColor="#000", tickColor="#000")
            if sumbu == "y":
                ya = alt.Axis(labelExpr="datum.value + '%'", tickCount=atas // 20, labelFontSize=13, **hitam)
            elif sumbu == "isi":
                ya = alt.Axis(labels=False, ticks=False, domain=False, tickCount=atas // 20)
            else:
                ya = alt.Axis(labelExpr="datum.value + '%'", tickCount=atas // 20, labelFontSize=13, **hitam)
            x = alt.X("Tanggal:O", title=None, sort=hari, axis=alt.Axis(
                labelAngle=0, labelFontSize=fs, **{**hitam, "labelColor": "rgba(0,0,0,0)" if sumbu == "y" else "#000"}))
            y = alt.Y("Persen:Q", title=None, scale=alt.Scale(domain=[0, atas]), axis=ya)
            if sumbu == "y":  # grafik kosong, hanya untuk menggambar sumbu Y dengan tinggi yang sama
                return alt.Chart(df).mark_line(opacity=0).encode(x=x, y=y).properties(height=300, width=1)
            warna = alt.condition("datum.Merah", alt.value("#e00000"), alt.value("#222"))
            lap = alt.Chart(df).mark_line(color="#5b9bd5", strokeWidth=3, point=alt.OverlayMarkDef(color="#5b9bd5", size=70)).encode(x=x, y=y)
            for kode, dy in (("a", -fs - 3), ("b", fs + 5)):
                lap += alt.Chart(df).transform_filter(alt.datum.Pos == kode).mark_text(dy=dy, fontSize=fs, fontWeight="bold").encode(
                    x=x, y=y, text="Label:N", color=warna)
            if ab is not None:
                lap += alt.Chart(ab).mark_bar(size=26, cornerRadius=6, stroke="#00a2e8", strokeWidth=1.5, fill="#fff", opacity=1).encode(
                    x=x, y=alt.Y("a:Q"), y2="b:Q")
                lap += alt.Chart(ab).mark_text(angle=270, fontSize=fs, fontWeight="bold", color="#000").encode(
                    x=x, y=alt.Y("mid:Q"), text="Kode:N").transform_calculate(mid=str(atas // 2))
            return lap.properties(height=300, **({"width": lebar} if lebar else {}))

        svg = None
        try:
            import vl_convert as vlc
            cfg = lambda c, pad: c.properties(padding=pad).configure(background="#ffffff").to_dict()
            svg_y = vlc.vegalite_to_svg(cfg(buat(13, "y"), {"left": 4, "right": 0, "top": 12, "bottom": 6}))
            svg_isi = vlc.vegalite_to_svg(cfg(buat(13, "isi", lebar=max(300, 54 * len(hari))), {"left": 0, "right": 14, "top": 12, "bottom": 6}))
            svg = (svg_y, svg_isi)
        except Exception:
            svg = None
        if svg:
            # HP: sumbu Y tetap di kiri, hanya bagian grafik yang digeser kiri-kanan (jarak antar tanggal lega)
            st.markdown("<style>.gr-hp{display:none}@media (max-width:640px){.st-key-gr_desk{display:none}.gr-hp{display:flex}}"
                        ".gr-hp{align-items:flex-start;border:1px solid #cfd8e6;border-radius:8px;background:#fff;padding:4px 0}"
                        ".gr-hp .y{flex:none;background:#fff;z-index:2}.gr-hp .s{overflow-x:auto;flex:1;min-width:0}"
                        ".gr-hp svg{display:block;max-width:none}</style>", unsafe_allow_html=True)
            st.markdown(f"<div class='gr-hp'><div class='y'>{svg[0]}</div><div class='s'>{svg[1]}</div></div>"
                        "<div class='gr-hp' style='border:none;font-size:11px;color:#667;padding:0'>&#8596; geser grafik ke kiri / kanan</div>",
                        unsafe_allow_html=True)
        fs_d = 13 if len(hari) <= 14 else 10
        with st.container(key="gr_desk"):
            st.altair_chart(buat(fs_d, "penuh"), width="stretch")
        try:  # unduh gambar grafik (butuh vl-convert-python; bila tidak ada, tombol tidak ditampilkan)
            png = buat(13, "penuh", lebar=max(500, 40 * len(hari))).configure(background="#ffffff").to_dict()
            import vl_convert as vlc
            st.download_button("Unduh gambar grafik", vlc.vegalite_to_png(png, scale=2),
                               file_name=f"GRAFIK_{nama.replace(' ', '_')}_{bln}.png", mime="image/png", width="stretch")
        except Exception:
            pass
    st.markdown("**REKAP TIDAK TARGET**")
    tt = logic.tidak_target(bln, prn)
    if not tt:
        st.caption("Tidak ada hari di bawah target.")
    for n_, r in enumerate(tt):
      with st.container(key=f"tt_{n_}"):
        c = st.columns([1.3, 1.2, 5, 1.3], vertical_alignment="center")
        c[0].write(tgl_id(r["tgl"]))
        c[1].markdown(kotak(r["persen"], 1), unsafe_allow_html=True)
        c[2].write("; ".join(f"{a['masalah']} ({a['menit']} mnt)" for a in r["alasan"]) or "–")
        fotos = [a["foto"] for a in r["alasan"] if a["foto"]]
        if fotos:
            with c[3].popover("📷"):
                for fid in fotos:
                    st.image(img_foto(fid))
    st.markdown("**ABSENSI**")
    if not absen:
        st.caption("Tidak ada catatan absensi.")
    for n_, a in enumerate(absen):
      with st.container(key=f"ab_{n_}"):
        c = st.columns([1.3, 2, 4])
        c[0].write(tgl_id(a["tgl"]))
        c[1].write(logic.NAMA_ABSEN.get(a["kode"], a["kode"]))
        c[2].write(a["ket"] or "")


@st.dialog("KELAS PENCAPAIAN", width="large")
def dlg_kelas(g, k, bln, tgl):
    kontrol_jendela_pub("kelas")
    nm, _, lo, hi, _w = KELAS[k]
    rentang = nm.replace("<60%", "di bawah 60%").replace("≥100%", "100% ke atas")
    kepala_pub("rekap", f"KELAS {rentang}")
    if g == "h":
        pas = [(i, b["nama"], b["hari"][int(tgl[8:])][1]) for i, b in enumerate(baris)
               if b["hari"].get(int(tgl[8:]), (None, None))[0] == "pct"]
        ket = f"Hasil kerja harian {tgl_id(tgl)}"
    else:
        pas = [(i, b["nama"], b["rata"]) for i, b in enumerate(baris) if b["rata"] is not None]
        ket = f"Rata-rata {nama_bulan(bln)}"
    anggota = sorted(kelas_anggota(pas)[k], key=lambda x: x[2])  # persentase terkecil di atas
    st.markdown(f"<div class='id'><b>{ket}</b> &nbsp;·&nbsp; {len(anggota)} karyawan. Tekan nama untuk melihat rinciannya.</div>",
                unsafe_allow_html=True)
    if not anggota:
        st.caption("Tidak ada karyawan di kelas ini.")
    for n_, (i, nama, v) in enumerate(anggota):
        c = st.columns([5, 1.6], vertical_alignment="center")
        if c[0].button(f"{n_ + 1}. {nama}", key=f"kl_{n_}", width="stretch"):
            st.session_state["dari_kelas"] = (g, k, bln, tgl)
            st.session_state["buka"] = ("hari", bln, baris[i]["prn"], tgl) if g == "h" else ("rata", bln, baris[i]["prn"])
            st.rerun()
        c[1].markdown(kotak(v, 1), unsafe_allow_html=True)


# ---------------------------------------------------------------- halaman
atas, kanan = st.columns([6, 1.6], vertical_alignment="center")
kol, _ = atas.columns([1.6, 3])
with kol:
    bulan = pilih_bulan("utama", tersedia=opsi)
if st.session_state.get("me"):
    kanan.caption(f"Halo, **{st.session_state['me_nama']}**" + (" (admin)" if st.session_state.get("adm") else ""))
    if kanan.button("KELUAR", width="stretch"):
        for k_ in ("me", "me_nama", "adm"):
            st.session_state.pop(k_, None)
        st.rerun()
elif kanan.button("LOGIN", type="primary", width="stretch"):
    dlg_login()


@st.cache_data(ttl=60, show_spinner="Memuat data…")
def rekap(bln):
    return logic.rekap_bulan(bln)


baris = rekap(bulan)
# tampilan smartphone: admin boleh melihat siapa pun (pilih nama), karyawan hanya dirinya; belum login = tabel ringkas
_me = st.session_state.get("me")
if st.session_state.get("adm"):
    _boleh, _mode = list(range(len(baris))), "admin"
elif _me:
    _boleh, _mode = [i for i, b in enumerate(baris) if b["prn"] == _me], "me"
else:
    _boleh, _mode = [], ""
klik = tabel(tabel_html(baris, int(bulan[:4]), int(bulan[5:])), key="tabel",
             nama_file=f"MONITORING_HASIL_KERJA_{bulan}.png",
             kal=kalender_data(baris, int(bulan[:4]), int(bulan[5:]), _boleh), mode=_mode)


def buka_hari(prn, tgl, jenis="h"):
    if not st.session_state.get("me"):
        st.session_state["tunda"] = ("hari", prn, tgl, jenis)
        dlg_login()
    elif not boleh(prn):
        st.toast("Kamu hanya bisa membuka baris namamu sendiri.", icon="🔒")
    elif jenis == "k":
        dlg_kegiatan(bulan, prn, tgl)
    else:
        dlg_hari(bulan, prn, tgl)


ada_dlg = False
if klik and klik.get("n") != st.session_state.get("klik_n"):
    ada_dlg = True
    st.session_state.pop("dari_kelas", None)
    st.session_state["klik_n"] = klik["n"]
    for k_ in ("max_hari", "max_notes", "max_rata", "max_login"):
        st.session_state[k_] = False
    try:
        prn_klik = baris[int(klik["p"])]["prn"]
    except (ValueError, IndexError):
        prn_klik = None
    if prn_klik is None:
        pass
    elif klik["k"] in ("h", "k"):
        buka_hari(prn_klik, klik["d"], klik["k"])
    else:
        dlg_rata(bulan, prn_klik)
elif st.session_state.get("tunda") and st.session_state.get("me"):
    ada_dlg = True
    _, p_, t_, j_ = st.session_state.pop("tunda")
    buka_hari(p_, t_, j_)
else:
    pindah = st.session_state.pop("buka", None)
    if pindah:
        ada_dlg = True
        if pindah[0] == "hari" and st.session_state.get("adm"):
            dlg_hari(*pindah[1:])
        elif pindah[0] == "rata" and st.session_state.get("adm"):
            dlg_rata(*pindah[1:])
        elif pindah[0] == "kelas" and st.session_state.get("adm"):
            dlg_kelas(*pindah[1:])
        elif pindah[0] == "notes":
            dlg_notes(*pindah[1:]) if boleh(pindah[2]) else None
        elif pindah[0] == "terima":
            dlg_terima(*pindah[1:])
st.markdown("<div class='ket'><span style='background:#fff'></span>masuk"
            "<span style='background:#ffff00'></span>tidak masuk (S sakit, I ijin, CT cuti, D dispen, R resign)"
            "<span style='background:#f4c2dd'></span>libur</div>", unsafe_allow_html=True)

if st.session_state.get("adm"):  # grafik pencapaian: khusus admin
    tgl_ada = sorted({d for b in baris for d, (j, v) in b["hari"].items() if j == "pct"})
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    kt, _ = st.columns([2, 3])
    d_pil = kt.selectbox("Tanggal untuk grafik harian", tgl_ada, index=len(tgl_ada) - 1 if tgl_ada else None,
                         format_func=lambda d: f"{d:02d}-{bulan[5:]}-{bulan[:4]}", key="g_tgl") if tgl_ada else None
    tgl_g = f"{bulan}-{d_pil:02d}" if d_pil else ""
    ph = [(i, b["nama"], b["hari"][d_pil][1]) for i, b in enumerate(baris) if d_pil and b["hari"].get(d_pil, (None, None))[0] == "pct"]
    pb = [(i, b["nama"], b["rata"]) for i, b in enumerate(baris) if b["rata"] is not None]
    kg = grafik(data_grafik(ph, f"PENCAPAIAN HARIAN — {tgl_id(tgl_g)}" if tgl_g else "PENCAPAIAN HARIAN", f"{len(ph)} karyawan"),
                data_grafik(pb, f"PENCAPAIAN BULANAN — {nama_bulan(bulan)}", f"{len(pb)} karyawan (rata-rata bulan)"))
    if kg and kg.get("n") != st.session_state.get("klik_gn"):
        st.session_state["klik_gn"] = kg["n"]
        if not ada_dlg:
            for k_ in ("max_kelas", "max_hari", "max_rata"):
                st.session_state[k_] = False
            st.session_state.pop("dari_kelas", None)
            dlg_kelas(kg["g"], int(kg["k"]), bulan, tgl_g)
