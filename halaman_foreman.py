"""Halaman Upload Foreman: jendela INPUT LABEL AFKIR (input label afkir), notifikasi meja yang belum dicek,
tabel input hari ini (ubah/hapus)."""
from datetime import date, timedelta

import html
import pandas as pd
import time
import streamlit as st

from core.hub import roda
from core import akses, data, label, label_ui, laporan, stok
from core.store import BukuBulananBelumAda
from core.ui import gaya_global, gaya_responsif, kepala, kontrol_jendela

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
.st-key-btn_inputlabel button,.st-key-btn_inputstok button,.st-key-btn_selisih button,.st-key-btn_distribusi button{background:#e8f3ff;border:1px solid #9fd0fb;color:#0b3d91;font-weight:800;
  padding:.9rem 1.4rem;border-radius:12px;min-height:0;height:auto}
.st-key-btn_kosong button,.st-key-btn_operator button{background:#e8f3ff;border:1px solid #9fd0fb;color:#0b3d91;font-weight:800;
  padding:.9rem 1.4rem;border-radius:12px;min-height:0;height:auto}
@media (max-width:640px){.st-key-btn_label,.st-key-btn_kosong,.st-key-btn_operator,.st-key-btn_inputlabel,.st-key-btn_inputstok,.st-key-btn_selisih,.st-key-btn_distribusi{width:100%}}
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
.lb-kepala{background:linear-gradient(135deg,#1a73e8,#0b3d91);color:#fff;margin:-1.4rem -1.6rem 1rem -1.6rem;padding:14px 64px 14px 20px;
  border-radius:14px 14px 0 0}
.lb-kepala b{font-size:1.15rem;letter-spacing:.5px}.lb-kepala div{font-size:12px;opacity:.85}
.lb-ringkas{background:#eef4fe;border:1px solid #d4e1f5;border-radius:10px;padding:8px 12px;font-weight:700;color:#0b3d91;font-size:13px}
.st-key-lbm{overflow-x:auto;overflow-y:hidden;padding-bottom:22px}
.st-key-lbm [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.5rem !important;min-width:max-content}
.st-key-lbm [data-testid="stColumn"]{min-width:116px !important;flex:0 0 116px !important;width:116px !important}
.st-key-lbm [data-testid="stColumn"]:first-child{min-width:82px !important;flex:0 0 82px !important;width:82px !important}
.lb-th{background:#eef4fe;border:1.5px solid #1a73e8;border-radius:10px;text-align:center;padding:4px 2px;line-height:1.15;height:46px;box-sizing:border-box;display:flex;flex-direction:column;justify-content:center}
.lb-th.lb-sni{background:#fff4e5;border-color:#f59e0b}
.lb-th.lb-sni b{color:#b45309}
.lb-th small{display:block;font-size:10px;color:#5b7399;font-weight:700;letter-spacing:.5px}
.lb-th b{font-size:13px;color:#0b3d91}
.lb-jenis{font-weight:700;font-size:13px;color:#0b3d91}
.lb-total{background:#fdeaea;border-radius:10px;text-align:center;font-weight:800;color:#b71c1c;line-height:38px;height:38px}
.st-key-lbm [data-testid="stColumn"]{position:relative}
[data-testid='stVerticalBlock']:has(>[data-testid='stElementContainer']>.lb-th){gap:0 !important}
[class*='st-key-lbx_']{position:absolute !important;top:-9px;right:-5px;width:auto !important;z-index:5}
[class*='st-key-lbx_'] button{min-height:0;height:20px;width:20px;padding:0;font-size:11px;line-height:1;border-radius:50%;color:#b71c1c;background:#fff;border:1px solid #e5a0a0;box-shadow:0 1px 3px #0002}
[class*='st-key-lbx_'] button p{font-size:11px;margin:0}
.st-key-lbplus button{height:46px;min-height:0;border:2px dashed #1a73e8;color:#1a73e8;font-weight:700;background:#fff}
.st-key-lbsimpan button{font-weight:800}
[class*='st-key-stk_'] button{min-height:38px;height:38px;border-radius:10px;font-weight:800;width:100%}
[class*='st-key-stk_ok_'] button{background:#e6f4ea;border:1px solid #9fd3ae;color:#14602b}
[class*='st-key-stk_low_'] button{background:#fff3c4;border:1px solid #e8c55a;color:#8a5a00}
[class*='st-key-stk_min_'] button{background:#fde8e8;border:1px solid #e5a0a0;color:#b71c1c}
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
    for k in [k for k in st.session_state if k.startswith(("w_n_", "w_kat_", "w_typ_", "w_pinit_"))] + ["w_auto"]:
        st.session_state.pop(k, None)
    st.session_state["w_cols"] = []
    st.session_state["w_tambah"] = False
    st.session_state["w_edit"] = None
    st.session_state.pop("w_op", None)
    st.session_state.pop("w_catatan", None)
    if not jaga_meja:
        for k in [k for k in st.session_state if k.startswith("w_meja_")]:
            del st.session_state[k]


def _peringatan_ada(ada, nama, prn, pabrik, meja, tgl_s, shift):
    """Peringatan 'data sudah diinput' (muncul tepat setelah nomor meja dipilih)."""
    st.markdown("""<style>
.pw{background:#fff4d6;border:2px solid #f0a500;border-radius:14px;padding:14px 16px;margin:.6rem 0}
.pw h4{margin:0 0 4px;color:#8a5a00;font-size:16px;font-weight:800}
.pw p{margin:0;color:#5a4300;font-size:13px}
.pw table{width:100%;border-collapse:collapse;margin-top:10px;font-size:12.5px;background:#fff}
.pw th,.pw td{border:1px solid #e8d49a;padding:4px 8px;text-align:center}.pw th{background:#fbe9ad;color:#6b4a00}
</style>""", unsafe_allow_html=True)
    baris = "".join(f"<tr><td><b>{x['type']}</b></td><td>{label._int(x['lengket'])}</td><td>{label._int(x['garis'])}</td>"
                    f"<td>{label._int(x['kotor'])}</td><td>{label._int(x['proses'])}</td><td><b>{x['total']}</b></td><td>{x['waktu']}</td>"
                    f"<td>{x.get('oleh', '')}</td></tr>" for _, x in ada.iterrows())
    tg = f"{tgl_s[8:]}-{tgl_s[5:7]}-{tgl_s[:4]}"
    st.markdown(f"<div class='pw'><h4>⚠ DATA INI SUDAH PERNAH DIINPUT</h4>"
                f"<p>{nama} · {label.nama_meja(pabrik, meja)} · {tg} ({shift}) sudah punya input label afkir. "
                "Supaya data lama tidak hilang atau dobel, perbaiki lewat tombol di bawah (riwayat perubahan tercatat).</p>"
                "<table><tr><th>TYPE</th><th>LENGKET</th><th>GARIS</th><th>KOTOR</th><th>PROSES</th><th>TOTAL</th><th>JAM</th><th>OLEH</th></tr>"
                f"{baris}</table></div>", unsafe_allow_html=True)
    rw = label.riwayat_kelompok(tgl_s, shift, prn, pabrik, str(meja))
    if len(rw):
        with st.expander(f"Riwayat perubahan sebelumnya ({len(rw)})"):
            for _, x in rw.iterrows():
                st.caption(f"{x['waktu'][5:16]} · {x['oleh']} · {x['jenis']} · {str(x['kunci']).split('|')[-1]}: "
                           f"{x['sebelum'] or '-'} → {x['sesudah']}")
    b1, b2 = st.columns(2)
    if b1.button("✎ PERBAIKI DATA", type="primary", width="stretch", key="lb_ubah_ada"):
        kolom = {x["type"]: {j: x[j] for j, _ in label.JENIS} for _, x in ada.iterrows()}
        st.session_state["w_muat"] = {"prn": prn, "pabrik": pabrik, "meja": str(meja), "kolom": kolom,
                                      "catatan": str(ada.iloc[0].get("catatan", "") or "")}
        st.rerun(scope="fragment")
    b2.button("PILIH MEJA LAIN", width="stretch", key="lb_meja_lain",
              on_click=lambda: st.session_state.__setitem__(f"w_meja_{pabrik}", None))


@st.dialog("INPUT LABEL AFKIR", width="large", on_dismiss="rerun")
def dlg_label():
    kontrol_jendela("afkir")
    kepala("label", "INPUT LABEL AFKIR")
    st.markdown(CSS_JENDELA, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    oleh = akses.pelaku()
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
        st.session_state["w_cols"] = _tanpa_sni_ganda(list(muat["kolom"]))
        for t, v in muat["kolom"].items():
            for j, _ in label.JENIS:
                n = label._int(v.get(j))
                st.session_state[f"w_n_{t}_{j}"] = n or None  # 0 ditampilkan kosong (tampil placeholder 0)
        st.session_state["w_edit"] = (muat["prn"], muat["pabrik"], muat["meja"])
        st.session_state["w_catatan"] = muat.get("catatan", "")
    cols = st.session_state.setdefault("w_cols", [])
    if isinstance(cols, dict):
        cols = st.session_state["w_cols"] = list(cols)
    induk = list(cols)  # label yang dipilih; kolom SNI pendamping ditambahkan otomatis
    if any(label.ket_label(x) for x in induk) and "CE7" not in induk:
        induk.insert(0, "CE7")  # label warna (DR, MA, PIV, ...) selalu disertai type CE7 di paling depan
    cols = label.kolom_lengkap(induk)

    a, b = st.columns([3, 2], vertical_alignment="center")
    tgl = a.date_input("Tanggal kerja", key="w_tgl", format="DD/MM/YYYY", label_visibility="collapsed")
    shift = b.segmented_control("Shift", label.SHIFT, key="w_shift", label_visibility="collapsed") or "Pagi"
    edit = st.session_state.get("w_edit")
    if edit:
        st.info("Mode ubah: simpan akan mengganti data lama operator dan meja ini.")

    n1, n2 = st.columns([3, 1.3], vertical_alignment="bottom")
    nama_pilih = n1.selectbox("NAMA OPERATOR", list(peta), index=None, key="w_op", placeholder="Pilih operator…")
    prn = peta.get(nama_pilih, "")
    n2.text_input("PRN", value=prn, disabled=True)
    pabrik = st.segmented_control("PABRIK", list(label.PABRIK), key="w_pabrik") or "Pabrik 1"
    meja = st.selectbox("MEJA", label.meja_daftar(pabrik), index=None, key=f"w_meja_{pabrik}",
                        format_func=lambda m: f"Meja {m}", placeholder="Pilih meja…")
    if prn and meja and not edit:
        ada = label.baca_hari(_tgl_iso(tgl), shift)
        ada = ada[(ada["prn"] == prn) & (ada["pabrik"] == pabrik) & (ada["meja"] == str(meja))]
        if len(ada):  # data yang sama sudah ada: tampilkan peringatan dulu, form disembunyikan sampai foreman memilih
            _peringatan_ada(ada, nama_pilih, prn, pabrik, meja, _tgl_iso(tgl), shift)
            return
    stok_m = stok.stok_meja(pabrik, meja, _tgl_iso(tgl)) if meja else {}
    posting = _tgl_iso(tgl) if prn else ""  # SAP dicocokkan dengan tanggal kerja (Transaction Date)
    sap = laporan.sap_hari(prn, posting) if prn else {}
    kunci_auto = (prn, posting)
    if prn and not edit and st.session_state.get("w_auto") != kunci_auto:
        # type yang dikerjakan operator pada hari itu terisi otomatis dari SAP (satu kali per operator/tanggal/shift)
        st.session_state["w_auto"] = kunci_auto
        baru_ = [lb for lb in sap if label.kategori_label(lb)]
        if baru_ != induk:
            st.session_state["w_cols"] = baru_
            st.rerun(scope="fragment")
    elif not prn:
        st.session_state.pop("w_auto", None)
    if prn and not sap and not edit and not induk:
        st.caption("Belum ada data SAP operator ini pada tanggal tersebut. Klik **+ Label** untuk memilih type sendiri.")

    st.markdown("<div class='kt' style='margin:.4rem 0 .2rem'>JUMLAH LABEL AFKIR PER JENIS LABEL</div>", unsafe_allow_html=True)
    with st.container(key="lbm"):
        k = st.columns([1] + [1] * len(cols) + [1], vertical_alignment="top")
        k[0].markdown("<div class='lb-jenis' style='line-height:46px'>JENIS AFKIR</div>", unsafe_allow_html=True)
        for i, t in enumerate(cols):
            with k[i + 1]:
                kecil, besar, sni, boleh = _kepala_kolom(t, induk)
                st.markdown(f"<div class='lb-th{' lb-sni' if sni else ''}'><small>{kecil}</small><b>{besar}</b></div>",
                            unsafe_allow_html=True)
                if boleh:
                    with st.container(key=f"lbx_{i}"):
                        if st.button("✕", key=f"lbrm_{i}", help="Hapus label ini"):
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
                if j == "proses" and st.session_state.get(f"w_pinit_{t}") != (prn, posting):
                    # Proses terisi otomatis dari SAP (M+LA+LB+F) untuk type closet CW; tetap bisa ditambah/dikurangi
                    st.session_state[f"w_pinit_{t}"] = (prn, posting)
                    if not edit:
                        st.session_state[f"w_n_{t}_proses"] = _proses_sap(sap, t) or None
                v = r[i + 1].number_input(f"{nm} {t}", min_value=0, max_value=9999, step=1, value=None, placeholder="0",
                                          key=f"w_n_{t}_{j}", label_visibility="collapsed")
                nilai[t][j] = int(v or 0)
                total[t] += int(v or 0)
        if cols:
            r = st.columns([1] + [1] * len(cols), vertical_alignment="center")
            r[0].markdown("<div class='lb-jenis' style='color:#b71c1c'>TOTAL</div>", unsafe_allow_html=True)
            for i, t in enumerate(cols):
                r[i + 1].markdown(f"<div class='lb-total'>{total[t]}</div>", unsafe_allow_html=True)
            if meja:
                r = st.columns([1] + [1] * len(cols), vertical_alignment="center")
                r[0].markdown("<div class='lb-jenis' style='color:#8a5a00;font-size:11px'>STOK LABEL DI MEJA</div>", unsafe_allow_html=True)
                for i, t in enumerate(cols):
                    n_ = stok_m.get(t, 0)
                    kls = "min" if n_ < 0 else ("low" if n_ < 50 else "ok")
                    with r[i + 1], st.container(key=f"stk_{kls}_{i}"):
                        with st.popover(f"{n_:,}".replace(",", "."), width="stretch", help="Klik untuk memindahkan stok"):
                            label_ui.edit_stok(pabrik, meja, t, n_, _tgl_iso(tgl), oleh, kp=f"es_{i}")
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

    if prn and meja:
        rw = label.riwayat_kelompok(_tgl_iso(tgl), shift, prn, pabrik, str(meja))
        if len(rw):
            with st.expander(f"Riwayat perubahan ({len(rw)})"):
                for _, x in rw.iterrows():
                    st.caption(f"{x['waktu'][5:16]} · {x['oleh']} · {x['jenis']} · {str(x['kunci']).split('|')[-1]}: "
                               f"{x['sebelum'] or '-'} → {x['sesudah']}")

    catatan = st.text_input("CATATAN (opsional)", key="w_catatan", max_chars=200,
                            placeholder="Alasan bila afkir tinggi, mis. 'label lengket karena kemasan basah'")
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
                    galat = label.simpan(_tgl_iso(tgl), shift, prn, nama_pilih, pabrik, meja, nilai, oleh, ganti_lama=edit, catatan=catatan)
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
    oleh = akses.pelaku()
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
            _buka_jendela({"prn": r["prn"], "pabrik": r["pabrik"], "meja": r["meja"], "kolom": kolom,
                           "catatan": str(r.get("catatan", "") or "")})
        with c[1].popover("🗑 Hapus input ini", use_container_width=True):
            st.write(f"Hapus {nama[i]}? (Tidak bisa dibatalkan.)")
            if st.button("YA, HAPUS", type="primary", key="pg_hapus"):
                with st.spinner("Menghapus…"):
                    label.hapus_baris(tgl_s, shift, r["prn"], r["pabrik"], r["meja"], r["type"], oleh)
                st.toast("Input dihapus.", icon="🗑")
                st.rerun()


@st.dialog("DAFTAR OPERATOR", width="large", on_dismiss="rerun")
def dlg_operator():
    """Nama + kode operator yang bisa dipilih di Input Label Afkir."""
    kontrol_jendela("operator")
    kepala("operator", "DAFTAR OPERATOR")
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
            label.operator_simpan(sorted(daftar, key=lambda x: nama.get(x, x)), akses.pelaku())
        st.session_state.pop("op_daftar", None)
        st.session_state["pg_toast"] = "Daftar operator disimpan."
        st.rerun()


def _num(x):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return 0


def _pilih_dept(kunci, judul="Foreman"):
    """QC / SK. Akun yang hanya boleh satu departemen tidak diberi pilihan."""
    boleh = akses.dept_boleh()
    if len(boleh) == 1:
        st.markdown(f"<div class='ls-lbl'>{judul.upper()}: <b>{boleh[0]}</b></div>", unsafe_allow_html=True)
        return boleh[0]
    st.markdown(f"<div class='ls-lbl'>{judul.upper()}</div>", unsafe_allow_html=True)
    return st.segmented_control(judul, boleh, default=boleh[0], key=kunci, label_visibility="collapsed") or boleh[0]


CSS_TBL = """<style>
.st-key-tb_tbl [data-testid='stHorizontalBlock']{flex-wrap:nowrap!important;gap:.4rem!important;align-items:center}
.st-key-tb_tbl [data-testid='stColumn']{min-width:0!important;flex:1 1 0!important}
.st-key-tb_tbl [class*='st-key-tbkuning_']{background:#fff6d6;border-radius:8px;padding:2px 4px}
.tb-th{font-size:.66rem;font-weight:800;color:#5b7399;letter-spacing:.5px;padding:2px 0 4px}
.tb-ty small{display:block;font-size:.58rem;font-weight:800;color:#7b8fb0;letter-spacing:.5px}.tb-ty b{font-size:.95rem;color:#0b3d91}
.tb-n{text-align:right;font-weight:700;color:#35507f;font-size:.95rem}.tb-n.tot{color:#0b3d91;font-weight:800}.tb-n.kosong{color:#c0c9db}
</style>"""


def _sel_ty(t, kecil=None):
    kecil = kecil or ("LABEL" if label.adalah_sni(t) else (label.ket_label(t) or label.kategori_label(t)).upper())
    return f"<div class='tb-ty'><small>{kecil}</small><b>{html.escape(t)}</b></div>"


def _urut():
    return {lb: i for i, lb in enumerate(stok.semua_label())}


def _ang(n):
    return f"{int(float(n)):,}".replace(",", ".")


def _kepala_tbl(W, judul, rata):
    h = st.columns(W)
    for c, tx, al in zip(h, judul, rata):
        c.markdown(f"<div class='tb-th' style='text-align:{al}'>{tx}</div>", unsafe_allow_html=True)


def _baris_tambah(pref, ent, W, ganda):
    """Baris kosong di ujung tabel: klik kolom TYPE untuk memilih. ganda=True: type yang sama boleh dipilih lagi.
    SNI hadir otomatis bila type CW dipilih, CE7 bila label warna dipilih (aturan lama)."""
    sudah = set() if ganda else {x[1] for x in ent}
    opsi = [(t, k) for t, k in _semua_type_pilihan() if t not in sudah]
    kat = dict(opsi)
    r = st.columns([1], vertical_alignment="center")
    pilih = r[0].selectbox("Tambah type", [t for t, _k in opsi], index=None, key=f"{pref}_add_{st.session_state.get(pref + '_na', 0)}",
                           label_visibility="collapsed", placeholder="＋ klik di sini untuk menambah type…", format_func=lambda t: f"{kat.get(t, '')} · {t}")
    if pilih:
        tambah = [pilih]
        ada = {x[1] for x in ent}
        if label.punya_sni(pilih) and label.SNI not in ada:
            tambah.append(label.SNI)
        if label.ket_label(pilih) and "CE7" not in ada and "CE7" not in tambah:
            tambah.append("CE7")
        for t in tambah:
            ent.append([st.session_state[f"{pref}_nid"], t])
            st.session_state[f"{pref}_nid"] += 1
        st.session_state[f"{pref}_na"] = st.session_state.get(f"{pref}_na", 0) + 1
        st.rerun(scope="fragment")


def _tabel_terima(pref, tgl, dept):
    """TYPE | DITAMBAH | SISA STOK (sampai tanggal itu) | JADI. Type baris kosong dipilih dengan klik; sisa stok muncul setelah type dipilih."""
    ke = f"{pref}_ent"
    if ke not in st.session_state:
        st.session_state[ke] = []
        st.session_state[f"{pref}_nid"] = 0
    ent = st.session_state[ke]
    sisa = stok.stok_foreman(tgl, dept)
    W = [1.4, 1.1, 1, 1]
    hasil = []
    with st.container(key="tb_tbl"):
        _kepala_tbl(W, ("TYPE", "DITAMBAH (PCS)", "SISA STOK", "JADI"), ("left", "left", "right", "right"))
        for idb, t in ent:
            r = st.columns(W, vertical_alignment="center")
            r[0].markdown(_sel_ty(t), unsafe_allow_html=True)
            v = r[1].number_input(f"Tambah {t} {idb}", min_value=0, max_value=9999999, step=1, value=None, placeholder="0",
                                  key=f"{pref}_n_{idb}", label_visibility="collapsed")
            sb = int(sisa.get(t, 0))
            r[2].markdown(f"<div class='tb-n'>{_ang(sb)}</div>", unsafe_allow_html=True)
            r[3].markdown(f"<div class='tb-n tot'>{_ang(sb + int(v or 0))}</div>", unsafe_allow_html=True)
            if v:
                hasil.append((t, int(v)))
        _baris_tambah(pref, ent, W, ganda=False)
    if ent and st.button("↶ Hapus baris terakhir", key=f"{pref}_undo", width="stretch"):
        idb, _t = ent.pop()
        st.session_state.pop(f"{pref}_n_{idb}", None)
        st.rerun(scope="fragment")
    return hasil


def _tab_terima(oleh):
    """Label diterima dari packing = menambah stok Foreman departemen (QC atau SK)."""
    dept = _pilih_dept("il_dept_t", "Masuk ke stok Foreman")
    tgl = st.date_input("Tanggal diterima", value=label.hari_ini(), format="DD/MM/YYYY", key="il_tgl_t")
    st.caption("Klik baris kosong di kolom TYPE untuk memilih type, lalu isi jumlah (pcs). Sisa stok muncul setelah type dipilih.")
    pilih = _tabel_terima(f"il_t{dept}", _tgl_iso(tgl), dept)
    if st.button("SIMPAN LABEL DITERIMA", type="primary", width="stretch", key="il_simpan_t", disabled=not pilih):
        with st.spinner("Menyimpan…"):
            n = stok.terima_simpan(_tgl_iso(tgl), pilih, oleh, dept)
        st.session_state["il_toast"] = f"{n} penerimaan label tersimpan."
        label_ui._reset(f"il_t{dept}")
        st.rerun(scope="fragment")
    riwayat = stok.terima_daftar(label.hari_ini().strftime("%Y-%m"), dept)
    st.markdown(f"**Penerimaan bulan ini · Foreman {dept}**")
    if riwayat.empty:
        st.caption("Belum ada penerimaan.")
    for i, r in riwayat.head(12).iterrows():
        c = st.columns([2.2, 2, 2, 1], vertical_alignment="center")
        c[0].caption(f"{r['tgl'][8:]}-{r['tgl'][5:7]}-{r['tgl'][:4]}")
        c[1].write(f"**{r['label']}**")
        c[2].write(f"{r['jumlah']:,} pcs".replace(",", "."))
        if c[3].button("✕", key=f"il_x_{i}", help="Hapus penerimaan ini"):
            stok.terima_hapus(r["tgl"], r["waktu"], r["label"], oleh)
            st.session_state["il_toast"] = "Penerimaan dihapus."
            st.rerun(scope="fragment")


def _lok_ringkas(lk):
    if stok.adalah_foreman(lk):
        return stok.lok_nama(lk)
    return label.nama_meja(*lk.split("|", 1))


def _tanpa_sni_ganda(daftar):
    """SNI hadir otomatis bila ada type CW; simpan di pilihan hanya bila berdiri sendiri."""
    if any(label.punya_sni(x) for x in daftar):
        return [x for x in daftar if not label.adalah_sni(x)]
    return list(daftar)


def _kepala_kolom(t, induk):
    """(kecil, besar, kelas_sni, boleh_hapus) untuk judul kolom type. SNI tampil sebagai 'SNI' saja; boleh dihapus kecuali bila ada type CW."""
    if label.adalah_sni(t):
        return "LABEL", "SNI", True, not any(label.punya_sni(x) for x in induk)
    warna_wajib = t == "CE7" and any(label.ket_label(x) for x in induk)
    return (label.ket_label(t) or label.kategori_label(t)).upper(), t, False, not warna_wajib


def _proses_sap(sap, t):
    """Afkir Proses otomatis dari SAP; SNI = jumlah semua type CW."""
    if label.adalah_sni(t):
        return sum(v for lb, v in sap.items() if label.punya_sni(lb))
    return sap.get(t, 0) if laporan.proses_berlaku(t) else 0


def _grid_hitung(kp, awal):
    """Jendela isian seperti INPUT LABEL AFKIR: kolom per type label, satu baris jumlah hitungan fisik.
    awal = {label: jumlah} yang sudah tersimpan. Return {label: jumlah} untuk kolom yang dipilih."""
    tipe_kat = label.type_per_kategori()
    kc = f"{kp}_cols"
    if kc not in st.session_state:
        st.session_state[kc] = _tanpa_sni_ganda(list(dict.fromkeys(awal)))
        for lb, v in awal.items():
            st.session_state[f"{kp}_n_{lb}"] = int(v) or None
    induk = list(st.session_state[kc])
    if any(label.ket_label(x) for x in induk) and "CE7" not in induk:
        induk.insert(0, "CE7")
    cols = label.kolom_lengkap(induk)
    out = {}
    with st.container(key="lbm"):
        k = st.columns([1] * len(cols) + [1], vertical_alignment="top")
        for i, t in enumerate(cols):
            with k[i]:
                kecil, besar, sni, boleh = _kepala_kolom(t, induk)
                st.markdown(f"<div class='lb-th{' lb-sni' if sni else ''}'><small>{kecil}</small><b>{besar}</b></div>", unsafe_allow_html=True)
                if boleh:
                    with st.container(key=f"lbx_{i}"):
                        if st.button("✕", key=f"{kp}_rm_{i}", help="Hapus label ini"):
                            st.session_state[kc] = [x for x in induk if x != t]
                            st.rerun(scope="fragment")
        with k[len(cols)], st.container(key="lbplus"):
            if st.button("+ Label", key=f"{kp}_tambah", width="stretch"):
                st.session_state[f"{kp}_tb"] = not st.session_state.get(f"{kp}_tb", False)
                st.rerun(scope="fragment")
        if cols:
            r = st.columns([1] * len(cols))
            for i, t in enumerate(cols):
                v = r[i].number_input(f"Hitungan {t}", min_value=0, max_value=9999999, step=1, value=None, placeholder="0",
                                      key=f"{kp}_n_{t}", label_visibility="collapsed")
                out[t] = int(v or 0)
        else:
            st.caption("Klik **+ Label** untuk memilih type label yang dihitung.")
    if st.session_state.get(f"{kp}_tb"):
        n = st.session_state.setdefault(f"{kp}_pk", 0)
        with st.container(border=True):
            kat = st.pills("PILIH KATEGORI", label.KATEGORI, key=f"{kp}_kat_{n}")
            if kat:
                pilihan = [t for t in tipe_kat.get(kat, []) if t not in induk]
                if not pilihan:
                    st.caption("Tidak ada type untuk kategori ini (atau semuanya sudah dipilih).")
                else:
                    tp = st.pills(f"{kat.upper()} → PILIH LABEL", pilihan, key=f"{kp}_typ_{n}_{kat}")
                    if tp:
                        st.session_state[kc] = induk + [tp]
                        st.session_state[f"{kp}_tb"] = False
                        st.session_state[f"{kp}_pk"] = n + 1
                        st.rerun(scope="fragment")
    return out


CSS_OPNAME = """<style>
.op-th{display:grid;grid-template-columns:1.2fr 1.4fr 1fr;gap:1rem;font:700 10px monospace;letter-spacing:.15em;color:#5b7399;padding:.4rem .2rem;border-bottom:2px solid #dbe7f7;margin-top:.4rem}
.op-th .sb{text-align:right;color:#b07400}
.op-ty small{display:block;font:10px monospace;letter-spacing:.12em;color:#5b7399}.op-ty b{color:#0b3d91;font-size:1.05rem}
.op-sb{text-align:right;font-weight:800;font-size:1.05rem;color:#b07400}.op-sb.neg{color:#d33}
.op-tot{display:flex;justify-content:space-between;border-top:2px solid #2a8fe8;padding:.55rem .2rem;margin:.3rem 0 .6rem;color:#0b3d91}
</style>"""


@st.cache_data(ttl=600, show_spinner=False)
def _semua_type_pilihan():
    """[(type, kategori)] semua type + versi SNI-nya, berurutan seperti tabel jenis label. Di-cache 10 menit (tabel ini jarang berubah)."""
    t = label.jenis_tabel()
    hasil, lihat, pos_sni = [], set(), None
    for r in t.itertuples():
        lb = r.label
        if not lb or lb in lihat:
            continue
        lihat.add(lb)
        hasil.append((lb, r.kategori or "Lainnya"))
        if str(r.sni).lower() == "ya":
            pos_sni = len(hasil)  # SNI satu saja, diletakkan sesudah type CW terakhir yang punya SNI
    if pos_sni is not None:
        hasil.insert(pos_sni, (label.SNI, label.SNI))
    return hasil


def _ctx_opname(lk, tgl):
    """Data berat satu lokasi/tanggal (stok sistem, hitungan tersimpan, progres) dihitung SEKALI lalu disimpan di sesi,
    supaya klik kecil di jendela tidak memicu perhitungan ulang. Dihapus saat simpan (lihat _reset_ctx)."""
    k = f"opx_{lk}_{tgl}"
    c = st.session_state.get(k)
    if c and time.time() - c["t"] < 180:
        return c
    info = stok.opname_info(tgl, lk)
    ada = {x: v for x, v in (stok.opname_baris(tgl, lk) if info else {}).items() if x != stok.KOSONG}
    c = {"t": time.time(), "sis": stok.stok_lokasi(lk, tgl), "info": info, "ada": ada}
    st.session_state[k] = c
    return c


def _status_opname(tgl):
    k = f"opx_sl_{tgl}"
    c = st.session_state.get(k)
    if c and time.time() - c["t"] < 180:
        return c["v"]
    v = stok.opname_status(tgl)
    st.session_state[k] = {"t": time.time(), "v": v}
    return v


def _reset_ctx():
    for k in [k for k in st.session_state if str(k).startswith("opx_")]:
        del st.session_state[k]


def _baris_opname(pref, sis, nama_lok, meja, ada):
    """Tabel opname: TYPE | HITUNG AKTUAL | SISTEM | SELISIH. Awalnya kosong; klik baris kosong di kolom TYPE untuk memilih type,
    stok sistem muncul setelah type dipilih. Type yang sama boleh diinput lagi (baris kuning): jumlahnya terakumulasi,
    SISTEM tetap sama dan SELISIH berkurang sesuai total hitungan sampai baris itu.
    Return (baru[(type, total jumlah)], 'simpan'/'kosong'/None, daftar_baris[(id, type)])."""
    ke = f"{pref}_ent"
    if ke not in st.session_state:
        st.session_state[ke] = []
        st.session_state[f"{pref}_nid"] = 0
    ent = st.session_state[ke]
    W = [1.4, 1.1, 1, 1]
    total, lihat = {}, set()
    with st.container(key="tb_tbl"):
        _kepala_tbl(W, ("TYPE", "HITUNG AKTUAL", "SISTEM", "SELISIH"), ("left", "left", "right", "right"))
        for idb, t in ent:
            ulang = t in lihat
            lihat.add(t)
            with st.container(key=f"{'tbkuning_' if ulang else 'tbbiasa_'}{pref}_{idb}"):
                r = st.columns(W, vertical_alignment="center")
                r[0].markdown(_sel_ty(t, "SUDAH DIINPUT" if ulang else None), unsafe_allow_html=True)
                v = r[1].number_input(f"Hitungan {t} {idb}", min_value=0, max_value=9999999, step=1, value=None, placeholder="0",
                                      key=f"{pref}_n_{idb}", label_visibility="collapsed")
                sb = int(sis.get(t, 0))
                r[2].markdown(f"<div class='tb-n'>{_ang(sb)}</div>", unsafe_allow_html=True)
                if v is not None:
                    total[t] = total.get(t, 0) + int(v)
                    r[3].markdown(f"<div class='tb-n'>{_selisih_angka(total[t] - sb)}</div>", unsafe_allow_html=True)
                else:
                    r[3].markdown("<div class='tb-n kosong'>–</div>", unsafe_allow_html=True)
        _baris_tambah(pref, ent, W, ganda=True)
    c1, c2 = st.columns(2)
    if ent and c1.button("↶ Hapus baris terakhir", key=f"{pref}_undo", width="stretch"):
        idb, _t = ent.pop()
        st.session_state.pop(f"{pref}_n_{idb}", None)
        st.rerun(scope="fragment")
    if ent and c2.button("Salin baris terakhir", key=f"{pref}_dup", width="stretch", help="Tambah baris dengan type yang sama untuk hitungan berikutnya"):
        ent.append([st.session_state[f"{pref}_nid"], ent[-1][1]])
        st.session_state[f"{pref}_nid"] += 1
        st.rerun(scope="fragment")
    st.caption("Type yang punya stok sistem tetapi tidak kamu masukkan dianggap 0 saat disimpan. Baris dengan type yang sama dijumlahkan; bila type itu sudah pernah tersimpan, kamu akan ditanya mau dijumlahkan atau pilih salah satu.")
    pencet = None
    b1, b2 = st.columns([2, 1])
    if b1.button(("SIMPAN TAMBAHAN " if ada else "SIMPAN HITUNGAN ") + nama_lok.upper(), type="primary", width="stretch", key=f"{pref}_simpan"):
        pencet = "simpan"
    if meja and b2.button("MEJA KOSONG", width="stretch", key=f"{pref}_kosong"):
        pencet = "kosong"
    # type yang punya stok sistem tetapi belum ada di tabel (dan belum tersimpan) -> daftar "belum dihitung"
    dipakai = {t for _i, t in ent} | set(ada or {})
    belum = [(t, n) for t, n in sorted(sis.items(), key=lambda x: _urut().get(x[0], 9999)) if n and t not in dipakai]
    if belum:
        st.markdown(f"<div class='kt'>BELUM DIHITUNG — {len(belum)} type masih punya stok sistem</div>"
                    + "".join(f"<span class='ls-chip min'>{html.escape(t)} ({_ang(n)})</span>" for t, n in belum)
                    + "<div style='font-size:.72rem;color:#8a98b3;margin-top:.3rem'>Hilang dari daftar ini setelah type-nya masuk ke tabel hitung di atas.</div>",
                    unsafe_allow_html=True)
    return list(total.items()), pencet, ent


def _kumpul_konflik(baru, tersimpan):
    """Gabungkan hitungan baru dengan yang tersimpan. Return (final{type: jumlah}, konflik{type: [(sumber, nilai)]})."""
    cand = {}
    for t, v in tersimpan.items():
        if t != stok.KOSONG and v:
            cand.setdefault(t, []).append(("tersimpan", int(v)))
    kasus = {t: list(c) for t, c in cand.items()}
    for t, v in baru:
        kasus.setdefault(t, []).append(("baru", int(v)))
    final, konflik = {}, {}
    for t, c in kasus.items():
        if len(c) == 1:
            final[t] = c[0][1]
        else:
            konflik[t] = c
    return final, konflik


def _panel_konflik(kf, oleh):
    """Pertanyaan saat ada type kembar: jumlahkan atau pilih salah satu. Mengembalikan True bila halaman perlu berhenti menggambar form."""
    st.warning("**⚠ Ada type yang nilainya lebih dari satu.** Pilih cara menggabungkannya untuk setiap type di bawah ini.")
    pilihan = {}
    for t, c in kf["konflik"].items():
        total = sum(v for _s, v in c)
        opsi = [f"JUMLAHKAN semuanya = {total:,}".replace(",", ".")]
        for i, (sumber, v) in enumerate(c):
            opsi.append(f"PILIH SALAH SATU: {v:,} ({sumber})".replace(",", ".") + ("" if len([1 for x in c if x[0] == sumber]) == 1 else f" #{i + 1}"))
        daftar = " + ".join(f"{v:,} ({sm})".replace(",", ".") for sm, v in c)
        st.markdown(f"**{t}** — {daftar}")
        pilihan[t] = (st.radio(f"Cara untuk {t}", opsi, index=None, key=f"kf_{kf['pref']}_{t}", label_visibility="collapsed"), opsi, total, c)
    lengkap = all(v[0] is not None for v in pilihan.values())
    b1, b2 = st.columns([2, 1])
    if b1.button("YA, SIMPAN", type="primary", width="stretch", disabled=not lengkap, key="kf_ok"):
        final = dict(kf["final"])
        for t, (pil, opsi, total, c) in pilihan.items():
            idx = opsi.index(pil)
            final[t] = total if idx == 0 else c[idx - 1][1]
        with st.spinner("Menyimpan…"):
            stok.opname_simpan(kf["tgl"], kf["lk"], final, oleh)
        for t in kf["konflik"]:
            st.session_state.pop(f"kf_{kf['pref']}_{t}", None)
        label_ui._reset(kf["pref"]); _reset_ctx()
        if kf.get("next"):
            st.session_state["op_next"] = kf["next"]
        st.session_state["il_toast"] = f"Hitungan {kf['nama']} tersimpan."
        st.session_state.pop("op_konf", None)
        st.rerun(scope="fragment")
    if b2.button("KEMBALI", width="stretch", key="kf_back"):
        for idb, val in kf["nilai"].items():
            st.session_state[f"{kf['pref']}_n_{idb}"] = val
        for t in kf["konflik"]:
            st.session_state.pop(f"kf_{kf['pref']}_{t}", None)
        st.session_state.pop("op_konf", None)
        st.rerun(scope="fragment")


def _opname_form(tgl, oleh, dept):
    sl = _status_opname(tgl)
    kp = f"opl{dept}"
    kf = st.session_state.get("op_konf")
    if kf:
        _panel_konflik(kf, oleh)
        return
    nxt = st.session_state.pop("op_next", None)
    if nxt:
        st.session_state[f"{kp}_lok"] = nxt[0]
        st.session_state[f"{kp}_mej_{nxt[0]}"] = nxt[1]
    st.markdown("<div class='ls-lbl'>LOKASI LABEL <span class='ls-wajib'>wajib</span></div>", unsafe_allow_html=True)
    opsi = ["Foreman"] + stok.DEPT[dept]
    lokasi = st.segmented_control("Lokasi", opsi, key=f"{kp}_lok", default="Foreman", label_visibility="collapsed",
                                  format_func=lambda x: f"Foreman {dept}" if x == "Foreman" else x) or "Foreman"
    pabrik = meja = None
    if lokasi == "Foreman":
        lk = stok.foreman_dept(dept)
        nama_lok = f"Foreman {dept}"
    else:
        pabrik = lokasi
        meja = st.selectbox("NOMOR MEJA", label.meja_daftar(pabrik), index=None, key=f"{kp}_mej_{pabrik}",
                            format_func=lambda m: f"Meja {m}", placeholder="Pilih nomor meja…")
        lk = stok.lok(pabrik, str(meja)) if meja else None
        nama_lok = label.nama_meja(pabrik, meja) if meja else ""
    if lk:
        tgl_txt = f"{tgl[8:10]}/{tgl[5:7]}/{tgl[:4]}"
        cx = _ctx_opname(lk, tgl)
        info, ada = cx["info"], cx["ada"]
        if info:
            oleh_l, jam, adj = info
            chips = " ".join(f"<span class='ls-chip'>{k} · {int(v[0]):,}</span>".replace(",", ".") for k, v in ada.items() if v[0]) or "(meja ditandai kosong)"
            st.warning(f"**⚠ SUDAH PERNAH DIINPUT** — {tgl_txt} · {nama_lok} — terakhir disimpan oleh {oleh_l or '-'} pukul {jam}.  \n"
                       "Yang sudah tersimpan tampil di bawah. Isi tabel hanya untuk **tambahan** atau **perubahan**; "
                       "jika type-nya sama, kamu akan ditanya mau dijumlahkan atau pilih salah satu."
                       + ("  \nHitungan ini sudah di-ADJUST; setelah diubah, lakukan ADJUST lagi di menu Selisih." if adj else ""))
            st.markdown(f"<div class='kt'>SUDAH TERSIMPAN</div><div>{chips}</div>", unsafe_allow_html=True)
        else:
            st.success(f"Belum ada hitungan untuk {tgl_txt} · {nama_lok}. Silakan input baru.")
        pref = f"og_{lk}_{tgl}"
        baru, tekan, ent = _baris_opname(pref, cx["sis"], nama_lok, meja, ada)
        nxt_m = None
        if meja:
            nxt_m = (pabrik, str(int(meja) + 1) if str(meja).isdigit() and int(meja) < label.PABRIK[pabrik] else str(meja))
        if tekan == "kosong":
            stok.opname_simpan(tgl, lk, {}, oleh)
            label_ui._reset(pref); _reset_ctx()
            if nxt_m:
                st.session_state["op_next"] = nxt_m
            st.session_state["il_toast"] = f"{nama_lok} ditandai kosong."
            st.rerun(scope="fragment")
        elif tekan == "simpan":
            if not baru:
                st.error("Belum ada jumlah yang diisi.")
            else:
                final, konflik = _kumpul_konflik(baru, {k: v[0] for k, v in ada.items()})
                for k, v in ada.items():      # type tersimpan yang tidak disentuh tetap dipertahankan
                    if k != stok.KOSONG and k not in final and k not in konflik:
                        final[k] = int(v[0])
                if konflik:
                    nilai = {idb: st.session_state.get(f"{pref}_n_{idb}") for idb, _t in ent}
                    st.session_state["op_konf"] = {"pref": pref, "tgl": tgl, "lk": lk, "nama": nama_lok, "final": final,
                                                   "konflik": konflik, "next": nxt_m, "ent": [list(e) for e in ent], "nilai": nilai}
                    st.rerun(scope="fragment")
                else:
                    with st.spinner("Menyimpan…"):
                        stok.opname_simpan(tgl, lk, final, oleh)
                    label_ui._reset(pref); _reset_ctx()
                    if nxt_m:
                        st.session_state["op_next"] = nxt_m
                    st.session_state["il_toast"] = f"Hitungan {nama_lok} tersimpan."
                    st.rerun(scope="fragment")
    elif lokasi != "Foreman":
        st.caption("Pilih nomor meja dulu.")
    if pabrik:
        daftar = label.meja_daftar(pabrik)
        n = sum(1 for m in daftar if stok.lok(pabrik, m) in sl)
        st.markdown(f"<div class='kt'>PROGRES {pabrik.upper()} — {n} dari {len(daftar)} meja sudah dihitung</div>", unsafe_allow_html=True)
        st.markdown("".join(
            f"<span class='ls-chip{'' if stok.lok(pabrik, m) in sl else ' min'}'>{m}{'' if stok.lok(pabrik, m) in sl else ' belum'}</span>" for m in daftar),
            unsafe_allow_html=True)


@st.dialog("STOK OPNAME LABEL", width="large", on_dismiss="rerun")
def dlg_opname():
    kontrol_jendela("inputlabel")
    kepala("label", "STOK OPNAME LABEL")
    st.markdown(label_ui.CSS, unsafe_allow_html=True)
    st.markdown(CSS_JENDELA + CSS_OPNAME + CSS_TBL, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    dept = _pilih_dept("op_dept", "Departemen")
    tgl = _tgl_iso(st.date_input("Tanggal opname (stok akhir hari)", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="op_tgl"))
    _opname_form(tgl, akses.pelaku(), dept)
    st.caption("Hasil hitung baru dipakai sistem setelah tombol ADJUST di menu SELISIH STOK OPNAME.")


def _selisih_angka(d):
    c = "#1d6f2f" if d == 0 else ("#b71c1c" if d < 0 else "#8a5a00")
    return f"<b style='color:{c}'>{d:+,}</b>".replace(",", ".") if d else "<b style='color:#1d6f2f'>0</b>"


def _excel_selisih(tgl, status):
    import io
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Selisih opname"
    ws.append(["LOKASI", "TYPE", "SISTEM", "AKTUAL", "SELISIH"])
    for lk in status:
        for lb, (a, sx) in stok.opname_baris(tgl, lk).items():
            r = ws.max_row + 1
            ws.append([_lok_ringkas(lk), lb, sx, a, f"=D{r}-C{r}"])
    for col, w in zip("ABCDE", (16, 16, 11, 11, 11)):
        ws.column_dimensions[col].width = w
    from core import rekap
    return rekap.bytes_rekap(tgl, wb=wb)  # + sheet rekap QC TK / SK / INPUT (format Oktober)


@st.cache_data(ttl=30, show_spinner=False)
def _excel_selisih_c(tgl, lokasi):
    return _excel_selisih(tgl, list(lokasi))


def _konfirmasi_adjust(tgl, dept, belum, oleh):
    """Panel konfirmasi ADJUST (menggantikan isi jendela; jendela tidak boleh bertingkat)."""
    st.warning(f"**Yakin ADJUST stok {dept} tanggal {label_ui.tgl_id(tgl)}?**")
    st.markdown(f"- {len(belum)} lokasi akan diganti stok sistemnya dengan **stok aktual** hasil hitungan:  \n"
                + ", ".join(_lok_ringkas(lk) for lk in belum)
                + "\n- Pemakaian dihitung lagi mulai hari berikutnya.\n- Lokasi yang tidak dihitung tidak berubah.")
    c1, c2 = st.columns(2)
    if c1.button("YA, ADJUST SEKARANG", type="primary", width="stretch", key="sl_adj_ya"):
        with st.spinner("Menyesuaikan stok…"):
            n = stok.opname_adjust(tgl, oleh, belum)
        st.session_state.pop("sl_konfirm", None)
        st.session_state.update({"sl_dept": dept, "sl_tgl": tgl})
        st.session_state["il_toast"] = f"{n} lokasi {dept} di-adjust: stok aktual jadi stok awal."
        st.rerun(scope="fragment")
    if c2.button("BATAL", width="stretch", key="sl_adj_batal"):
        st.session_state.pop("sl_konfirm", None)
        st.session_state.update({"sl_dept": dept, "sl_tgl": tgl})
        st.rerun(scope="fragment")


@st.dialog("SELISIH STOK OPNAME", width="large", on_dismiss="rerun")
def dlg_selisih():
    kontrol_jendela("inputlabel")
    kepala("label", "SELISIH STOK OPNAME")
    st.markdown(label_ui.CSS, unsafe_allow_html=True)
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    oleh = akses.pelaku()
    tanggal = stok.opname_tanggal()
    if not tanggal:
        st.info("Belum ada hasil stok opname. Isi dulu lewat menu STOK OPNAME LABEL.")
        return
    konf = st.session_state.get("sl_konfirm")
    if konf:
        _konfirmasi_adjust(konf[0], konf[1], konf[2], oleh)
        return
    boleh = akses.dept_boleh()
    c1, c2 = st.columns([1, 1.4], vertical_alignment="bottom")
    tgl = c1.selectbox("Opname tanggal", tanggal, key="sl_tgl", format_func=label_ui.tgl_id)
    dept_pil = c2.segmented_control("Departemen", ["QC", "SK", "Gabungan"], default="QC", key="sl_dept", label_visibility="collapsed") or "QC"
    dept = None if dept_pil == "Gabungan" else dept_pil
    lihat = st.segmented_control("Lihat", ["Total per type", "Foreman", "Per meja"], default="Total per type", key="sl_lihat", label_visibility="collapsed") or "Total per type"
    status = {lk: v for lk, v in stok.opname_status(tgl).items() if stok.dept_cocok(lk, dept)}
    if not status:
        st.info(f"Belum ada lokasi {dept_pil} yang dihitung pada tanggal ini.")
    lokasi = None
    if lihat == "Foreman":
        fm = [lk for lk in status if stok.adalah_foreman(lk)]
        lokasi = fm[0] if len(fm) == 1 else (st.selectbox("Foreman", fm, key="sl_fm", format_func=_lok_ringkas) if fm else None)
        if not fm and status:
            st.info("Foreman belum dihitung pada tanggal ini.")
    elif lihat == "Per meja":
        meja_ada = [lk for lk in status if not stok.adalah_foreman(lk)]
        lokasi = st.selectbox("Meja yang sudah dihitung", meja_ada, index=None, placeholder="Pilih meja…", key="sl_lok", format_func=_lok_ringkas)
    kolom = [1.6, 1.4, 1.6, 1.2]
    st.markdown("<style>.st-key-sl_tbl [data-testid='stHorizontalBlock']{flex-wrap:nowrap!important;gap:.4rem!important}"
                ".st-key-sl_tbl [data-testid='stColumn']{min-width:0!important;flex:1 1 0!important}"
                ".st-key-sl_tbl .kt{font-size:.68rem;font-weight:700;color:#555}</style>", unsafe_allow_html=True)
    tbl = st.container(key="sl_tbl")
    if lihat == "Total per type" and status:
        sis, akt = {}, {}
        for lk in status:
            for lb, (a, sx) in stok.opname_baris(tgl, lk).items():
                sis[lb] = sis.get(lb, 0) + sx
                akt[lb] = akt.get(lb, 0) + a
        for c, t in zip(tbl.columns(kolom), ["TYPE", "SISTEM", "AKTUAL", "SELISIH"]):
            c.markdown(f"<div class='kt'>{t}</div>", unsafe_allow_html=True)
        for lb in stok.urut_label(sis):
            c = tbl.columns(kolom, vertical_alignment="center")
            c[0].markdown(f"**{lb}**")
            c[1].write(f"{sis[lb]:,}".replace(",", "."))
            c[2].write(f"{akt[lb]:,}".replace(",", "."))
            c[3].markdown(_selisih_angka(akt[lb] - sis[lb]), unsafe_allow_html=True)
        st.caption(f"Gabungan semua lokasi {dept_pil} (Foreman + meja) yang sudah dihitung pada tanggal ini. Kolom sistem tidak bisa diedit.")
    elif lokasi:
        h = stok.opname_baris(tgl, lokasi)
        dp = stok.dept_lokasi(lokasi)
        boleh_edit = dp in boleh
        if not h:
            st.success("Lokasi ini dicatat kosong (0).")
        for c, t in zip(tbl.columns(kolom), ["TYPE", "SISTEM", "AKTUAL (bisa diedit)", "SELISIH"]):
            c.markdown(f"<div class='kt'>{t}</div>", unsafe_allow_html=True)
        nilai = {}
        for lb in stok.urut_label(h):
            a, sx = h[lb]
            c = tbl.columns(kolom, vertical_alignment="center")
            c[0].markdown(f"**{lb}**")
            c[1].write(f"{sx:,}".replace(",", "."))
            nilai[lb] = int(c[2].number_input(f"Aktual {lb}", min_value=0, max_value=9999999, step=1, value=int(a), key=f"sl_a_{tgl}_{lokasi}_{lb}",
                                              label_visibility="collapsed", disabled=not boleh_edit))
            c[3].markdown(_selisih_angka(nilai[lb] - sx), unsafe_allow_html=True)
        if not boleh_edit:
            st.caption(f"Akun ini hanya bisa mengubah hitungan {', '.join(boleh)}.")
        if st.button("SIMPAN PERUBAHAN AKTUAL", width="stretch", key="sl_simpan", disabled=not h or not boleh_edit):
            stok.opname_simpan(tgl, lokasi, nilai, oleh)
            st.session_state["il_toast"] = "Perubahan stok aktual tersimpan."
            st.rerun(scope="fragment")
    elif lihat != "Total per type" and status:
        st.caption("Pilih lokasi yang ingin dilihat.")
    if status:
        st.download_button("⬇ UNDUH EXCEL (selisih + rekap hitung label)", _excel_selisih_c(tgl, tuple(status)), file_name=f"selisih_opname_{dept_pil}_{tgl}.xlsx", width="stretch", key="sl_xls")
        from core import rekap, rencana
        bp = rekap.bulan_rencana(tgl)
        st.caption(f"Excel berisi sheet Selisih opname + REKAP HITUNG LABEL QC / SK + INPUT. Rencana produksi: {rencana.nama_bulan(bp)}"
                   + ("" if rencana.per_type(bp, "QC") else " (belum diupload di admin)") + ".")
    st.markdown("---")
    belum = [lk for lk, sdh in status.items() if not sdh]
    st.markdown("**ADJUST** — jadikan stok aktual sebagai stok awal periode berikutnya")
    if dept is None:
        st.caption("Pilih QC atau SK di atas untuk ADJUST (ADJUST dilakukan per departemen).")
    elif dept not in boleh:
        st.caption(f"ADJUST {dept} hanya bisa dilakukan oleh foreman {dept} atau admin.")
    else:
        _ai = stok.adjust_terakhir(dept)
        if _ai:
            st.caption(f"Terakhir di-ADJUST: stok opname tanggal {label_ui.tgl_id(_ai['tgl'])} (diproses {_ai['waktu'][11:16]} {label_ui.tgl_id(_ai['waktu'][:10])}, oleh {_ai['oleh']}).")
        st.caption(f"{len(status)} lokasi {dept} dihitung pada tanggal ini, {len(belum)} belum di-adjust. "
                   "Stok sistem diganti angka aktual mulai tanggal opname; lokasi yang tidak dihitung tidak berubah.")
        with st.container(key="il_adj"):
            if st.button(f"ADJUST STOK {dept}", type="primary", width="stretch", key="sl_adj", disabled=not belum):
                st.session_state["sl_konfirm"] = (tgl, dept, belum)
                st.rerun(scope="fragment")


# ---- distribusi / pinjam label antar foreman
@st.dialog("DISTRIBUSI LABEL ANTAR FOREMAN", width="large", on_dismiss="rerun")
def dlg_distribusi():
    kontrol_jendela("inputlabel")
    kepala("label", "DISTRIBUSI LABEL ANTAR FOREMAN")
    st.markdown(label_ui.CSS, unsafe_allow_html=True)
    st.markdown(CSS_JENDELA, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    oleh = akses.pelaku()
    st.caption("Pinjam / kirim label antar Foreman QC dan SK. Stok foreman asal berkurang, stok foreman tujuan bertambah.")
    tgl = _tgl_iso(st.date_input("Tanggal", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="ds_tgl"))
    punya = akses.dept_boleh()[0]
    st.markdown("<div class='ls-lbl'>ARAH</div>", unsafe_allow_html=True)
    arah = st.segmented_control("Arah", ["QC → SK", "SK → QC"], default=("SK → QC" if punya == "SK" else "QC → SK"), key="ds_arah", label_visibility="collapsed") or "QC → SK"
    dari, ke = arah.split(" → ")
    c1, c2 = st.columns(2)
    c1.markdown(f"<div class='ls-lbl'>STOK FOREMAN {dari} (asal)</div>" + label_ui.chips(stok.stok_foreman(tgl, dari)), unsafe_allow_html=True)
    c2.markdown(f"<div class='ls-lbl'>STOK FOREMAN {ke} (tujuan)</div>" + label_ui.chips(stok.stok_foreman(tgl, ke)), unsafe_allow_html=True)
    isi = _grid_hitung(f"ds_{dari}", {})
    isi = {k: v for k, v in isi.items() if v > 0}
    asal = stok.stok_foreman(tgl, dari)
    lebih = [f"{lb} ({n} > {asal.get(lb, 0)})" for lb, n in isi.items() if n > asal.get(lb, 0)]
    if lebih:
        st.warning("Jumlah melebihi stok sistem foreman asal: " + ", ".join(lebih) + ". Tetap bisa disimpan (stok bisa jadi minus).")
    ket = st.text_input("Keterangan (opsional)", placeholder="mis. pinjam CE7 untuk produksi SK", key="ds_ket")
    if st.button("SIMPAN DISTRIBUSI", type="primary", width="stretch", key="ds_simpan", disabled=not isi):
        galat = stok.distribusi_simpan(tgl, dari, ke, list(isi.items()), oleh, ket)
        if galat:
            st.error(galat)
        else:
            label_ui._reset(f"ds_{dari}")
            st.session_state["il_toast"] = "Distribusi label tersimpan."
            st.rerun(scope="fragment")
    st.markdown("**Riwayat distribusi terbaru**")
    d = stok.distribusi_daftar(12)
    if d.empty:
        st.caption("Belum ada distribusi.")
    for _, r in d.iterrows():
        c = st.columns([1.3, 1.2, 1.4, 1.2, 2, 0.6], vertical_alignment="center")
        c[0].caption(label_ui.tgl_id(r["tgl"]))
        c[1].caption(f"{r['dari']} → {r['ke']}")
        c[2].write(f"**{r['label']}**")
        c[3].write(f"{r['jumlah']:,} pcs".replace(",", "."))
        c[4].caption(str(r.get("ket", "") or ""))
        if c[5].button("✕", key=f"ds_x_{r['id']}", help="Hapus (tercatat di riwayat)"):
            stok.distribusi_hapus(r["id"], oleh)
            st.rerun(scope="fragment")


@st.dialog("INPUT LABEL BAGUS", width="large", on_dismiss="rerun")
def dlg_label_bagus():
    kontrol_jendela("inputlabel")
    kepala("label", "INPUT LABEL BAGUS")
    st.markdown(label_ui.CSS, unsafe_allow_html=True)
    st.markdown(CSS_JENDELA + CSS_TBL, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    _tab_terima(akses.pelaku())


CSS_CEK = """<style>
.st-key-ck_tbl [data-testid='stHorizontalBlock']{flex-wrap:nowrap!important;gap:.4rem!important;align-items:center}
.st-key-ck_tbl [data-testid='stColumn']{min-width:0!important;flex:1 1 0!important}
.ck-th{font-size:.66rem;font-weight:800;color:#5b7399;letter-spacing:.5px;padding:2px 0 4px}
.ck-ty i{display:block;font-style:normal;font-size:.62rem;color:#8a98b3}.ck-ty i .fm{color:#1d6f2f;font-weight:700}.ck-sb.tot{color:#0b3d91;font-weight:800}
.ck-ty small{display:block;font-size:.58rem;font-weight:800;color:#7b8fb0;letter-spacing:.5px}.ck-ty b{font-size:.95rem;color:#0b3d91}
.ck-by{font-size:.78rem;line-height:1.2;color:#35507f}.ck-by.fm{color:#1d6f2f;font-weight:700}.ck-by.no{color:#9aa8c2}
.ck-sb{font-weight:700;color:#35507f;text-align:right}
.ck-nt{background:#fff7e0;border:1px solid #f0d88a;border-radius:10px;padding:9px 12px;color:#6b5200;font-size:.85rem;margin:.4rem 0}
.ck-in{background:#eef3fb;border:1px solid #c9d8f3;border-radius:10px;padding:9px 12px;color:#35507f;font-size:.85rem;margin:.4rem 0}
</style>"""


def _baris_cek(pref, cur, awal):
    """SATU tabel: TYPE | STOK AWAL | DIINPUT KARYAWAN (bisa diubah foreman) | TOTAL HARI ITU.
    Selalu ada satu baris kosong di bawah untuk menambah type. Return ({type: jumlah diinput}, ditekan_simpan)."""
    ke = f"{pref}_ent"
    info = {r.label: r for r in cur.itertuples()}
    if ke not in st.session_state:
        st.session_state[f"{pref}_nid"] = 0
        ent = []
        for lb in stok.urut_label(set(awal) | set(info)):
            i = st.session_state[f"{pref}_nid"]
            ent.append([i, lb])
            st.session_state[f"{pref}_n_{i}"] = int(info[lb].jumlah) if lb in info else 0
            st.session_state[f"{pref}_nid"] = i + 1
        st.session_state[ke] = ent
    ent = st.session_state[ke]
    sudah = {x[1] for x in ent}
    opsi = [(t, k) for t, k in _semua_type_pilihan() if t not in sudah]
    kat_dari = dict(opsi)
    W = [1.5, 0.8, 1.2, 0.9]
    hasil, pencet = {}, False
    with st.container(key="ck_tbl"):
        h = st.columns(W)
        for c, tx, al in zip(h, ("TYPE", "STOK AWAL", "DIINPUT KARYAWAN", "TOTAL"), ("left", "right", "left", "right")):
            c.markdown(f"<div class='ck-th' style='text-align:{al}'>{tx}</div>", unsafe_allow_html=True)
        for idb, t in ent:
            r = st.columns(W, vertical_alignment="center")
            nm = t
            kecil = "LABEL" if label.adalah_sni(t) else (label.ket_label(t) or label.kategori_label(t)).upper()
            x = info.get(t)
            if x is None:
                oleh_t = ""
            elif x.foreman:
                oleh_t = f"<span class='fm'>Foreman · {html.escape(x.oleh)} {x.jam}</span>"
            else:
                oleh_t = f"{html.escape(x.oleh)} · {x.jam}"
            r[0].markdown(f"<div class='ck-ty'><small>{kecil}</small><b>{nm}</b><i>{oleh_t}</i></div>", unsafe_allow_html=True)
            aw = int(awal.get(t, 0))
            r[1].markdown(f"<div class='ck-sb'>{aw:,}</div>".replace(",", "."), unsafe_allow_html=True)
            v = r[2].number_input(f"Diinput {t} {idb}", min_value=0, max_value=9999999, step=1, key=f"{pref}_n_{idb}", label_visibility="collapsed")
            v = int(v or 0)
            hasil[t] = v
            r[3].markdown(f"<div class='ck-sb tot'>{aw + v:,}</div>".replace(",", "."), unsafe_allow_html=True)
        # baris kosong: klik untuk menambah type (SNI boleh berdiri sendiri, tanpa type induknya)
        r = st.columns(W, vertical_alignment="center")
        pilih = r[0].selectbox("Tambah type", [t for t, _k in opsi], index=None, key=f"{pref}_add_{st.session_state.get(pref + '_na', 0)}",
                               label_visibility="collapsed", placeholder="＋ tambah type…", format_func=lambda t: f"{kat_dari.get(t, '')} · {t}")
        if pilih:
            ent.append([st.session_state[f"{pref}_nid"], pilih])
            st.session_state[f"{pref}_nid"] += 1
            st.session_state[f"{pref}_na"] = st.session_state.get(f"{pref}_na", 0) + 1
            st.rerun(scope="fragment")
    st.caption("Ubah angka di kolom DIINPUT KARYAWAN (tambah atau kurangi) lalu SIMPAN. Setelah disimpan, pengisinya tercatat sebagai Foreman. "
               "TOTAL = stok awal + yang diinput hari itu.")
    if st.button("SIMPAN", type="primary", width="stretch", key=f"{pref}_simpan"):
        pencet = True
    return hasil, pencet


@st.dialog("CHECK LABEL", width="large", on_dismiss="rerun")
def dlg_check_label():
    kontrol_jendela("inputlabel")
    kepala("label", "CHECK LABEL MEJA")
    st.markdown(label_ui.CSS + CSS_JENDELA + CSS_OPNAME + CSS_CEK, unsafe_allow_html=True)
    if st.session_state.get("ck_toast"):
        st.toast(st.session_state.pop("ck_toast"), icon="✅")
    oleh = akses.pelaku()
    st.caption("Label yang dikeluarkan foreman ke karyawan per meja. Bila karyawan sudah menginput label diterima, riwayatnya muncul di tabel dan bisa dikoreksi di sini.")
    tgl = _tgl_iso(st.date_input("Tanggal", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="ck_tgl"))
    pabrik, meja = label_ui.pilih_meja("ck", "", wajib=True, bawaan=(None, None))
    if not (pabrik and meja):
        st.caption("Pilih pabrik dan nomor meja dulu.")
        return
    ctx = (tgl, pabrik, str(meja))
    if st.session_state.get("ck_ctx") != ctx:
        label_ui._reset("ckf")
        st.session_state["ck_ctx"] = ctx
    cur = stok.meja_cek(tgl, pabrik, meja)
    kemarin = (date.fromisoformat(tgl) - timedelta(days=1)).isoformat()
    awal = stok.stok_meja(pabrik, meja, kemarin)
    if len(cur):
        op = cur[~cur["foreman"]]
        siapa = ", ".join(sorted(set(op["oleh"]))) or "foreman"
        st.markdown(f"<div class='ck-nt'><b>SUDAH DIINPUT</b> pada tanggal ini ({html.escape(siapa)}). "
                    "Bila ada yang salah, ubah jumlahnya di tabel lalu SIMPAN.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='ck-in'>Belum ada label diterima di meja ini pada tanggal ini.</div>", unsafe_allow_html=True)
    hasil, pencet = _baris_cek("ckf", cur, awal)
    if pencet:
        n, galat = stok.meja_cek_simpan(tgl, pabrik, meja, hasil, oleh)
        if galat:
            st.error(galat)
        elif n == 0:
            st.info("Tidak ada perubahan jumlah.")
        else:
            label_ui._reset("ckf")
            st.session_state.pop("ck_ctx", None)
            st.session_state["ck_toast"] = f"Tersimpan: {n} type diperbarui."
            st.rerun(scope="fragment")


def _isi_semua(isi):
    for k, v in isi.items():
        st.session_state[k] = v


def _tab_pindah_stok(oleh):
    """Foreman memindahkan stok label dari satu meja ke meja lain, atau menariknya kembali ke stok Foreman."""
    tgl = _tgl_iso(st.date_input("Tanggal pemindahan", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="pf_tgl"))
    dp, dm = label_ui.pilih_meja("pf_a", "DARI", wajib=True, bawaan=(None, None))
    tuj = st.segmented_control("Tujuan", ["Meja lain", "Stok Foreman"], default="Meja lain", key="pf_tuj", label_visibility="collapsed") or "Meja lain"
    ke = stok.FOREMAN
    if tuj == "Meja lain":
        kp, km = label_ui.pilih_meja("pf_b", "KE", wajib=True, bawaan=(None, None))
        ke = (kp, km) if kp and km else None
    if not (dp and dm):
        st.caption("Pilih meja asal dulu.")
        return
    sis = {lb: n for lb, n in stok.stok_meja(dp, dm, tgl).items() if n > 0}
    if not sis:
        st.info(f"Tidak ada stok label positif di {dp} · Meja {dm} sampai tanggal ini.")
        return
    W = [1.5, 1, 1.2]
    keys = {}
    hasil = []
    with st.container(key="tb_tbl"):
        _kepala_tbl(W, ("TYPE", "STOK DI MEJA", "DIPINDAHKAN"), ("left", "right", "left"))
        for lb in stok.urut_label(sis):
            r = st.columns(W, vertical_alignment="center")
            r[0].markdown(_sel_ty(lb), unsafe_allow_html=True)
            r[1].markdown(f"<div class='tb-n'>{_ang(sis[lb])}</div>", unsafe_allow_html=True)
            k = f"pf_n_{dp}_{dm}_{lb}"
            keys[k] = sis[lb]
            v = r[2].number_input(f"Pindah {lb}", min_value=0, max_value=int(sis[lb]), step=1, value=None, placeholder="0", key=k, label_visibility="collapsed")
            if v:
                hasil.append((lb, int(v)))
    st.button("Pindahkan semua stok", key="pf_semua", on_click=_isi_semua, args=(keys,), width="stretch")
    tujuan_t = "stok Foreman" if ke == stok.FOREMAN else (f"{ke[0]} · Meja {ke[1]}" if ke else "…")
    st.caption(f"Dari {dp} · Meja {dm} ke {tujuan_t}. Pemindahan tercatat atas nama {oleh} dan muncul di rincian stok per tanggal.")
    if st.button("SIMPAN PEMINDAHAN", type="primary", width="stretch", key="pf_simpan", disabled=not hasil or not ke):
        galat = stok.pindah_simpan(tgl, dp, dm, ke, hasil, oleh)
        if galat:
            st.error(galat)
        else:
            for k in keys:
                st.session_state.pop(k, None)
            st.session_state["pf_toast"] = f"{len(hasil)} type dipindahkan ke {tujuan_t}."
            st.rerun(scope="fragment")


def _tampil_dampak(kunci):
    """Tampilkan perubahan stok (sebelum -> sesudah) hasil koreksi terakhir, lalu hapus dari session."""
    dm = st.session_state.pop(kunci, None)
    if dm is None:
        return
    if not dm:
        st.warning("Koreksi tersimpan, tetapi **tidak ada saldo stok yang berubah**. Biasanya karena opname ADJUST di tanggal sesudahnya "
                   "sudah menetapkan stok (menimpa koreksi), atau perubahannya saling meniadakan. Cek tab **Koreksi stok opname**.")
        return
    baris = "".join(f"<tr><td>{stok.lok_nama(lk)}</td><td>{_sel_ty(lb)}</td><td class='n'>{_ang(a)}</td><td class='n'><b>{_ang(b)}</b></td></tr>"
                    for lk, lb, a, b in dm[:30])
    st.success("Stok berubah setelah koreksi:")
    st.markdown("<div class='sx2'><table class='lb'><tr><th>Lokasi</th><th>Type</th><th class='n'>Sebelum</th><th class='n'>Sesudah</th></tr>"
                f"{baris}</table></div>", unsafe_allow_html=True)


def _tab_koreksi_terima(oleh):
    """Perbaiki entri 'label diterima' yang salah ketik oleh karyawan: type, jumlah, meja, atau nama penerima."""
    _tampil_dampak("pk_dampak")
    tgl = _tgl_iso(st.date_input("Tanggal label diterima", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="pk_tgl"))
    d = stok.meja_terima_daftar(tgl=tgl)
    if d.empty:
        st.info("Belum ada label diterima di meja pada tanggal ini.")
        return
    opsi = {r.id: f"{r.pabrik} · Meja {r.meja} · {r.label} · {_ang(r.jumlah)} · {r.nama or r.oleh} ({str(r.waktu)[:5]})" for r in d.itertuples()}
    pil = st.selectbox("Pilih entri yang salah", list(opsi), index=None, format_func=opsi.get, placeholder="Pilih entri label diterima…", key=f"pk_id_{tgl}")
    if not pil:
        st.caption("Pilih entri, lalu ubah type, jumlah, meja, atau karyawan penerimanya.")
        return
    r = d[d["id"] == pil].iloc[0]
    kar = data.baca("karyawan")
    kar = kar[kar["nama_web"].astype(str) != ""] if len(kar) else kar
    nama_opsi = sorted(set(kar["nama_web"].astype(str))) if len(kar) else []
    if r["nama"] and r["nama"] not in nama_opsi:
        nama_opsi.append(r["nama"])
    tipe = stok.semua_label()
    c1, c2 = st.columns(2)
    lb = c1.selectbox("Type", tipe, index=tipe.index(r["label"]) if r["label"] in tipe else None, key=f"pk_l_{pil}")
    jml = c2.number_input("Jumlah (pcs)", min_value=-9999999, max_value=9999999, step=1, value=int(r["jumlah"]), key=f"pk_j_{pil}")
    pab = list(label.PABRIK)
    c3, c4 = st.columns(2)
    pb = c3.selectbox("Pabrik", pab, index=pab.index(r["pabrik"]) if r["pabrik"] in pab else None, key=f"pk_p_{pil}")
    mj_opsi = label.meja_daftar(pb) if pb else []
    mj = c4.selectbox("Meja", mj_opsi, index=mj_opsi.index(str(r["meja"])) if str(r["meja"]) in [str(x) for x in mj_opsi] else None,
                      format_func=lambda m: f"Meja {m}", key=f"pk_m_{pil}_{pb}")
    nm = st.selectbox("Karyawan penerima", nama_opsi, index=nama_opsi.index(r["nama"]) if r["nama"] in nama_opsi else None, key=f"pk_n_{pil}")
    prn = r["prn"]
    if nm and nm != r["nama"] and len(kar):
        x = kar[kar["nama_web"].astype(str) == nm]
        prn = x.iloc[0]["prn"] if len(x) else prn
    st.caption(f"Diinput {r['nama'] or r['oleh']} pukul {str(r['waktu'])[:5]}. Perubahan tercatat di riwayat atas nama {oleh}.")
    try:
        lks = {stok.lok(r["pabrik"], str(r["meja"])), stok.foreman_dept(stok.dept_pabrik(r["pabrik"]))}
        if pb and mj:
            lks |= {stok.lok(pb, str(mj)), stok.foreman_dept(stok.dept_pabrik(pb))}
        tm = stok.timpa_opname(r["tgl"], lks, {r["label"], lb} - {None})
        if tm:
            st.warning("Ada opname ADJUST sesudah tanggal ini yang menetapkan stok: " + "; ".join(
                f"{t[8:]}/{t[5:7]} {stok.lok_nama(lk)} {l2}={_ang(a)}" for t, lk, l2, a in tm[:6]) +
                ". Koreksi ini **tidak mengubah stok sesudah tanggal itu**; sesuaikan angkanya di tab Koreksi stok opname bila perlu.")
    except Exception:
        pass
    b1, b2 = st.columns([2, 1])
    if b1.button("SIMPAN PERUBAHAN", type="primary", width="stretch", key="pk_simpan"):
        sbl = stok._ringkas_saldo()
        galat = stok.meja_terima_koreksi(pil, lb, jml, pb, mj, prn, nm or r["nama"], oleh)
        if galat:
            st.error(galat)
        else:
            st.session_state["pk_dampak"] = stok.selisih_saldo(sbl, stok._ringkas_saldo())
            st.session_state["pf_toast"] = "Entri label diterima diperbaiki."
            st.rerun(scope="fragment")
    sure = b2.checkbox("Yakin hapus", key=f"pk_y_{pil}")
    if b2.button("HAPUS ENTRI", width="stretch", key="pk_hapus", disabled=not sure):
        stok.meja_terima_hapus(pil, oleh)
        st.session_state["pf_toast"] = "Entri dihapus."
        st.rerun(scope="fragment")


def _tab_koreksi_opname(oleh):
    """Ubah jumlah hitung aktual satu type pada opname yang sudah diinput (salah ketik angka)."""
    _tampil_dampak("po_dampak")
    tg = stok.opname_tanggal()
    if not tg:
        st.info("Belum ada hasil stok opname.")
        return
    tgl = st.selectbox("Tanggal opname", tg, format_func=lambda t: f"{t[8:]}/{t[5:7]}/{t[:4]}", key="po_tgl")
    status = stok.opname_status(tgl)
    lks = sorted(status, key=lambda x: (not stok.adalah_foreman(x), x))
    lk = st.selectbox("Lokasi", lks, format_func=stok.lok_nama, key=f"po_lk_{tgl}")
    if not lk:
        return
    baris = stok.opname_baris(tgl, lk)
    st.caption(f"{stok.lok_nama(lk)} · {'sudah di-ADJUST' if status.get(lk) else 'belum di-ADJUST'}. Ubah angka aktual yang salah, lalu simpan.")
    W = [1.5, 1, 1.2]
    ubah = {}
    with st.container(key="tb_tbl"):
        _kepala_tbl(W, ("TYPE", "SAAT ITU", "AKTUAL (PCS)"), ("left", "right", "left"))
        for lb in stok.urut_label(baris):
            a, sx = baris[lb]
            r = st.columns(W, vertical_alignment="center")
            r[0].markdown(_sel_ty(lb), unsafe_allow_html=True)
            r[1].markdown(f"<div class='tb-n'>{_ang(a)}</div>", unsafe_allow_html=True)
            v = r[2].number_input(f"Aktual {lb}", min_value=0, max_value=9999999, step=1, value=int(a), key=f"po_n_{tgl}_{lk}_{lb}", label_visibility="collapsed")
            if int(v) != int(a):
                ubah[lb] = int(v)
    with st.expander("Tambah type yang belum ada di opname ini"):
        tipe = [t for t in stok.semua_label() if t not in baris]
        c1, c2 = st.columns(2)
        lb_b = c1.selectbox("Type", tipe, index=None, placeholder="Pilih type…", key=f"po_tb_{tgl}_{lk}")
        n_b = c2.number_input("Aktual (pcs)", min_value=0, max_value=9999999, step=1, value=0, key=f"po_nb_{tgl}_{lk}")
        if lb_b:
            ubah[lb_b] = int(n_b)
    if ubah:
        st.caption("Akan diubah: " + ", ".join(f"{k} → {_ang(v)}" for k, v in ubah.items()))
    if st.button("SIMPAN KOREKSI OPNAME", type="primary", width="stretch", key="po_simpan", disabled=not ubah):
        sbl = stok._ringkas_saldo()
        galat = stok.opname_koreksi(tgl, lk, ubah, oleh)
        if galat:
            st.error(galat)
        else:
            for lb in list(ubah):
                st.session_state.pop(f"po_n_{tgl}_{lk}_{lb}", None)
            st.session_state["po_dampak"] = stok.selisih_saldo(sbl, stok._ringkas_saldo())
            st.session_state["pf_toast"] = "Jumlah opname dikoreksi."
            st.rerun(scope="fragment")


def _notif_hitung():
    try:
        return stok.notif_stok()
    except Exception:
        return []


def _lapor_hitung():
    try:
        return stok.lapor_buka()
    except Exception:
        return []


def _kartu_lapor(n, oleh):
    """Laporan karyawan: stok meja tidak sama dengan sistem. Foreman cek fisik meja, lalu koreksi stok atau selesai."""
    lk = stok.lok(n["pabrik"], str(n["meja"]))
    sis_kini = int(stok.stok_lokasi(lk).get(n["label"], 0))
    tg = f"{str(n['tgl'])[8:]}/{str(n['tgl'])[5:7]}"
    sel = int(float(n["aktual"] or 0)) - int(float(n["sistem"] or 0))
    k = str(n["id"])
    with st.container(border=True, key=f"lp_{k}"):
        st.markdown(f"**{stok.lok_nama(lk)}** · **{n['label']}** &nbsp; <span style='background:#fff1cf;color:#7a5200;border-radius:999px;padding:2px 10px;font-size:12px;font-weight:800'>Laporan karyawan</span>",
                    unsafe_allow_html=True)
        st.caption(f"{tg} · dilaporkan {n['nama'] or n['prn']}")
        c = st.columns(3)
        c[0].metric("Menurut sistem (saat lapor)", _ang(n["sistem"]))
        c[1].metric("Yang ada (kata karyawan)", _ang(n["aktual"]))
        c[2].metric("Selisih", _ang(sel))
        if n["catatan"]:
            st.caption(f"Catatan: {n['catatan']}")
        st.caption(f"Stok sistem sekarang: **{_ang(sis_kini)}**. Cek fisik meja, isi jumlah yang benar, lalu koreksi.")
        jml = st.number_input("Jumlah sebenarnya di meja (pcs)", min_value=0, max_value=9999999, step=1, value=int(float(n["aktual"] or 0)), key=f"lpj_{k}")
        b = st.columns(2)
        if b[0].button("KOREKSI STOK", type="primary", key=f"lpk_{k}", width="stretch",
                       help="Stok meja disamakan dengan jumlah di atas (dicatat sebagai hitung opname + ADJUST hari ini)."):
            g = stok.lapor_selesai(k, oleh, aktual=jml)
            if g:
                st.error(g)
            else:
                st.session_state["pf_toast"] = "Stok dikoreksi."
                st.rerun(scope="fragment")
        if b[1].button("SELESAI (TANPA KOREKSI)", key=f"lps_{k}", width="stretch"):
            stok.lapor_selesai(k, oleh)
            st.rerun(scope="fragment")


def _kartu_notif(n, oleh):
    p, m = n["lokasi"].split("|", 1)
    tg = f"{n['tgl'][8:]}/{n['tgl'][5:7]}"
    k = n["id"].replace(" ", "_")
    with st.container(border=True, key=f"nt_{k}"):
        if n["jenis"] == "ambil_meja":
            st.markdown(f"**{tg} · {n['nama']}** memakai lebih dari stok **{n['label']}** di {p} · Meja {m} (**kurang {_ang(n['kurang'])} pcs**). "
                        f" Label itu ada di meja lain, kemungkinan **diambil tanpa Pindah Label**.")
            opsi = [a for a, _s in n["sumber"]]
            ss = dict(n["sumber"])
            asal = st.selectbox("Diambil dari meja", opsi, format_func=lambda a: f"{stok.lok_nama(a)} (stok {_ang(ss[a])})", key=f"nta_{k}")
            mx = int(ss.get(asal, n["kurang"]))
            jml = st.number_input("Jumlah dipindah ke meja ini (pcs)", min_value=1, max_value=max(mx, 1), step=1, value=min(n["kurang"], max(mx, 1)),
                                  key=f"ntj_{k}", help="Yang terpakai dipotong; sisanya tetap di meja ini.")
            st.caption("SETUJUI = label dianggap pindah dari meja asal ke meja ini, terpakai, sisanya ikut di meja ini.")
        else:
            st.markdown(f"**{tg} · {n['nama']}** memakai lebih dari stok **{n['label']}** di {p} · Meja {m} (**kurang {_ang(n['kurang'])} pcs**), dan tidak ada meja lain yang punya stoknya. "
                        f" Kemungkinan **diambil dari Foreman** tanpa tercatat (stok Foreman saat ini {_ang(n['foreman'])}).")
            asal = None
            jml = st.number_input("Jumlah diterima dari Foreman (pcs)", min_value=1, max_value=9999999, step=1, value=int(n["kurang"]), key=f"ntj_{k}",
                                  help="Isi lebih besar bila Foreman memberi lebih dari yang terpakai; sisanya tetap di meja ini.")
            st.caption("SETUJUI = stok Foreman terdistribusi ke meja ini sebanyak jumlah di atas.")
        c = st.columns(2)
        if c[0].button("SETUJUI", type="primary", key=f"nts_{k}", width="stretch"):
            g = stok.notif_setujui(n, jml, asal, oleh)
            if g:
                st.error(g)
            else:
                st.session_state["pf_toast"] = "Disetujui dan dicatat."
                st.rerun(scope="fragment")
        if c[1].button("ABAIKAN", key=f"nti_{k}", width="stretch"):
            stok.notif_putuskan(n["id"], "abaikan", oleh)
            st.rerun(scope="fragment")


@st.dialog("NOTIFIKASI STOK LABEL", width="large")
def dlg_notif_stok():
    kontrol_jendela("inputlabel")
    kepala("label", "NOTIFIKASI STOK LABEL")
    st.markdown(label_ui.CSS + CSS_JENDELA + CSS_TBL, unsafe_allow_html=True)
    if st.session_state.get("pf_toast"):
        st.toast(st.session_state.pop("pf_toast"), icon="✅")
    oleh = akses.pelaku()
    lapor = _lapor_hitung()
    if lapor:
        st.markdown(f"**LAPORAN KARYAWAN ({len(lapor)})**")
        st.caption("Karyawan melihat stok meja di sistem tidak sama dengan label yang ada. Cek meja itu, lalu koreksi bila memang berbeda.")
        for n in lapor[:25]:
            _kartu_lapor(n, oleh)
    daftar = _notif_hitung()
    if not daftar:
        if not lapor:
            st.success("Tidak ada notifikasi stok yang perlu ditinjau. ✅")
        return
    if lapor:
        st.markdown("---")
        st.markdown(f"**STOK MINUS ({len(daftar)})**")
    st.caption(f"{len(daftar)} pemakaian label melebihi stok meja. Setujui bila memang label berpindah, atau abaikan bila bukan. "
               "Setiap persetujuan tercatat sebagai pemindahan / label diterima atas nama Anda.")
    daftar = sorted(daftar, key=lambda n: n["tgl"], reverse=True)
    for n in daftar[:25]:
        _kartu_notif(n, oleh)
    if len(daftar) > 25:
        st.caption(f"+{len(daftar) - 25} notifikasi lebih lama ditampilkan setelah yang di atas diselesaikan.")


@st.dialog("PERBAIKAN DATA LABEL", width="large")
def dlg_perbaikan():
    kontrol_jendela("inputlabel")
    kepala("label", "PERBAIKAN DATA LABEL")
    st.markdown(label_ui.CSS + CSS_JENDELA + CSS_TBL, unsafe_allow_html=True)
    if st.session_state.get("pf_toast"):
        st.toast(st.session_state.pop("pf_toast"), icon="✅")
    oleh = akses.pelaku()
    mode = st.segmented_control("Perbaikan", ["Pindah / tarik stok meja", "Koreksi label diterima", "Koreksi stok opname"], default="Pindah / tarik stok meja",
                                key="pf_mode", label_visibility="collapsed") or "Pindah / tarik stok meja"
    if mode.startswith("Pindah"):
        st.caption("Pindahkan stok label dari satu meja ke meja berikutnya, atau tarik kembali ke stok Foreman.")
        _tab_pindah_stok(oleh)
    elif mode.startswith("Koreksi label"):
        st.caption("Karyawan salah ketik type, jumlah, atau memilih meja yang keliru? Perbaiki entri label diterimanya di sini.")
        _tab_koreksi_terima(oleh)
    else:
        st.caption("Salah mengisi jumlah hitung aktual di stok opname? Ubah jumlah type tertentu di sini.")
        _tab_koreksi_opname(oleh)


def _hub():
    """Roda gigi bergaya Jarvis (komponen yang sama dengan halaman admin): ikon menu mengitari roda, sinar menunjuk menu aktif."""
    try:
        t_op = stok.opname_tanggal()
        t_op = t_op[0] if t_op else None
    except Exception:
        t_op = None
    n_nt = len(_notif_hitung()) + len(_lapor_hitung())
    ket_nt = f"{n_nt} perlu ditinjau" if n_nt else "Tidak ada"
    ket_op = f"Opname terakhir: {t_op[8:10]}/{t_op[5:7]}/{t_op[:4]}" if t_op else "Belum ada opname"
    MENU = {"afkir": ("INPUT LABEL AFKIR", "Catat label kotor per karyawan, pabrik, dan meja", "tag", _buka_jendela, "Fungsi", "Input harian"),
            "bagus": ("INPUT LABEL BAGUS", "Catat label bagus yang diterima foreman", "box", dlg_label_bagus, "Fungsi", "Barang masuk"),
            "distribusi": ("DISTRIBUSI LABEL", "Pinjam atau pindahkan label antar foreman QC dan SK", "swap", dlg_distribusi, "Fungsi", "QC ⇄ SK"),
            "check": ("CHECK LABEL", "Label keluar ke karyawan per meja, cek stok meja", "check", dlg_check_label, "Fungsi", "Per meja"),
            "opname": ("STOK OPNAME LABEL", "Hitung fisik label per lokasi, pabrik, dan meja", "calc", dlg_opname, "Status", ket_op),
            "selisih": ("SELISIH STOK OPNAME", "Bandingkan stok sistem dengan hitungan fisik, lalu ADJUST", "bars", dlg_selisih, "Status", ket_op),
            "notif": ("NOTIFIKASI STOK", "Stok minus dan laporan karyawan: setujui, cek meja, koreksi", "bell", dlg_notif_stok, "Notifikasi", ket_nt),
            "perbaikan": ("PERBAIKAN DATA", "Pindah stok antar meja, koreksi label diterima, koreksi stok opname", "wrench", dlg_perbaikan, "Fungsi", "Koreksi"),
            "operator": ("DAFTAR OPERATOR", "Daftarkan operator untuk Input Label Afkir", "user", dlg_operator, "Fungsi", "Akun operator")}
    daftar = [{"id": k, "label": v[0], "sub": v[1], "icon": v[2], "status_label": v[4], "status": v[5], "disabled": False}
              for k, v in MENU.items()]
    klik = roda(daftar, start=st.session_state.get("rf_id"), key="roda_f", judul1="UPLOAD", judul2="FOREMAN", hud=True)
    if klik and klik.get("n") != st.session_state.get("rf_n"):
        st.session_state["rf_n"] = klik.get("n")
        st.session_state["rf_id"] = klik["id"]
        if klik["id"] == "operator":
            st.session_state.pop("op_daftar", None)
        if klik["id"] == "opname":
            st.session_state.pop("op_konf", None)
        MENU[klik["id"]][3]()


def tampil(halaman_admin=None):
    akses.butuh(akses.ADMIN, akses.FOREMAN)
    st.markdown(CSS, unsafe_allow_html=True)
    gaya_global()
    gaya_responsif()
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
    nt = _notif_hitung()
    lp = _lapor_hitung()
    if nt or lp:
        with st.container(border=True):
            c = st.columns([4, 1.4], vertical_alignment="center")
            ket_ = []
            if nt:
                ket_.append(f"**{len(nt)} stok label minus** (pemakaian melebihi stok meja)")
            if lp:
                ket_.append(f"**{len(lp)} laporan karyawan** (stok meja tidak sesuai)")
            c[0].markdown("⚠️ " + " dan ".join(ket_) + " — perlu ditinjau Foreman.")
            c[1].button("Tinjau", key="nt_buka", type="primary", width="stretch", on_click=dlg_notif_stok)
    st.write("")
    a, b, c = st.columns([2, 2, 1], vertical_alignment="center")
    tgl = a.date_input("Tanggal", key="pg_tgl", format="DD/MM/YYYY")
    shift = b.segmented_control("Shift", label.SHIFT, key="pg_shift", label_visibility="collapsed") or "Pagi"
    c.button("↻ Segarkan", key="pg_segar", on_click=lambda: data._tembolok().clear())
    tgl_s = _tgl_iso(tgl)
    _notifikasi(tgl_s, shift)
    st.write("")
    _tabel(tgl_s, shift)
