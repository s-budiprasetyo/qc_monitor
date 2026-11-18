"""Halaman Upload Foreman: jendela MONITORING LABEL (input label afkir), notifikasi meja yang belum dicek,
tabel input hari ini (ubah/hapus)."""
from datetime import date

import pandas as pd
import streamlit as st

from core import akses, data, label
from core.store import BukuBulananBelumAda
from core.ui import gaya_global

CSS = """
<style>
.block-container{max-width:1180px;padding-top:1.6rem}
h1.judul-f{font-weight:800;color:#0b3d91;letter-spacing:.5px;margin:.6rem 0 1rem 0}
.st-key-btn_label button{background:linear-gradient(135deg,#1a73e8,#0b3d91);border:0;color:#fff;font-weight:800;
  padding:.9rem 1.6rem;border-radius:12px;font-size:15px;min-height:0;height:auto}
.st-key-btn_label button:hover{filter:brightness(1.1);color:#fff}
.st-key-btn_label button p{font-size:15px;font-weight:800}
.st-key-hub_f{display:flex!important;flex-direction:row!important;align-items:center;gap:12px;flex-wrap:wrap}
.st-key-hub_f>div{width:auto!important;flex:0 0 auto}
.st-key-op_list [data-testid='stHorizontalBlock']{flex-wrap:nowrap!important;gap:6px}
.st-key-op_list [data-testid='stColumn']{min-width:0!important}
.st-key-op_list [data-testid='stColumn']:nth-child(1){flex:1 1 0!important}
.st-key-op_list [data-testid='stColumn']:nth-child(2){flex:0 0 38%!important}
.st-key-op_list [data-testid='stColumn']:nth-child(3){flex:0 0 44px!important;width:44px!important}
.st-key-btn_operator button p{font-size:15px;font-weight:800}
.st-key-hub_f [class*='st-key-hub_gear'] button{width:58px;height:58px;min-height:0;padding:0;border-radius:50%;border:0;color:#fff;
  background:linear-gradient(135deg,#6ec6ff,#2a8fe8);box-shadow:0 3px 10px #2a8fe855;transition:transform .5s}
.st-key-hub_f [class*='st-key-hub_gear'] button p{font-size:30px;line-height:1;margin:0}
.st-key-hub_f [class*='st-key-hub_gear'] button:hover{transform:rotate(90deg);color:#fff;filter:brightness(1.05)}
.st-key-hub_gear_buka button{transform:rotate(180deg)}
.st-key-btn_operator button{background:#e8f3ff;border:1px solid #9fd0fb;color:#0b3d91;font-weight:800;
  padding:.9rem 1.4rem;border-radius:12px;min-height:0;height:auto}
@media (max-width:640px){.st-key-btn_label,.st-key-btn_operator{width:100%}}
.nf-baris{display:flex;align-items:center;gap:10px;font-weight:700;color:#0b3d91}
.nf-x{background:#e53935;color:#fff;border-radius:6px;width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;font-size:14px}
[class*='st-key-nf_']{border:1px solid #f1b9b6;background:#fff7f6;border-radius:10px;padding:4px 10px;margin-bottom:6px}
[class*='st-key-nf_'] button{border-radius:8px;font-size:13px;padding:.15rem .8rem;min-height:0}
table.lb{border-collapse:collapse;width:100%;font-size:13px;background:#fff}
table.lb th{background:#eef3fb;color:#0b3d91;text-align:left;padding:6px 8px;font-size:12px;border-bottom:2px solid #d4e1f5}
table.lb td{padding:6px 8px;border-bottom:1px solid #e6ecf5}
table.lb td.n,table.lb th.n{text-align:right}
.sx2{overflow-x:auto}
.cap-f{color:#5b7399;font-size:13px}
@media (max-width:640px){h1.judul-f{font-size:1.9rem}}
.kt{color:#5b7399;font-size:12px}
</style>
"""

CSS_JENDELA = """
<style>
[data-testid='stDialog'] [role='dialog'] h2{display:none !important}
[data-testid='stDialog'] [role='dialog']{position:relative}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']{position:absolute !important;top:16px;right:22px;z-index:30;color:#fff !important;background:transparent !important}
.lb-kepala{background:linear-gradient(135deg,#1a73e8,#0b3d91);color:#fff;margin:-1.4rem -1.6rem 1rem -1.6rem;padding:14px 64px 14px 20px;
  border-radius:14px 14px 0 0}
.lb-kepala b{font-size:1.15rem;letter-spacing:.5px}.lb-kepala div{font-size:12px;opacity:.85}
.lb-ringkas{background:#eef4fe;border:1px solid #d4e1f5;border-radius:10px;padding:8px 12px;font-weight:700;color:#0b3d91;font-size:13px}
.st-key-lbm{overflow-x:auto;overflow-y:hidden;padding-bottom:22px}
.st-key-lbm [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.5rem !important;min-width:max-content}
.st-key-lbm [data-testid="stColumn"]{min-width:116px !important;flex:0 0 116px !important;width:116px !important}
.st-key-lbm [data-testid="stColumn"]:first-child{min-width:82px !important;flex:0 0 82px !important;width:82px !important}
.lb-th{background:#eef4fe;border:1.5px solid #1a73e8;border-radius:10px;text-align:center;padding:4px 2px;line-height:1.15}
.lb-th.lb-sni{background:#fff4e5;border-color:#f59e0b}
.lb-th.lb-sni b{color:#b45309}
.lb-th small{display:block;font-size:10px;color:#5b7399;font-weight:700;letter-spacing:.5px}
.lb-th b{font-size:13px;color:#0b3d91}
.lb-jenis{font-weight:700;font-size:13px;color:#0b3d91}
.lb-total{background:#fdeaea;border-radius:10px;text-align:center;font-weight:800;color:#b71c1c;line-height:38px;height:38px}
[class*='st-key-lbx_'] button{min-height:0;height:22px;padding:0 .5rem;font-size:11px;border-radius:999px;color:#b71c1c}
.st-key-lbplus button{border:2px dashed #1a73e8;color:#1a73e8;font-weight:700;background:#fff}
.st-key-lbsimpan button{font-weight:800}
.st-key-lbsimpan button[kind="primary"]{background:#1e9e50;border-color:#1e9e50}
</style>
"""


# isian angka: seluruh isi terblok saat diklik, jadi langsung tertimpa angka yang diketik
JS_PILIH = """<script>
(function(){const d=window.parent.document; if(d.__lbPilih) return; d.__lbPilih=1;
d.addEventListener('focusin',function(e){const t=e.target;
 if(t&&t.tagName==='INPUT'&&t.type==='number'&&t.closest('.st-key-lbm')){setTimeout(function(){try{t.select()}catch(x){}},0)}});})();
</script>"""


def _nama_peta():
    ops = label.operator_daftar()
    nama, hitung = {}, {}
    for _, n in ops:
        hitung[n] = hitung.get(n, 0) + 1
    for p, n in ops:
        nama[n if hitung[n] == 1 else f"{n} ({p})"] = p
    return nama


def _tgl_iso(d):
    return d.strftime("%Y-%m-%d")


def _bersih_form(jaga_meja=False):
    for k in [k for k in st.session_state if k.startswith(("w_n_", "w_kat_", "w_typ_"))]:
        del st.session_state[k]
    st.session_state["w_cols"] = []
    st.session_state["w_tambah"] = False
    st.session_state["w_edit"] = None
    st.session_state.pop("w_op", None)
    if not jaga_meja:
        for k in [k for k in st.session_state if k.startswith("w_meja_")]:
            del st.session_state[k]


@st.dialog("MONITORING LABEL", width="large", on_dismiss="rerun")
def dlg_label():
    st.markdown(CSS_JENDELA, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    st.markdown("<div class='lb-kepala'><b>MONITORING LABEL</b><div>Input label afkir</div></div>", unsafe_allow_html=True)
    oleh = st.session_state.get("nama_masuk", "")
    tipe_kat = label.type_per_kategori()
    peta = _nama_peta()

    # nilai awal sebelum widget dibuat (reset / muat untuk ubah)
    reset = st.session_state.pop("w_reset", None)
    if reset == "lain":
        _bersih_form(jaga_meja=True)
    muat = st.session_state.pop("w_muat", None)
    if muat:
        _bersih_form()
        nm = next((n for n, p in peta.items() if p == muat["prn"]), None)
        if nm:
            st.session_state["w_op"] = nm
        st.session_state["w_pabrik"] = muat["pabrik"]
        st.session_state[f"w_meja_{muat['pabrik']}"] = muat["meja"]
        st.session_state["w_cols"] = [t for t in muat["kolom"] if not t.startswith(label.SNI + " ")]
        for t, v in muat["kolom"].items():
            for j, _ in label.JENIS:
                n = label._int(v.get(j))
                st.session_state[f"w_n_{t}_{j}"] = n or None  # 0 ditampilkan kosong (tampil placeholder 0)
        st.session_state["w_edit"] = (muat["prn"], muat["pabrik"], muat["meja"])
    cols = st.session_state.setdefault("w_cols", [])
    if isinstance(cols, dict):
        cols = st.session_state["w_cols"] = list(cols)
    induk = list(cols)  # label yang dipilih; kolom SNI pendamping ditambahkan otomatis
    cols = label.kolom_lengkap(induk)

    a, b = st.columns([3, 2], vertical_alignment="center")
    tgl = a.date_input("Tanggal kerja", key="w_tgl", format="DD/MM/YYYY", label_visibility="collapsed")
    shift = b.segmented_control("Shift", label.SHIFT, key="w_shift", label_visibility="collapsed") or "Pagi"
    edit = st.session_state.get("w_edit")
    if edit:
        st.info("Mode ubah: simpan akan mengganti data lama operator dan meja ini.")

    nama_pilih = st.selectbox("NAMA OPERATOR", list(peta), index=None, key="w_op", placeholder="Pilih operator…")
    prn = peta.get(nama_pilih, "")
    c1, c2 = st.columns(2)
    c1.text_input("PRN", value=prn, disabled=True)
    pabrik = st.segmented_control("PABRIK", list(label.PABRIK), key="w_pabrik") or "Pabrik 1"
    meja = c2.selectbox("MEJA", label.meja_daftar(pabrik), index=None, key=f"w_meja_{pabrik}",
                        format_func=lambda m: f"Meja {m}", placeholder="Pilih meja…")

    st.markdown("<div class='kt' style='margin:.4rem 0 .2rem'>JUMLAH LABEL AFKIR PER JENIS LABEL</div>", unsafe_allow_html=True)
    with st.container(key="lbm"):
        k = st.columns([1] + [1] * len(cols) + [1], vertical_alignment="center")
        k[0].markdown("<div class='lb-jenis'>JENIS AFKIR</div>", unsafe_allow_html=True)
        for i, t in enumerate(cols):
            with k[i + 1]:
                sni = t.startswith(label.SNI + " ")
                if sni:
                    kecil, besar = "SNI · PENDAMPING", t[len(label.SNI) + 1:]
                else:
                    kecil, besar = (label.ket_label(t) or label.kategori_label(t)).upper(), t
                st.markdown(f"<div class='lb-th{' lb-sni' if sni else ''}'><small>{kecil}</small><b>{besar}</b></div>",
                            unsafe_allow_html=True)
                if not sni:
                    with st.container(key=f"lbx_{i}"):
                        if st.button("✕ hapus", key=f"lbrm_{i}"):
                            st.session_state["w_cols"] = [x for x in induk if x != t]
                            st.rerun(scope="fragment")
        with k[len(cols) + 1], st.container(key="lbplus"):
            if st.button("+ Label", key="lb_tambah", width="stretch"):
                st.session_state["w_tambah"] = not st.session_state.get("w_tambah", False)
                st.rerun(scope="fragment")
        total = {t: 0 for t in cols}
        nilai = {t: {} for t in cols}
        for j, nm in label.JENIS:
            r = st.columns([1] + [1] * len(cols), vertical_alignment="center")
            r[0].markdown(f"<div class='lb-jenis'>{nm}</div>", unsafe_allow_html=True)
            for i, t in enumerate(cols):
                v = r[i + 1].number_input(f"{nm} {t}", min_value=0, max_value=9999, step=1, value=None, placeholder="0",
                                          key=f"w_n_{t}_{j}", label_visibility="collapsed")
                nilai[t][j] = int(v or 0)
                total[t] += int(v or 0)
        if cols:
            r = st.columns([1] + [1] * len(cols), vertical_alignment="center")
            r[0].markdown("<div class='lb-jenis' style='color:#b71c1c'>TOTAL</div>", unsafe_allow_html=True)
            for i, t in enumerate(cols):
                r[i + 1].markdown(f"<div class='lb-total'>{total[t]}</div>", unsafe_allow_html=True)
        else:
            st.caption("Klik **+ Label** untuk memilih jenis label yang dicek.")

    if st.session_state.get("w_tambah"):
        n = st.session_state.setdefault("w_pk", 0)
        with st.container(border=True):
            kat = st.pills("PILIH KATEGORI", label.KATEGORI, key=f"w_kat_{n}")
            if kat:
                pilihan = [t for t in tipe_kat.get(kat, []) if t not in induk]
                if not pilihan:
                    st.caption("Tidak ada type untuk kategori ini (atau semuanya sudah dipilih).")
                else:
                    tp = st.pills(f"{kat.upper()} → PILIH LABEL", pilihan, key=f"w_typ_{n}_{kat}")
                    if tp:
                        st.session_state["w_cols"] = induk + [tp]
                        st.session_state["w_tambah"] = False
                        st.session_state["w_pk"] = n + 1
                        st.rerun(scope="fragment")

    st.write("")
    s1, s2 = st.columns([1, 1.4])
    with s1, st.container(key="lbsimpan"):
        simpan = st.button("SIMPAN", type="primary", width="stretch", key="lb_simpan")
    simpan_lain = s2.button("SIMPAN + OPERATOR LAIN DI MEJA INI", width="stretch", key="lb_simpan_lain")
    if simpan or simpan_lain:
        if not prn:
            st.error("Pilih nama operator.")
        elif not meja:
            st.error("Pilih meja.")
        elif not induk:
            st.error("Pilih minimal satu label (klik + Label).")
        else:
            try:
                with st.spinner("Menyimpan…"):
                    galat = label.simpan(_tgl_iso(tgl), shift, prn, nama_pilih, pabrik, meja, nilai, oleh, ganti_lama=edit)
            except BukuBulananBelumAda as e:
                st.error(str(e))
                return
            if galat:
                st.error(galat)
                return
            st.session_state["pg_set"] = (tgl, shift)
            st.session_state["pg_toast"] = f"Tersimpan: {nama_pilih} · {label.nama_meja(pabrik, meja)}"
            if simpan_lain:
                st.session_state["w_reset"] = "lain"
                st.toast(st.session_state.pop("pg_toast"), icon="✅")
                st.rerun(scope="fragment")
            else:
                st.rerun()


def _buka_jendela(muat=None):
    for k in [k for k in st.session_state if k.startswith("w_") and k not in ("w_cols",)]:
        del st.session_state[k]
    _bersih_form()
    st.session_state["w_tgl"] = st.session_state.get("pg_tgl", label.hari_ini())
    st.session_state["w_shift"] = st.session_state.get("pg_shift", "Pagi")
    st.session_state["w_pabrik"] = "Pabrik 1"
    if muat:
        st.session_state["w_muat"] = muat
    dlg_label()


def _notifikasi(tgl_s, shift):
    belum = label.meja_belum(tgl_s, shift)
    total = sum(len(v) for v in belum.values())
    oleh = st.session_state.get("nama_masuk", "")
    with st.container(border=True):
        st.markdown(f"**Meja yang belum dicek** — {total} meja" if total else "**Semua meja sudah dicek** ✅")
        if total:
            opsi = [f"{p} · {len(m)}" for p, m in belum.items()]
            pilih = st.segmented_control("Pabrik", opsi, key="pg_pab", label_visibility="collapsed") or opsi[0]
            pab = list(belum)[opsi.index(pilih)] if pilih in opsi else list(belum)[0]
            with st.container(height=min(60 + 56 * len(belum[pab]), 380), border=False):
                for m in belum[pab]:
                    with st.container(key=f"nf_{pab}_{m}".replace(" ", "")):
                        c = st.columns([5, 1.3], vertical_alignment="center")
                        c[0].markdown(f"<div class='nf-baris'><span class='nf-x'>✕</span>{label.nama_meja(pab, m)}</div>",
                                      unsafe_allow_html=True)
                        if c[1].button("Abaikan", key=f"ab_{pab}_{m}"):
                            label.abaikan(tgl_s, shift, pab, m, oleh)
                            st.rerun()
        ab = label.abaikan_hari(tgl_s, shift)
        if len(ab):
            with st.expander(f"Diabaikan ({len(ab)})"):
                for r in ab.itertuples():
                    c = st.columns([5, 1.6], vertical_alignment="center")
                    c[0].write(f"{label.nama_meja(r.pabrik, r.meja)} — Diabaikan oleh {r.oleh} ({r.waktu})")
                    if c[1].button("Batalkan", key=f"ba_{r.pabrik}_{r.meja}"):
                        label.batal_abaikan(tgl_s, shift, r.pabrik, r.meja)
                        st.rerun()


def _tabel(tgl_s, shift):
    d = label.baca_hari(tgl_s, shift)
    st.markdown(f"**Input label {pd.to_datetime(tgl_s).strftime('%d/%m/%Y')} ({shift})**")
    if d.empty:
        st.markdown("<div class='cap-f'>Belum ada input.</div>", unsafe_allow_html=True)
        return
    d = d.sort_values(["waktu", "pabrik", "meja"]).reset_index(drop=True)
    pk = {"Pabrik 1": "P1", "Pabrik 2": "P2", "QC SK": "SK"}
    baris = "".join(
        f"<tr><td>{r.waktu}</td><td>{pk.get(r.pabrik, r.pabrik)}-{r.meja}</td><td>{r.nama}</td><td>{r.type}</td>"
        f"<td class='n'>{r.lengket}</td><td class='n'>{r.garis}</td><td class='n'>{r.kotor}</td><td class='n'>{label._int(r.proses)}</td><td class='n'><b>{r.total}</b></td>"
        f"<td>{r.tgl_posting[8:]}-{r.tgl_posting[5:7]}</td></tr>" for r in d.itertuples())
    st.markdown("<div class='sx2'><table class='lb'><tr><th>Jam</th><th>Meja</th><th>Operator</th><th>Label</th>"
                "<th class='n'>Lengket</th><th class='n'>Garis</th><th class='n'>Kotor</th><th class='n'>Proses</th><th class='n'>Total</th>"
                f"<th>Posting</th></tr>{baris}</table></div>", unsafe_allow_html=True)
    nama = [f"{r.waktu} · {pk.get(r.pabrik, r.pabrik)}-{r.meja} · {r.nama} · {r.type}" for r in d.itertuples()]
    with st.expander("Ubah atau hapus input"):
        i = st.selectbox("Pilih input", range(len(d)), format_func=lambda x: nama[x], key="pg_pilih")
        r = d.iloc[i]
        c = st.columns(2)
        if c[0].button("✎ Ubah operator & meja ini", key="pg_ubah", width="stretch"):
            grup = d[(d["prn"] == r["prn"]) & (d["pabrik"] == r["pabrik"]) & (d["meja"] == r["meja"])]
            kolom = {x["type"]: {j: x[j] for j, _ in label.JENIS} for _, x in grup.iterrows()}
            _buka_jendela({"prn": r["prn"], "pabrik": r["pabrik"], "meja": r["meja"], "kolom": kolom})
        with c[1].popover("🗑 Hapus input ini", use_container_width=True):
            st.write(f"Hapus {nama[i]}? (Tidak bisa dibatalkan.)")
            if st.button("YA, HAPUS", type="primary", key="pg_hapus"):
                with st.spinner("Menghapus…"):
                    label.hapus_baris(tgl_s, shift, r["prn"], r["pabrik"], r["meja"], r["type"])
                st.toast("Input dihapus.", icon="🗑")
                st.rerun()


@st.dialog("DAFTAR OPERATOR", width="large", on_dismiss="rerun")
def dlg_operator():
    """Nama + kode operator yang bisa dipilih di Monitoring Label."""
    k = label.logic.info_karyawan()
    nama = {p: (n if n else s) for p, n, s in zip(k["prn"], k["nama_web"], k["nama_sap"])}
    kode = dict(zip(k["prn"], k["kode_opr"]))
    if "op_daftar" not in st.session_state:
        tersimpan = label.operator_tersimpan()
        st.session_state["op_daftar"] = tersimpan if tersimpan is not None else [p for p, _, _ in label.operator_default()]
    daftar = st.session_state["op_daftar"]
    st.caption(f"{len(daftar)} operator. Hanya nama di daftar ini yang muncul di pilihan NAMA OPERATOR.")
    tambah = st.selectbox("Tambah operator", [p for p in sorted(nama, key=lambda x: nama[x]) if p not in daftar],
                          index=None, format_func=lambda p: f"{nama[p]} · {p}", placeholder="Cari nama…", key="op_tambah")
    if st.button("+ Tambah", key="op_btn_tambah", disabled=tambah is None):
        daftar.append(tambah)
        st.session_state.pop("op_tambah", None)
        st.rerun(scope="fragment")
    with st.container(height=340, key="op_list"):
        for i, p in enumerate(sorted(daftar, key=lambda x: nama.get(x, x))):
            a, b, c = st.columns([5, 2, 1], vertical_alignment="center")
            a.write(nama.get(p, p))
            b.caption(f"PRN {p} · Kode {kode.get(p, '') or '-'}")
            if c.button("✕", key=f"op_x_{p}"):
                daftar.remove(p)
                st.rerun(scope="fragment")
    if st.button("SIMPAN DAFTAR", type="primary", width="stretch", key="op_simpan"):
        with st.spinner("Menyimpan…"):
            label.operator_simpan(sorted(daftar, key=lambda x: nama.get(x, x)), st.session_state.get("nama_masuk", ""))
        st.session_state.pop("op_daftar", None)
        st.session_state["pg_toast"] = "Daftar operator disimpan."
        st.rerun()


def _hub():
    """Roda gigi biru muda: klik untuk membuka/menutup menu. Menu bisa ditambah item lain nanti."""
    buka = st.session_state.get("hub_buka", True)
    with st.container(key="hub_f"):
        with st.container(key="hub_gear" + ("_buka" if buka else "")):
            if st.button("⚙", key="hub_klik", help="Menu"):
                st.session_state["hub_buka"] = not buka
                st.rerun()
        if buka:
            with st.container(key="btn_label"):
                if st.button("🏷  MONITORING LABEL"):
                    _buka_jendela()
            with st.container(key="btn_operator"):
                if st.button("👥  DAFTAR OPERATOR"):
                    st.session_state.pop("op_daftar", None)
                    dlg_operator()


def tampil(halaman_admin=None):
    akses.butuh(akses.ADMIN, akses.FOREMAN)
    st.markdown(CSS, unsafe_allow_html=True)
    gaya_global()
    akses.bilah(halaman_admin, "Ke halaman Admin")
    st.markdown("<h1 class='judul-f'>UPLOAD FOREMAN</h1>", unsafe_allow_html=True)

    # tanggal & shift halaman; diganti dari jendela setelah simpan (diterapkan sebelum widget dibuat)
    st.session_state.setdefault("pg_tgl", label.hari_ini())
    st.session_state.setdefault("pg_shift", "Pagi")
    ganti = st.session_state.pop("pg_set", None)
    if ganti:
        st.session_state["pg_tgl"], st.session_state["pg_shift"] = ganti
    if st.session_state.get("pg_toast"):
        st.toast(st.session_state.pop("pg_toast"), icon="✅")

    _hub()
    st.write("")
    a, b, c = st.columns([2, 2, 1], vertical_alignment="center")
    tgl = a.date_input("Tanggal", key="pg_tgl", format="DD/MM/YYYY")
    shift = b.segmented_control("Shift", label.SHIFT, key="pg_shift", label_visibility="collapsed") or "Pagi"
    c.button("↻ Segarkan", key="pg_segar", on_click=lambda: data._tembolok().clear())
    tgl_s = _tgl_iso(tgl)
    _notifikasi(tgl_s, shift)
    st.write("")
    _tabel(tgl_s, shift)
