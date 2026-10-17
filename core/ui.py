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


def gaya_responsif():
    """Khusus halaman utama: jendela di tengah layar (desktop) dan bottom-sheet dari bawah (smartphone)."""
    st.markdown("""<style>
[data-testid='stDialog']{align-items:center !important}
[data-testid='stDialog'] [role='dialog']{max-height:92vh;overflow:auto}
.sx{overflow-x:auto}
@media (max-width:640px){
  [data-testid='stDialog']{align-items:center !important;padding-bottom:7vh !important;box-sizing:border-box}
  [data-testid='stDialog'] > div{margin:0 auto !important;width:94vw !important;max-width:94vw !important}
  [data-testid='stDialog'] [role='dialog']{width:94vw !important;max-width:94vw !important;margin:0 auto !important;
    border-radius:16px !important;max-height:84vh;padding:0 !important}
  .sx{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .sx table.d{min-width:600px}
  .kp span{font-size:.95rem}
  .kp{padding-right:100px}
  [data-testid='stDialog'] table.d{font-size:10.5px}[data-testid='stDialog'] table.d th{font-size:9.5px;padding:3px 2px;white-space:normal}[data-testid='stDialog'] table.d td{padding:3px 2px}
  [data-testid='stDialog'] table.d .v{font-size:10.5px;padding:0 3px;border-width:1.5px}
  /* kartu untuk baris REKAP TIDAK TARGET */
  [class*='st-key-tt_']{border:2px solid #000;border-radius:8px;padding:8px;margin-bottom:8px}
  [class*='st-key-nt_']{border:1px solid #cfd8e6;border-radius:10px;padding:8px;margin-bottom:8px;background:#f6f8fb}
  [class*='st-key-ab_']{border:2px solid #000;border-radius:8px;padding:6px 8px;margin-bottom:6px}
  [class*='st-key-tt_'] [data-testid='stVerticalBlock'],[class*='st-key-ab_'] [data-testid='stVerticalBlock']{gap:.4rem !important}
  [class*='st-key-tt_'] [data-testid='stHorizontalBlock'],[class*='st-key-ab_'] [data-testid='stHorizontalBlock']{gap:.3rem !important;flex-wrap:wrap}
  [class*='st-key-tt_'] [data-testid='stColumn'],[class*='st-key-ab_'] [data-testid='stColumn']{width:100% !important;flex:1 1 100% !important}
  h1.judul{font-size:1.25rem}
}
</style>""", unsafe_allow_html=True)


# ---------------------------------------------------------------- header baru khusus halaman utama
_IKON_PUB = {  # ikon garis putih (24x24)
    "login": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
    "hasil": '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16l2 2 4-4"/>',
    "notes": '<path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-5 4z"/><path d="M8 8h8M8 12h5"/>',
    "rekap": '<path d="M3 3v18h18"/><path d="M7 15l4-5 3 3 5-7"/>',
    "kegiatan": '<circle cx="12" cy="12" r="9"/><path d="M12 8v4l3 2"/>',
    "terima": '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
}


def _svg_uri(isi, warna="#fff", lebar=2.4):
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='{warna}' stroke-width='{lebar}' "
           f"stroke-linecap='round' stroke-linejoin='round'>{isi}</svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _css_pub(besar):
    maks = _svg_uri('<path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7"/>')
    res = _svg_uri('<path d="M20 10h-6V4M4 14h6v6M14 10l7-7M3 21l7-7"/>')
    css = f"""<style>
[data-testid='stDialog'] [role='dialog']{{position:relative;scrollbar-width:none;overflow-x:hidden}}
[data-testid='stDialog'] [role='dialog']::-webkit-scrollbar{{display:none}}
[data-testid='stDialog'] [role='dialog'] h2{{display:none !important}}
[data-testid='stDialog'] [role='dialog'] > div:last-child{{padding:0 16px 20px !important}}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']{{position:absolute !important;top:13px;right:10px;z-index:30;
  width:34px;height:34px;display:flex;align-items:center;justify-content:center;background:transparent !important;border:none !important;
  border-radius:50%;color:#fff !important}}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close'] svg{{width:15px;height:15px;stroke:#fff;stroke-width:2.6}}
[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']:hover,[data-testid='stDialog'] [role='dialog'] > button[aria-label='Close']:active{{background:#ffffff33 !important}}
.kpx{{display:flex;align-items:center;gap:10px;margin:-16px -16px 14px;padding:10px 92px 10px 14px;min-height:60px;box-sizing:border-box;color:#fff;
  background:linear-gradient(135deg,#0b3d91,#1a73e8)}}
.kpx .li{{flex:none;width:38px;height:38px;border-radius:12px;background:#ffffff26;border:1.5px solid #ffffff55;display:flex;align-items:center;justify-content:center}}
.kpx .li svg{{width:22px;height:22px;stroke:#fff;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}}
.kpx b{{font-size:1.05rem;line-height:1.15;letter-spacing:.4px;font-weight:800;color:#fff}}
[class*='st-key-tbmax_'],[class*='st-key-tbres_']{{position:absolute !important;top:13px;right:46px;z-index:20;width:34px !important}}
[class*='st-key-tbmax_'] button,[class*='st-key-tbres_'] button{{width:34px;min-height:0;height:34px;padding:0;border:none !important;border-radius:50%;
  background-color:transparent !important;background-repeat:no-repeat;background-position:center;background-size:20px}}
[class*='st-key-tbmax_'] button{{background-image:url({maks})}}
[class*='st-key-tbres_'] button{{background-image:url({res})}}
[class*='st-key-tbmax_'] button p,[class*='st-key-tbres_'] button p{{display:none}}
[class*='st-key-tbmax_'] button:focus,[class*='st-key-tbres_'] button:focus{{outline:none !important;box-shadow:none !important}}
[class*='st-key-tbmax_'] button:hover,[class*='st-key-tbres_'] button:hover,[class*='st-key-tbmax_'] button:active,[class*='st-key-tbres_'] button:active{{background-color:#ffffff33 !important}}
@media (max-width:640px){{.kpx{{margin:-16px -16px 12px}}.kpx b{{font-size:.95rem}}}}
</style>"""
    if besar:
        css += ("<style>[data-testid='stDialog'] [role='dialog']{position:fixed !important;inset:0 !important;"
                "width:100vw !important;max-width:100vw !important;height:100vh !important;max-height:100vh !important;"
                "margin:0 !important;border-radius:0 !important;overflow:auto !important;background:#fff !important;"
                "z-index:1000002 !important}</style>")
    return css


def kontrol_jendela_pub(nama):
    kunci = f"max_{nama}"
    besar = st.session_state.get(kunci, False)
    st.markdown(_css_pub(besar), unsafe_allow_html=True)
    st.button("x", key=f"{'tbres' if besar else 'tbmax'}_{nama}", help="Kecilkan jendela" if besar else "Perbesar jendela",
              on_click=lambda: st.session_state.update({kunci: not besar}))


def kepala_pub(jenis, judul):
    """Header jendela halaman utama: gradasi biru penuh sampai tepi, ikon garis putih, judul boleh turun baris."""
    st.markdown(f"<div class='kpx'><span class='li'><svg viewBox='0 0 24 24'>{_IKON_PUB[jenis]}</svg></span><b>{judul}</b></div>",
                unsafe_allow_html=True)
