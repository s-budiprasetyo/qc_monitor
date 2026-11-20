"""Halaman Upload Foreman: jendela INPUT LABEL AFKIR (input label afkir), notifikasi meja yang belum dicek,
tabel input hari ini (ubah/hapus)."""
from datetime import date

import pandas as pd
import streamlit as st

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
.st-key-btn_inputlabel button,.st-key-btn_inputstok button,.st-key-btn_selisih button{background:#e8f3ff;border:1px solid #9fd0fb;color:#0b3d91;font-weight:800;
  padding:.9rem 1.4rem;border-radius:12px;min-height:0;height:auto}
.st-key-btn_kosong button,.st-key-btn_operator button{background:#e8f3ff;border:1px solid #9fd0fb;color:#0b3d91;font-weight:800;
  padding:.9rem 1.4rem;border-radius:12px;min-height:0;height:auto}
@media (max-width:640px){.st-key-btn_label,.st-key-btn_kosong,.st-key-btn_operator,.st-key-btn_inputlabel,.st-key-btn_inputstok,.st-key-btn_selisih{width:100%}}
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
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']{position:absolute !important;top:40px;right:24px;z-index:30;width:34px;height:34px;border-radius:50%;
  color:#fff !important;background:rgba(255,255,255,.28) !important;border:2px solid #fff !important;display:flex;align-items:center;justify-content:center;padding:0}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']:hover{background:#d93025 !important;border-color:#fff !important}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close'] svg{width:20px;height:20px;stroke:#fff;stroke-width:2.5px;fill:#fff;color:#fff !important}
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
    st.markdown(CSS_JENDELA, unsafe_allow_html=True)
    st.html(JS_PILIH, unsafe_allow_javascript=True)
    st.markdown("<div class='lb-kepala'><b>INPUT LABEL AFKIR</b><div>Input label afkir</div></div>", unsafe_allow_html=True)
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
        st.session_state["w_cols"] = [t for t in muat["kolom"] if not t.startswith(label.SNI + " ")]
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
    posting = label.tanggal_posting(prn, _tgl_iso(tgl), shift) if prn else ""
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
                sni = t.startswith(label.SNI + " ")
                if sni:
                    kecil, besar = "SNI · PENDAMPING", t[len(label.SNI) + 1:]
                else:
                    kecil, besar = (label.ket_label(t) or label.kategori_label(t)).upper(), t
                st.markdown(f"<div class='lb-th{' lb-sni' if sni else ''}'><small>{kecil}</small><b>{besar}</b></div>",
                            unsafe_allow_html=True)
                if not sni and not (t == "CE7" and any(label.ket_label(x) for x in induk)):
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
                        induk_t = t[len(label.SNI) + 1:] if t.startswith(label.SNI + " ") else t
                        st.session_state[f"w_n_{t}_proses"] = (sap.get(induk_t, 0) if laporan.proses_berlaku(t) else 0) or None
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


def _tab_terima(oleh):
    """Label diterima dari packing = menambah stok QC."""
    tgl = st.date_input("Tanggal diterima", value=label.hari_ini(), format="DD/MM/YYYY", key="il_tgl_t")
    st.caption("Pilih label lalu isi jumlah (pcs). Contoh: CE7 7000. Tambah baris dengan klik baris kosong paling bawah.")
    ed = st.data_editor(
        pd.DataFrame({"Label": pd.Series([], dtype="object"), "Jumlah": pd.Series([], dtype="float")}),
        num_rows="dynamic", hide_index=True, width="stretch", key="il_ed_t",
        column_config={"Label": st.column_config.SelectboxColumn("Label", options=stok.semua_label(), required=True),
                       "Jumlah": st.column_config.NumberColumn("Jumlah (pcs)", min_value=1, max_value=999999, step=1, format="%d")})
    pilih = [(r["Label"], _num(r["Jumlah"])) for _, r in ed.iterrows() if r["Label"] and _num(r["Jumlah"]) > 0]
    if st.button("SIMPAN LABEL DITERIMA", type="primary", width="stretch", key="il_simpan_t", disabled=not pilih):
        with st.spinner("Menyimpan…"):
            n = stok.terima_simpan(_tgl_iso(tgl), pilih, oleh)
        st.session_state["il_toast"] = f"{n} penerimaan label tersimpan."
        st.session_state.pop("il_ed_t", None)
        st.rerun(scope="fragment")
    riwayat = stok.terima_daftar(label.hari_ini().strftime("%Y-%m"))
    st.markdown("**Penerimaan bulan ini**")
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
    return "Foreman" if lk == stok.FOREMAN else label.nama_meja(*lk.split("|", 1))


def _tabel_isian(kunci, awal):
    """Tabel type + jumlah (hitungan fisik). awal = {label: jumlah} yang sudah tersimpan."""
    df = pd.DataFrame({"Type": list(awal), "Jumlah": [float(v) for v in awal.values()]}) if awal else \
        pd.DataFrame({"Type": pd.Series([], dtype="object"), "Jumlah": pd.Series([], dtype="float")})
    ed = st.data_editor(
        df, num_rows="dynamic", hide_index=True, width="stretch", key=kunci,
        column_config={"Type": st.column_config.SelectboxColumn("Type label", options=stok.semua_label(), required=True),
                       "Jumlah": st.column_config.NumberColumn("Jumlah hitungan fisik (pcs)", min_value=0, max_value=9999999, step=1, format="%d")})
    out = {}
    for _, r in ed.iterrows():
        if r["Type"] and r["Jumlah"] == r["Jumlah"]:
            out[r["Type"]] = out.get(r["Type"], 0) + _num(r["Jumlah"])
    return out


def _opname_foreman(tgl, oleh):
    ada = stok.opname_baris(tgl, stok.FOREMAN)
    st.caption("Hitung label di gudang foreman. Type yang tidak diisi dianggap 0. Simpan ulang pada tanggal yang sama = menimpa hitungan sebelumnya.")
    isi = _tabel_isian(f"op_ed_f_{tgl}", {lb: a for lb, (a, _s) in ada.items()})
    if st.button("SIMPAN HITUNGAN FOREMAN", type="primary", width="stretch", key="op_simpan_f"):
        with st.spinner("Menyimpan…"):
            stok.opname_simpan(tgl, stok.FOREMAN, isi, oleh)
        st.session_state["il_toast"] = "Hitungan Foreman tersimpan."
        st.session_state.pop(f"op_ed_f_{tgl}", None)
        st.rerun(scope="fragment")
    if stok.FOREMAN in stok.opname_status(tgl):
        st.success("Hitungan Foreman pada tanggal ini sudah tersimpan.")


def _opname_meja(tgl, oleh):
    sl = stok.opname_status(tgl)
    nxt = st.session_state.pop("op_next", None)
    if nxt:
        st.session_state["opm_pab"] = nxt[0]
        st.session_state[f"opm_mej_{nxt[0]}"] = nxt[1]
    pabrik, meja = label_ui.pilih_meja("opm", "", wajib=True, bawaan=(None, None))
    if pabrik and meja:
        lk = stok.lok(pabrik, str(meja))
        ada = stok.opname_baris(tgl, lk)
        isi = _tabel_isian(f"op_ed_m_{tgl}_{lk}", {lb: a for lb, (a, _s) in ada.items()})
        c1, c2 = st.columns([2, 1])

        def _lanjut():
            n = str(int(meja) + 1) if str(meja).isdigit() and int(meja) < label.PABRIK[pabrik] else str(meja)
            st.session_state["op_next"] = (pabrik, n)
            st.session_state["il_toast"] = f"Hitungan {label.nama_meja(pabrik, meja)} tersimpan."
        if c1.button(f"SIMPAN MEJA {meja}", type="primary", width="stretch", key="op_simpan_m", disabled=not isi):
            stok.opname_simpan(tgl, lk, isi, oleh)
            st.session_state.pop(f"op_ed_m_{tgl}_{lk}", None)
            _lanjut()
            st.rerun(scope="fragment")
        if c2.button("MEJA KOSONG", width="stretch", key="op_kosong_m", help="Tidak ada label di meja ini: dicatat sudah dihitung (0)"):
            stok.opname_simpan(tgl, lk, {}, oleh)
            st.session_state.pop(f"op_ed_m_{tgl}_{lk}", None)
            _lanjut()
            st.rerun(scope="fragment")
        if lk in sl:
            st.success(f"{label.nama_meja(pabrik, meja)} sudah dihitung pada tanggal ini (boleh disimpan ulang).")
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
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    tgl = _tgl_iso(st.date_input("Tanggal opname (stok akhir hari)", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="op_tgl"))
    oleh = akses.pelaku()
    t1, t2 = st.tabs(["1 · STOK FOREMAN", "2 · STOK PER MEJA"])
    with t1:
        _opname_foreman(tgl, oleh)
    with t2:
        _opname_meja(tgl, oleh)
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
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


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
    c1, c2 = st.columns([1, 2], vertical_alignment="bottom")
    tgl = c1.selectbox("Opname tanggal", tanggal, key="sl_tgl", format_func=label_ui.tgl_id)
    lihat = c2.segmented_control("Lihat", ["Total per type", "Foreman", "Per meja"], default="Total per type", key="sl_lihat", label_visibility="collapsed") or "Total per type"
    status = stok.opname_status(tgl)
    lokasi = None
    if lihat == "Foreman":
        lokasi = stok.FOREMAN
    elif lihat == "Per meja":
        meja_ada = [lk for lk in status if lk != stok.FOREMAN]
        lokasi = st.selectbox("Meja yang sudah dihitung", meja_ada, index=None, placeholder="Pilih meja…", key="sl_lok", format_func=_lok_ringkas)
    kolom = [1.6, 1.4, 1.6, 1.2]
    if lihat == "Total per type":
        sis, akt = {}, {}
        for lk in status:
            for lb, (a, sx) in stok.opname_baris(tgl, lk).items():
                sis[lb] = sis.get(lb, 0) + sx
                akt[lb] = akt.get(lb, 0) + a
        k = st.columns(kolom)
        for c, t in zip(k, ["TYPE", "SISTEM", "AKTUAL", "SELISIH"]):
            c.markdown(f"<div class='kt'>{t}</div>", unsafe_allow_html=True)
        for lb in stok.urut_label(sis):
            c = st.columns(kolom, vertical_alignment="center")
            c[0].markdown(f"**{lb}**")
            c[1].write(f"{sis[lb]:,}".replace(",", "."))
            c[2].write(f"{akt[lb]:,}".replace(",", "."))
            c[3].markdown(_selisih_angka(akt[lb] - sis[lb]), unsafe_allow_html=True)
        st.caption("Gabungan semua lokasi (Foreman + meja) yang sudah dihitung pada tanggal ini.")
    elif lokasi:
        if lokasi not in status:
            st.info("Lokasi ini belum dihitung pada tanggal tersebut.")
        else:
            h = stok.opname_baris(tgl, lokasi)
            if not h:
                st.success("Lokasi ini dicatat kosong (0).")
            k = st.columns(kolom)
            for c, t in zip(k, ["TYPE", "SISTEM", "AKTUAL (bisa diedit)", "SELISIH"]):
                c.markdown(f"<div class='kt'>{t}</div>", unsafe_allow_html=True)
            nilai = {}
            for lb in stok.urut_label(h):
                a, sx = h[lb]
                c = st.columns(kolom, vertical_alignment="center")
                c[0].markdown(f"**{lb}**")
                c[1].write(f"{sx:,}".replace(",", "."))
                nilai[lb] = int(c[2].number_input(f"Aktual {lb}", min_value=0, max_value=9999999, step=1, value=int(a), key=f"sl_a_{tgl}_{lokasi}_{lb}", label_visibility="collapsed"))
                c[3].markdown(_selisih_angka(nilai[lb] - sx), unsafe_allow_html=True)
            if st.button("SIMPAN PERUBAHAN AKTUAL", width="stretch", key="sl_simpan", disabled=not h):
                stok.opname_simpan(tgl, lokasi, nilai, oleh)
                st.session_state["il_toast"] = "Perubahan stok aktual tersimpan."
                st.rerun(scope="fragment")
    else:
        st.caption("Pilih meja yang ingin dilihat.")
    belum = [lk for lk, sdh in status.items() if not sdh]
    st.download_button("⬇ UNDUH EXCEL", _excel_selisih(tgl, status), file_name=f"selisih_opname_{tgl}.xlsx", width="stretch", key="sl_xls")
    st.markdown("---")
    st.markdown(f"**ADJUST** — jadikan stok aktual sebagai stok awal periode berikutnya  \n"
                f"<span class='ls-nt'>{len(status)} lokasi dihitung pada tanggal ini, {len(belum)} belum di-adjust. "
                "Stok sistem lokasi itu diganti angka aktual mulai tanggal opname; pemakaian dihitung lagi dari hari berikutnya. "
                "Lokasi yang tidak dihitung tidak berubah.</span>", unsafe_allow_html=True)
    ya = st.checkbox("Saya yakin, pakai stok aktual sebagai stok awal", key="sl_ya", disabled=not belum)
    with st.container(key="il_adj"):
        if st.button("ADJUST: PAKAI STOK AKTUAL SEBAGAI STOK AWAL", type="primary", width="stretch", key="sl_adj", disabled=not (belum and ya)):
            with st.spinner("Menyesuaikan stok…"):
                n = stok.opname_adjust(tgl, oleh, belum)
            st.session_state["il_toast"] = f"{n} lokasi di-adjust: stok aktual jadi stok awal."
            st.session_state.pop("sl_ya", None)
            st.rerun(scope="fragment")


@st.dialog("KOSONGKAN LABEL MEJA", width="small", on_dismiss="rerun")
def dlg_kosong():
    kontrol_jendela("kosong")
    kepala("label", "KOSONGKAN LABEL MEJA")
    st.caption("Semua stok label di meja pada pabrik yang dipilih menjadi 0 (mulai tanggal yang dipilih). Stok Foreman tidak berubah. "
               "Dipakai sebelum hitung stok per meja.")
    tgl = st.date_input("Mulai tanggal", value=label.hari_ini(), max_value=label.hari_ini(), format="DD/MM/YYYY", key="ks_tgl")
    pab = st.segmented_control("Pabrik", list(label.PABRIK), key="ks_pab", label_visibility="collapsed")
    ya = st.checkbox("Saya yakin, stok semua meja di pabrik ini dijadikan 0", key="ks_ya", disabled=not pab)
    if st.button("KOSONGKAN", type="primary", width="stretch", key="ks_ok", disabled=not (pab and ya)):
        galat = stok.kosongkan(_tgl_iso(tgl), pab, akses.pelaku())
        if galat:
            st.error(galat)
        else:
            st.session_state["pg_toast"] = f"Stok semua meja {pab} dikosongkan."
            for k_ in ("ks_pab", "ks_ya"):
                st.session_state.pop(k_, None)
            st.rerun()


@st.dialog("INPUT LABEL BAGUS", width="large", on_dismiss="rerun")
def dlg_label_bagus():
    kontrol_jendela("inputlabel")
    kepala("label", "INPUT LABEL BAGUS")
    if st.session_state.get("il_toast"):
        st.toast(st.session_state.pop("il_toast"), icon="✅")
    _tab_terima(akses.pelaku())


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
                if st.button("🏷  INPUT LABEL AFKIR"):
                    _buka_jendela()
            with st.container(key="btn_inputlabel"):
                if st.button("📦  INPUT LABEL BAGUS"):
                    dlg_label_bagus()
            with st.container(key="btn_inputstok"):
                if st.button("🧮  STOK OPNAME LABEL"):
                    dlg_opname()
            with st.container(key="btn_selisih"):
                if st.button("📊  SELISIH STOK OPNAME"):
                    dlg_selisih()
            with st.container(key="btn_kosong"):
                if st.button("🧹  KOSONGKAN LABEL MEJA"):
                    for k_ in ("ks_pab", "ks_ya"):
                        st.session_state.pop(k_, None)
                    dlg_kosong()
            with st.container(key="btn_operator"):
                if st.button("👥  DAFTAR OPERATOR"):
                    st.session_state.pop("op_daftar", None)
                    dlg_operator()


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
    st.write("")
    a, b, c = st.columns([2, 2, 1], vertical_alignment="center")
    tgl = a.date_input("Tanggal", key="pg_tgl", format="DD/MM/YYYY")
    shift = b.segmented_control("Shift", label.SHIFT, key="pg_shift", label_visibility="collapsed") or "Pagi"
    c.button("↻ Segarkan", key="pg_segar", on_click=lambda: data._tembolok().clear())
    tgl_s = _tgl_iso(tgl)
    _notifikasi(tgl_s, shift)
    st.write("")
    _tabel(tgl_s, shift)
