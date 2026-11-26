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
        kls = "min" if n < 0 else ("sni" if label.adalah_sni(lb) else ("low" if n < 50 else ""))
        h += f"<span class='ls-chip {kls}'>{html.escape(str(lb))} ({n:,})</span>".replace(",", ".")
    return h


def _tabel_stok_meja(pabrik, meja, tgl, tambah=None):
    """Stok awal (sisa kemarin sore), menerima hari ini, dan stok saat ini per type di meja.
    tambah = {label: jumlah} yang sedang diisi tetapi belum disimpan: ikut dihitung (ditandai hijau) dan type baru langsung muncul."""
    try:
        r = stok.meja_ringkas(pabrik, meja, tgl)
    except Exception:
        return chips(stok.stok_meja(pabrik, meja, tgl))
    tambah = {lb: n for lb, n in (tambah or {}).items() if n}
    r = {lb: dict(d) for lb, d in r.items() if d["awal"] or d["sisa"] or d["terima"]}
    for lb, n in tambah.items():
        d = r.setdefault(lb, {"awal": 0, "terima": 0, "sisa": 0, "keluar": 0, "pakai": 0, "kor": 0})
        d["terima"] += n
        d["sisa"] += n
    if not r:
        return "<span class='ls-nt'>Belum ada stok label di meja ini.</span>"
    f = lambda v: f"{int(v):,}".replace(",", ".")
    baris = ""
    for lb in stok.urut_label(r):
        d = r[lb]
        ket = []
        if d["keluar"]:
            ket.append(f"keluar {f(-d['keluar'])}" if d["keluar"] < 0 else f"+{f(d['keluar'])}")
        if d["pakai"]:
            ket.append(f"terpakai {f(-d['pakai'])}")
        if d["kor"]:
            ket.append(f"koreksi {f(d['kor'])}")
        warna = "#b3261e" if d["sisa"] < 0 else ("#1b7a3d" if lb in tambah else "#0b3d91")
        if lb in tambah:
            ket.append("belum disimpan")
        baris += (f"<tr><td style='text-align:left;font-weight:800'>{html.escape(str(lb))}</td><td>{f(d['awal'])}</td><td>{('+' + f(d['terima'])) if d['terima'] else '–'}</td>"
                  f"<td style='font-weight:800;color:{warna}'>{f(d['sisa'])}</td><td style='text-align:left;color:#7b8fb0;font-size:11.5px'>{', '.join(ket)}</td></tr>")
    return ("<table style='width:100%;border-collapse:collapse;font-size:13px;text-align:right'><tr style='color:#5b7399;font-size:11px;letter-spacing:.4px'>"
            "<th style='text-align:left'>TYPE</th><th>STOK AWAL<br><span style='font-weight:500'>(sisa kemarin)</span></th><th>MENERIMA<br><span style='font-weight:500'>(hari ini)</span></th>"
            "<th>STOK SAAT INI</th><th style='text-align:left'>&nbsp;</th></tr>" + baris + "</table>")


def tgl_id(t):
    return f"{t[8:]}-{t[5:7]}-{t[:4]}"


def pilih_meja(kp, judul, prn=None, tgl=None, wajib=True, bawaan=None, pabriks=None):
    """Pilih pabrik (segmen) dan nomor meja. Return (pabrik, meja) atau (None, None) bila belum lengkap."""
    pab = list(pabriks) if pabriks else list(label.PABRIK)
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



def _reset(kp):
    for k in [k for k in st.session_state if str(k).startswith(kp + "_")]:
        st.session_state.pop(k, None)


def isi_jumlah(kp, awal=None, minimal=1, maksimal=999999, judul="Pilih type label"):
    """Isian type + jumlah TANPA data_editor (data_editor memuat JS tambahan yang sering gagal di tablet/sinyal lemah).
    awal = {label: jumlah} untuk nilai bawaan. Return list [(label, jumlah)] untuk type yang jumlahnya terisi."""
    opsi = stok.semua_label()
    kd = f"{kp}_pilih"
    if kd not in st.session_state:
        st.session_state[kd] = [lb for lb in (awal or {}) if lb in opsi]
    dipilih = st.multiselect(judul, opsi, key=kd, placeholder="Ketik/pilih type label…")
    out = []
    for lb in dipilih:
        c = st.columns([1, 1.3], vertical_alignment="center")
        c[0].markdown(f"**{lb}**")
        v = c[1].number_input(lb, min_value=0 if minimal == 0 else minimal, max_value=maksimal, step=1,
                              value=int((awal or {}).get(lb, 0)) if minimal == 0 else None,
                              key=f"{kp}_n_{lb}", label_visibility="collapsed", placeholder="pcs")
        if v is not None and (v >= minimal if minimal else True):
            out.append((lb, int(v)))
    return out


# ------------------------------------------------------------------ label diterima operator
_CSS_TBL = """<style>
.st-key-{k} [data-testid='stHorizontalBlock']{{flex-wrap:nowrap!important;gap:.4rem!important}}
.st-key-{k} [data-testid='stColumn']{{min-width:0!important}}
.tt-th{{font-size:.66rem;font-weight:800;color:#5b7399;letter-spacing:.4px}}
.tt-th.r,.tt-n{{text-align:right}}
.tt-ty b{{font-size:1rem;color:#0b3d91}} .tt-ty small{{display:block;color:#7b8fb0;font-size:.68rem;line-height:1.1}}
.tt-n{{font-size:1rem;font-weight:700;color:#1c2a44}} .tt-n.ok{{color:#1b7a3d;font-weight:800}} .tt-n.min{{color:#b3261e;font-weight:800}}
.tt-tot{{border:1px solid #d6e4f8;border-radius:12px;background:#f8fbff;padding:8px 12px;margin:6px 0}}
.tt-tot b{{color:#0b3d91;font-size:1.15rem}}
</style>"""


def _f(v):
    return f"{int(v):,}".replace(",", ".")


def _baris_foreman(pabrik, meja, tgl, kp):
    """Baris tabel Dari Foreman: type yang ada di meja ini + type yang ditambahkan karyawan. [(label, awal, sisa_sekarang, terima_hari_ini)]."""
    try:
        r = stok.meja_ringkas(pabrik, meja, tgl)
    except Exception:
        r = {}
    dasar = {lb: d for lb, d in r.items() if d["awal"] or d["sisa"] or d["terima"]}
    tambah = list(st.session_state.get(f"{kp}_tipe", []))
    induk = [t for t in tambah if not label.adalah_sni(t)]
    if any(label.ket_label(x) for x in induk) and "CE7" not in induk:
        induk.insert(0, "CE7")
    induk += [t for t in tambah if label.adalah_sni(t)]
    for t in label.kolom_lengkap(induk):
        dasar.setdefault(t, {"awal": 0, "sisa": 0, "terima": 0})
    return [(lb, int(dasar[lb]["awal"]), int(dasar[lb]["sisa"]), int(dasar[lb]["terima"])) for lb in stok.urut_label(dasar)]


def _tambah_type(kp, ada, daftar="tipe", n="tb"):
    """Tombol '+ Tambah type': membuka pilihan SATU type (bisa diketik); setelah dipilih daftar menutup sendiri dan type menjadi baris baru."""
    kb = f"{kp}_{n}"
    if not st.session_state.get(kb):
        if st.button("+ Tambah type", key=f"{kp}_{n}btn", type="tertiary"):
            st.session_state[kb] = True
            st.rerun(scope="fragment")
        return
    opsi = [t for t in stok.semua_label() if t not in ada]

    def _pilih():
        v = st.session_state.get(f"{kp}_{n}pilih")
        if v:
            st.session_state[f"{kp}_{daftar}"] = list(st.session_state.get(f"{kp}_{daftar}", [])) + [v]
        st.session_state[kb] = False
        st.session_state.pop(f"{kp}_{n}pilih", None)
    c = st.columns([4, 1.2], vertical_alignment="center")
    c[0].selectbox("Tambah type", opsi, index=None, placeholder="Ketik / pilih satu type…", key=f"{kp}_{n}pilih", on_change=_pilih, label_visibility="collapsed")
    if c[1].button("Batal", key=f"{kp}_{n}batal"):
        st.session_state[kb] = False
        st.rerun(scope="fragment")


def _tabel_terima_foreman(pabrik, meja, tgl, kp):
    """Tabel stok meja yang langsung bisa diisi: TYPE | AWAL | TERIMA (ketik) | SEKARANG (otomatis). Return [(label, jumlah)] yang terisi."""
    kt = f"{kp}_tbl"
    st.markdown(_CSS_TBL.format(k=kt), unsafe_allow_html=True)
    rows = _baris_foreman(pabrik, meja, tgl, kp)
    W = [1.25, 0.8, 1.05, 1.0]
    out = []
    with st.container(key=kt):
        h = st.columns(W)
        for c, t, rr in zip(h, ["TYPE", "AWAL", "TERIMA", "SEKARANG"], ["", " r", " r", " r"]):
            c.markdown(f"<div class='tt-th{rr}'>{t}</div>", unsafe_allow_html=True)
        for lb, awal, sisa, terima in rows:
            c = st.columns(W, vertical_alignment="center")
            ket = f"+{_f(terima)} hari ini" if terima else ""
            c[0].markdown(f"<div class='tt-ty'><b>{html.escape(str(lb))}</b><small>{ket}</small></div>", unsafe_allow_html=True)
            c[1].markdown(f"<div class='tt-n'>{_f(awal)}</div>", unsafe_allow_html=True)
            v = c[2].number_input(f"Terima {lb}", min_value=0, max_value=9999999, step=1, value=None, placeholder="0", key=f"{kp}_f_{pabrik}_{meja}_{lb}",
                                  label_visibility="collapsed")
            n = int(v or 0)
            skr = sisa + n
            c[3].markdown(f"<div class='tt-n {'min' if skr < 0 else ('ok' if n else '')}'>{_f(skr)}</div>", unsafe_allow_html=True)
            if n > 0:
                out.append((lb, n))
        _tambah_type(kp, [r[0] for r in rows])
    return out


def _ganti_type(kp, cur):
    """Tombol 'Ganti type' (atau '+ Pilih type' bila belum ada): membuka pilihan SATU type; setelah dipilih daftar menutup dan type itu yang tampil."""
    kb = f"{kp}_mlbuka"
    if not st.session_state.get(kb):
        if st.button("Ganti type" if cur else "+ Pilih type", key=f"{kp}_mlbtn", width="stretch", type="secondary" if cur else "primary"):
            st.session_state[kb] = True
            st.rerun(scope="fragment")
        return

    def _pilih():
        v = st.session_state.get(f"{kp}_mlpilih")
        if v:
            st.session_state[f"{kp}_mlcur"] = v
        st.session_state[kb] = False
        st.session_state.pop(f"{kp}_mlpilih", None)
    c = st.columns([4, 1.4], vertical_alignment="center")
    c[0].selectbox("Pilih type", [t for t in stok.semua_label() if t != cur], index=None, placeholder="Ketik / pilih satu type…", key=f"{kp}_mlpilih",
                   on_change=_pilih, label_visibility="collapsed")
    if c[1].button("Batal", key=f"{kp}_mlbatal"):
        st.session_state[kb] = False
        st.rerun(scope="fragment")


def _panel_meja_lain(pabrik, meja, tgl, kp, tempat):
    """Dari meja lain: satu type tampil sekali waktu (tabel MEJA·PABRIK | STOK | DIAMBIL | SISA). Jumlah DIAMBIL tersimpan SEMENTARA di sesi
    (muncul di tabel stok meja di atas) sehingga karyawan bisa Ganti type dan mengambil type lain; permanen baru saat SIMPAN PERPINDAHAN.
    DIAMBIL diisi 0 = batal. Return ([(lokasi_asal, label, diambil)], daftar meja asal type yang tampil)."""
    kt = f"{kp}_mltbl"
    kpend = f"{kp}_mlpend"
    pend = dict(st.session_state.get(kpend, {}))  # {(lokasi, label): jumlah}
    cur = st.session_state.get(f"{kp}_mlcur")
    sumber = []
    if cur:
        sumber = stok.stok_di_meja_lain(cur, tgl, (pabrik, meja))
        st.markdown(f"<div class='ls-lbl' style='font-size:13px'>{html.escape(str(cur))} · label ini ada di meja:</div>", unsafe_allow_html=True)
        if not sumber:
            st.info(f"Tidak ada meja lain yang punya stok {cur}. Bila labelnya dari Foreman, pilih 'Foreman' di atas.")
        else:
            W = [1.7, 0.8, 1.05, 0.8]
            with st.container(key=f"{kt}_0"):
                st.markdown(_CSS_TBL.format(k=f"{kt}_0"), unsafe_allow_html=True)
                h = st.columns(W)
                for c, t, rr in zip(h, ["MEJA · PABRIK", "STOK", "DIAMBIL", "SISA"], ["", " r", " r", " r"]):
                    c.markdown(f"<div class='tt-th{rr}'>{t}</div>", unsafe_allow_html=True)
                for lk, n in sumber:
                    c = st.columns(W, vertical_alignment="center")
                    c[0].markdown(f"<div class='tt-ty'><b style='font-size:.9rem'>{html.escape(stok.lok_nama(lk))}</b></div>", unsafe_allow_html=True)
                    c[1].markdown(f"<div class='tt-n'>{_f(n)}</div>", unsafe_allow_html=True)
                    awal = pend.get((lk, cur))
                    v = c[2].number_input(f"Diambil {cur} {lk}", min_value=0, max_value=int(n), step=1, value=min(int(awal), int(n)) if awal else None,
                                          placeholder="0", key=f"{kp}_ml_{pabrik}_{meja}_{cur}_{lk}", label_visibility="collapsed")
                    d = int(v or 0)
                    c[3].markdown(f"<div class='tt-n {'ok' if d else ''}'>{_f(n - d)}</div>", unsafe_allow_html=True)
                    if d > 0:
                        pend[(lk, cur)] = d
                    else:
                        pend.pop((lk, cur), None)
            st.session_state[kpend] = pend
    _ganti_type(kp, cur)
    ambil = [(lk, lb, n) for (lk, lb), n in pend.items() if n > 0]
    total = {}
    for lk, lb, n in ambil:
        total[lb] = total.get(lb, 0) + n
    with tempat:
        st.markdown("<div class='ls-lbl'>STOK LABEL DI MEJA INI" + (" — sudah termasuk yang akan diterima" if total else " SEKARANG") + "</div>"
                    + _tabel_stok_meja(pabrik, meja, tgl, total), unsafe_allow_html=True)
        if total:
            st.caption("Yang berwarna hijau baru tersimpan sementara. Tekan SIMPAN PERPINDAHAN agar permanen; isi DIAMBIL dengan 0 untuk membatalkan.")
    return ambil, [lk for lk, _n in sumber]


def _lapor(prn, nama, tgl, pabrik, meja, kp, lain=()):
    """Tombol Laporkan: stok di sistem tidak sama dengan yang ada di meja. Foreman mendapat notifikasi untuk mengecek meja itu."""
    with st.popover("Laporkan stok tidak sesuai", icon=":material/report:", width="stretch"):
        pilihan = [stok.lok(pabrik, str(meja))] + [lk for lk in lain if lk != stok.lok(pabrik, str(meja))]
        lk = st.selectbox("Meja yang dilaporkan", pilihan, format_func=stok.lok_nama, key=f"{kp}_lp_lk")
        ada = stok.stok_lokasi(lk, tgl)
        opsi = stok.urut_label(ada) if ada else stok.semua_label()
        lb = st.selectbox("Type label", opsi, index=None, placeholder="Pilih type…", key=f"{kp}_lp_lb_{lk}")
        sistem = int(ada.get(lb, 0)) if lb else 0
        if lb:
            st.markdown(f"Menurut sistem: **{_f(sistem)} pcs**")
        n = st.number_input("Yang ada di meja (pcs)", min_value=0, max_value=9999999, step=1, value=None, placeholder="isi jumlah", key=f"{kp}_lp_n_{lk}_{lb}")
        cat = st.text_input("Catatan (boleh kosong)", max_chars=200, key=f"{kp}_lp_c_{lk}_{lb}")
        st.caption("Stok tidak berubah. Foreman akan menerima notifikasi untuk mengecek meja ini dan memperbaikinya.")
        if st.button("KIRIM LAPORAN", type="primary", width="stretch", key=f"{kp}_lp_kirim", disabled=not (lb and n is not None)):
            p2, m2 = stok._lok_pisah(lk)
            g = stok.lapor_simpan(tgl, prn, nama, p2, m2, lb, sistem, n, cat)
            if g:
                st.error(g)
            else:
                st.toast("Laporan terkirim ke Foreman.", icon="✅")
                for k_ in [k for k in st.session_state if str(k).startswith(f"{kp}_lp_")]:
                    st.session_state.pop(k_, None)
                st.rerun(scope="fragment")


def form_terima(prn, nama, tgl, oleh, adm=False, kp="lt"):
    """Tab INPUT LABEL: label diterima meja, dari Foreman (tabel stok meja diisi langsung) atau dari meja lain (otomatis menjadi Pindah Label)."""
    st.markdown(CSS, unsafe_allow_html=True)
    pabrik, meja = pilih_meja(kp, "", prn, tgl)
    ctx = (pabrik, str(meja), tgl)
    if st.session_state.get(f"{kp}_ctx") != ctx:  # ganti meja/tanggal: isian lama dibuang
        for k_ in [k for k in st.session_state if str(k).startswith((f"{kp}_f_", f"{kp}_tipe", f"{kp}_ml"))]:
            st.session_state.pop(k_, None)
        st.session_state[f"{kp}_ctx"] = ctx
    if not (pabrik and meja):
        st.caption("Pilih pabrik dan nomor meja dulu — tanpa alamat meja, stok tidak bisa dipetakan.")
        _daftar_terima(prn, tgl, oleh, adm, kp)
        return
    st.markdown("<div class='ls-lbl'>LABEL DITERIMA DARI</div>", unsafe_allow_html=True)
    sumber = st.segmented_control("Label diterima dari", ["Foreman", "Meja lain"], default="Foreman", key=f"{kp}_sumber", label_visibility="collapsed") or "Foreman"
    sudah = stok.meja_terima_daftar(prn, tgl)
    tot_lama = {}
    for r in sudah.itertuples():
        tot_lama[r.label] = tot_lama.get(r.label, 0) + int(r.jumlah)
    if sumber == "Foreman":
        st.markdown("<div class='ls-lbl'>STOK LABEL DI MEJA INI — isi kolom TERIMA</div>", unsafe_allow_html=True)
        baris = _tabel_terima_foreman(pabrik, meja, tgl, kp)
        for lb, n in baris:
            if tot_lama.get(lb):
                st.caption(f"{lb}: sudah {_f(tot_lama[lb])} hari ini + baru {_f(n)} = **{_f(tot_lama[lb] + n)} pcs**")
        if tot_lama:
            st.caption("Input yang sama pada tanggal ini **ditambahkan** ke jumlah sebelumnya (bukan mengganti).")
        _lapor(prn, nama, tgl, pabrik, meja, kp)
        if st.button("SIMPAN", type="primary", width="stretch", key=f"{kp}_simpan", disabled=not baris):
            galat = stok.meja_terima_simpan(tgl, prn, nama, pabrik, meja, baris, oleh)
            if galat:
                st.error(galat)
            else:
                for k_ in [k for k in st.session_state if str(k).startswith((f"{kp}_f_", f"{kp}_tipe"))]:
                    st.session_state.pop(k_, None)
                st.toast("Label diterima tersimpan.", icon="✅")
                st.rerun(scope="fragment")
    else:
        tempat = st.container()
        st.markdown("<div class='ls-lbl'>PILIH TYPE LABEL, lalu isi kolom DIAMBIL (boleh ganti type, isian sebelumnya tetap)</div>", unsafe_allow_html=True)
        ambil, lain = _panel_meja_lain(pabrik, meja, tgl, kp, tempat)
        st.caption("Label di rak dan tidak tahu dari meja berapa? Cukup pilih type; sistem menunjukkan meja yang punya stoknya. Isi DIAMBIL hanya pada meja yang labelnya kamu ambil.")
        _lapor(prn, nama, tgl, pabrik, meja, kp, lain)
        if st.button("SIMPAN PERPINDAHAN", type="primary", width="stretch", key=f"{kp}_simpan_ml", disabled=not ambil):
            galat = stok.terima_dari_meja_lain(tgl, prn, (pabrik, meja), ambil, oleh)
            if galat:
                st.error(galat)
            else:
                for k_ in [k for k in st.session_state if str(k).startswith(f"{kp}_ml")]:
                    st.session_state.pop(k_, None)
                st.toast("Perpindahan label tersimpan.", icon="✅")
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
    """Tab PINDAH MEJA: meja saat ini (isi sisa label di meja; afkir terisi dari input foreman) -> meja selanjutnya (label yang dibawa)."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown("<div class='ls-lbl' style='font-size:14px'>① MEJA SAAT INI</div>", unsafe_allow_html=True)
    p1, m1 = pilih_meja(f"{kp}_a", "", prn, tgl)
    baris, salah, bawa_total = [], [], {}
    if p1 and m1:
        awal = stok.stok_lokasi(stok.lok(p1, str(m1)), tgl, abaikan=(prn, tgl))
        afk = {lb: n for (pp, mm, lb), n in stok.afkir_hari(prn, tgl).items() if (pp, mm) == (p1, str(m1))}
        daftar = stok.urut_label({lb for lb, n in awal.items() if n != 0} | set(afk))
        st.markdown(f"<div class='ls-lbl'>STOK LABEL DI {label.nama_meja(p1, m1).upper()} (sebelum pemakaian hari ini)</div>" + chips(awal), unsafe_allow_html=True)
        if not daftar:
            st.info("Tidak ada stok label di meja ini. Pindah meja tetap bisa dicatat.")
        else:
            st.markdown("<div class='ls-lbl'>ISI <b>SISA</b> LABEL DI MEJA DAN <b>DIBAWA</b> KE MEJA SELANJUTNYA</div>", unsafe_allow_html=True)
            st.markdown(f"<style>.st-key-{kp}_tbl [data-testid='stHorizontalBlock']{{flex-wrap:nowrap!important;gap:.5rem!important}}"
                        f".st-key-{kp}_tbl [data-testid='stColumn']{{min-width:0!important}}"
                        ".pm-ty b{font-size:1rem;color:#0b3d91}.pm-ty small{display:block;color:#7b8fb0;font-size:.7rem}"
                        ".pm-th{font-size:.68rem;font-weight:800;color:#5b7399;letter-spacing:.4px}"
                        ".pm-in{font-size:.75rem;color:#7a5a00;margin:-.4rem 0 .5rem}</style>", unsafe_allow_html=True)

            def _semua():
                for lb_ in daftar:
                    sv = st.session_state.get(f"{kp}_s_{p1}_{m1}_{lb_}")
                    if sv:
                        st.session_state[f"{kp}_w_{p1}_{m1}_{lb_}"] = sv

            def _nol():
                for lb_ in daftar:
                    st.session_state.pop(f"{kp}_w_{p1}_{m1}_{lb_}", None)
            with st.container(key=f"{kp}_tbl"):
                h = st.columns([1.2, 1, 1])
                for c, t in zip(h, ["TYPE", "SISA DI MEJA", "DIBAWA"]):
                    c.markdown(f"<div class='pm-th'>{t}</div>", unsafe_allow_html=True)
                for lb in daftar:
                    c = st.columns([1.2, 1, 1], vertical_alignment="center")
                    s0 = awal.get(lb, 0)
                    c[0].markdown(f"<div class='pm-ty'><b>{lb}</b><small>stok {s0:,} · afkir {afk.get(lb, 0)}</small></div>".replace(",", "."), unsafe_allow_html=True)
                    sisa = c[1].number_input(f"Sisa {lb}", min_value=0, max_value=999999, step=1, value=None, placeholder="sisa", key=f"{kp}_s_{p1}_{m1}_{lb}",
                                             label_visibility="collapsed")
                    bawa = c[2].number_input(f"Bawa {lb}", min_value=0, max_value=999999, step=1, value=None, placeholder="bawa", key=f"{kp}_w_{p1}_{m1}_{lb}",
                                             label_visibility="collapsed", disabled=sisa is None) or 0
                    if sisa is None:
                        continue
                    pakai = max(0, s0 - sisa)
                    if bawa > sisa:
                        salah.append(lb)
                    tinggal = sisa - bawa
                    st.markdown(f"<div class='pm-in'>terpakai <b>{pakai:,}</b> · tinggal di meja <b style='color:{'#b71c1c' if tinggal < 0 else '#7a5a00'}'>{tinggal:,}</b></div>".replace(",", "."),
                                unsafe_allow_html=True)
                    if sisa > s0:
                        st.caption(f"{lb}: sisa fisik lebih besar dari stok sistem — stok meja ini dikoreksi +{sisa - s0}.")
                    baris.append((lb, sisa, bawa))
                    if bawa:
                        bawa_total[lb] = bawa
            b1, b2 = st.columns(2)
            b1.button("BAWA SEMUA SISA", key=f"{kp}_semua", on_click=_semua, width="stretch")
            b2.button("TIDAK ADA YANG DIBAWA", key=f"{kp}_nol", on_click=_nol, width="stretch")
            if salah:
                st.error(f"Label dibawa melebihi sisa: {', '.join(salah)}.")
            st.caption("Afkir tetap tercatat di meja ini. Sisa yang tidak dibawa tinggal di meja ini; yang dibawa pindah ke meja selanjutnya.")
    st.markdown("<div class='ls-lbl' style='font-size:14px;margin-top:14px'>② MEJA SELANJUTNYA</div>", unsafe_allow_html=True)
    p2, m2 = pilih_meja(f"{kp}_b", "", wajib=True, bawaan=(None, None))
    if p2 and m2:
        s2 = stok.stok_meja(p2, m2, tgl)
        st.markdown(f"<div class='ls-lbl'>STOK LABEL DI {label.nama_meja(p2, m2).upper()}</div>" + chips(s2), unsafe_allow_html=True)
        if bawa_total:
            sesudah = dict(s2)
            for lb, n in bawa_total.items():
                sesudah[lb] = sesudah.get(lb, 0) + n
            st.markdown("<div class='ls-lbl'>SETELAH LABEL DIBAWA</div>" + chips(sesudah), unsafe_allow_html=True)
        st.caption("Pemakaian dan afkir operator setelah pindah dihitung di meja ini.")
    ok = bool(p1 and m1 and p2 and m2) and not salah
    if not (p1 and m1 and p2 and m2):
        st.caption("Pilih meja saat ini dan meja selanjutnya (pabrik + nomor meja).")
    if st.button("PINDAH MEJA", type="primary", width="stretch", key=f"{kp}_simpan", disabled=not ok):
        galat = stok.pindahmeja_simpan(tgl, prn, nama, (p1, m1), (p2, m2), baris, oleh)
        if galat:
            st.error(galat)
        else:
            for k_ in [k for k in st.session_state if str(k).startswith((f"{kp}_s_", f"{kp}_w_"))]:
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
        ring = ", ".join(f"{x.label} sisa {x.sisa}" + (f" bawa {x.bawa}" if x.bawa else "") for x in g.itertuples() if x.label)
        c[1].caption(f"{label.nama_meja(r['dari_pabrik'], r['dari_meja'])} → {label.nama_meja(r['ke_pabrik'], r['ke_meja'])}" + (f" · {ring}" if ring else ""))
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
