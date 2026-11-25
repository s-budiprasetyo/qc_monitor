"""Laporan bulanan REKAPAN PEMAKAIAN LABEL QC & SK (kolom E–U format file REKAPAN) + unduh Excel (satu bulan / setahun)."""
from datetime import datetime

import pandas as pd
import streamlit as st

from core import akses, data, rekap_pakai as R
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))

st.markdown("""
<style>
.block-container{max-width:1500px}
.lp-judul{font-size:2rem;font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.2rem 0 0}
.lp-sub{color:#5b7399;font-size:14px;margin-bottom:.9rem}
.peringatan{background:#fff7e0;border:1px solid #f0d88a;border-radius:12px;padding:10px 14px;font-size:13px;color:#6b5200;margin:.4rem 0}
table.rp{border-collapse:collapse;font-size:12.5px;width:100%}
table.rp th{background:#1a5fc8;color:#fff;padding:6px 7px;border:1px solid #b8c7dd;text-align:center;font-size:11.5px;position:sticky;top:0;z-index:3}
table.rp td{padding:4px 7px;border:1px solid #d6e0ef;text-align:right;white-space:nowrap}
table.rp td.t{text-align:left;font-weight:700;position:sticky;left:0;background:#fff;z-index:1}
table.rp td.n{text-align:center;color:#7b8fb0}
table.rp tr.ce7 td{background:#fff9e5}
table.rp tr.sni td{background:#fff7ec;color:#7a5a1e}
table.rp tr.tot td{background:#eaf3ff;font-weight:800;color:#0b3d91}
table.rp td.m{color:#c00000;font-weight:800}
.bungkus{overflow:auto;max-height:640px;border:1px solid #d6e4f8;border-radius:10px}
@media (max-width:700px){.lp-judul{font-size:1.5rem}}
</style>
""", unsafe_allow_html=True)

hari_ini = datetime.now(data.WIB).date()
st.markdown("<div class='lp-judul'>REKAPAN PEMAKAIAN LABEL</div><div class='lp-sub'>Laporan bulanan pemakaian label QC TK & SK. "
            "Stok sistem = (stok bulan lalu + pengambilan) − (bagus OP100 + afkir proses + lengket + kotor + garis).</div>", unsafe_allow_html=True)

c1, c2, c3 = st.columns([1, 1, 2.2], vertical_alignment="bottom")
tahun = c1.selectbox("Tahun", list(range(hari_ini.year, 2025, -1)), key="rp_th")
bulan_n = c2.selectbox("Bulan", range(1, 13), index=hari_ini.month - 1 if tahun == hari_ini.year else 11, format_func=lambda m: R.NAMA_BULAN[m], key="rp_bl")
dept_pil = c3.segmented_control("Departemen", ["QC", "SK", "Gabungan QC + SK"], default="QC", key="rp_dept", label_visibility="collapsed") or "QC"
dept = {"QC": "QC", "SK": "SK"}.get(dept_pil, "GAB")
bulan = f"{tahun}-{bulan_n:02d}"


@st.cache_data(ttl=60, show_spinner="Menghitung…")
def _muat(b, d, versi):
    df, cat = R.data_bulan(b, d)
    return R.hitung(df), cat


riw = R.riwayat()
if bulan in riw and dept == "GAB":  # bulan sebelum aplikasi berjalan: angka dari file REKAPAN lama
    isi = pd.DataFrame(0, index=R.NAMA + [R.SNI], columns=R.KOLOM_ANGKA, dtype=float)
    for n, v in riw[bulan].items():
        if n in isi.index:
            for c in R.KOLOM_ANGKA:
                isi.loc[n, c] = v.get(c, 0)
    df, cat = R.hitung(isi), ["Angka dari file REKAPAN lama (gabungan QC + SK)."]
elif bulan in riw:
    df, cat = None, ["Bulan ini terjadi sebelum aplikasi dipakai: hanya tersedia sebagai Gabungan QC + SK (dari file REKAPAN lama)."]
else:
    df, cat = _muat(bulan, dept, data.versi() if hasattr(data, "versi") else 0)

if cat:
    st.markdown("<div class='peringatan'>" + "<br>".join("• " + t for t in cat) + "</div>", unsafe_allow_html=True)

KOLOM = [("E", "NO"), ("F", "TYPE"), ("G", "RENCANA<br>PRODUKSI"), ("H", f"STOK<br>{R.NAMA_BULAN[int(R.bulan_sebelum(bulan)[5:])].upper()}"), ("I", "PENGAMBILAN<br>(BKB)"),
         ("J", "BAGUS<br>OP100"), ("K", "AFKIR<br>PROSES"), ("L", "LENGKET"), ("M", "KOTOR"), ("N", "GARIS"), ("O", "PERBAIKAN"), ("P", "GERINDA"),
         ("Q", "CEK<br>ULANG"), ("R", "TAP &<br>TAD"), ("S", "SETTING<br>CR"), ("T", "TOTAL<br>RUSAK"), ("U", "% AFKIR")]


def _f(x):
    return "-" if not x else f"{int(x):,}".replace(",", ".")


def _tabel(d):
    h = "<table class='rp'><tr>" + "".join(f"<th>{t}</th>" for _, t in KOLOM) + "</tr>"

    def baris(n, no, kelas):
        x = d.loc[n]
        sel = f"<td class='n'>{no}</td><td class='t'>{n}</td>"
        for c, _ in KOLOM[2:-1]:
            sel += f"<td>{_f(x[c])}</td>"
        pct = f"{x['U'] * 100:.1f}%".replace(".", ",") if x["J"] else "-"
        return f"<tr class='{kelas}'>{sel}<td>{pct}</td></tr>"
    for i, n in enumerate(R.NAMA):
        h += baris(n, i + 1, "ce7" if n == "CE7" else "")
    t = R.total(d)
    h += ("<tr class='tot'><td class='n' colspan='2'>TOTAL</td>" + "".join(f"<td>{_f(t[c])}</td>" for c, _ in KOLOM[2:-1])
          + f"<td>{(f'{t[chr(85)] * 100:.1f}%'.replace('.', ',') if t['J'] else '-')}</td></tr>")
    h += baris(R.SNI, 47, "sni")
    return h + "</table>"


if df is None:
    st.stop()
st.markdown(f"<div class='bungkus'>{_tabel(df)}</div>", unsafe_allow_html=True)
st.caption("Baris CE7 = CE7 + semua warna. Baris SNI = jumlah semua type CW kecuali CW52J. TOTAL tidak memuat baris SNI. "
           "Stok sistem dan stok akhir aktual (kolom X, Y) serta stok body (AG–AM) ada di file Excel.")

st.markdown("**Unduh Excel**")
d1, d2 = st.columns([1.2, 2.8], vertical_alignment="bottom")
periode = d1.segmented_control("Periode", ["Bulan ini saja", f"Semua bulan {tahun}"], default="Bulan ini saja", key="rp_per", label_visibility="collapsed") or "Bulan ini saja"
setahun = periode != "Bulan ini saja"
kunci = f"rp_x_{bulan}_{dept}_{int(setahun)}"
if d2.button("Siapkan file Excel", key="rp_siap"):
    from core import rekap_pakai_xlsx as X
    with st.spinner("Menyusun Excel…"):
        st.session_state[kunci] = X.bytes_xlsx(bulan, dept, setahun)
if st.session_state.get(kunci):
    nama = f"REKAPAN_PEMAKAIAN_LABEL_{dept}_{tahun if setahun else bulan}.xlsx"
    st.download_button("⬇ Unduh Excel", st.session_state[kunci], file_name=nama,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="rp_unduh")
    if setahun and dept != "GAB":
        st.caption("Bulan sebelum aplikasi dipakai (Januari–Oktober) hanya tersedia untuk Gabungan QC + SK, jadi tidak ikut di file ini.")
