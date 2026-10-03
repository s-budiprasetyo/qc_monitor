"""Halaman utama (umum): Monitoring Hasil Kerja Karyawan. Jalankan: streamlit run app_publik.py"""
import calendar
import html
import streamlit as st
from core import data, logic

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
.ket span{display:inline-block;width:12px;height:12px;border:1px solid #000;margin:0 4px 0 12px;vertical-align:-1px}
</style>""", unsafe_allow_html=True)


def nama_bulan(kode):
    return f"{BULAN[int(kode[5:]) - 1]} {kode[:4]}"


def kotak(v, desimal=0):
    # merah bila angka yang tampil masih di bawah 100%
    teks = f"{v:.{desimal}f}".replace(".", ",") + "%"
    return f"<span class='v{' m' if round(v, desimal) < 100 else ''}'>{teks}</span>"


def sel(jenis, nilai):
    if jenis == "pct":
        return f"<td>{kotak(nilai)}</td>"
    if jenis == "abs":
        return f"<td class='ab'><span class='v kd'>{html.escape(nilai)}</span></td>"
    if jenis == "libur":
        return "<td class='lb'></td>"
    return "<td></td>"


def tabel_html(baris, tahun, bln):
    n_hari = calendar.monthrange(tahun, bln)[1]
    h = "<div class='wrap'><table class='t'><tr><th class='n'>NAMA</th><th>PRN</th>"
    for d in range(1, n_hari + 1):
        h += f"<th class='{'we' if calendar.weekday(tahun, bln, d) >= 5 else ''}'>{d}</th>"
    h += "<th>RATA RATA</th></tr>"
    for b in baris:
        h += f"<tr><td class='n'>{html.escape(b['nama'])}</td><td>{html.escape(b['prn'])}</td>"
        for d in range(1, n_hari + 1):
            jenis, nilai = b["hari"].get(d, (None, None))
            h += sel(jenis, nilai)
        h += f"<td>{kotak(b['rata'], 1) if b['rata'] is not None else ''}</td></tr>"
    return h + "</table></div>"


st.markdown("<h1 class='judul'>MONITORING HASIL KERJA KARYAWAN</h1>", unsafe_allow_html=True)
opsi = data.daftar_bulan()
if not opsi:
    if not data.pakai_google_sheet():
        st.error("Aplikasi ini belum terhubung ke Google Sheet: **sheet_id** dan **[gcp_service_account]** belum ada di "
                 "Secrets app ini (Manage app → Settings → Secrets). Isi sama persis dengan Secrets app admin.")
        st.stop()
    st.info("Belum ada data hasil kerja. Admin perlu mengupload file SAP terlebih dahulu.")
    st.stop()
kol, _ = st.columns([1, 3])
bulan = kol.selectbox("BULAN", opsi[::-1], format_func=nama_bulan)

baris = logic.rekap_bulan(bulan)
st.markdown(tabel_html(baris, int(bulan[:4]), int(bulan[5:])), unsafe_allow_html=True)
st.markdown("<div class='ket'><span style='background:#fff'></span>masuk"
            "<span style='background:#ffff00'></span>tidak masuk (S sakit, I ijin, CT cuti, D dispen, R resign)"
            "<span style='background:#f4c2dd'></span>libur</div>", unsafe_allow_html=True)

catatan = logic.catatan_otomatis(bulan)
if catatan:
    with st.expander(f"Catatan otomatis ({len(catatan)})"):
        st.caption("Operation tanpa target (OP107) tidak dihitung persennya dan dicatat otomatis.")
        st.dataframe([{"TANGGAL": c["tgl"], "NAMA": c["nama"], "CATATAN": c["teks"]} for c in catatan],
                     hide_index=True, width="stretch")
