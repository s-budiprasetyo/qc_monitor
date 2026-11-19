"""Login berperan (admin / foreman) dan bilah atas: tombol kecil pindah halaman, nama pengguna, Keluar.

Admin  : user dan password di Secrets [admin] (dan akun Google terdaftar bila [auth] aktif).
Foreman: user dan password karyawan (tabel karyawan) yang jenisnya FOREMAN.
Daftar halaman dibuat menurut peran (lihat app_admin.py): foreman tidak punya halaman admin sama sekali."""
import base64
import hashlib
import hmac
import json
import time

import streamlit as st

from core import data, parsers

ADMIN, FOREMAN = "admin", "foreman"
MAKS_GAGAL = 5

CSS_BAR = """
<style>
.st-key-bar{background:#fff;border:1px solid #d6e4f8;border-radius:16px;padding:.5rem .8rem;box-shadow:0 2px 12px #2a5db014;margin-bottom:.4rem}
.st-key-bar [data-testid="stColumn"]{min-width:0}
.st-key-bar a{display:flex !important;align-items:center;justify-content:center;gap:.45rem;border:1px solid #cfe0f7 !important;
  border-radius:12px !important;background:#eef5ff !important;color:#1a5fc8 !important;font-weight:700;padding:.5rem .6rem !important;
  font-size:13px;text-decoration:none;white-space:nowrap;min-height:0 !important;transition:background .15s,box-shadow .15s}
.st-key-bar a:hover{background:#dcebff !important;box-shadow:0 2px 8px #2a8fe833}
.st-key-bar a p,.st-key-bar a span{font-size:13px;margin:0;font-weight:700;color:inherit !important}
.st-key-bar a[aria-current="page"]{background:linear-gradient(135deg,#4da3f5,#1f6fd8) !important;color:#fff !important;border-color:#1f6fd8 !important}
.st-key-bar a[aria-current="page"] p{color:#fff}
.kip{display:flex;align-items:center;gap:.6rem;justify-content:flex-end;min-width:0}
.kip .av{flex:0 0 auto;width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#6ec6ff,#2a8fe8);color:#fff;
  font-weight:800;font-size:14px;display:flex;align-items:center;justify-content:center}
.kip .tx{min-width:0;line-height:1.15}
.kip .nm{font-weight:800;color:#0b3d91;font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:190px}
.kip .rl{font-size:11px;font-weight:700;color:#1d9a54;letter-spacing:.5px;text-transform:uppercase}
.st-key-kl button{border-radius:12px;padding:.45rem .6rem;min-height:0;height:auto;font-size:13px;font-weight:700;border:1px solid #f0c9c9;color:#b3261e;background:#fff}
.st-key-kl button:hover{background:#fdeceb;border-color:#e8a9a5;color:#b3261e}
@media (max-width:640px){
  .st-key-bar [data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important;gap:.35rem !important}
  .st-key-bar [data-testid="stColumn"]{min-width:0 !important;width:auto !important;flex:1 1 0 !important}
  .st-key-bar a p{display:none}
  .kip .tx{display:none}
  .st-key-bar>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:nth-child(2){display:none}
  .st-key-bar>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:nth-child(3){flex:0 0 auto !important}
  .st-key-bar>div>[data-testid="stHorizontalBlock"]>[data-testid="stColumn"]:nth-child(4){flex:0 0 52px !important}
  .st-key-kl button p{display:none}
  .st-key-kl button{padding:.45rem .3rem}
}
</style>
"""


def peran():
    return st.session_state.get("peran")


def keluar():
    for k in ("peran", "admin_ok", "nama_masuk", "prn_masuk", "gagal_masuk", "via_token"):
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


def _google_foreman():
    """Foreman wajib verifikasi Google bila login Google aktif (email apa pun yang sah; dicatat di riwayat)."""
    try:
        return "auth" not in st.secrets or bool(st.user.is_logged_in)
    except Exception:
        return False


def pelaku():
    """Nama pengguna yang masuk + email Google terverifikasi, untuk riwayat perubahan."""
    n = st.session_state.get("nama_masuk", "")
    try:
        e = str(st.user.email) if "auth" in st.secrets and st.user.is_logged_in else ""
    except Exception:
        e = ""
    return f"{n} ({e})" if e else n


def gerbang():
    """Tampilkan login bila belum masuk, lalu st.stop(). Setelah lolos, peran() terisi."""
    adm = _rahasia_admin()
    if not adm:
        st.error("Pengaturan [admin] belum ada di secrets. Aplikasi dikunci.")
        st.stop()
    if not peran():
        tk = terima_token()
        if tk:  # sudah diverifikasi di aplikasi asal (termasuk Google untuk admin)
            st.session_state.update({"peran": tk["p"], "nama_masuk": tk["n"], "prn_masuk": tk["x"], "gagal_masuk": 0,
                                     "admin_ok": tk["p"] == ADMIN, "via_token": True})
    if peran() == ADMIN and not st.session_state.get("via_token") and not _google_ok(adm):
        st.markdown("<h1 style='text-align:center'>WELCOME ADMIN QC TOTO</h1>", unsafe_allow_html=True)
        if not st.user.is_logged_in:
            st.info("Langkah 2: verifikasi akun Google admin.")
            st.button("Masuk dengan Google", on_click=st.login, type="primary")
        else:
            st.error("Akun Google ini tidak punya akses admin.")
            st.button("Keluar Google", on_click=st.logout)
        st.stop()
    if peran() == FOREMAN and not st.session_state.get("via_token") and not _google_foreman():
        st.markdown("<h1 style='text-align:center'>WELCOME FOREMAN QC TOTO</h1>", unsafe_allow_html=True)
        st.info("Langkah 2: verifikasi akun Google. Emailmu dicatat sebagai tanda siapa yang melakukan setiap perubahan.")
        st.button("Masuk dengan Google", on_click=st.login, type="primary")
        st.button("Batal", on_click=keluar)
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


# ---- masuk antar aplikasi tanpa login ulang: token bertanda tangan (HMAC) berumur pendek, di-Secrets: kunci_masuk
UMUR_TOKEN = 30 * 60


def buat_token(peran_, nama, prn, kunci, sekarang=None):
    isi = json.dumps({"p": peran_, "n": nama, "x": prn, "e": int((sekarang or time.time()) + UMUR_TOKEN)}, separators=(",", ":"))
    b = base64.urlsafe_b64encode(isi.encode()).decode().rstrip("=")
    return b + "." + hmac.new(kunci.encode(), b.encode(), hashlib.sha256).hexdigest()[:40]


def baca_token(t, kunci, sekarang=None):
    """Return dict {p,n,x} bila tanda tangan benar dan belum kedaluwarsa; selain itu None. Murni (tanpa st)."""
    try:
        b, sig = str(t).split(".", 1)
        if not kunci or not hmac.compare_digest(sig, hmac.new(kunci.encode(), b.encode(), hashlib.sha256).hexdigest()[:40]):
            return None
        d = json.loads(base64.urlsafe_b64decode(b + "=" * (-len(b) % 4)))
        return d if d.get("e", 0) >= (sekarang or time.time()) and d.get("p") in (ADMIN, FOREMAN) else None
    except Exception:
        return None


def terima_token():
    """Dipanggil di awal app: bila alamat membawa ?t= yang sah, jadikan pengguna masuk. Mengembalikan dict token atau None.
    Parameter t selalu dibuang dari alamat."""
    t = st.query_params.get("t")
    if not t:
        return None
    try:
        del st.query_params["t"]
    except Exception:
        pass
    return baca_token(t, _rahasia("kunci_masuk"))


def _tautan(url):
    """Tambahkan token masuk ke alamat bila pengguna sudah masuk dan kunci_masuk ada."""
    kunci = _rahasia("kunci_masuk")
    if not kunci or not peran():
        return url
    t = buat_token(peran(), st.session_state.get("nama_masuk", ""), st.session_state.get("prn_masuk", ""), kunci)
    return url + ("&" if "?" in url else "?") + "t=" + t


def tautan_luar(app):
    """Tombol pindah antar aplikasi menurut peran. app = 'admin' | 'laporan'.
    Alamat dibaca dari Secrets: url_admin, url_laporan, url_utama (kosong = tombol tidak muncul).
    Admin dari app admin: Laporan + Halaman Utama. Foreman: Laporan. Dari app laporan: kembali ke halaman admin/foreman."""
    if app == "laporan":
        u = _rahasia("url_admin")
        if not u:
            return []
        return [("Halaman Admin", _tautan(u + "/upload-admin"))] if peran() == ADMIN else [("Halaman Foreman", _tautan(u + "/upload-foreman"))]
    hasil = []
    if _rahasia("url_laporan"):
        hasil.append(("Laporan", _tautan(_rahasia("url_laporan"))))
    if peran() == ADMIN and _rahasia("url_utama"):
        hasil.append(("Halaman Utama", _tautan(_rahasia("url_utama"))))
    return hasil


_IKON = {"Laporan": ":material/bar_chart:", "Halaman Utama": ":material/home:", "Halaman Admin": ":material/admin_panel_settings:",
         "Halaman Foreman": ":material/engineering:"}


def bilah(halaman_lain=None, label_lain="", tautan=None):
    """Bar atas bergaya kartu: [navigasi antar halaman/aplikasi] ........ [avatar · nama · peran] [Keluar]."""
    st.markdown(CSS_BAR, unsafe_allow_html=True)
    nama = st.session_state.get("nama_masuk", "")
    item = []
    if halaman_lain is not None and peran() == ADMIN:
        item.append(("page", label_lain, halaman_lain))
    for lb, url in (tautan if tautan is not None else tautan_luar("admin")):
        item.append(("url", lb, url))
    with st.container(key="bar"):
        c = st.columns([max(len(item), 1) * 2.1, 0.4, 3.2, 1.25], vertical_alignment="center")
        if item:
            for col, (jenis, lb, tujuan) in zip(c[0].columns(len(item)), item):
                with col:
                    if jenis == "page":
                        st.page_link(tujuan, label=lb, icon=_IKON.get(lb, ":material/swap_horiz:"), width="stretch")
                    else:
                        st.link_button(lb, tujuan, icon=_IKON.get(lb, ":material/open_in_new:"), width="stretch")
        awal = (nama.strip()[:1] or "?").upper()
        c[2].markdown(f"<div class='kip'><div class='av'>{awal}</div><div class='tx'><div class='nm'>{nama}</div>"
                      f"<div class='rl'>{'Admin' if peran() == ADMIN else 'Foreman'}</div></div></div>", unsafe_allow_html=True)
        with c[3], st.container(key="kl"):
            if st.button("Keluar", key="btn_keluar", icon=":material/logout:", width="stretch"):
                keluar()
                st.rerun()
