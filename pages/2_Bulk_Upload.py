import hashlib

import pandas as pd
import streamlit as st

from utils.auth import require_login
from utils.schemas import SCHEMAS
from utils.db import insert_records, clear_cache
from utils.templates import build_excel_template
from utils.calculations import compute_food_database_fields

st.set_page_config(page_title="Bulk Upload", page_icon="📤", layout="wide")
username, role = require_login()

st.title("📤 Bulk Upload")

dataset_name = st.selectbox("Select dataset", list(SCHEMAS.keys()))
schema = SCHEMAS[dataset_name]
fields = schema["fields"]
headers = [f["name"] for f in fields]
enterable_headers = [f["name"] for f in fields if f["type"] != "computed"]

st.caption(f"Upload many records at once into **{dataset_name}**.")

# --- Excel template download ---
st.download_button(
    "⬇️ Download Excel template for this dataset",
    data=build_excel_template(dataset_name, schema),
    file_name=f"{dataset_name.replace(' ', '_')}_template.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

uploaded = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])

if uploaded:
    try:
        if uploaded.name.endswith(".csv"):
            df = pd.read_csv(uploaded)
        else:
            df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read the file: {e}")
        st.stop()

    df.columns = [str(c).strip() for c in df.columns]

    missing_cols = [c for c in enterable_headers if c not in df.columns]
    extra_cols = [c for c in df.columns if c not in enterable_headers]

    if missing_cols:
        st.error(
            f"The uploaded file is missing required column(s): {', '.join(missing_cols)}. "
            "Please use the template above."
        )
        st.stop()
    if extra_cols:
        st.warning(f"These columns will be ignored (not in the schema): {', '.join(extra_cols)}")

    # Required-field check
    required_cols = [f["name"] for f in fields if f.get("required") and f["type"] != "computed"]
    bad_rows = df[df[required_cols].isnull().any(axis=1)] if required_cols else pd.DataFrame()

    st.subheader("Preview")
    st.dataframe(df.head(20), use_container_width=True)
    st.caption(f"{len(df)} row(s) detected.")

    if not bad_rows.empty:
        st.error(f"{len(bad_rows)} row(s) are missing required fields ({', '.join(required_cols)}) and will be skipped.")

    valid_df = df.drop(index=bad_rows.index) if not bad_rows.empty else df

    upload_signature = hashlib.sha256(
        f"{dataset_name}:".encode("utf-8") + uploaded.getvalue()
    ).hexdigest()
    processed_uploads = st.session_state.setdefault("processed_bulk_uploads", set())
    upload_locked = upload_signature in processed_uploads
    if upload_locked:
        st.info("This file has already been submitted for this dataset. Choose another file or dataset to submit again.")

    if st.button(
        f"Submit {len(valid_df)} record(s) to the database",
        type="primary",
        disabled=upload_locked,
    ):
        # Lock before any database work; retain the lock even if some rows fail
        # so a retry cannot duplicate rows that were already inserted.
        processed_uploads.add(upload_signature)
        st.session_state["processed_bulk_uploads"] = processed_uploads
        records = valid_df.to_dict(orient="records")
        date_fields = {
            field["name"] for field in fields if field["type"] == "date"
        }

        # Compute derived fields per dataset, same logic as single-entry page
        for r in records:
            if dataset_name == "Students Performance":
                scores = [r.get("Term1_Score"), r.get("Term2_Score"), r.get("Term3_Score")]
                scores = [s for s in scores if s not in (None, 0, "")]
                r["Yearly_Average"] = round(sum(scores) / len(scores), 2) if scores else ""
            elif dataset_name == "Students Item":
                qty = r.get("Quantity") or 0
                price = r.get("Price") or 0
                r["Total_Cost"] = round(float(qty) * float(price), 2) if pd.notna(qty) and pd.notna(price) else ""
            elif dataset_name == "Food Database":
                r.update(compute_food_database_fields(r))
            # Normalize NaN -> None and dates -> ISO strings for clean DB writes
            for k, v in list(r.items()):
                if pd.isna(v):
                    r[k] = None
                elif hasattr(v, "isoformat"):
                    if k in date_fields and hasattr(v, "date"):
                        r[k] = v.date().isoformat()
                    else:
                        r[k] = v.isoformat()

        try:
            with st.spinner("Uploading to the database..."):
                success_count, errors = insert_records(dataset_name, records)
            clear_cache()
            st.session_state[f"bulk_upload_result_{upload_signature}"] = {
                "success_count": success_count,
                "errors": errors,
                "error": None,
            }
        except Exception as e:
            st.session_state[f"bulk_upload_result_{upload_signature}"] = {
                "success_count": 0,
                "errors": [],
                "error": f"Could not write to the database: {e}",
            }
        st.rerun()

    if upload_locked:
        result = st.session_state.get(f"bulk_upload_result_{upload_signature}")
        if result:
            if result["error"]:
                st.error(result["error"])
            if result["success_count"]:
                st.success(f"Uploaded {result['success_count']} record(s) to '{dataset_name}' ✅")
            if result["errors"]:
                st.error(f"{len(result['errors'])} row(s) failed to upload:")
                error_df = pd.DataFrame(
                    [{"Row #": i + 1, "Error": msg} for i, msg in result["errors"]]
                )
                st.dataframe(error_df, use_container_width=True)
