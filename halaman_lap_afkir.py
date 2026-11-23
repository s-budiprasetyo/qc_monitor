"""Laporan % afkir label: tabel operator x tanggal; kotak persen bisa diklik (rincian hari itu); RATA RATA membuka grafik + hari tertinggi."""
import calendar
import html

import altair as alt
import pandas as pd
import streamlit as st

from core import akses, data, laporan
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))

NAMA_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]
HIJAU, MERAH = "#dff3e6", "#fde2e2"

st.markdown("""
<style>
.block-container{max-width:1240px}
.lp-judul{font-size:2rem;font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.2rem 0 0}
.lp-sub{color:#5b7399;font-size:14px;margin-bottom:.9rem}
.kpi{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:.4rem 0 1rem}
.kpi div.k{background:#fff;border:1px solid #d6e4f8;border-radius:14px;padding:12px 16px;box-shadow:0 2px 10px #2a5db00f}
.kpi small{display:block;font-size:11.5px;font-weight:800;color:#5b7399;letter-spacing:.6px}
.kpi b{display:block;font-size:22px;color:#0b3d91;margin:2px 0}
.kpi span{font-size:12.5px;color:#7b8fb0}
.leg{display:flex;gap:16px;font-size:12px;color:#5b7399;margin:.3rem 0 .6rem;flex-wrap:wrap}
.leg i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-2px}
table.rin{border-collapse:collapse;width:100%;font-size:13px}
table.rin th{background:#1a5fc8;color:#fff;padding:7px 8px;font-size:12px;border:1px solid #b8c7dd;text-align:center}
table.rin td{padding:6px 8px;border:1px solid #d6e0ef;text-align:right}
table.rin td.t{text-align:left}
table.rin tr.sni td{background:#fff7ec;color:#7a5a1e}
table.rin tr.tot td{background:#eaf3ff;font-weight:800;color:#0b3d91}
table.rin td.m{background:#fde2e2;color:#c00000;font-weight:800}
.cat{background:#f4f8ff;border-left:4px solid #2a8fe8;border-radius:8px;padding:8px 12px;font-size:13px;color:#33507a;margin:.4rem 0}
@media (max-width:700px){.kpi{grid-template-columns:1fr}.lp-judul{font-size:1.5rem}}
div#portal{display:none!important}
</style>
""", unsafe_allow_html=True)


def _bln(k):
    return f"{NAMA_BULAN[int(k[5:])]} {k[:4]}"


def _p(x, nol="-"):
    return nol if pd.isna(x) else f"{x * 100:.2f}%".replace(".", ",")


def _n(x):
    return f"{int(x):,}".replace(",", ".")


@st.cache_data(ttl=60, show_spinner=False)
def _muat(bulan, versi):
    return laporan.tabel(bulan)


def _rincian_html(d):
    h = ("<div style='overflow-x:auto'><table class='rin'><tr><th>LABEL</th><th>PCS BAGUS</th><th>LABEL AFKIR (KOTOR)</th>"
         "<th>% LABEL AFKIR</th></tr>")
    tot_a = tot_b = 0
    for r in d.itertuples():
        a = int(r.kotor)
        sni = str(r.label) == "SNI"
        pct = a / r.bagus if r.bagus > 0 else float("nan")
        merah = pct > laporan.BATAS_KOTOR if r.bagus > 0 else False
        h += (f"<tr class='{'sni' if sni else ''}'><td class='t'>{html.escape(str(r.label))}</td><td>{_n(r.bagus)}</td>"
              f"<td class='{'m' if merah else ''}'>{_n(a)}</td><td class='{'m' if merah else ''}'>{_p(pct)}</td></tr>")
        tot_a += a
        tot_b += r.bagus
    pt = tot_a / tot_b if tot_b > 0 else float("nan")
    h += (f"<tr class='tot'><td class='t' colspan='2'>% TOTAL AFKIR LABEL = {_n(tot_a)} ÷ {_n(tot_b)} pcs bagus</td><td>{_n(tot_a)}</td><td>{_p(pt)}</td></tr></table></div>")
    return h


@st.dialog("RINCIAN AFKIR LABEL", width="large")
def dlg_hari(df, prn, nama, tgl):
    st.markdown(f"**{html.escape(nama)}** · {tgl[8:]}-{tgl[5:7]}-{tgl[:4]}")
    d = df[(df["prn"] == prn) & (df["tgl"] == tgl)]
    st.markdown(_rincian_html(d), unsafe_allow_html=True)
    cat = [c for c in d["catatan"].unique() if str(c).strip()]
    for c in cat:
        st.markdown(f"<div class='cat'>📝 {html.escape(str(c))}</div>", unsafe_allow_html=True)
    st.caption("% label afkir = afkir kotor ÷ pcs bagus. Total pcs bagus = jumlah semua baris label, label SNI ikut dihitung (pcs bagus SNI = jumlah pcs bagus semua type CW). Di atas 0,5% berwarna merah.")


def _jenis_dominan(r):
    j = {"Lengket": r["lengket"], "Garis": r["garis"], "Kotor": r["kotor"], "Proses": r["proses"]}
    k, v = max(j.items(), key=lambda x: x[1])
    return f"{k} ({_n(v)})" if v > 0 else "-"


@st.dialog("RATA RATA % AFKIR LABEL", width="large")
def dlg_rata(df, rh, prn, nama, bulan):
    st.markdown(f"**{html.escape(nama)}** · {_bln(bulan)}")
    o = rh[rh["prn"] == prn].sort_values("tgl").copy()
    tot = o["afkir"].sum() / o["bagus"].sum() if o["bagus"].sum() > 0 else float("nan")
    st.markdown(f"<div class='kpi' style='grid-template-columns:repeat(3,1fr)'><div class='k'><small>% AFKIR LABEL BULAN INI</small><b>{_p(tot)}</b>"
                f"<span>{_n(o['afkir'].sum())} afkir ÷ {_n(o['bagus'].sum())} pcs bagus</span></div>"
                f"<div class='k'><small>HARI TERCATAT</small><b>{len(o)}</b><span>hari ada input label</span></div>"
                f"<div class='k'><small>TERTINGGI</small><b>{_p(o['pct'].max())}</b><span>{o.loc[o['pct'].idxmax(), 'tgl'][8:] + ' ' + NAMA_BULAN[int(bulan[5:])] if o['pct'].notna().any() else '-'}</span></div></div>",
                unsafe_allow_html=True)
    if o["pct"].notna().any():
        c = o.dropna(subset=["pct"]).assign(hari=lambda x: x["tgl"].str[8:].astype(int), persen=lambda x: x["pct"] * 100)
        atas = c.nlargest(3, "persen")
        dasar = alt.Chart(c).encode(x=alt.X("hari:Q", title="Tanggal", axis=alt.Axis(tickMinStep=1, grid=False, labelColor="#222", titleColor="#222")),
                                    y=alt.Y("persen:Q", title="% afkir label", axis=alt.Axis(labelColor="#222", titleColor="#222"), scale=alt.Scale(zero=True)))
        gr = (dasar.mark_area(opacity=.12, color="#2a8fe8", line={"color": "#1a5fc8", "strokeWidth": 2.4}, interpolate="linear")
              + dasar.mark_point(color="#1a5fc8", filled=True, size=55)
              + alt.Chart(atas).mark_point(color="#d93025", filled=True, size=120).encode(x="hari:Q", y="persen:Q")
              + alt.Chart(atas).mark_text(dy=-14, color="#d93025", fontWeight="bold", fontSize=12).encode(x="hari:Q", y="persen:Q", text=alt.Text("persen:Q", format=".2f")))
        st.altair_chart(gr.properties(height=260), use_container_width=True)
    st.markdown("**% afkir label tertinggi**")
    top = o.dropna(subset=["pct"]).nlargest(5, "pct")
    if top.empty:
        st.caption("Belum ada data.")
    for r in top.itertuples():
        d = df[(df["prn"] == prn) & (df["tgl"] == r.tgl)]
        cat = "; ".join(c for c in d["catatan"].unique() if str(c).strip()) or "— belum ada catatan foreman"
        jenis = _jenis_dominan({"lengket": d["lengket"].sum(), "garis": d["garis"].sum(), "kotor": d["kotor"].sum(), "proses": d["proses"].sum()})
        st.markdown(f"<div class='cat'><b>{r.tgl[8:]}-{r.tgl[5:7]}</b> · <b>{_p(r.pct)}</b> ({_n(r.afkir)} ÷ {_n(r.bagus)})<br>"
                    f"<span style='color:#5b7399'>Alasan:</span> {html.escape(cat)}</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ halaman
st.markdown("<div class='lp-judul'>% AFKIR LABEL</div><div class='lp-sub'>% label afkir = label afkir kotor (input foreman) ÷ pcs bagus SAP per operator per hari. "
            "Klik kotak persen untuk rincian hari itu, klik RATA RATA untuk grafik dan hari tertinggi.</div>", unsafe_allow_html=True)
ada = sorted(set(data.daftar_bulan()), reverse=True)
if not ada:
    st.info("Belum ada data hasil kerja dari SAP.")
    st.stop()
a, b = st.columns([1.3, 1.5], vertical_alignment="bottom")
bulan = a.selectbox("Bulan", ada, format_func=_bln, key="lp_bulan")
bagian = b.segmented_control("Bagian", ["QC", "QC SK"], default="QC", key="lp_bagian") or "QC"
with st.spinner("Menghitung…"):
    df = _muat(bulan, data.versi())
df = df[df["bagian"] == bagian]
if df.empty:
    st.info(f"Belum ada input label afkir {bagian} untuk {_bln(bulan)}.")
    st.stop()
rh = laporan.ringkas_harian(df)
rb = laporan.ringkas_bulan(rh).set_index("prn")

# ringkasan
tot_b, tot_a = rh["bagus"].sum(), rh["afkir"].sum()
pt = tot_a / tot_b if tot_b else float("nan")
hari = rh.groupby("tgl")[["afkir", "bagus"]].sum()
hari["pct"] = hari["afkir"] / hari["bagus"].where(hari["bagus"] > 0)
ht = hari["pct"].idxmax() if hari["pct"].notna().any() else None
lab = df.groupby("label")["kotor"].sum().sort_values(ascending=False)
st.markdown(f"<div class='kpi'><div class='k'><small>% AFKIR LABEL {bagian}</small><b>{_p(pt)}</b><span>{_n(tot_a)} afkir ÷ {_n(tot_b)} pcs bagus</span></div>"
            f"<div class='k'><small>HARI TERTINGGI</small><b>{_p(hari.loc[ht, 'pct']) if ht else '-'}</b><span>{(ht[8:] + ' ' + NAMA_BULAN[int(bulan[5:])]) if ht else '-'}</span></div>"
            f"<div class='k'><small>LABEL PALING BANYAK AFKIR</small><b>{html.escape(str(lab.index[0])) if len(lab) else '-'}</b><span>{_n(lab.iloc[0]) if len(lab) else 0} label afkir</span></div></div>",
            unsafe_allow_html=True)

# matriks operator x tanggal
th, bl = int(bulan[:4]), int(bulan[5:])
hari_n = calendar.monthrange(th, bl)[1]
tgls = [f"{bulan}-{d:02d}" for d in range(1, hari_n + 1)]
ops = rh.drop_duplicates("prn")[["prn", "nama"]].sort_values("nama").reset_index(drop=True)
nilai = pd.DataFrame(index=ops["nama"], columns=[str(d) for d in range(1, hari_n + 1)] + ["RATA RATA"], dtype=float)
merah = pd.DataFrame(False, index=nilai.index, columns=nilai.columns)
for r in rh.itertuples():
    k = str(int(r.tgl[8:]))
    nilai.loc[r.nama, k] = r.pct
    merah.loc[r.nama, k] = bool(r.pct_kotor > laporan.BATAS_KOTOR) if pd.notna(r.pct_kotor) else False
for r in ops.itertuples():
    nilai.loc[r.nama, "RATA RATA"] = rb.loc[r.prn, "pct"]
    merah.loc[r.nama, "RATA RATA"] = bool(rb.loc[r.prn, "pct_kotor"] > laporan.BATAS_KOTOR)
nilai = nilai.loc[:, [c for c in nilai.columns if c == "RATA RATA" or nilai[c].notna().any()]]  # hanya tanggal yang ada data


def _warna(_):
    st_ = pd.DataFrame("", index=nilai.index, columns=nilai.columns)
    for c in nilai.columns:
        for i in nilai.index:
            if pd.notna(nilai.loc[i, c]):
                st_.loc[i, c] = f"background-color:{MERAH if merah.loc[i, c] else HIJAU};color:{'#b3261e' if merah.loc[i, c] else '#14532d'};font-weight:600"
    return st_


tampil = nilai.map(lambda v: "" if pd.isna(v) else _p(v))
gaya = tampil.style.apply(lambda _: _warna(_).map(lambda x: x + ";text-align:right" if x else ""), axis=None)
st.markdown(f"<div class='leg'><span><i style='background:{HIJAU}'></i>≤ 0,5%</span><span><i style='background:{MERAH}'></i>&gt; 0,5%</span>"
            "<span>Kosong = tidak ada pcs bagus SAP · 0,00% = belum ada afkir kotor diinput</span></div>", unsafe_allow_html=True)
ev = st.dataframe(gaya, on_select="rerun", selection_mode="single-cell", key="lp_grid", width="stretch",
                  height=min(45 + 35 * len(nilai), 640))
sel = (ev.selection.cells if ev and ev.selection else None) or []
if not sel:
    st.session_state.pop("lp_dibuka", None)
elif st.session_state.get("lp_dibuka") != tuple(sel[0]):
    st.session_state["lp_dibuka"] = tuple(sel[0])  # dialog yang sudah ditutup tidak muncul lagi pada rerun berikutnya
    bar, kol = sel[0]
    nama = nilai.index[bar]
    prn = ops.loc[ops["nama"] == nama, "prn"].iloc[0]
    if kol == "RATA RATA":
        dlg_rata(df, rh, prn, nama, bulan)
    elif pd.notna(nilai.loc[nama, kol]):
        dlg_hari(df, prn, nama, f"{bulan}-{int(kol):02d}")

# unduh
with st.popover("⬇ Unduh Excel"):
    st.download_button("Bulanan (ringkasan + per hari)", laporan.excel_bulanan(df, f"{bagian} · {_bln(bulan)}"),
                       file_name=f"label_afkir_{bagian.replace(' ', '')}_{bulan}.xlsx", key="dl_b",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
    hari_pilih = st.selectbox("Harian: pilih tanggal posting", sorted(df["tgl"].unique(), reverse=True), key="dl_tgl")
    st.download_button("Harian", laporan.excel_harian(df[df["tgl"] == hari_pilih], f"{bagian} · {hari_pilih}"),
                       file_name=f"label_afkir_{bagian.replace(' ', '')}_{hari_pilih}.xlsx", key="dl_h",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch")
