"""Monitoring stok label: stok sistem = stok awal + diterima - pcs bagus - afkir, dibandingkan hitungan aktual foreman."""
import html
from datetime import datetime

import pandas as pd
import streamlit as st

from core import akses, data, label, stok
from core.ui import gaya_global

akses.butuh(akses.ADMIN, akses.FOREMAN)
gaya_global()
akses.bilah(tautan=akses.tautan_luar("laporan"))

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
.peringatan{background:#fff7e0;border:1px solid #f0d88a;border-radius:12px;padding:10px 14px;font-size:13px;color:#6b5200;margin-bottom:.8rem}
@media (max-width:700px){.kpi{grid-template-columns:1fr}.lp-judul{font-size:1.5rem}}
</style>
""", unsafe_allow_html=True)


def _n(x):
    return "" if pd.isna(x) else f"{int(x):,}".replace(",", ".")


hari_ini = datetime.now(data.WIB).date()
st.markdown("<div class='lp-judul'>STOK LABEL</div><div class='lp-sub'>Stok label = stok Foreman + stok di tiap meja. "
            "Stok meja = label diterima operator ± pemindahan − pcs bagus SAP − label afkir (semua kategori).</div>", unsafe_allow_html=True)
c1, c2 = st.columns([1.3, 2.7], vertical_alignment="bottom")
tgl = c1.date_input("Stok per tanggal (akhir hari)", value=hari_ini, min_value=datetime.strptime(stok.MULAI, "%Y-%m-%d").date(),
                    max_value=hari_ini, format="DD/MM/YYYY", key="st_tgl")
dept_pil = c2.segmented_control("Departemen", ["QC", "SK", "Gabungan QC + SK"], default="QC", key="st_dept", label_visibility="collapsed") or "QC"
dept = {"QC": "QC", "SK": "SK"}.get(dept_pil)
tgl_s = tgl.strftime("%Y-%m-%d")


@st.cache_data(ttl=60, show_spinner=False)
def _cek_adjust(dpt, versi):
    return stok.adjust_cek(dpt)


def _tgl_id(t):
    return f"{t[8:10]}-{t[5:7]}-{t[:4]}"


def _panel_adjust(dpt):
    """Kapan stok aktual terakhir di-ADJUST jadi stok sistem, dan bukti bahwa stok sistem sudah sama dengan hasil hitung."""
    info, df, belum = _cek_adjust(dpt, data.versi())
    st.markdown(f"**ADJUST STOK {dpt}**")
    if not info:
        st.caption("Belum pernah di-ADJUST. (Foreman: Stok Opname Label → Selisih Stok Opname → ADJUST)")
        return
    w = info["waktu"]
    st.markdown(f"Terakhir di-ADJUST: **stok opname tanggal {_tgl_id(info['tgl'])}**, diproses {w[11:16]} {_tgl_id(w[:10])} oleh {info['oleh']} "
                f"({len(info['lokasi'])} lokasi).")
    ok = int(df["ok"].sum()) if len(df) else 0
    if len(df) and ok == len(df):
        st.success(f"✔ Sudah berlaku: stok sistem akhir hari {_tgl_id(info['tgl'])} sama dengan hasil hitung aktual untuk semua {len(df)} type.")
    elif len(df):
        st.warning(f"{len(df) - ok} dari {len(df)} type stok sistemnya belum sama dengan hasil hitung aktual (lihat tabel di bawah).")
    if belum:
        st.info(f"{len(belum)} lokasi sudah dihitung pada tanggal itu tetapi belum di-ADJUST.")
    if len(df):
        with st.expander("Lihat perbandingan per type (aktual vs stok sistem)"):
            x = pd.DataFrame({"TYPE": df["label"], "AKTUAL (hitung)": df["aktual"], "STOK SISTEM": df["sistem"],
                              "STATUS": ["✔ sudah berlaku" if o else "✘ beda" for o in df["ok"]]})
            st.dataframe(x, hide_index=True, width="stretch", height=min(380, 38 + 35 * len(x)))
            st.caption(f"Stok sistem dihitung akhir hari {_tgl_id(info['tgl'])}. Setelah itu stok bergerak lagi (label bagus, afkir, penerimaan), jadi angka stok hari ini bisa berbeda.")


for _d in (["QC", "SK"] if dept is None else [dept]):
    _panel_adjust(_d)
with st.spinner("Menghitung stok…"):
    total = stok.stok_semua(tgl_s, dept)
    permeja = stok.stok_per_meja(tgl_s, dept)
    sebaran = stok.stok_sebaran(tgl_s, dept)
    _, tanpa = stok.saldo(tgl_s)
if total.empty:
    st.info(f"Belum ada stok label {dept_pil}. Foreman: Input Label Bagus / Stok Opname, lalu operator/admin mencatat label diterima di halaman utama.")
    st.stop()
st.markdown("<div class='peringatan'>Stok dihitung mulai "
            f"{stok.MULAI[8:]}-{stok.MULAI[5:7]}-{stok.MULAI[:4]} dari 0. Stok bisa minus sampai Label Bagus dan hitungan per meja diinput "
            "(Foreman: Stok Opname Label → Selisih Stok Opname → ADJUST).</div>", unsafe_allow_html=True)
minus = int((total["total"] < 0).sum())
nmeja = permeja[["pabrik", "meja"]].drop_duplicates().shape[0] if len(permeja) else 0
st.markdown(f"<div class='kpi'><div class='k'><small>TYPE LABEL</small><b>{len(total)}</b><span>punya stok / pergerakan</span></div>"
            f"<div class='k'><small>TOTAL MINUS</small><b style='color:{'#b3261e' if minus else '#1d6f2f'}'>{minus}</b><span>label</span></div>"
            f"<div class='k'><small>MEJA BERSTOK</small><b>{nmeja}</b><span>meja</span></div></div>", unsafe_allow_html=True)


def _f(v):
    return f"{int(v):,}".replace(",", ".")


def _warna(num, kol):
    def f(col):
        if col.name in kol:
            return ["color:#b3261e;font-weight:800" if v < 0 else "font-weight:700" for v in num[col.name]]
        return [""] * len(col)
    return f


BULAN_ID = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def _lok_baca(lk):
    return "Foreman" if lk == stok.FOREMAN else stok.lok_nama(lk)


def _tab_harian():
    """Matriks TYPE x tanggal 1..31: stok label akhir hari. Klik kotak -> rincian posisi (Foreman / meja + PIC) dan hasil ADJUST."""
    mulai = pd.Period(stok.MULAI[:7], freq="M")
    sekarang = pd.Period(hari_ini.strftime("%Y-%m"), freq="M")
    opsi = [str(p) for p in pd.period_range(mulai, sekarang, freq="M")]
    awal = tgl.strftime("%Y-%m")
    bln = st.selectbox("Bulan", opsi, index=opsi.index(awal) if awal in opsi else len(opsi) - 1, key="st_bln",
                       format_func=lambda b: f"{BULAN_ID[int(b[5:])]} {b[:4]}")
    hari, adj = stok.harian(bln)
    p = pd.Period(bln, freq="M")
    jml = p.days_in_month
    peta, adj_hari, adj_sel = {}, set(), set()
    for tg, sal in hari.items():
        d_ = int(tg[8:])
        for (lk, lb), n in sal.items():
            if n and stok.dept_cocok(lk, dept):
                peta[(lb, d_)] = peta.get((lb, d_), 0) + n
    for tg, x in adj.items():
        for (lk, lb) in x:
            if stok.dept_cocok(lk, dept):
                adj_hari.add(int(tg[8:]))
                adj_sel.add((lb, int(tg[8:])))
    tipe = stok.urut_label({lb for (lb, _d) in peta})
    if not tipe:
        st.info("Belum ada stok label pada bulan ini.")
        return
    kol = {d_: f"{d_}◆" if d_ in adj_hari else str(d_) for d_ in range(1, jml + 1)}
    maks = int(hari_ini.strftime("%d")) if bln == hari_ini.strftime("%Y-%m") else jml
    angka = pd.DataFrame({kol[d_]: [peta.get((lb, d_), 0) if d_ <= maks else None for lb in tipe] for d_ in range(1, jml + 1)})
    teks = angka.copy()
    for c in teks.columns:
        teks[c] = angka[c].map(lambda v: "" if pd.isna(v) else (_f(v) if v else "–"))
    teks.insert(0, "TYPE", tipe)

    def _gaya(df):
        g = pd.DataFrame("", index=df.index, columns=df.columns)
        for j, d_ in enumerate(range(1, jml + 1)):
            c = kol[d_]
            for i, lb in enumerate(tipe):
                v = angka.iloc[i, j]
                if pd.isna(v):
                    continue
                if (lb, d_) in adj_sel:
                    g.loc[i, c] = "background-color:#dff3e4;font-weight:800;color:#14532d"
                elif v < 0:
                    g.loc[i, c] = "color:#b3261e;font-weight:800"
                elif v == 0:
                    g.loc[i, c] = "color:#b6c0d4"
        g["TYPE"] = "font-weight:800;color:#0b3d91"
        return g
    st.caption("Klik satu kotak untuk melihat rincian posisinya. ◆ pada tanggal = ada hasil ADJUST hari itu; kotak hijau = type yang di-ADJUST (angkanya sudah hasil hitung aktual).")
    ev = st.dataframe(teks.style.apply(_gaya, axis=None), hide_index=True, width="stretch", height=min(48 + 35 * len(teks), 640),
                      on_select="rerun", selection_mode="single-cell", key="st_grid",
                      column_config={"TYPE": st.column_config.TextColumn("TYPE", pinned=True, width="small"),
                                     **{kol[d_]: st.column_config.TextColumn(kol[d_], alignment="right", width=62) for d_ in range(1, jml + 1)}})
    sel = (ev.selection.cells if ev and ev.selection else None) or []
    if not sel:
        return
    bar, nm = sel[0]
    if nm == "TYPE" or bar is None or int(bar) >= len(tipe):
        return
    lb, d_ = tipe[int(bar)], int(str(nm).replace("◆", ""))
    tg = f"{bln}-{d_:02d}"
    if tg not in hari:
        st.caption("Belum ada data untuk tanggal itu.")
        return
    pic = stok.pic_meja(tg)
    baris = []
    for (lk, l2), n in hari[tg].items():
        if l2 != lb or not stok.dept_cocok(lk, dept) or (n == 0 and (lk, lb) not in adj.get(tg, {})):
            continue
        a = adj.get(tg, {}).get((lk, lb))
        baris.append((lk, _lok_baca(lk), ", ".join(pic.get(lk, [])) if not stok.adalah_foreman(lk) else "–", n,
                      f"✔ ADJUST: sistem {_f(a[0])} → aktual {_f(a[1])}" if a else ""))
    for (lk, l2), a in adj.get(tg, {}).items():
        if l2 == lb and stok.dept_cocok(lk, dept) and not any(b[0] == lk for b in baris):
            baris.append((lk, _lok_baca(lk), ", ".join(pic.get(lk, [])) if not stok.adalah_foreman(lk) else "–", 0,
                          f"✔ ADJUST: sistem {_f(a[0])} → aktual {_f(a[1])}"))

    def _u(b):
        lk = b[0]
        if stok.adalah_foreman(lk):
            return (0, 0, 0)
        pb, mj = stok._lok_pisah(lk)
        return (1, list(label.PABRIK).index(pb) if pb in label.PABRIK else 9, int(mj) if str(mj).isdigit() else 999)
    baris.sort(key=_u)
    tot = sum(b[3] for b in baris)
    st.markdown(f"**RINCIAN {html.escape(lb)} · {d_:02d}-{bln[5:]}-{bln[:4]}** (stok akhir hari) — total **{_f(tot)}** pcs")
    rd = pd.DataFrame({"POSISI": [b[1] for b in baris], "PIC MEJA (hari itu)": [b[2] for b in baris],
                       "STOK": [_f(b[3]) for b in baris], "KETERANGAN": [b[4] for b in baris]})
    st.dataframe(rd, hide_index=True, width="stretch", height=min(48 + 35 * len(rd), 420),
                 column_config={"STOK": st.column_config.TextColumn("STOK", alignment="right", width="small")})


tH, t0, t1, t2 = st.tabs(["PER TANGGAL", "DI MANA SAJA", "TOTAL PER LABEL", "PER MEJA"])
with tH:
    _tab_harian()
with t0:
    st.caption("Setiap type label: total stok dan sebarannya (Foreman dan meja).")
    ring = []
    for lb in total["label"]:
        x = sebaran[sebaran["label"] == lb]
        ring.append({"Label": lb, "Total": int(total.loc[total["label"] == lb, "total"].iloc[0]),
                     "Sebaran": " · ".join(f"{r.nama} ({_f(r.stok)})" for r in x.itertuples())})
    rt = pd.DataFrame(ring)
    tam = rt.copy()
    tam["Total"] = rt["Total"].map(_f)
    st.dataframe(tam.style.apply(_warna(rt, ["Total"])), hide_index=True, width="stretch", height=min(80 + 38 * len(tam), 680),
                 column_config={"Total": st.column_config.TextColumn("Total", alignment="right", width="small"),
                                "Sebaran": st.column_config.TextColumn("Sebaran (lokasi dan pcs)", width="large")})
    pilih = st.selectbox("Rincian satu type", total["label"], index=None, placeholder="Pilih type label…", key="st_lb")
    if pilih:
        x = sebaran[sebaran["label"] == pilih]
        rd = pd.DataFrame({"Lokasi": x["nama"], "Departemen": x["dept"], "Stok": x["stok"].map(_f)})
        st.dataframe(rd, hide_index=True, width="stretch", column_config={"Stok": st.column_config.TextColumn("Stok", alignment="right")})
with t1:
    num = pd.DataFrame({"Label": total["label"], "Stok Foreman": total["foreman"], "Stok di meja": total["meja"], "Total": total["total"]})
    tam = num.copy()
    for k in ["Stok Foreman", "Stok di meja", "Total"]:
        tam[k] = num[k].map(_f)
    st.dataframe(tam.style.apply(_warna(num, ["Stok Foreman", "Stok di meja", "Total"])), hide_index=True, width="stretch",
                 height=min(80 + 36 * len(tam), 680),
                 column_config={k: st.column_config.TextColumn(k, alignment="right") for k in ["Stok Foreman", "Stok di meja", "Total"]})
with t2:
    if permeja.empty:
        st.info("Belum ada stok di meja.")
    else:
        pil = st.segmented_control("Pabrik", ["Semua"] + [p for p in label.PABRIK if not dept or stok.dept_pabrik(p) == dept], default="Semua", key="st_pab", label_visibility="collapsed") or "Semua"
        d = permeja if pil == "Semua" else permeja[permeja["pabrik"] == pil]
        num = pd.DataFrame({"Pabrik": d["pabrik"], "Meja": d["meja"].astype(str), "Label": d["label"], "Stok": d["stok"]})
        tam = num.copy()
        tam["Stok"] = num["Stok"].map(_f)
        st.dataframe(tam.style.apply(_warna(num, ["Stok"])), hide_index=True, width="stretch", height=min(80 + 36 * len(tam), 680),
                     column_config={"Stok": st.column_config.TextColumn("Stok", alignment="right")})
if tanpa is not None and len(tanpa):
    n_ = int(tanpa["n"].sum()) if "n" in tanpa.columns else 0
    st.caption(f"Pemakaian SAP/afkir {n_:,} pcs belum bisa dipetakan ke meja (operator belum punya alamat meja pada hari itu) — "
               "tidak mengurangi stok meja mana pun.".replace(",", "."))
st.caption("Angka merah = stok minus. Stok meja bergeser otomatis saat operator mencatat label diterima / pindah di halaman utama.")
st.download_button("⬇ Unduh Excel", stok.excel_stok(total, permeja, tgl.strftime("%d-%m-%Y"), sebaran),
                   file_name=f"stok_label_{dept_pil[:3].strip()}_{tgl_s}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
