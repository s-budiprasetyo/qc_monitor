"""Tampilan bersama untuk stok label: dipakai halaman utama (karyawan/admin) dan halaman Foreman.
Semua fungsi dipanggil di dalam jendela (st.dialog) dan memakai `kp` sebagai awalan key supaya tidak bentrok."""
import html

import pandas as pd
import streamlit as st

from core import label, stok

CSS = """<style>
.ls-chip{display:inline-block;border-radius:8px;padding:4px 10px;font-size:12.5px;font-weight:800;margin:2px 5px 2px 0;background:#e6f4ea;color:#14602b}
.ls-chip.sni{background:#fff4e5;color:#b45309}
.ls-chip.min{background:#fde8e8;color:#b71c1c}
.ls-chip.low{background:#fff0d6;color:#a35a00}
.ls-lbl{font-size:12px;font-weight:700;color:#33415c;margin:10px 0 2px}
.ls-wajib{color:#b71c1c;font-size:11px;font-weight:700}
.ls-nt{font-size:12px;color:#6b7a99}
</style>"""


def chips(d):
    """{label: jumlah} -> chip 'TYPE (jumlah)'. SNI berwarna oranye, minus merah, stok tipis kuning."""
    if not d:
        return "<span class='ls-nt'>Belum ada stok label di meja ini.</span>"
    h = ""
    for lb in stok.urut_label(d):
        n = d[lb]
        kls = "min" if n < 0 else ("sni" if str(lb).startswith("SNI ") else ("low" if n < 50 else ""))
        h += f"<span class='ls-chip {kls}'>{html.escape(str(lb))} ({n:,})</span>".replace(",", ".")
    return h


def tgl_id(t):
    return f"{t[8:]}-{t[5:7]}-{t[:4]}"


def pilih_meja(kp, judul, prn=None, tgl=None, wajib=True, bawaan=None):
    """Pilih pabrik (segmen) dan nomor meja. Return (pabrik, meja) atau (None, None) bila belum lengkap."""
    pab = list(label.PABRIK)
    if f"{kp}_pab" not in st.session_state:
        p0, m0 = bawaan if bawaan else (stok.meja_terakhir(prn, tgl) if prn else (None, None))
        if p0 in pab:
            st.session_state[f"{kp}_pab"] = p0
            if m0:
                st.session_state[f"{kp}_mej_{p0}"] = str(m0)
    c1, c2 = st.columns([1.2, 1])
    tag = " <span class='ls-wajib'>wajib</span>" if wajib else ""
    c1.markdown(f"<div class='ls-lbl'>{(judul + ' · ') if judul else ''}PABRIK{tag}</div>", unsafe_allow_html=True)
    pabrik = c1.segmented_control("Pabrik", pab, key=f"{kp}_pab", label_visibility="collapsed")
    c2.markdown(f"<div class='ls-lbl'>NOMOR MEJA{tag}</div>", unsafe_allow_html=True)
    meja = None
    if pabrik:
        meja = c2.selectbox("Nomor meja", label.meja_daftar(pabrik), index=None, placeholder="Pilih meja…", key=f"{kp}_mej_{pabrik}",
                            format_func=lambda m: f"Meja {m}", label_visibility="collapsed")
    else:
        c2.selectbox("Nomor meja", [], index=None, placeholder="Pilih pabrik dulu", key=f"{kp}_mej_kosong", disabled=True, label_visibility="collapsed")
    return (pabrik, meja) if pabrik and meja else (None, None)


def _tujuan(kp):
    """Pilihan alamat pindah: foreman atau meja lain. Return stok.FOREMAN, (pabrik, meja), atau None bila belum lengkap."""
    st.markdown("<div class='ls-lbl'>PINDAH KE <span class='ls-wajib'>wajib</span></div>", unsafe_allow_html=True)
    jenis = st.segmented_control("Pindah ke", ["Foreman (stok utama)", "Meja lain"], key=f"{kp}_tj", label_visibility="collapsed")
    if jenis == "Foreman (stok utama)":
        return stok.FOREMAN
    if jenis == "Meja lain":
        p, m = pilih_meja(f"{kp}_ke", "TUJUAN", wajib=True, bawaan=(None, None))
        return (p, m) if p and m else None
    return None


# ------------------------------------------------------------------ label diterima operator
def form_terima(prn, nama, tgl, oleh, adm=False, kp="lt"):
    """Tab INPUT LABEL: operator menerima label dari foreman (masuk stok meja)."""
    st.markdown(CSS, unsafe_allow_html=True)
    pabrik, meja = pilih_meja(kp, "", prn, tgl)
    if pabrik and meja:
        st.markdown("<div class='ls-lbl'>STOK DI MEJA SEKARANG</div>" + chips(stok.stok_meja(pabrik, meja, tgl)), unsafe_allow_html=True)
    st.markdown("<div class='ls-lbl'>LABEL DITERIMA</div>", unsafe_allow_html=True)
    st.caption("Label SNI diinput sendiri (jumlah boleh berbeda dari type induknya).")
    ed = st.data_editor(
        pd.DataFrame({"Type": pd.Series([], dtype="object"), "Jumlah": pd.Series([], dtype="float")}),
        num_rows="dynamic", hide_index=True, width="stretch", key=f"{kp}_ed",
        column_config={"Type": st.column_config.SelectboxColumn("Type label", options=stok.semua_label(), required=True),
                       "Jumlah": st.column_config.NumberColumn("Jumlah (pcs)", min_value=1, max_value=999999, step=1, format="%d")})
    baris = [(r["Type"], r["Jumlah"]) for _, r in ed.iterrows() if r["Type"] and r["Jumlah"] == r["Jumlah"] and r["Jumlah"] > 0]
    lengkap = bool(pabrik and meja and baris)
    if not (pabrik and meja):
        st.caption("Pilih pabrik dan nomor meja dulu — tanpa alamat meja, stok tidak bisa dipetakan.")
    if st.button("SIMPAN", type="primary", width="stretch", key=f"{kp}_simpan", disabled=not lengkap):
        galat = stok.meja_terima_simpan(tgl, prn, nama, pabrik, meja, baris, oleh)
        if galat:
            st.error(galat)
        else:
            st.session_state.pop(f"{kp}_ed", None)
            st.toast("Label diterima tersimpan.", icon="✅")
            st.rerun(scope="fragment")
    _daftar_terima(prn, tgl, oleh, adm, kp)


def _daftar_terima(prn, tgl, oleh, adm, kp):
    d = stok.meja_terima_daftar(prn, tgl)
    st.markdown("<div class='ls-lbl'>SUDAH DIINPUT PADA TANGGAL INI</div>", unsafe_allow_html=True)
    if d.empty:
        st.caption("Belum ada label diterima pada tanggal ini.")
        return
    for i, r in d.iterrows():
        c = st.columns([1.1, 1.6, 1.8, 1.2, 0.7] if adm else [1.1, 1.6, 1.8, 1.2], vertical_alignment="center")
        c[0].caption(r["waktu"][:5])
        c[1].caption(label.nama_meja(r["pabrik"], r["meja"]))
        c[2].write(f"**{r['label']}**")
        c[3].write(f"{r['jumlah']:,} pcs".replace(",", "."))
        if adm and c[4].button("🗑", key=f"{kp}_hp_{r['id']}", help="Hapus (tercatat di riwayat)"):
            stok.meja_terima_hapus(r["id"], oleh)
            st.rerun(scope="fragment")
    if not adm:
        st.caption("Salah input? Minta admin atau foreman memperbaikinya.")


# ------------------------------------------------------------------ pindah label
def form_pindah(prn, nama, tgl, oleh, adm=False, kp="lp"):
    """Tab PINDAH LABEL: operator pindah meja dan membawa labelnya (atau mengembalikan ke foreman)."""
    st.markdown(CSS, unsafe_allow_html=True)
    pabrik, meja = pilih_meja(kp, "DARI", prn, tgl)
    jumlah = []
    if pabrik and meja:
        sk = {lb: n for lb, n in stok.stok_meja(pabrik, meja, tgl).items() if n > 0}
        st.markdown("<div class='ls-lbl'>STOK DI MEJA ASAL — isi jumlah yang dibawa</div>", unsafe_allow_html=True)
        if not sk:
            st.info("Tidak ada stok label di meja ini.")
        for lb in stok.urut_label(sk):
            c = st.columns([2, 1.2], vertical_alignment="center")
            c[0].markdown(f"**{lb}** <span class='ls-nt'>(stok {sk[lb]:,})</span>".replace(",", "."), unsafe_allow_html=True)
            n = c[1].number_input(f"Jumlah {lb}", min_value=0, max_value=int(sk[lb]), step=1, value=0, key=f"{kp}_n_{pabrik}_{meja}_{lb}",
                                  label_visibility="collapsed")
            if n:
                jumlah.append((lb, n))
    ke = _tujuan(kp)
    ok = bool(pabrik and meja and jumlah and ke)
    if not ke:
        st.caption("Alamat pindah wajib dipilih dan dilengkapi.")
    c1, c2 = st.columns(2)
    if c1.button("SIMPAN PINDAH", type="primary", width="stretch", key=f"{kp}_simpan", disabled=not ok):
        galat = stok.pindah_simpan(tgl, pabrik, meja, ke, jumlah, oleh, prn)
        if galat:
            st.error(galat)
        else:
            for k_ in [k for k in st.session_state if str(k).startswith(f"{kp}_n_")]:
                st.session_state.pop(k_, None)
            st.toast("Pemindahan label tersimpan.", icon="✅")
            st.rerun(scope="fragment")
    d = stok.pindah_daftar(prn, tgl)
    st.markdown("<div class='ls-lbl'>PEMINDAHAN PADA TANGGAL INI</div>", unsafe_allow_html=True)
    if d.empty:
        st.caption("Belum ada pemindahan pada tanggal ini.")
    for i, r in d.iterrows():
        c = st.columns([3.2, 1.6, 1.3, 0.7] if adm else [3.2, 1.6, 1.3], vertical_alignment="center")
        c[0].caption(f"{label.nama_meja(r['dari_pabrik'], r['dari_meja'])} → "
                     f"{'Foreman' if not r['ke_pabrik'] else label.nama_meja(r['ke_pabrik'], r['ke_meja'])}")
        c[1].write(f"**{r['label']}**")
        c[2].write(f"{r['jumlah']:,} pcs".replace(",", "."))
        if adm and c[3].button("🗑", key=f"{kp}_hx_{r['id']}", help="Hapus (tercatat di riwayat)"):
            stok.pindah_hapus(r["id"], oleh)
            st.rerun(scope="fragment")


# ------------------------------------------------------------------ pindah meja (operator)
def _bagus_sap(prn, tgl):
    """{label: pcs bagus SAP} operator itu pada tanggal (label SNI memakai pcs bagus induknya)."""
    from core import laporan
    b = laporan.pcs_bagus(str(tgl)[:7])
    m = b[(b["prn"] == prn) & (b["tgl"] == tgl)]
    out = {}
    for lb, n in zip(m["label"], m["bagus"]):
        out[lb] = out.get(lb, 0) + int(n)
        if label.punya_sni(lb):
            out[label.nama_sni(lb)] = out.get(label.nama_sni(lb), 0) + int(n)
    return out


def form_pindahmeja(prn, nama, tgl, oleh, adm=False, kp="pm"):
    """Tab PINDAH MEJA: meja saat ini (isi pcs bagus yang sudah terpakai) -> meja selanjutnya."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<div class='ls-lbl' style='font-size:14px'>① MEJA SAAT INI</div>", unsafe_allow_html=True)
    p1, m1 = pilih_meja(f"{kp}_a", "", prn, tgl)
    baris = []
    if p1 and m1:
        sk = stok.stok_meja(p1, m1, tgl)
        afk = {lb: n for (pp, mm, lb), n in stok.afkir_hari(prn, tgl).items() if (pp, mm) == (p1, str(m1))}
        sap = _bagus_sap(prn, tgl)
        daftar = stok.urut_label({lb for lb, n in sk.items() if n != 0} | set(afk))
        st.markdown(f"<div class='ls-lbl'>STOK LABEL DI {label.nama_meja(p1, m1).upper()}</div>" + chips(sk), unsafe_allow_html=True)
        st.markdown("<div class='ls-lbl'>LABEL TERPAKAI DI MEJA INI SAMPAI SAAT INI <span class='ls-wajib'>pcs bagus</span></div>", unsafe_allow_html=True)
        if not daftar:
            st.info("Tidak ada stok label di meja ini. Pindah meja tetap bisa dicatat.")
        else:
            k = st.columns([1.5, 1, 1.3, 1, 1.1])
            for c, t in zip(k, ["TYPE", "STOK", "PCS BAGUS", "AFKIR HARI INI", "SISA"]):
                c.markdown(f"<div class='ls-lbl'>{t}</div>", unsafe_allow_html=True)
        lebih = []
        for lb in daftar:
            c = st.columns([1.5, 1, 1.3, 1, 1.1], vertical_alignment="center")
            n_stok = sk.get(lb, 0)
            c[0].markdown(f"**{lb}**")
            c[1].write(f"{n_stok:,}".replace(",", "."))
            n = c[2].number_input(f"Bagus {lb}", min_value=0, max_value=999999, step=1, value=0, key=f"{kp}_n_{p1}_{m1}_{lb}", label_visibility="collapsed")
            c[3].caption(str(afk.get(lb, 0)))
            sisa = n_stok - n
            c[4].markdown(f"<b style='color:{'#b71c1c' if sisa < 0 else '#8a5a00'}'>{sisa:,}</b>".replace(",", "."), unsafe_allow_html=True)
            baris.append((lb, n))
            if n and n > sap.get(lb, 0):
                lebih.append(lb)
        if lebih:
            st.warning(f"Pcs bagus {', '.join(lebih)} lebih besar dari SAP hari ini. Tetap bisa disimpan; akan dicek.")
        if daftar:
            st.caption("Afkir tidak diisi di sini (sudah tercatat dari input foreman). Sisa label tetap di meja ini.")
    st.markdown("<div class='ls-lbl' style='font-size:14px;margin-top:14px'>② MEJA SELANJUTNYA</div>", unsafe_allow_html=True)
    p2, m2 = pilih_meja(f"{kp}_b", "", wajib=True, bawaan=(None, None))
    if p2 and m2:
        st.markdown(f"<div class='ls-lbl'>STOK LABEL DI {label.nama_meja(p2, m2).upper()}</div>" + chips(stok.stok_meja(p2, m2, tgl)), unsafe_allow_html=True)
        st.caption("Pemakaian dan afkir operator setelah pindah dihitung di meja ini.")
    ok = bool(p1 and m1 and p2 and m2)
    if not ok:
        st.caption("Pilih meja saat ini dan meja selanjutnya (pabrik + nomor meja).")
    if st.button("PINDAH MEJA", type="primary", width="stretch", key=f"{kp}_simpan", disabled=not ok):
        galat = stok.pindahmeja_simpan(tgl, prn, nama, (p1, m1), (p2, m2), baris, oleh)
        if galat:
            st.error(galat)
        else:
            for k_ in [k for k in st.session_state if str(k).startswith(f"{kp}_n_")]:
                st.session_state.pop(k_, None)
            st.session_state.pop(f"{kp}_a_pab", None)
            st.session_state.pop(f"{kp}_b_pab", None)
            st.toast("Pindah meja tercatat.", icon="✅")
            st.rerun(scope="fragment")
    d = stok.pindahmeja_daftar(prn, tgl)
    st.markdown("<div class='ls-lbl'>PINDAH MEJA PADA TANGGAL INI</div>", unsafe_allow_html=True)
    if d.empty:
        st.caption("Belum ada pindah meja pada tanggal ini.")
    for w, g in d.groupby("waktu", sort=True):
        r = g.iloc[0]
        c = st.columns([1, 3.6, 0.7] if adm else [1, 3.6], vertical_alignment="center")
        c[0].caption(w[:5])
        pakai = ", ".join(f"{x.label} {x.bagus}" for x in g.itertuples() if x.label and x.bagus)
        c[1].caption(f"{label.nama_meja(r['dari_pabrik'], r['dari_meja'])} → {label.nama_meja(r['ke_pabrik'], r['ke_meja'])}" + (f" · terpakai: {pakai}" if pakai else ""))
        if adm and c[2].button("🗑", key=f"{kp}_hx_{w}", help="Hapus (tercatat di riwayat)"):
            stok.pindahmeja_hapus(w, tgl, prn, oleh)
            st.rerun(scope="fragment")


# ------------------------------------------------------------------ edit stok meja (klik angka stok)
def edit_stok(pabrik, meja, lb, sekarang, tgl, oleh, kp):
    """Isi popover pada angka stok: stok dikurangi dan selisihnya WAJIB dipindahkan ke alamat yang jelas."""
    st.markdown(f"**{lb}** · {label.nama_meja(pabrik, meja)}")
    if sekarang <= 0:
        st.caption("Stok 0 atau minus: tidak ada yang bisa dipindahkan.")
        return
    baru = st.number_input("Stok baru di meja ini", min_value=0, max_value=int(sekarang), value=int(sekarang), step=1, key=f"{kp}_b")
    pindah = int(sekarang) - int(baru)
    st.markdown(f"Dipindahkan: **{pindah:,}** pcs (stok sekarang {sekarang:,})".replace(",", "."))
    ke = _tujuan(kp)
    if st.button("SIMPAN PINDAH", type="primary", width="stretch", key=f"{kp}_ok", disabled=not (pindah > 0 and ke)):
        galat = stok.pindah_simpan(tgl, pabrik, meja, ke, [(lb, pindah)], oleh)
        if galat:
            st.error(galat)
        else:
            st.session_state["il_toast"] = f"{pindah} pcs {lb} dipindahkan."
            st.rerun(scope="fragment")
    if pindah == 0:
        st.caption("Kurangi stok baru, lalu pilih alamat pindahnya (tidak boleh kosong).")
    elif not ke:
        st.caption("Alamat pindah wajib dilengkapi.")
