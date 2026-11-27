"""Monitoring stok label: stok sistem = stok awal + diterima - pcs bagus - afkir, dibandingkan hitungan aktual foreman."""
import html
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from core import akses, data, label, logic, stok
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


def _hari_libur(bln, aktif):
    """Tanggal (angka) yang dikosongkan: jadwal libur (Sabtu/Minggu atau jadwal karyawan: mayoritas X) DAN tidak ada pemakaian SAP/afkir hari itu."""
    jm = logic.jadwal_peta(bln)
    default = logic.hari_libur_default(bln)
    hasil = set()
    for d_ in range(1, logic.n_hari(bln) + 1):
        tg = f"{bln}-{d_:02d}"
        st_ = [v for (p_, t_), v in jm.items() if t_ == tg]
        lib = (sum(1 for v in st_ if v == "X") * 2 >= len(st_)) if st_ else default[d_]
        if lib and tg not in aktif:
            hasil.add(d_)
    return hasil


_NAMA_GRUP = {"MASUK": "MASUK", "KELUAR": "KELUAR", "SAP": "PAKAI SAP", "AFKIR": "AFKIR", "KOREKSI": "KOREKSI"}


@st.dialog("RINCIAN STOK LABEL", width="large")
def _dlg_rincian(lb, tg0, dept_):
    """Telusur satu type pada satu hari: stok awal -> masuk/keluar/pakai SAP/afkir/koreksi -> sisa, per lokasi dan karyawan."""
    tg = st.session_state.get("rc_tg", tg0)
    if st.session_state.get("rc_dasar") != (lb, tg0):
        st.session_state["rc_dasar"] = (lb, tg0)
        tg = tg0
    d_ = date.fromisoformat(tg)
    n1, n2, n3 = st.columns([1, 3, 1], vertical_alignment="center")
    if n1.button("◀ Sebelumnya", key="rc_prev", width="stretch", disabled=d_ <= date.fromisoformat(stok.MULAI)):
        st.session_state["rc_tg"] = (d_ - timedelta(days=1)).isoformat()
        st.rerun(scope="fragment")
    n2.markdown(f"<div style='text-align:center'><span style='font-size:1.5rem;font-weight:800;color:#0b3d91'>{html.escape(lb)}</span><br>"
                f"<b>{d_.strftime('%d-%m-%Y')}</b> · stok akhir hari (setelah pemakaian)</div>", unsafe_allow_html=True)
    if n3.button("Berikutnya ▶", key="rc_next", width="stretch", disabled=d_ >= hari_ini):
        st.session_state["rc_tg"] = (d_ + timedelta(days=1)).isoformat()
        st.rerun(scope="fragment")
    r = stok.rincian(tg, lb)
    pic = stok.pic_meja(tg)
    lokasi = {lk for lk, _l in list(r["awal"]) + list(r["akhir"]) if stok.dept_cocok(lk, dept_)} | {k[0] for k in r["kejadian"] if stok.dept_cocok(k[0], dept_)}
    if not lokasi:
        st.info("Tidak ada stok maupun pergerakan type ini pada tanggal tersebut.")
    baris, tot = [], {g: 0 for g in stok.GRUP}
    tot["awal"] = tot["sisa"] = 0
    for lk in lokasi:
        aw = r["awal"].get((lk, lb), 0)
        sisa = r["akhir"].get((lk, lb), 0)
        g = {x: 0 for x in stok.GRUP}
        nama = []
        for k in r["kejadian"]:
            if k[0] == lk:
                g[k[1]] += k[4]
                if k[2] and k[2] not in nama:
                    nama.append(k[2])
        if not stok.adalah_foreman(lk):
            nama += [x for x in pic.get(lk, []) if x not in nama]
        cat = "⚠ MINUS — telusuri kejadian di bawah" if sisa < 0 else ""
        baris.append({"lk": lk, "posisi": _lok_baca(lk), "nama": ", ".join(nama) if nama else "–", "aw": aw, **g, "sisa": sisa, "cat": cat})
        tot["awal"] += aw
        tot["sisa"] += sisa
        for x in stok.GRUP:
            tot[x] += g[x]

    def _u(b):
        lk = b["lk"]
        if stok.adalah_foreman(lk):
            return (0, 0, 0)
        pb, mj = stok._lok_pisah(lk)
        return (1, list(label.PABRIK).index(pb) if pb in label.PABRIK else 9, int(mj) if str(mj).isdigit() else 999)
    baris.sort(key=_u)
    sg = lambda v: ("+" if v > 0 else "") + _f(v) if v else "–"
    sv = lambda v: ("+" if v > 0 else "") + _f(v)
    st.markdown(f"**STOK AWAL {_f(tot['awal'])}** (sisa hari sebelumnya) &nbsp;|&nbsp; MASUK {sv(tot['MASUK'])} &nbsp;|&nbsp; KELUAR {sv(tot['KELUAR'])} &nbsp;|&nbsp; "
                f"PAKAI SAP {sv(tot['SAP'])} &nbsp;|&nbsp; AFKIR {sv(tot['AFKIR'])} &nbsp;|&nbsp; KOREKSI {sv(tot['KOREKSI'])} &nbsp;|&nbsp; **SISA {_f(tot['sisa'])}**")
    if baris:
        x = pd.DataFrame({"POSISI": [b["posisi"] for b in baris], "KARYAWAN": [b["nama"] for b in baris], "AWAL": [_f(b["aw"]) for b in baris],
                          "MASUK": [sg(b["MASUK"]) for b in baris], "KELUAR": [sg(b["KELUAR"]) for b in baris],
                          "PAKAI SAP": [sg(b["SAP"]) for b in baris], "AFKIR": [sg(b["AFKIR"]) for b in baris],
                          "KOREKSI": [sg(b["KOREKSI"]) for b in baris], "SISA": [_f(b["sisa"]) for b in baris], "CATATAN": [b["cat"] for b in baris]})
        num = [b["sisa"] for b in baris]
        st.dataframe(x.style.apply(lambda c: ["color:#b3261e;font-weight:800" if num[i] < 0 else "font-weight:700" for i in range(len(c))] if c.name == "SISA" else [""] * len(c)),
                     hide_index=True, width="stretch", height=min(62 + 36 * len(x), 400),
                     column_config={**{k: st.column_config.TextColumn(k, alignment="right", width="small") for k in ["AWAL", "MASUK", "KELUAR", "PAKAI SAP", "AFKIR", "KOREKSI", "SISA"]},
                                    "POSISI": st.column_config.TextColumn("POSISI", width="medium"), "KARYAWAN": st.column_config.TextColumn("KARYAWAN", width="medium")})
    kj = [k for k in r["kejadian"] if stok.dept_cocok(k[0], dept_)]
    if kj:
        st.markdown("**KEJADIAN HARI ITU** (dasar penelusuran)")
        y = pd.DataFrame({"POSISI": [_lok_baca(k[0]) for k in kj], "KEJADIAN": [_NAMA_GRUP[k[1]] + " · " + k[3] for k in kj],
                          "KARYAWAN / PENGINPUT": [k[2] or "–" for k in kj], "JUMLAH": [sg(k[4]) for k in kj]})
        st.dataframe(y, hide_index=True, width="stretch", height=min(62 + 36 * len(y), 320),
                     column_config={"JUMLAH": st.column_config.TextColumn("JUMLAH", alignment="right", width="small")})
    tp = r["tanpa"]
    if len(tp):
        st.warning("Pemakaian SAP belum terpetakan ke meja (operator belum punya alamat meja hari itu), jadi tidak mengurangi stok meja mana pun: "
                   + "; ".join(f"{n} {_f(v)} pcs" for n, v in zip(tp["nama"], tp["n"])))
    st.caption("SISA hari ini otomatis menjadi STOK AWAL hari berikutnya. Koreksi = selisih hasil hitung aktual (ADJUST) terhadap stok sistem, atau koreksi saat pindah meja.")


def _tab_harian():
    """Matriks TYPE x tanggal 1..31: stok label akhir hari. Klik kotak -> rincian posisi (Foreman / meja + PIC) dan hasil ADJUST."""
    mulai = pd.Period(stok.MULAI[:7], freq="M")
    sekarang = pd.Period(hari_ini.strftime("%Y-%m"), freq="M")
    opsi = [str(p) for p in pd.period_range(mulai, sekarang, freq="M")]
    awal = tgl.strftime("%Y-%m")
    bln = st.selectbox("Bulan", opsi, index=opsi.index(awal) if awal in opsi else len(opsi) - 1, key="st_bln",
                       format_func=lambda b: f"{BULAN_ID[int(b[5:])]} {b[:4]}")
    hari, adj, aktif = stok.harian(bln)
    libur = _hari_libur(bln, aktif)
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
    adj_hari -= libur
    kol = {d_: f"{d_}◆" if d_ in adj_hari else str(d_) for d_ in range(1, jml + 1)}
    maks = int(hari_ini.strftime("%d")) if bln == hari_ini.strftime("%Y-%m") else jml
    angka = pd.DataFrame({kol[d_]: [peta.get((lb, d_), 0) if d_ <= maks and d_ not in libur else None for lb in tipe] for d_ in range(1, jml + 1)})
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
                    if d_ in libur:
                        g.loc[i, c] = "background-color:#f1f3f8"
                    continue
                if (lb, d_) in adj_sel:
                    g.loc[i, c] = "background-color:#dff3e4;font-weight:800;color:#14532d"
                elif v < 0:
                    g.loc[i, c] = "color:#b3261e;font-weight:800"
                elif v == 0:
                    g.loc[i, c] = "color:#b6c0d4"
        g["TYPE"] = "font-weight:800;color:#0b3d91"
        return g
    st.caption("Stok = akhir hari, SETELAH pemakaian (pcs bagus SAP dan afkir); sisa hari ini = stok awal besok. Klik satu kotak untuk rincian lengkap. Kolom abu-abu = hari libur (dikosongkan). ◆ pada tanggal = ada hasil ADJUST hari itu; kotak hijau = type yang di-ADJUST (angkanya sudah hasil hitung aktual).")
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
    if d_ in libur:
        st.caption("Hari libur (tidak ada pemakaian) — dikosongkan. Stok tetap berlanjut ke hari kerja berikutnya.")
        return
    if tg not in hari or d_ > maks:
        st.caption("Belum ada data untuk tanggal itu.")
        return
    tanda = (lb, tg, dept_pil)
    if st.session_state.get("rc_buka") != tanda:  # buka pop-up hanya saat kotak baru dipilih (bukan di setiap rerun)
        st.session_state["rc_buka"] = tanda
        st.session_state.pop("rc_tg", None)
        _dlg_rincian(lb, tg, dept)
    elif st.button(f"🔍 Buka rincian {lb} · {d_:02d}-{bln[5:]}-{bln[:4]}", key="rc_lagi"):
        st.session_state.pop("rc_tg", None)
        _dlg_rincian(lb, tg, dept)


@st.dialog("STOK LABEL MEJA", width="large")
def _dlg_meja(lk, tg0):
    if st.session_state.get("pm_dasar") != (lk, tg0):
        st.session_state["pm_dasar"] = (lk, tg0)
        st.session_state["pm_tg"] = tg0
    tg = st.session_state.get("pm_tg", tg0)
    d_ = date.fromisoformat(tg)
    n1, n2, n3 = st.columns([1, 3, 1], vertical_alignment="center")
    if n1.button("◀ Sebelumnya", key="pm_prev", width="stretch", disabled=d_ <= date.fromisoformat(stok.MULAI)):
        st.session_state["pm_tg"] = (d_ - timedelta(days=1)).isoformat()
        st.rerun(scope="fragment")
    n2.markdown(f"<div style='text-align:center'><span style='font-size:1.4rem;font-weight:800;color:#0b3d91'>{html.escape(_lok_baca(lk))}</span><br>"
                f"<b>{d_.strftime('%d-%m-%Y')}</b></div>", unsafe_allow_html=True)
    if n3.button("Berikutnya ▶", key="pm_next", width="stretch", disabled=d_ >= hari_ini):
        st.session_state["pm_tg"] = (d_ + timedelta(days=1)).isoformat()
        st.rerun(scope="fragment")
    pab, mj = stok._lok_pisah(lk)
    r = stok.meja_ringkas(pab, mj, tg)
    r = {lb: v for lb, v in r.items() if v["awal"] or v["sisa"] or v["terima"] or v["sap"] or v["afkir"] or v["keluar"] or v["kor"]}
    if not r:
        st.info("Tidak ada stok maupun pergerakan label di meja ini pada tanggal tersebut.")
        return
    pic_meja = stok.pic_meja(tg).get(lk, [])
    sv = lambda v: "–" if not v else ("+" if v > 0 else "") + _f(v)

    def _asal(v):  # "Meja 3 · Pabrik 1: +30" per meja asal (digabung bila meja sama)
        per = {}
        for a_, n_ in v["dari_meja"]:
            per[a_] = per.get(a_, 0) + n_
        return "\n".join(f"{a_}: +{_f(n_)}" for a_, n_ in per.items()) if per else "–"
    baris = []
    for lb in stok.urut_label(r):
        v = r[lb]
        orang = v["orang"]
        baris.append({"TYPE": lb, "STOK AWAL": _f(v["awal"]), "DARI FOREMAN": sv(v["foreman"]),
                      "DARI MEJA LAIN": _asal(v).replace("\n", " · ") if v["meja_lain"] else "–",
                      "PIC MENERIMA": ", ".join(v["pic_pindah"]) if v["pic_pindah"] else "–",
                      "DIAMBIL": sv(v["keluar"]), "PAKAI SAP": sv(v["sap"]),
                      "AFKIR": sv(v["afkir"]), "SISA": _f(v["sisa"]), "PIC": ", ".join(orang) if orang else "–"})
    tot = {"TYPE": "TOTAL", "STOK AWAL": _f(sum(v["awal"] for v in r.values())), "DARI FOREMAN": sv(sum(v["foreman"] for v in r.values())),
           "DARI MEJA LAIN": sv(sum(v["meja_lain"] for v in r.values())), "PIC MENERIMA": ", ".join(sorted({n_ for v in r.values() for n_ in v["pic_pindah"]})) or "–",
           "DIAMBIL": sv(sum(v["keluar"] for v in r.values())),
           "PAKAI SAP": sv(sum(v["sap"] for v in r.values())), "AFKIR": sv(sum(v["afkir"] for v in r.values())),
           "SISA": _f(sum(v["sisa"] for v in r.values())), "PIC": ", ".join(sorted({n_ for v in r.values() for n_ in v["orang"]})) or "–"}
    y = pd.DataFrame(baris + [tot])
    minus = {i for i, b_ in enumerate(baris) if r[b_["TYPE"]]["sisa"] < 0}

    def _g(df):
        g = pd.DataFrame("", index=df.index, columns=df.columns)
        for i in minus:
            g.loc[i, "SISA"] = "color:#b3261e;font-weight:800"
        g.loc[len(df) - 1, :] = "font-weight:800;background-color:#eef4ff"
        return g
    st.dataframe(y.style.apply(_g, axis=None), hide_index=True, width="stretch", height=min(62 + 36 * len(y), 560),
                 column_config={**{c: st.column_config.TextColumn(c, alignment="right", width="small") for c in ("STOK AWAL", "DIAMBIL", "PAKAI SAP", "AFKIR", "SISA")},
                                "TYPE": st.column_config.TextColumn("TYPE", width="small"),
                                "DARI FOREMAN": st.column_config.TextColumn("DARI FOREMAN", alignment="right", width="medium"),
                                "DARI MEJA LAIN": st.column_config.TextColumn("DARI MEJA LAIN (asal meja)", width="medium"),
                                "PIC MENERIMA": st.column_config.TextColumn("PIC MENERIMA (label dari Foreman / meja lain)", width="medium"),
                                "PIC": st.column_config.TextColumn("PIC MEMAKAI (hasil kerja SAP)", width="medium")})
    if minus:
        st.error("Ada type MINUS. Kemungkinan karyawan menyimpan label, mengambil dari meja lain, atau salah input. Perbaiki lewat Perbaikan Data / Notifikasi Stok di halaman Foreman.")
    kl = stok.keluar_rinci(pab, mj, tg)
    if kl:
        st.markdown("**Label yang diambil dari meja ini**")
        st.dataframe(pd.DataFrame([{"JAM": x["jam"], "TYPE": x["label"], "DIAMBIL": f"-{_f(x['jumlah'])}", "DIAMBIL OLEH": x["siapa"], "DIPINDAH KE": x["ke"],
                                    "KET": "dibawa pindah meja" if x["jenis"] == "dibawa" else "pindah label"} for x in kl]),
                     hide_index=True, width="stretch", height=min(62 + 36 * len(kl), 360),
                     column_config={"DIAMBIL": st.column_config.TextColumn("DIAMBIL", alignment="right", width="small"),
                                    "JAM": st.column_config.TextColumn("JAM", width="small"), "TYPE": st.column_config.TextColumn("TYPE", width="small")})
    st.caption("DARI FOREMAN = label diterima dari Foreman. DARI MEJA LAIN = label yang dipindah/diambil dari meja lain (asal meja dan jumlahnya). PIC MENERIMA = yang menerima label dari Foreman / meja lain; PIC MEMAKAI = operator yang mengerjakan type itu (hasil kerja SAP). DIAMBIL = label keluar dari meja ini (diambil operator lain, dibawa pindah meja, atau dikembalikan ke Foreman). "
               "SISA hari ini = STOK AWAL besok.")


def _tab_meja():
    """Matriks MEJA x tanggal 1..31: total pcs label di meja pada akhir hari. Klik angka -> tabel per type (awal, diterima, SAP, afkir, sisa, PIC)."""
    mulai = pd.Period(stok.MULAI[:7], freq="M")
    sekarang = pd.Period(hari_ini.strftime("%Y-%m"), freq="M")
    opsi = [str(p) for p in pd.period_range(mulai, sekarang, freq="M")]
    awal = tgl.strftime("%Y-%m")
    c1, c2 = st.columns([1.3, 2], vertical_alignment="bottom")
    bln = c1.selectbox("Bulan", opsi, index=opsi.index(awal) if awal in opsi else len(opsi) - 1, key="pm_bln",
                       format_func=lambda b: f"{BULAN_ID[int(b[5:])]} {b[:4]}")
    pab = [p for p in label.PABRIK if not dept or stok.dept_pabrik(p) == dept]
    pil = c2.segmented_control("Pabrik", ["Semua"] + pab, default="Semua", key="pm_pab", label_visibility="collapsed") or "Semua"
    hari, adj, aktif = stok.harian(bln)
    akt = stok.aktivitas_bulan(bln)
    mejas = {lk for sal in hari.values() for (lk, lb), n in sal.items() if n} | {lk for _t, lk, _l in akt}
    mejas = {lk for lk in mejas if not stok.adalah_foreman(lk) and stok.dept_cocok(lk, dept)}
    if pil != "Semua":
        mejas = {lk for lk in mejas if stok._lok_pisah(lk)[0] == pil}
    mejas = sorted(mejas, key=lambda lk: (list(label.PABRIK).index(stok._lok_pisah(lk)[0]) if stok._lok_pisah(lk)[0] in label.PABRIK else 9,
                                          int(stok._lok_pisah(lk)[1]) if str(stok._lok_pisah(lk)[1]).isdigit() else 999))
    if not mejas:
        st.info("Belum ada stok atau pergerakan label di meja pada bulan ini.")
        return
    libur = _hari_libur(bln, aktif)
    jml = pd.Period(bln, freq="M").days_in_month
    maks = int(hari_ini.strftime("%d")) if bln == hari_ini.strftime("%Y-%m") else jml
    akt_mj = {(t, lk) for t, lk, _l in akt}
    angka, ada_min = {}, {}
    for d_ in range(1, jml + 1):
        sal = hari.get(f"{bln}-{d_:02d}", {})
        ok = d_ <= maks and d_ not in libur
        angka[d_] = [sum(n for (lk2, lb), n in sal.items() if lk2 == lk) if ok else None for lk in mejas]
        ada_min[d_] = [any(n < 0 for (lk2, lb), n in sal.items() if lk2 == lk) if ok else False for lk in mejas]
    teks = pd.DataFrame({str(d_): ["" if v is None else (_f(v) if v else "–") for v in angka[d_]] for d_ in angka})
    teks.insert(0, "MEJA", [_lok_baca(lk) for lk in mejas])

    def _gaya(df):
        g = pd.DataFrame("", index=df.index, columns=df.columns)
        for d_ in angka:
            for i, lk in enumerate(mejas):
                v = angka[d_][i]
                if v is None:
                    if d_ in libur:
                        g.loc[i, str(d_)] = "background-color:#f1f3f8"
                    continue
                st_ = ""
                if ada_min[d_][i] or v < 0:
                    st_ = "color:#b3261e;font-weight:800;"
                elif v == 0:
                    st_ = "color:#b6c0d4;"
                if (f"{bln}-{d_:02d}", lk) in akt_mj:
                    st_ += "font-weight:800;background-color:#eef4ff"
                g.loc[i, str(d_)] = st_
        g["MEJA"] = "font-weight:800;color:#0b3d91"
        return g
    st.caption("Angka = total pcs label di meja pada akhir hari. Kotak biru = ada pergerakan hari itu. Merah = ada type yang minus. Klik angka untuk melihat tabel per type.")
    ev = st.dataframe(teks.style.apply(_gaya, axis=None), hide_index=True, width="stretch", height=min(48 + 35 * len(teks), 640),
                      on_select="rerun", selection_mode="single-cell", key="pm_grid",
                      column_config={"MEJA": st.column_config.TextColumn("MEJA", pinned=True, width="medium"),
                                     **{str(d_): st.column_config.TextColumn(str(d_), alignment="right", width=58) for d_ in range(1, jml + 1)}})
    sel = (ev.selection.cells if ev and ev.selection else None) or []
    if not sel:
        return
    bar, nm = sel[0]
    if nm == "MEJA" or bar is None or int(bar) >= len(mejas):
        return
    lk, d_ = mejas[int(bar)], int(nm)
    tg = f"{bln}-{d_:02d}"
    if d_ > maks or tg not in hari:
        st.caption("Belum ada data untuk tanggal itu.")
        return
    tanda = (lk, tg)
    if st.session_state.get("pm_buka") != tanda:
        st.session_state["pm_buka"] = tanda
        st.session_state.pop("pm_dasar", None)
        _dlg_meja(lk, tg)
    elif st.button(f"🔍 Buka {_lok_baca(lk)} · {d_:02d}-{bln[5:]}-{bln[:4]}", key="pm_lagi"):
        st.session_state.pop("pm_dasar", None)
        _dlg_meja(lk, tg)


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
    _tab_meja()
    with st.expander(f"Posisi stok per meja pada {tgl.strftime('%d-%m-%Y')} (daftar)"):
        if permeja.empty:
            st.info("Belum ada stok di meja.")
        else:
            d = permeja
            num = pd.DataFrame({"Pabrik": d["pabrik"], "Meja": d["meja"].astype(str), "Label": d["label"], "Stok": d["stok"]})
            tam = num.copy()
            tam["Stok"] = num["Stok"].map(_f)
            st.dataframe(tam.style.apply(_warna(num, ["Stok"])), hide_index=True, width="stretch", height=min(80 + 36 * len(tam), 480),
                         column_config={"Stok": st.column_config.TextColumn("Stok", alignment="right")})
if tanpa is not None and len(tanpa):
    n_ = int(tanpa["n"].sum()) if "n" in tanpa.columns else 0
    st.caption(f"Pemakaian SAP/afkir {n_:,} pcs belum bisa dipetakan ke meja (operator belum punya alamat meja pada hari itu) — "
               "tidak mengurangi stok meja mana pun.".replace(",", "."))
st.caption("Angka merah = stok minus. Stok meja bergeser otomatis saat operator mencatat label diterima / pindah di halaman utama.")
st.download_button("⬇ Unduh Excel", stok.excel_stok(total, permeja, tgl.strftime("%d-%m-%Y"), sebaran),
                   file_name=f"stok_label_{dept_pil[:3].strip()}_{tgl_s}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
