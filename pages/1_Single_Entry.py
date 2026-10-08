import datetime
import streamlit as st

from utils.auth import require_login
from utils.schemas import SCHEMAS
from utils.db import insert_record, clear_cache, DatabaseError
from utils.calculations import compute_food_database_fields
from utils.food_catalog import FOOD_ITEMS, units_for_item, categories_for_item_and_unit


def reset_food_dependents():
    st.session_state.pop("Food Database_Purchase_Unit", None)
    st.session_state.pop("Food Database_Food_Category", None)


def reset_food_category():
    st.session_state.pop("Food Database_Food_Category", None)

st.set_page_config(page_title="Single Entry", page_icon="✍️", layout="wide")
username, role = require_login()

st.title("✍️ Single Entry")

dataset_name = st.selectbox("Select dataset", list(SCHEMAS.keys()))
submit_lock_key = f"single_entry_submitted_{dataset_name}"
submit_result_key = f"single_entry_result_{dataset_name}"
schema = SCHEMAS[dataset_name]
fields = schema["fields"]
headers = [f["name"] for f in fields]

st.caption(f"Adding one record to **{dataset_name}**.")

if dataset_name == "Food Database":
    values = {}
    cols = st.columns(2)
    col_i = 0
    for field in fields:
        if field["type"] == "computed":
            continue
        target_col = cols[col_i % 2]
        col_i += 1
        label = field["name"].replace("_", " ") + (" *" if field.get("required") else "")

        if field["name"] == "Food_Item":
            values[field["name"]] = target_col.selectbox(
                label,
                FOOD_ITEMS,
                key="Food Database_Food_Item",
                on_change=reset_food_dependents,
            )
        elif field["name"] == "Purchase_Unit":
            selected_item = st.session_state.get("Food Database_Food_Item", FOOD_ITEMS[0])
            values[field["name"]] = target_col.selectbox(
                label,
                units_for_item(selected_item),
                key="Food Database_Purchase_Unit",
                on_change=reset_food_category,
            )
        elif field["name"] == "Food_Category":
            selected_item = st.session_state.get("Food Database_Food_Item", FOOD_ITEMS[0])
            selected_unit = st.session_state.get(
                "Food Database_Purchase_Unit", units_for_item(selected_item)[0]
            )
            values[field["name"]] = target_col.selectbox(
                label,
                categories_for_item_and_unit(selected_item, selected_unit),
                key="Food Database_Food_Category",
            )
        elif field["type"] == "date":
            values[field["name"]] = target_col.date_input(
                label, value=datetime.date.today(), key=f"{dataset_name}_{field['name']}"
            )
        elif field["type"] == "number":
            values[field["name"]] = target_col.number_input(
                label, value=0.0, step=1.0, key=f"{dataset_name}_{field['name']}"
            )
    submitted = st.button(
        "Submit record",
        use_container_width=True,
        disabled=st.session_state.get(submit_lock_key, False),
        key="food_database_submit",
    )
else:
    with st.form(key=f"form_{dataset_name}", clear_on_submit=True):
        values = {}
        cols = st.columns(2)
        col_i = 0
        for field in fields:
            if field["type"] == "computed":
                continue  # computed fields are calculated after submit, not entered
            target_col = cols[col_i % 2]
            col_i += 1
            label = field["name"].replace("_", " ") + (" *" if field.get("required") else "")

            if field["type"] == "text":
                values[field["name"]] = target_col.text_input(label, key=f"{dataset_name}_{field['name']}")
            elif field["type"] == "number":
                values[field["name"]] = target_col.number_input(
                    label, value=0.0, step=1.0, key=f"{dataset_name}_{field['name']}"
                )
            elif field["type"] == "date":
                if field.get("required"):
                    values[field["name"]] = target_col.date_input(
                        label, value=datetime.date.today(), key=f"{dataset_name}_{field['name']}"
                    )
                else:
                    values[field["name"]] = target_col.date_input(
                        label,
                        value=None,
                        key=f"{dataset_name}_{field['name']}",
                    )
            elif field["type"] == "select":
                values[field["name"]] = target_col.selectbox(
                    label, field["options"], key=f"{dataset_name}_{field['name']}"
                )

        submitted = st.form_submit_button(
            "Submit record",
            use_container_width=True,
            disabled=st.session_state.get(submit_lock_key, False),
        )

if submitted:
    st.session_state[submit_lock_key] = True
    # Basic required-field validation
    missing = [
        f["name"]
        for f in fields
        if f.get("required") and f["type"] != "computed" and not str(values.get(f["name"], "")).strip()
    ]
    if missing:
        st.session_state[submit_result_key] = (
            "error", f"Please fill in required field(s): {', '.join(missing)}"
        )
    else:
        # Convert date objects to ISO strings
        for k, v in values.items():
            if isinstance(v, datetime.date):
                values[k] = v.isoformat()

        # Compute derived fields
        if dataset_name == "Students Performance":
            scores = [values.get("Term1_Score", 0), values.get("Term2_Score", 0), values.get("Term3_Score", 0)]
            scores = [s for s in scores if s not in (None, 0, "")]
            values["Yearly_Average"] = round(sum(scores) / len(scores), 2) if scores else ""
        elif dataset_name == "Students Item":
            qty = values.get("Quantity") or 0
            price = values.get("Price") or 0
            values["Total_Cost"] = round(qty * price, 2)
        elif dataset_name == "Food Database":
            values.update(compute_food_database_fields(values))

        try:
            insert_record(dataset_name, values)
            clear_cache()
            st.session_state[submit_result_key] = (
                "success", f"Record added to '{dataset_name}' ✅"
            )
        except DatabaseError as e:
            st.session_state[submit_result_key] = ("error", str(e))
        except Exception as e:
            st.session_state[submit_result_key] = (
                "error", f"Could not write to the database: {e}"
            )
    # Rerender immediately so the submit button is visibly locked.
    st.rerun()

if st.session_state.get(submit_lock_key):
    result = st.session_state.get(submit_result_key)
    if result:
        if result[0] == "success":
            st.success(result[1])
        else:
            st.error(result[1])
    st.info("Submit is locked. Start another record to enable it again.")
    if st.button("Start another record", key=f"start_another_{dataset_name}"):
        st.session_state[submit_lock_key] = False
        st.session_state.pop(submit_result_key, None)
        st.rerun()
