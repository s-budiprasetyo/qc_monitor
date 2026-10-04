"""Tampilan bersama untuk semua jendela (halaman admin dan halaman utama): ikon, spanduk kuning, tombol perbesar/kecilkan."""
import base64
import os

import streamlit as st

_ASET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")


@st.cache_data(show_spinner=False)
def ikon(nama):
    """Ikon dari file Excel pengguna (folder assets) sebagai data-uri."""
    with open(os.path.join(_ASET, f"{nama}.png"), "rb") as f:
        return "data:image/png;base64," + base64.b64encode(f.read()).decode()


def _css_jendela(besar):
    maks, res = ikon("maks"), ikon("restore")
    css = f"""<style>
/* judul bawaan dialog disembunyikan: spanduk kuning sudah menjadi kepala jendela (hemat tempat) */
[data-testid='stDialog'] [role='dialog']{{position:relative;scrollbar-width:none}}
[data-testid='stDialog'] [role='dialog']::-webkit-scrollbar{{display:none}}
[data-testid='stDialog'] [role='dialog'] h2{{display:none !important}}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']{{position:absolute !important;top:19px;right:32px;z-index:30;
  width:30px;height:30px;display:flex;align-items:center;justify-content:center;background:#fff !important;border:2px solid #000 !important;border-radius:6px;color:#000 !important}}
.kp{{display:flex;align-items:center;gap:12px;background:#ffff00;border:2px solid #000;border-radius:6px;
  padding:5px 112px 5px 10px;margin:-20px 0 10px 0}}
.kp img{{height:38px;width:38px;object-fit:contain;background:#fff;border-radius:50%;border:2px solid #000}}
.kp span{{font-weight:800;font-size:1.1rem;letter-spacing:.4px;color:#000}}
[class*='st-key-tbmax_'],[class*='st-key-tbres_']{{position:absolute !important;top:17px;right:70px;z-index:20;width:34px !important}}
[class*='st-key-tbmax_'] button,[class*='st-key-tbres_'] button{{width:34px;min-height:0;height:34px;padding:0;border:2px solid #000 !important;
  border-radius:6px;background-color:#fff;background-repeat:no-repeat;background-position:center;background-size:20px}}
[class*='st-key-tbmax_'] button{{background-image:url({maks})}}
[class*='st-key-tbres_'] button{{background-image:url({res})}}
[class*='st-key-tbmax_'] button p,[class*='st-key-tbres_'] button p{{display:none}}
[class*='st-key-tbmax_'] button:focus,[class*='st-key-tbres_'] button:focus{{outline:none !important;box-shadow:none !important;border-color:#000 !important}}
[class*='st-key-tbmax_'] button:hover,[class*='st-key-tbres_'] button:hover{{background-color:#e8f6fd}}
</style>"""
    if besar:
        css += ("<style>[data-testid='stDialog'] [role='dialog']{position:fixed !important;inset:0 !important;"
                "width:100vw !important;max-width:100vw !important;height:100vh !important;max-height:100vh !important;"
                "margin:0 !important;border-radius:0 !important;overflow:auto !important;background:#fff !important;"
                "z-index:1000002 !important}</style>")
    return css


def kontrol_jendela(nama):
    """Tombol ikon perbesar/kecilkan di sebelah kiri tombol close (tanpa minimize; close bawaan dialog)."""
    kunci = f"max_{nama}"
    besar = st.session_state.get(kunci, False)
    st.markdown(_css_jendela(besar), unsafe_allow_html=True)
    st.button("x", key=f"{'tbres' if besar else 'tbmax'}_{nama}", help="Kecilkan jendela" if besar else "Perbesar jendela",
              on_click=lambda: st.session_state.update({kunci: not besar}))


def kepala(nama_ikon, judul):
    """Spanduk kuning ala Excel dengan ikon; berfungsi sebagai kepala jendela."""
    st.markdown(f"<div class='kp'><img src='{ikon(nama_ikon)}'><span>{judul}</span></div>", unsafe_allow_html=True)


def gaya_global():
    """Hilangkan efek pudar/blur saat Streamlit memuat ulang (elemen 'stale' jadi transparan) dan latar buram dialog."""
    st.markdown("""<style>
[data-stale="true"],[data-stale="true"] *{opacity:1 !important;transition:none !important;filter:none !important}
[data-testid="stDialog"],[data-testid="stDialog"] > div{backdrop-filter:none !important;-webkit-backdrop-filter:none !important}
[data-testid="stAppViewContainer"] *{transition-duration:0s !important}
</style>""", unsafe_allow_html=True)
