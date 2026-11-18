"""Login berperan (admin / foreman) dan bilah atas: tombol kecil pindah halaman, nama pengguna, Keluar.

Admin  : user dan password di Secrets [admin] (dan akun Google terdaftar bila [auth] aktif).
Foreman: user dan password karyawan (tabel karyawan) yang jenisnya FOREMAN.
Daftar halaman dibuat menurut peran (lihat app_admin.py): foreman tidak punya halaman admin sama sekali."""
import hmac

import streamlit as st

from core import data, parsers

ADMIN, FOREMAN = "admin", "foreman"
MAKS_GAGAL = 5

CSS_BAR = """
<style>
.st-key-sw a,.st-key-sw2 a{border:1.5px solid #1a73e8;border-radius:999px;background:#fff;color:#1a73e8 !important;font-weight:700;
  padding:.3rem .9rem;font-size:13px;text-decoration:none;display:inline-flex;gap:.4rem;align-items:center;white-space:nowrap}
.st-key-sw a:hover,.st-key-sw2 a:hover{background:#e8f0fe}
.st-key-sw a p,.st-key-sw2 a p{font-size:13px;margin:0}
.kip{background:#fff;border:1px solid #d4e1f5;border-radius:999px;padding:.38rem .9rem;font-size:13px;color:#44628f;
  font-weight:700;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}
.kip b{color:#0b3d91}
.st-key-kl button{border-radius:999px;padding:.2rem .8rem;min-height:0;height:auto;font-size:13px;border-color:#c9d1dd;color:#5b6678}
@media (max-width:640px){
  .st-key-bar [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.35rem !important}
  .st-key-bar [data-testid="stColumn"]{min-width:0 !important;width:auto !important;flex:0 0 auto !important}
  .st-key-bar [data-testid="stColumn"]:first-child{flex:1 1 auto !important}
  .st-key-sw a p,.st-key-sw2 a p{display:none}
  .kip{display:none}
}
</style>
"""


def peran():
    return st.session_state.get("peran")


def keluar():
    for k in ("peran", "admin_ok", "nama_masuk", "prn_masuk", "gagal_masuk"):
        st.session_state.pop(k, None)


def butuh(*boleh):
    """Pagar tiap halaman: berhenti bila peran tidak termasuk yang diizinkan."""
    if peran() not in boleh:
        st.error("Halaman ini tidak tersedia untuk akun Anda.")
        st.stop()


def _rahasia_admin():
    try:
        return st.secrets.get("admin")
    except Exception:  # file secrets belum ada
        return None


def cek_login(user, password, adm, karyawan):
    """Return (peran, nama, prn) atau None. Murni (tanpa st) supaya mudah diuji."""
    u = (user or "").strip()
    if not u or not password:
        return None
    if adm and hmac.compare_digest(u.encode(), str(adm["user"]).encode()) \
            and hmac.compare_digest(password.encode(), str(adm["password"]).encode()):
        return ADMIN, str(adm["user"]), ""
    k = karyawan[karyawan["user"].str.strip().str.upper() == u.upper()]
    k = k[k["jenis"].str.strip().str.upper() == "FOREMAN"]
    if len(k) and hmac.compare_digest(parsers.hash_pw(password), str(k.iloc[0]["pass_hash"])):
        return FOREMAN, str(k.iloc[0]["nama_web"]), str(k.iloc[0]["prn"])
    return None


def _google_ok(adm):
    """Bila login Google aktif, admin wajib memakai akun yang terdaftar."""
    if "auth" not in st.secrets:
        return True
    try:
        return bool(st.user.is_logged_in) and st.user.email.lower() in [e.lower() for e in adm.get("emails", [])]
    except Exception:
        return False


def gerbang():
    """Tampilkan login bila belum masuk, lalu st.stop(). Setelah lolos, peran() terisi."""
    adm = _rahasia_admin()
    if not adm:
        st.error("Pengaturan [admin] belum ada di secrets. Aplikasi dikunci.")
        st.stop()
    if peran() == ADMIN and not _google_ok(adm):
        st.markdown("<h1 style='text-align:center'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)
        if not st.user.is_logged_in:
            st.info("Langkah 2: verifikasi akun Google admin.")
            st.button("Masuk dengan Google", on_click=st.login, type="primary")
        else:
            st.error("Akun Google ini tidak punya akses admin.")
            st.button("Keluar Google", on_click=st.logout)
        st.stop()
    if peran():
        return
    st.markdown("<h1 style='text-align:center;font-weight:800'>QC TOTO</h1>"
                "<p style='text-align:center;color:#5b7399'>Masuk sebagai admin atau foreman</p>", unsafe_allow_html=True)
    _, tengah, _ = st.columns([1, 1.2, 1])
    with tengah, st.form("login"):
        u = st.text_input("User")
        p = st.text_input("Password", type="password")
        ok = st.form_submit_button("Masuk", type="primary", width="stretch")
    if ok:
        if st.session_state.get("gagal_masuk", 0) >= MAKS_GAGAL:
            tengah.error("Terlalu banyak percobaan salah. Muat ulang halaman untuk mencoba lagi.")
            st.stop()
        hasil = cek_login(u, p, adm, data.baca("karyawan"))
        if hasil:
            st.session_state.update({"peran": hasil[0], "nama_masuk": hasil[1], "prn_masuk": hasil[2], "gagal_masuk": 0,
                                     "admin_ok": hasil[0] == ADMIN})
            st.rerun()
        st.session_state["gagal_masuk"] = st.session_state.get("gagal_masuk", 0) + 1
        tengah.error("User atau password salah.")
    st.stop()


def _rahasia(kunci):
    try:
        return str(st.secrets.get(kunci, "") or "").strip().rstrip("/")
    except Exception:
        return ""


def tautan_luar(app):
    """Tombol pindah antar aplikasi menurut peran. app = 'admin' | 'laporan'.
    Alamat app lain dibaca dari Secrets: url_admin, url_laporan (kosong = tombol tidak muncul)."""
    if app == "laporan":
        u = _rahasia("url_admin")
        if not u:
            return []
        return [("Ke Upload Admin", u + "/upload-admin")] if peran() == ADMIN else [("Ke Upload Foreman", u + "/upload-foreman")]
    u = _rahasia("url_laporan")
    return [("Laporan", u)] if u else []


def bilah(halaman_lain=None, label_lain="", tautan=None):
    """Baris kecil di kanan atas: [pindah halaman (hanya admin)] [nama · peran] [Keluar]."""
    st.markdown(CSS_BAR, unsafe_allow_html=True)
    nama = st.session_state.get("nama_masuk", "")
    with st.container(key="bar"):
        c = st.columns([4, 2.7, 4.2, 1.3], vertical_alignment="center")
        with c[0], st.container(key="sw2"):
            for i, (lb, url) in enumerate(tautan if tautan is not None else tautan_luar("admin")):
                st.link_button(lb, url, icon=":material/bar_chart:" if lb == "Laporan" else ":material/swap_horiz:", key=f"lk_{i}")
        with c[1], st.container(key="sw"):
            if halaman_lain is not None and peran() == ADMIN:
                st.page_link(halaman_lain, label=label_lain, icon=":material/swap_horiz:")
        c[2].markdown(f"<div class='kip'><b>{nama}</b> · {'Admin' if peran() == ADMIN else 'Foreman'}</div>", unsafe_allow_html=True)
        with c[3], st.container(key="kl"):
            if st.button("Keluar", key="btn_keluar"):
                keluar()
                st.rerun()
