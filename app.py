"""Starter app Streamlit untuk Sistem Operasional PPOB BUMDes.

Install dependencies:
    pip install streamlit supabase pandas openpyxl

Secrets (lokal: .streamlit/secrets.toml; Streamlit Cloud: App secrets):
    SUPABASE_URL = "https://<project>.supabase.co"
    SUPABASE_KEY = "<anon key>"

Jalankan SQL schema Supabase terlebih dahulu. App ini mengharapkan tabel:
transaksi, deposit, utang_operator, pengaturan, log_aktivitas, riwayat_import.
Kolom `fee` pada transaksi dan `sisa` pada utang_operator adalah generated
column PostgreSQL, sehingga keduanya sengaja tidak dikirim saat INSERT.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client


st.set_page_config(page_title="PPOB BUMDes", page_icon="🏠", layout="wide")

PAYMENT_STATUS = ("Lunas", "Belum Dibayar")
DEPOSIT_TYPES = ("Masuk", "Keluar")
TRANSACTION_TYPES = ("Token PLN", "Pulsa", "PDAM", "PKB", "BPJS")


@st.cache_resource
def get_supabase() -> Client:
    """Create one reusable Supabase client for the Streamlit process."""
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


try:
    supabase = get_supabase()
except Exception:
    st.error(
        "Konfigurasi Supabase belum tersedia. Isi SUPABASE_URL dan SUPABASE_KEY "
        "di Streamlit secrets, lalu muat ulang aplikasi."
    )
    st.stop()


def rupiah(value: Any) -> str:
    """Format value returned by Postgres/Pandas as Indonesian Rupiah."""
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        number = 0
    return f"Rp {number:,.0f}".replace(",", ".")


def numeric_sum(rows: list[dict[str, Any]], field: str) -> float:
    return sum(float(row.get(field) or 0) for row in rows)


def log_activity(activity: str, table: str | None = None, record_id: str | None = None) -> None:
    """Logs must not prevent the primary business action from succeeding."""
    payload: dict[str, Any] = {"aktivitas": activity}
    if table:
        payload["tabel"] = table
    if record_id:
        payload["id_data"] = record_id
    try:
        supabase.table("log_aktivitas").insert(payload).execute()
    except Exception:
        # Replace with proper server-side logging later if required.
        pass


def active_query(table: str):
    """Base query for tables which use deleted_at soft delete."""
    return supabase.table(table).select("*").is_("deleted_at", "null")


def soft_delete(table: str, record_id: str, label: str) -> None:
    supabase.table(table).update({"deleted_at": datetime.now(timezone.utc).isoformat()}).eq("id", record_id).execute()
    log_activity(f"Hapus (soft delete): {label}", table, record_id)


def parse_money(series: pd.Series) -> pd.Series:
    """Accept numbers and common Indonesian Excel currency formatting."""
    cleaned = (
        series.astype(str)
        .str.replace("Rp", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce")


def validate_import(
    source: pd.DataFrame,
    date_col: str,
    type_col: str,
    name_col: str,
    total_col: str,
    cost_col: str,
    status_col: str | None,
    default_status: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return valid Supabase payloads and row-level errors; do not write yet."""
    valid: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    dates = pd.to_datetime(source[date_col], errors="coerce")
    totals = parse_money(source[total_col])
    costs = parse_money(source[cost_col])

    for index in source.index:
        problems: list[str] = []
        transaction_date = dates.loc[index]
        jenis = str(source.at[index, type_col]).strip()
        nama_value = source.at[index, name_col]
        nama = "" if pd.isna(nama_value) else str(nama_value).strip()
        total, modal = totals.loc[index], costs.loc[index]
        status = default_status
        if status_col:
            cell = source.at[index, status_col]
            if not pd.isna(cell) and str(cell).strip():
                status = str(cell).strip()

        if pd.isna(transaction_date):
            problems.append("tanggal kosong atau tidak valid")
        if not jenis or jenis.lower() == "nan":
            problems.append("jenis transaksi kosong")
        if pd.isna(total):
            problems.append("total bayar kosong atau tidak valid")
        if pd.isna(modal):
            problems.append("modal kosong atau tidak valid")
        if not pd.isna(total) and total < 0:
            problems.append("total bayar tidak boleh negatif")
        if not pd.isna(modal) and modal < 0:
            problems.append("modal tidak boleh negatif")
        if not pd.isna(total) and not pd.isna(modal) and total < modal:
            problems.append("total bayar lebih kecil dari modal")
        if status not in PAYMENT_STATUS:
            problems.append(f"status tidak dikenal: {status}")

        if problems:
            errors.append({"Baris Excel": int(index) + 2, "Masalah": "; ".join(problems)})
        else:
            valid.append(
                {
                    "tanggal": transaction_date.date().isoformat(),
                    "jenis": jenis,
                    "nama": nama or None,
                    "total_bayar": float(total),
                    "modal": float(modal),
                    "status": status,
                }
            )
    return valid, errors


def insert_batches(table: str, records: list[dict[str, Any]], batch_size: int = 250) -> None:
    for start in range(0, len(records), batch_size):
        supabase.table(table).insert(records[start : start + batch_size]).execute()


st.sidebar.title("🏠 PPOB BUMDes")
menu = st.sidebar.radio(
    "Menu",
    ("Dashboard", "Transaksi PPOB", "Deposit PPOB", "Piutang Pelanggan", "Utang Operator", "Import Excel", "Riwayat Aktivitas"),
)
st.sidebar.caption("V1 • tanpa login")


if menu == "Dashboard":
    st.title("Dashboard")
    try:
        transactions = active_query("transaksi").execute().data or []
        deposits = active_query("deposit").execute().data or []
        debts = active_query("utang_operator").execute().data or []

        deposit_in = numeric_sum([r for r in deposits if r["jenis"] == "Masuk"], "nominal")
        deposit_out = numeric_sum([r for r in deposits if r["jenis"] == "Keluar"], "nominal")
        outstanding = [r for r in transactions if r.get("status") != "Lunas"]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Jumlah transaksi", len(transactions))
        c2.metric("Total fee", rupiah(numeric_sum(transactions, "fee")))
        c3.metric("Saldo deposit", rupiah(deposit_in - deposit_out))
        c4.metric("Piutang pelanggan", rupiah(numeric_sum(outstanding, "total_bayar")))
        st.metric("Utang operator belum diganti", rupiah(numeric_sum(debts, "sisa")))

        st.subheader("10 transaksi terakhir")
        recent = active_query("transaksi").order("tanggal", desc=True).limit(10).execute().data or []
        if recent:
            st.dataframe(pd.DataFrame(recent), use_container_width=True, hide_index=True)
        else:
            st.info("Belum ada transaksi.")
    except Exception as exc:
        st.error(f"Dashboard tidak dapat dimuat: {exc}")


elif menu == "Transaksi PPOB":
    st.title("Transaksi PPOB")
    form_tab, list_tab = st.tabs(("Tambah transaksi", "Daftar transaksi"))
    with form_tab:
        with st.form("transaction_form", clear_on_submit=True):
            a, b = st.columns(2)
            with a:
                transaction_date = st.date_input("Tanggal", value=date.today())
                transaction_type = st.selectbox("Jenis transaksi", TRANSACTION_TYPES)
                customer_name = st.text_input("Nama pelanggan")
            with b:
                total = st.number_input("Total bayar (Rp)", min_value=0.0, step=1000.0)
                cost = st.number_input("Modal (Rp)", min_value=0.0, step=1000.0)
                payment_status = st.selectbox("Status pembayaran", PAYMENT_STATUS)
            st.caption("Fee akan dihitung oleh database: total bayar − modal.")
            note = st.text_area("Keterangan (opsional)")
            save = st.form_submit_button("Simpan transaksi")
        if save:
            if total < cost:
                st.error("Total bayar tidak boleh lebih kecil dari modal.")
            else:
                try:
                    result = supabase.table("transaksi").insert({
                        "tanggal": transaction_date.isoformat(), "jenis": transaction_type,
                        "nama": customer_name.strip() or None, "total_bayar": total,
                        "modal": cost, "status": payment_status, "keterangan": note.strip() or None,
                    }).execute()
                    record_id = result.data[0]["id"] if result.data else None
                    log_activity(f"Tambah transaksi {transaction_type}", "transaksi", record_id)
                    st.success("Transaksi tersimpan.")
                except Exception as exc:
                    st.error(f"Gagal menyimpan transaksi: {exc}")
    with list_tab:
        rows = active_query("transaksi").order("tanggal", desc=True).limit(200).execute().data or []
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            options = {f"{r['tanggal']} — {r['jenis']} — {r.get('nama') or '-'}": r["id"] for r in rows}
            selection = st.selectbox("Pilih transaksi untuk dihapus", ["-"] + list(options))
            if selection != "-" and st.button("Hapus transaksi terpilih", type="secondary"):
                try:
                    soft_delete("transaksi", options[selection], selection)
                    st.success("Transaksi dipindahkan dari tampilan aktif.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Gagal menghapus transaksi: {exc}")
        else:
            st.info("Belum ada transaksi.")


elif menu == "Deposit PPOB":
    st.title("Deposit PPOB")
    with st.form("deposit_form", clear_on_submit=True):
        a, b = st.columns(2)
        with a:
            deposit_date = st.date_input("Tanggal deposit", value=date.today())
            deposit_type = st.selectbox("Jenis", DEPOSIT_TYPES)
        with b:
            amount = st.number_input("Nominal (Rp)", min_value=0.0, step=10000.0)
            note = st.text_input("Keterangan")
        save = st.form_submit_button("Simpan deposit")
    if save:
        try:
            result = supabase.table("deposit").insert({"tanggal": deposit_date.isoformat(), "jenis": deposit_type, "nominal": amount, "keterangan": note or None}).execute()
            log_activity(f"Deposit {deposit_type}", "deposit", result.data[0]["id"] if result.data else None)
            st.success("Deposit tersimpan.")
        except Exception as exc:
            st.error(f"Gagal menyimpan deposit: {exc}")
    rows = active_query("deposit").order("tanggal", desc=True).limit(200).execute().data or []
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True) if rows else st.info("Belum ada deposit.")


elif menu == "Piutang Pelanggan":
    st.title("Piutang Pelanggan")
    st.caption("Piutang diambil langsung dari transaksi berstatus Belum Dibayar; tidak ada tabel piutang terpisah.")
    rows = active_query("transaksi").eq("status", "Belum Dibayar").order("tanggal", desc=True).execute().data or []
    if rows:
        st.metric("Total piutang", rupiah(numeric_sum(rows, "total_bayar")))
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.success("Tidak ada piutang aktif.")


elif menu == "Utang Operator":
    st.title("Utang Operator")
    st.caption("Status ditentukan oleh nilai sisa dari database: sisa 0 berarti lunas.")
    with st.form("debt_form", clear_on_submit=True):
        a, b = st.columns(2)
        with a:
            debt_date = st.date_input("Tanggal", value=date.today())
            debt_amount = st.number_input("Nominal talangan (Rp)", min_value=0.0, step=10000.0)
        with b:
            paid_amount = st.number_input("Sudah dibayar (Rp)", min_value=0.0, step=10000.0)
            note = st.text_input("Keterangan")
        save = st.form_submit_button("Simpan utang operator")
    if save:
        if paid_amount > debt_amount:
            st.error("Jumlah dibayar tidak boleh melebihi nominal talangan.")
        else:
            try:
                # `status` is kept here only for compatibility with the proposed
                # schema. The UI itself always derives its display from `sisa`.
                debt_status = "Lunas" if paid_amount == debt_amount else "Belum Lunas"
                result = supabase.table("utang_operator").insert({"tanggal": debt_date.isoformat(), "nominal": debt_amount, "dibayar": paid_amount, "status": debt_status, "keterangan": note or None}).execute()
                log_activity("Tambah utang operator", "utang_operator", result.data[0]["id"] if result.data else None)
                st.success("Utang operator tersimpan.")
            except Exception as exc:
                st.error(f"Gagal menyimpan utang: {exc}")
    rows = active_query("utang_operator").order("tanggal", desc=True).limit(200).execute().data or []
    if rows:
        view = pd.DataFrame(rows)
        view["status_tampil"] = view["sisa"].map(lambda value: "Lunas" if float(value or 0) == 0 else "Belum Lunas")
        st.dataframe(view, use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada utang operator.")


elif menu == "Import Excel":
    st.title("Import transaksi dari Excel")
    st.caption("Data divalidasi dan ditampilkan dahulu. Tidak ada data disimpan sebelum Anda menekan tombol import.")
    uploaded = st.file_uploader("Pilih file .xlsx", type=("xlsx",))
    if uploaded:
        try:
            raw = pd.read_excel(uploaded)
            if raw.empty:
                st.warning("File Excel tidak berisi data.")
                st.stop()
            st.dataframe(raw.head(10), use_container_width=True, hide_index=True)
            cols = list(raw.columns)
            a, b, c = st.columns(3)
            with a:
                map_date = st.selectbox("Kolom tanggal", cols)
                map_type = st.selectbox("Kolom jenis", cols)
            with b:
                map_name = st.selectbox("Kolom nama", cols)
                map_total = st.selectbox("Kolom total bayar", cols)
            with c:
                map_cost = st.selectbox("Kolom modal", cols)
                map_status = st.selectbox("Kolom status (opsional)", ["(gunakan default)"] + cols)
            default = st.selectbox("Status default", PAYMENT_STATUS)
            if st.button("Validasi data"):
                valid, errors = validate_import(raw, map_date, map_type, map_name, map_total, map_cost, None if map_status == "(gunakan default)" else map_status, default)
                st.session_state["import_payload"] = valid
                st.session_state["import_errors"] = errors
                st.session_state["import_file"] = uploaded.name
            if "import_payload" in st.session_state:
                valid = st.session_state["import_payload"]
                errors = st.session_state["import_errors"]
                x, y, z = st.columns(3)
                x.metric("Total baris", len(valid) + len(errors))
                y.metric("Valid", len(valid))
                z.metric("Bermasalah", len(errors))
                if errors:
                    st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
                if valid and st.button("Import data valid ke Supabase", type="primary"):
                    try:
                        insert_batches("transaksi", valid)
                        supabase.table("riwayat_import").insert({"nama_file": st.session_state["import_file"], "jumlah_data": len(valid) + len(errors), "berhasil": len(valid), "gagal": len(errors)}).execute()
                        log_activity(f"Import Excel {st.session_state['import_file']}: {len(valid)} data", "transaksi")
                        st.success(f"{len(valid)} transaksi berhasil diimpor.")
                        for key in ("import_payload", "import_errors", "import_file"):
                            st.session_state.pop(key, None)
                    except Exception as exc:
                        st.error(f"Import gagal: {exc}")
        except Exception as exc:
            st.error(f"File tidak dapat dibaca: {exc}")


elif menu == "Riwayat Aktivitas":
    st.title("Riwayat Aktivitas")
    rows = supabase.table("log_aktivitas").select("*").order("waktu", desc=True).limit(300).execute().data or []
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("Belum ada aktivitas yang tercatat.")
