"""Membaca file Excel: SAP (Catatan Periksa), target harian, dan data karyawan."""
import hashlib
import re
import pandas as pd

WAJIB_SAP = ["Posting Date", "Nama User", "Type", "Lokasi", "Total Periksa"]


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().upper()


def hash_pw(p):
    return hashlib.sha256(str(p).strip().encode()).hexdigest()


def baca_sap(file):
    """Return (DataFrame rapi, daftar catatan). Satu baris = satu type pada satu hari."""
    df = pd.read_excel(file)
    hilang = [c for c in WAJIB_SAP if c not in df.columns]
    if hilang:
        raise ValueError("Kolom tidak ditemukan di file SAP: " + ", ".join(hilang))
    lok = df["Lokasi"].astype(str).str.upper()
    out = pd.DataFrame({
        "tgl": pd.to_datetime(df["Posting Date"], errors="coerce").dt.strftime("%Y-%m-%d"),
        "nama_sap": df["Nama User"].map(norm),
        "type": df["Type"].map(norm),
        "lokasi": df["Lokasi"].astype(str).str.strip(),
        "grup": lok.str.startswith("QCSK").map({True: "SK", False: "QC"}),
        "op": lok.str.extract(r"OP\s*(\d+)")[0],
        "periksa": pd.to_numeric(df["Total Periksa"], errors="coerce"),
    })
    awal = len(out)
    out = out.dropna(subset=["tgl", "op", "periksa"])
    out = out[out["nama_sap"] != "NAN"]
    catatan = []
    if len(out) < awal:
        catatan.append(f"{awal - len(out)} baris dibuang karena tanggal, operation atau jumlah periksa tidak terbaca.")
    out["op"] = out["op"].astype(int).astype(str)
    out["periksa"] = out["periksa"].astype(int).astype(str)
    return out.reset_index(drop=True), catatan


def baca_target(file):
    """Sheet QC TARGET (grup QC) dan QC SK TARGET (grup SK) menjadi satu tabel panjang."""
    hasil = []
    for sheet, grup, hdr, ncol in (("QC TARGET", "QC", 1, 7), ("QC SK TARGET", "SK", 2, 6)):
        raw = pd.read_excel(file, sheet_name=sheet, header=None)
        ops = [int(x) for x in raw.iloc[hdr, 1:ncol]]
        for i in range(hdr + 1, len(raw)):
            tipe = raw.iat[i, 0]
            if not isinstance(tipe, str):
                continue
            tipe = norm(tipe)
            if tipe in ("SUM", "AVERAGE"):
                break
            if tipe.startswith("SPARE"):
                continue
            for j, op in enumerate(ops):
                v = raw.iat[i, 1 + j]
                if pd.notna(v) and isinstance(v, (int, float)) and v > 0:
                    hasil.append((grup, tipe, str(op), str(v)))
    return pd.DataFrame(hasil, columns=["grup", "type", "op", "target"]).drop_duplicates(["grup", "type", "op"])


def baca_karyawan(file):
    df = pd.read_excel(file)
    wajib = ["NAMA PADA TAMPILAN WEB", "KODE KARYAWAN", "USER", "PASWORD", "NAMA PADA FILE SAP"]
    hilang = [c for c in wajib if c not in df.columns]
    if hilang:
        raise ValueError("Kolom tidak ditemukan di file karyawan: " + ", ".join(hilang))
    kode = df["Kode Opr"] if "Kode Opr" in df.columns else pd.Series([None] * len(df))
    return pd.DataFrame({
        "prn": df["KODE KARYAWAN"].astype(int).astype(str),
        "nama_web": df["NAMA PADA TAMPILAN WEB"].map(norm),
        "nama_sap": df["NAMA PADA FILE SAP"].map(norm),
        "user": df["USER"].astype(str).str.strip(),
        "pass_hash": df["PASWORD"].map(hash_pw),
        "kode_opr": kode.map(lambda x: "" if pd.isna(x) else str(int(x))),
    })


def baca_jadwal(file, bulan, prn_valid=None):
    """Baca jadwal kerja (QC atau SK). Kode '-' = libur, kode lain = masuk.
    bulan = 'YYYY-MM' (menentukan bulan jadwal, bukan isi file).
    Return (DataFrame prn,tgl,status, catatan). Pencocokan karyawan lewat kolom 'PRN SAP'."""
    import calendar
    import openpyxl
    ws = openpyxl.load_workbook(file, data_only=True).active
    rows = list(ws.iter_rows(min_row=1, max_row=min(ws.max_row, 200), max_col=60, values_only=True))
    hdr = None
    for i, r in enumerate(rows[:25]):
        for j, c in enumerate(r):
            if isinstance(c, str) and c.strip().upper() == "PRN SAP":
                hdr = (i, j)
                break
        if hdr:
            break
    if not hdr:
        raise ValueError("Kolom 'PRN SAP' tidak ditemukan. Pastikan ini file jadwal kerja.")
    hi, pj = hdr
    # baris tanggal: baris di bawah header yang berisi angka 1, 2, 3, ...
    day_row, day_cols = None, {}
    for i in range(hi, min(hi + 4, len(rows))):
        cols = {}
        for j, c in enumerate(rows[i]):
            try:
                v = int(str(c).strip())
            except (TypeError, ValueError):
                continue
            if 1 <= v <= 31 and v not in cols.values():
                cols[j] = v
        if len(cols) >= 25 and 1 in cols.values():
            day_row, day_cols = i, cols
            break
    if day_row is None:
        raise ValueError("Baris tanggal 1 sampai 30/31 tidak ditemukan di file jadwal.")
    th, bl = int(bulan[:4]), int(bulan[5:])
    n_hari = calendar.monthrange(th, bl)[1]
    catatan = []
    if len(day_cols) != n_hari:
        catatan.append(f"File jadwal memuat {len(day_cols)} tanggal, sedangkan bulan yang dipilih punya {n_hari} hari. "
                       "Tanggal yang tidak ada di file dianggap mengikuti jadwal normal (Sabtu dan Minggu libur).")
    out = []
    for r in rows[day_row + 1:]:
        p = r[pj] if pj < len(r) else None
        if p is None or not str(p).strip().split(".")[0].isdigit():
            continue
        prn = str(int(float(str(p).strip())))
        if prn_valid is not None and prn not in prn_valid:
            continue
        for j, d in day_cols.items():
            if d > n_hari:
                continue
            v = r[j] if j < len(r) else None
            kode = "" if v is None else str(v).strip()
            if kode == "":
                continue
            out.append((prn, f"{bulan}-{d:02d}", "X" if kode == "-" else "O"))
    df = pd.DataFrame(out, columns=["prn", "tgl", "status"]).drop_duplicates(["prn", "tgl"], keep="last")
    return df, catatan
