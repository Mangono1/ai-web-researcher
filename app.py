import io
from datetime import date, datetime, timezone
from typing import Any
import pandas as pd
import streamlit as st
from supabase import create_client

st.set_page_config(page_title="PPOB BUMDes", page_icon="🏠", layout="wide")
STATUSES = ("Lunas", "Belum Dibayar")
JENIS = ("Token PLN", "Pulsa", "PDAM", "PKB", "BPJS")

def db():
    # supabase-py itself adds /rest/v1; only the project root belongs here.
    url = str(st.secrets["SUPABASE_URL"]).strip().rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[:-8]
    return create_client(url, st.secrets["SUPABASE_KEY"])

try:
    supabase = db()
except Exception:
    st.error("Isi SUPABASE_URL dan SUPABASE_KEY di Streamlit Secrets.")
    st.stop()

def money(value: Any) -> str:
    return f"Rp {float(value or 0):,.0f}".replace(",", ".")

def rows(table: str) -> list[dict]:
    # Filter soft delete locally, avoiding a PostgREST filter compatibility issue.
    return [x for x in (supabase.table(table).select("*").execute().data or []) if x.get("deleted_at") is None]

def log(text: str, table: str | None = None, record_id: str | None = None):
    payload = {"aktivitas": text}
    if table: payload["tabel"] = table
    if record_id: payload["id_data"] = record_id
    try: supabase.table("log_aktivitas").insert(payload).execute()
    except Exception: pass

def soft_delete(table: str, record_id: str):
    supabase.table(table).update({"deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", record_id).execute()
    log("Soft delete data", table, record_id)

st.sidebar.title("🏠 PPOB BUMDes")
page = st.sidebar.radio("Menu", ("Dashboard", "Transaksi PPOB", "Deposit PPOB", "Piutang Pelanggan", "Utang Operator", "Import Excel", "Log Aktivitas"))

if page == "Dashboard":
    st.title("Dashboard")
    try:
        trx, dep, debt = rows("transaksi"), rows("deposit"), rows("utang_operator")
        saldo = sum(float(x["nominal"]) if x["jenis"] == "Masuk" else -float(x["nominal"]) for x in dep)
        piutang = [x for x in trx if x["status"] == "Belum Dibayar"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Jumlah transaksi", len(trx))
        c2.metric("Total fee", money(sum(float(x["fee"] or 0) for x in trx)))
        c3.metric("Saldo deposit", money(saldo))
        c4.metric("Piutang", money(sum(float(x["total_bayar"]) for x in piutang)))
        st.metric("Utang operator", money(sum(float(x["sisa"] or 0) for x in debt)))
        st.subheader("Transaksi terakhir")
        st.dataframe(pd.DataFrame(sorted(trx, key=lambda x: x["tanggal"], reverse=True)[:10]), use_container_width=True, hide_index=True)
    except Exception as e: st.error(f"Dashboard tidak dapat dimuat: {e}")

elif page == "Transaksi PPOB":
    st.title("Transaksi PPOB")
    add, view = st.tabs(("Tambah", "Daftar"))
    with add:
        with st.form("trx", clear_on_submit=True):
            a, b = st.columns(2)
            with a: tanggal = st.date_input("Tanggal", date.today()); jenis = st.selectbox("Jenis", JENIS); nama = st.text_input("Nama pelanggan")
            with b: total = st.number_input("Total bayar", min_value=0.0, step=1000.0); modal = st.number_input("Modal", min_value=0.0, step=1000.0); status = st.selectbox("Status", STATUSES)
            ket = st.text_area("Keterangan")
            save = st.form_submit_button("Simpan")
        if save:
            if total < modal: st.error("Total bayar tidak boleh lebih kecil dari modal.")
            else:
                try:
                    r = supabase.table("transaksi").insert({"tanggal": str(tanggal), "jenis": jenis, "nama": nama or None, "total_bayar": total, "modal": modal, "status": status, "keterangan": ket or None}).execute()
                    log("Tambah transaksi", "transaksi", r.data[0]["id"] if r.data else None); st.success("Tersimpan.")
                except Exception as e: st.error(f"Gagal: {e}")
    with view:
        data = sorted(rows("transaksi"), key=lambda x: x["tanggal"], reverse=True)
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
        if data:
            selected = st.selectbox("Hapus transaksi", {f"{x['tanggal']} - {x['jenis']} - {x.get('nama') or '-'}": x['id'] for x in data})
            if st.button("Soft delete transaksi"): soft_delete("transaksi", selected); st.rerun()

elif page == "Deposit PPOB":
    st.title("Deposit PPOB")
    with st.form("dep", clear_on_submit=True):
        a, b = st.columns(2)
        with a: tanggal = st.date_input("Tanggal", date.today()); jenis = st.selectbox("Jenis", ("Masuk", "Keluar"))
        with b: nominal = st.number_input("Nominal", min_value=0.0, step=10000.0); ket = st.text_input("Keterangan")
        save = st.form_submit_button("Simpan deposit")
    if save:
        try: supabase.table("deposit").insert({"tanggal": str(tanggal), "jenis": jenis, "nominal": nominal, "keterangan": ket or None}).execute(); log("Tambah deposit", "deposit"); st.success("Tersimpan.")
        except Exception as e: st.error(f"Gagal: {e}")
    st.dataframe(pd.DataFrame(sorted(rows("deposit"), key=lambda x: x["tanggal"], reverse=True)), use_container_width=True, hide_index=True)

elif page == "Piutang Pelanggan":
    st.title("Piutang Pelanggan")
    data = [x for x in rows("transaksi") if x["status"] == "Belum Dibayar"]
    st.metric("Total piutang", money(sum(float(x["total_bayar"]) for x in data)))
    st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

elif page == "Utang Operator":
    st.title("Utang Operator")
    with st.form("debt", clear_on_submit=True):
        tanggal = st.date_input("Tanggal", date.today()); nominal = st.number_input("Nominal talangan", min_value=0.0); dibayar = st.number_input("Sudah dibayar", min_value=0.0); ket = st.text_input("Keterangan")
        save = st.form_submit_button("Simpan utang")
    if save:
        if dibayar > nominal: st.error("Dibayar tidak boleh melebihi nominal.")
        else:
            try: supabase.table("utang_operator").insert({"tanggal": str(tanggal), "nominal": nominal, "dibayar": dibayar, "status": "Lunas" if dibayar == nominal else "Belum Lunas", "keterangan": ket or None}).execute(); log("Tambah utang operator", "utang_operator"); st.success("Tersimpan.")
            except Exception as e: st.error(f"Gagal: {e}")
    st.dataframe(pd.DataFrame(rows("utang_operator")), use_container_width=True, hide_index=True)

elif page == "Import Excel":
    st.title("Import Excel")
    st.write("Unduh template di bawah ini jika Anda belum memiliki format filenya.")

    # --- 1. FUNGSI MEMBUAT TEMPLATE EXCEL (2 SHEET) ---
    def generate_excel_template():
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # SHEET 1: Contoh Format Data Transaksi
            df_template = pd.DataFrame([
                {
                    "Tanggal": "2026-07-26",
                    "Jenis Transaksi": "Token PLN",
                    "Nama Pelanggan": "Budi Santoso",
                    "Total Bayar": 52000,
                    "Modal": 50500
                },
                {
                    "Tanggal": "2026-07-26",
                    "Jenis Transaksi": "Pulsa",
                    "Nama Pelanggan": "Siti Aminah",
                    "Total Bayar": 12000,
                    "Modal": 10500
                }
            ])
            df_template.to_excel(writer, sheet_name="Data Transaksi", index=False)

            # SHEET 2: Panduan Pengisian
            df_panduan = pd.DataFrame([
                {
                    "Nama Kolom": "Tanggal",
                    "Format Data": "Teks / Tanggal",
                    "Aturan & Keterangan": "Gunakan format YYYY-MM-DD (Contoh: 2026-07-26)."
                },
                {
                    "Nama Kolom": "Jenis Transaksi",
                    "Format Data": "Teks",
                    "Aturan & Keterangan": "Pilihan: Token PLN, Pulsa, PDAM, PKB, BPJS."
                },
                {
                    "Nama Kolom": "Nama Pelanggan",
                    "Format Data": "Teks",
                    "Aturan & Keterangan": "Isi nama pelanggan. Boleh dikosongkan jika tidak ada."
                },
                {
                    "Nama Kolom": "Total Bayar",
                    "Format Data": "Angka Murni",
                    "Aturan & Keterangan": "Angka saja. JANGAN pakai 'Rp', titik, atau koma (Contoh: 52000)."
                },
                {
                    "Nama Kolom": "Modal",
                    "Format Data": "Angka Murni",
                    "Aturan & Keterangan": "Angka modal/harga kulakan. Angka saja (Contoh: 50500)."
                }
            ])
            df_panduan.to_excel(writer, sheet_name="Panduan Pengisian", index=False)

        output.seek(0)
        return output

    # --- 2. TOMBOL DOWNLOAD TEMPLATE ---
    st.download_button(
        label="📥 Download Template Excel (.xlsx)",
        data=generate_excel_template(),
        file_name="Template_Import_PPOB.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.divider()

    # --- 3. PROSES IMPORT FILE EXCEL ---
    file = st.file_uploader("Pilih file .xlsx yang akan diimpor", type="xlsx")
    if file:
        # sheet_name=0 memastikan hanya Sheet 1 yang dibaca oleh sistem
        raw = pd.read_excel(file, sheet_name=0) 
        st.subheader("Pratinjau Data (Sheet 1)")
        st.dataframe(raw.head(), use_container_width=True)

        cols = list(raw.columns)
        st.write("### Pemetaan Kolom")
        c1, c2, c3 = st.columns(3)
        with c1:
            t = st.selectbox("Kolom Tanggal", cols)
            j = st.selectbox("Kolom Jenis", cols)
        with c2:
            n = st.selectbox("Kolom Nama", cols)
            total = st.selectbox("Kolom Total Bayar", cols)
        with c3:
            modal = st.selectbox("Kolom Modal", cols)
            default = st.selectbox("Status Pembayaran Default", STATUSES)

        if st.button("Validasi & Import Data"):
            valid = []
            errors = []

            for i, x in raw.iterrows():
                dt = pd.to_datetime(x[t], errors="coerce")
                a = pd.to_numeric(x[total], errors="coerce")
                b = pd.to_numeric(x[modal], errors="coerce")

                if pd.isna(dt) or pd.isna(a) or pd.isna(b) or a < 0 or b < 0 or a < b:
                    errors.append({
                        "baris": i + 2, # +2 menyesuaikan header row di Excel
                        "error": "Tanggal/angka tidak valid atau Total Bayar < Modal"
                    })
                else:
                    valid.append({
                        "tanggal": dt.date().isoformat(),
                        "jenis": str(x[j]),
                        "nama": None if pd.isna(x[n]) else str(x[n]),
                        "total_bayar": float(a),
                        "modal": float(b),
                        "status": default
                    })

            if errors:
                st.error(f"Ditemukan {len(errors)} baris bermasalah:")
                st.dataframe(pd.DataFrame(errors), hide_index=True)

            if valid:
                try:
                    supabase.table("transaksi").insert(valid).execute()
                    supabase.table("riwayat_import").insert({
                        "nama_file": file.name,
                        "jumlah_data": len(valid) + len(errors),
                        "berhasil": len(valid),
                        "gagal": len(errors)
                    }).execute()
                    log(f"Import {file.name}", "transaksi")
                    st.success(f"Berhasil mengimpor {len(valid)} data transaksi.")
                except Exception as e:
                    st.error(f"Import gagal ke database: {e}")

else:
    st.title("Log Aktivitas")
    st.dataframe(pd.DataFrame(supabase.table("log_aktivitas").select("*").order("waktu", desc=True).execute().data or []), use_container_width=True, hide_index=True)
