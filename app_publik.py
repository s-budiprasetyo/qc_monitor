"""Halaman utama (umum): Monitoring Hasil Kerja Karyawan. Jalankan: streamlit run app_publik.py"""
import calendar
import html
import streamlit as st
from core import calc, data

BULAN = ["JANUARI", "FEBRUARI", "MARET", "APRIL", "MEI", "JUNI", "JULI", "AGUSTUS",
         "SEPTEMBER", "OKTOBER", "NOVEMBER", "DESEMBER"]

st.set_page_config(page_title="Monitoring Hasil Kerja Karyawan", layout="wide")
st.markdown("""<style>
table.t{border-collapse:collapse;width:100%;font-size:12px;text-align:center}
table.t th,table.t td{border:1px solid #000;padding:3px 1px;white-space:nowrap}
table.t td.n,table.t th.n{text-align:left;padding-left:4px}
table.t th.we{background:#ffff00;color:#e00000}
.v{display:inline-block;border:2px solid #000;border-radius:6px;padding:1px 3px;font-weight:600}
.m{color:#e00000}
</style>""", unsafe_allow_html=True)


def nama_bulan(kode):
    return f"{BULAN[int(kode[5:]) - 1]} {kode[:4]}"


def kotak(v, desimal=0):
    # merah bila angka yang tampil masih di bawah 100%
    teks = f"{v:.{desimal}f}".replace(".", ",") + "%"
    return f"<span class='v{' m' if round(v, desimal) < 100 else ''}'>{teks}</span>"


def tabel_html(baris, tahun, bln):
    n_hari = calendar.monthrange(tahun, bln)[1]
    h = "<table class='t'><tr><th class='n'>NAMA</th><th>PRN</th>"
    for d in range(1, n_hari + 1):
        h += f"<th class='{'we' if calendar.weekday(tahun, bln, d) >= 5 else ''}'>{d}</th>"
    h += "<th>RATA RATA</th></tr>"
    for nama, prn, per_hari, rata in baris:
        h += f"<tr><td class='n'>{html.escape(nama)}</td><td>{html.escape(prn)}</td>"
        for d in range(1, n_hari + 1):
            v = per_hari.get(d)
            h += f"<td>{kotak(v) if v is not None else ''}</td>"
        h += f"<td>{kotak(rata, 1)}</td></tr>"
    return h + "</table>"


st.markdown("<h1 style='text-align:center'>MONITORING HASIL KERJA KARYAWAN</h1>", unsafe_allow_html=True)
opsi = data.daftar_bulan()
if not opsi:
    st.info("Belum ada data hasil kerja. Admin perlu mengupload file SAP terlebih dahulu.")
    st.stop()
kol, _ = st.columns([1, 3])
bulan = kol.selectbox("BULAN", opsi[::-1], format_func=nama_bulan)

karyawan, alias, target = data.baca("karyawan"), data.baca("alias"), data.baca("target")
hasil = data.baca(f"hasil_{bulan}")
peta = calc.peta_nama(karyawan, alias)
hasil = hasil.assign(prn=hasil["nama_sap"].map(peta)).dropna(subset=["prn"])
harian, _ = calc.hitung_harian(hasil, target)

nama_web = dict(zip(karyawan["prn"], karyawan["nama_web"]))
baris = []
for prn, g in harian.groupby("prn"):
    per_hari = {int(t[8:]): p for t, p in zip(g["tgl"], g["persen"])}
    baris.append((nama_web.get(prn, prn), prn, per_hari, g["persen"].mean()))
baris.sort(key=lambda b: b[0])

st.markdown(tabel_html(baris, int(bulan[:4]), int(bulan[5:])), unsafe_allow_html=True)
