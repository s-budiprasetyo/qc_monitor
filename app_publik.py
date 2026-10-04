"""Halaman utama (umum): Monitoring Hasil Kerja Karyawan. Jalankan: streamlit run app_publik.py"""
import base64
import calendar
import hmac
import html

import altair as alt
import pandas as pd
import streamlit as st

from core import data, logic, parsers
from core.tabel import tabel
from core.ui import gaya_global, ikon, kepala, kontrol_jendela

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

st.set_page_config(page_title="Monitoring Hasil Kerja Karyawan", layout="wide")
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
    return "<td></td>"


def tabel_html(baris, tahun, bln):
    n_hari = calendar.monthrange(tahun, bln)[1]
    # tanggal sesudah data SAP terakhir yang diposting disembunyikan (belum ada nilainya)
    ada = [d for b in baris for d, (j, v) in b["hari"].items() if j == "pct" or (j == "abs" and v != "R")]
    if ada:
        n_hari = max(ada)
    h = "<table class='t'><tr><th class='n'>NAMA</th><th class='p'>PRN</th>"
    for d in range(1, n_hari + 1):
        h += f"<th class='{'we' if calendar.weekday(tahun, bln, d) >= 5 else ''}'>{d}</th>"
    h += "<th>RATA RATA</th></tr>"
    for b in baris:
        h += f"<tr><td class='n'>{html.escape(b['nama'])}</td><td class='p'>{html.escape(b['prn'])}</td>"
        for d in range(1, n_hari + 1):
            jenis, nilai = b["hari"].get(d, (None, None))
            h += sel(jenis, nilai, b["prn"], d)
        rata = kotak(b["rata"], 1, klik=f"data-k='r' data-p='{html.escape(b['prn'])}'") if b["rata"] is not None else ""
        h += f"<td>{rata}</td></tr>"
    return h + "</table>"


gaya_global()
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


@st.dialog("LOGIN")
def dlg_login():
    kontrol_jendela("login")
    kepala("evaluasi", "LOGIN KARYAWAN")
    with st.form("form_login"):
        u = st.text_input("User", placeholder="mis. QC-NAMA")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("MASUK", type="primary", width="stretch")
    if "auth" in st.secrets:  # lapis pertama (opsional): akun Google sebagai jejak email
        try:
            if st.user.is_logged_in:
                st.caption(f"Akun Google terverifikasi: {st.user.email}")
            else:
                st.button("Verifikasi dengan Google (disarankan)", on_click=st.login, width="stretch")
        except Exception:
            pass
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
    kontrol_jendela("hari")
    kepala("hasil", "HASIL KERJA HARIAN")
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>TANGGAL</b>: {tgl_id(tgl)} &nbsp;&nbsp; <b>NAMA</b>: {html.escape(nama)} "
                f"&nbsp;&nbsp; <b>PRN</b>: {html.escape(prn)}</div>", unsafe_allow_html=True)
    rinci, total = logic.detail_hari(bln, prn, tgl)
    h = "<table class='d'><tr><th>TYPE</th><th>OPERATION</th><th>PERIKSA</th><th>TARGET</th><th>% HASIL KERJA</th></tr>"
    for r in rinci:
        h += (f"<tr><td class='l'>{html.escape(r['type'])}</td><td>OP{html.escape(r['op'])}</td><td>{angka(r['periksa'])}</td>"
              f"<td>{angka(r['target']) if r['target'] else '-'}</td>"
              f"<td>{kotak(r['pct'], 1) if r['pct'] is not None else '-'}</td></tr>")
    h += f"<tr class='tot'><td colspan='4' class='l'>% TOTAL</td><td>{kotak(total, 1) if total is not None else '-'}</td></tr></table>"
    st.markdown(h, unsafe_allow_html=True)
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
    kontrol_jendela("notes")
    kepala("evaluasi", "NOTES — ALASAN TIDAK TARGET")
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
            st.session_state["buka"] = ("terima",)
            st.rerun()


@st.dialog("TERIMA KASIH")
def dlg_terima():
    kontrol_jendela("terima")
    st.markdown("<h3 style='text-align:center'>TERIMA KASIH</h3><p style='text-align:center'>"
                "Alasan kamu sudah diajukan ke atasan.</p>", unsafe_allow_html=True)
    if st.button("OK", width="stretch", type="primary"):
        st.rerun()


@st.dialog("REKAP BULANAN", width="large")
def dlg_rata(bln, prn):
    kontrol_jendela("rata")
    kepala("evaluasi", "REKAP BULANAN")
    nama = logic.peta_nama_prn().get(prn, prn)
    st.markdown(f"<div class='id'><b>NAMA</b>: {html.escape(nama)} &nbsp;&nbsp; <b>PRN</b>: {html.escape(prn)} "
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
        atas = max(120, int(max([v for v in nilai.values()] + [100]) // 20 + 1) * 20)
        x = alt.X("Tanggal:O", title=None, sort=hari, axis=alt.Axis(labelAngle=0, labelFontSize=11))
        y = alt.Y("Persen:Q", title=None, scale=alt.Scale(domain=[0, atas]),
                  axis=alt.Axis(labelExpr="datum.value + '%'", tickCount=atas // 20))
        warna = alt.condition("datum.Merah", alt.value("#e00000"), alt.value("#222"))
        lap = alt.Chart(df).mark_line(color="#5b9bd5", strokeWidth=3, point=alt.OverlayMarkDef(color="#5b9bd5", size=70)).encode(x=x, y=y)
        lap += alt.Chart(df).mark_text(dy=-14, fontSize=11, fontWeight="bold").encode(
            x=x, y=y, text="Label:N", color=warna)
        if abs_tgl:
            ab = pd.DataFrame({"Tanggal": list(abs_tgl), "Kode": list(abs_tgl.values()), "a": 0, "b": atas})
            lap += alt.Chart(ab).mark_bar(size=26, cornerRadius=6, stroke="#00a2e8", strokeWidth=1.5, fill="#fff", opacity=1).encode(
                x=x, y=alt.Y("a:Q"), y2="b:Q")
            lap += alt.Chart(ab).mark_text(angle=270, fontSize=13, fontWeight="bold", color="#000").encode(
                x=x, y=alt.Y("mid:Q"), text="Kode:N").transform_calculate(mid=str(atas // 2))
        st.altair_chart(lap.properties(height=300), width="stretch")
    st.markdown("**REKAP TIDAK TARGET**")
    tt = logic.tidak_target(bln, prn)
    if not tt:
        st.caption("Tidak ada hari di bawah target.")
    for r in tt:
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
    for a in absen:
        c = st.columns([1.3, 2, 4])
        c[0].write(tgl_id(a["tgl"]))
        c[1].write(logic.NAMA_ABSEN.get(a["kode"], a["kode"]))
        c[2].write(a["ket"] or "")


# ---------------------------------------------------------------- halaman
atas, kanan = st.columns([6, 1.6], vertical_alignment="center")
kol, _ = atas.columns([1, 3])
bulan = kol.selectbox("BULAN", opsi[::-1], format_func=nama_bulan)
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
klik = tabel(tabel_html(baris, int(bulan[:4]), int(bulan[5:])), key="tabel",
             nama_file=f"MONITORING_HASIL_KERJA_{bulan}.png")


def buka_hari(prn, tgl):
    if not st.session_state.get("me"):
        st.session_state["tunda"] = ("hari", prn, tgl)
        dlg_login()
    elif not boleh(prn):
        st.toast("Kamu hanya bisa membuka baris namamu sendiri.", icon="🔒")
    else:
        dlg_hari(bulan, prn, tgl)


if klik and klik.get("n") != st.session_state.get("klik_n"):
    st.session_state["klik_n"] = klik["n"]
    for k_ in ("max_hari", "max_notes", "max_rata", "max_login"):
        st.session_state[k_] = False
    if klik["k"] == "h":
        buka_hari(klik["p"], klik["d"])
    else:
        dlg_rata(bulan, klik["p"])
elif st.session_state.get("tunda") and st.session_state.get("me"):
    _, p_, t_ = st.session_state.pop("tunda")
    buka_hari(p_, t_)
else:
    pindah = st.session_state.pop("buka", None)
    if pindah:
        if pindah[0] == "notes":
            dlg_notes(*pindah[1:]) if boleh(pindah[2]) else None
        elif pindah[0] == "terima":
            dlg_terima()
st.markdown("<div class='ket'><span style='background:#fff'></span>masuk"
            "<span style='background:#ffff00'></span>tidak masuk (S sakit, I ijin, CT cuti, D dispen, R resign)"
            "<span style='background:#f4c2dd'></span>libur</div>", unsafe_allow_html=True)

catatan = logic.catatan_otomatis(bulan)
if catatan:
    with st.expander(f"Catatan otomatis ({len(catatan)})"):
        st.caption("Operation tanpa target (OP107) tidak dihitung persennya dan dicatat otomatis.")
        st.dataframe([{"TANGGAL": c["tgl"], "NAMA": c["nama"], "CATATAN": c["teks"]} for c in catatan],
                     hide_index=True, width="stretch")
