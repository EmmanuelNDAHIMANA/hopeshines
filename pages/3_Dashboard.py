import re

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.auth import require_admin
from utils.schemas import SCHEMAS
from utils.db import fetch_dataframe, clear_cache

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
username, role = require_admin()

st.title("📊 Dashboard")

if st.button("🔄 Refresh data"):
    clear_cache()
    st.rerun()

# --- Load all datasets ---
data = {}
for name, schema in SCHEMAS.items():
    headers = [f["name"] for f in schema["fields"]]
    try:
        data[name] = fetch_dataframe(name)
    except Exception as e:
        data[name] = pd.DataFrame(columns=headers)
        st.warning(f"Could not load '{name}': {e}")

students = data["Student Database"]
attendance = data["Center Attendence"]
performance = data["Students Performance"]
items = data["Students Item"]
food = data["Food Database"]
sponsorship = data["Sponsorship"]

# --- Top-level KPIs ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Students", len(students))
k2.metric("Sponsored Students", len(sponsorship))
k3.metric("Attendance Records", len(attendance))
k4.metric("Performance Records", len(performance))

st.divider()

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Students", "Attendance", "Performance", "Items & Food", "Sponsorship"]
)

with tab1:
    st.subheader("Student Overview")
    c1, c2 = st.columns(2)
    if not students.empty and "Student_Gender" in students.columns:
        c1.write("**By Gender**")
        c1.bar_chart(students["Student_Gender"].value_counts())
    if not students.empty and "Sponsorship_Status" in students.columns:
        c2.write("**By Sponsorship Status**")
        c2.bar_chart(students["Sponsorship_Status"].value_counts())
    if not students.empty and "Disability_Status" in students.columns:
        st.write("**By Disability Status**")
        st.bar_chart(students["Disability_Status"].value_counts())
    st.write("**Full Student Database**")
    student_column_config = {}
    if "Parent_Phone" in students.columns:
        students["Parent_Phone"] = students["Parent_Phone"].astype("string")
        student_column_config["Parent_Phone"] = st.column_config.TextColumn(
            "Parent_Phone"
        )
    st.dataframe(
        students,
        column_config=student_column_config,
        use_container_width=True,
    )

with tab2:
    st.subheader("Center Attendance")
    if not attendance.empty and "Interventions" in attendance.columns:
        st.write("**Sessions by Intervention Type**")
        st.bar_chart(attendance["Interventions"].value_counts())
    if not attendance.empty and "Holiday" in attendance.columns:
        st.write("**Holiday vs Non-Holiday Records**")
        st.bar_chart(attendance["Holiday"].value_counts())
    st.dataframe(attendance, use_container_width=True)

with tab3:
    st.subheader("Student Performance")
    if not performance.empty and "Yearly_Average" in performance.columns:
        perf_numeric = performance[performance["Yearly_Average"] != 0].copy()
        perf_numeric["Yearly_Average"] = pd.to_numeric(perf_numeric["Yearly_Average"], errors="coerce")
        c1, c2 = st.columns(2)
        if "Class" in perf_numeric.columns:
            c1.write("**Average Score by Class**")
            c1.bar_chart(perf_numeric.groupby("Class")["Yearly_Average"].mean())
        if "School_Year" in perf_numeric.columns:
            c2.write("**Average Score by School Year**")
            c2.bar_chart(perf_numeric.groupby("School_Year")["Yearly_Average"].mean())

    st.subheader("Class Repeating by School Year")
    required_repeat_columns = {"Student_ID", "Class", "School_Year"}
    if performance.empty or not required_repeat_columns.issubset(performance.columns):
        st.info("Repeating analysis needs Student_ID, Class, and School_Year records.")
    else:
        repeat_data = performance.copy()
        repeat_data["Student_ID"] = repeat_data["Student_ID"].astype("string").str.strip()
        repeat_data["Class"] = repeat_data["Class"].astype("string").str.strip()
        repeat_data["School_Year"] = repeat_data["School_Year"].astype("string").str.strip()
        repeat_data = repeat_data[
            repeat_data["Student_ID"].notna()
            & repeat_data["Student_ID"].ne("")
            & repeat_data["Class"].notna()
            & repeat_data["Class"].ne("")
            & repeat_data["School_Year"].notna()
            & repeat_data["School_Year"].ne("")
        ].copy()

        def school_year_start(value):
            match = re.search(r"(?:19|20)\d{2}", str(value))
            return int(match.group(0)) if match else None

        if repeat_data.empty:
            st.info("No performance rows have a student, class, and school year to compare.")
        else:
            repeat_data["_school_year_start"] = repeat_data["School_Year"].map(school_year_start)
            year_labels = (
                repeat_data[["School_Year", "_school_year_start"]]
                .drop_duplicates()
                .sort_values(["_school_year_start", "School_Year"], na_position="last")["School_Year"]
                .tolist()
            )
            year_labels = [year for year in year_labels if year]

            if "Date" in repeat_data.columns:
                repeat_data["_record_date"] = pd.to_datetime(repeat_data["Date"], errors="coerce")
                valid_dates = repeat_data["_record_date"].dropna()
            else:
                repeat_data["_record_date"] = pd.NaT
                valid_dates = pd.Series(dtype="datetime64[ns]")

            selected_range = None
            if not valid_dates.empty:
                min_date = valid_dates.min().date()
                max_date = valid_dates.max().date()
                selected_range = st.date_input(
                    "Performance record date range",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="performance_repeat_date_range",
                )
                if isinstance(selected_range, (tuple, list)):
                    if len(selected_range) == 2:
                        range_start, range_end = selected_range
                        repeat_data = repeat_data[
                            repeat_data["_record_date"].between(
                                pd.Timestamp(range_start),
                                pd.Timestamp(range_end) + pd.Timedelta(days=1) - pd.Timedelta(nanoseconds=1),
                            )
                        ].copy()
                    elif len(selected_range) == 1:
                        selected_day = selected_range[0]
                        repeat_data = repeat_data[
                            repeat_data["_record_date"].dt.date.eq(selected_day)
                        ].copy()
                else:
                    repeat_data = repeat_data[
                        repeat_data["_record_date"].dt.date.eq(selected_range)
                    ].copy()
            else:
                st.caption("No usable performance dates are available for a date-range filter.")

            year_pairs = {
                (school_year_start(year), year)
                for year in year_labels
                if school_year_start(year) is not None
            }
            comparable_targets = [
                year
                for start_year, year in sorted(year_pairs)
                if any(previous_start == start_year - 1 for previous_start, _ in year_pairs)
            ]
            if not comparable_targets:
                st.info("At least two consecutive School_Year values are needed for repeating analysis.")
            else:
                selected_years = st.multiselect(
                    "School year(s) to compare",
                    options=comparable_targets,
                    default=comparable_targets,
                    key="performance_repeat_years",
                )

                # Use the latest dated class record for each student in each school year.
                repeat_data = repeat_data.reset_index(drop=True)
                repeat_data["_source_order"] = range(len(repeat_data))
                latest_classes = (
                    repeat_data.sort_values(["_record_date", "_source_order"], na_position="first")
                    .drop_duplicates(["School_Year", "Student_ID"], keep="last")
                )
                year_start_map = {
                    year: school_year_start(year)
                    for year in latest_classes["School_Year"].unique()
                }
                start_to_year = {
                    start: year for year, start in year_start_map.items() if start is not None
                }
                summary_rows = []
                for current_year in selected_years:
                    current_start = school_year_start(current_year)
                    previous_year = start_to_year.get(current_start - 1) if current_start is not None else None
                    if previous_year is None:
                        continue
                    previous_records = latest_classes[latest_classes["School_Year"] == previous_year]
                    current_records = latest_classes[latest_classes["School_Year"] == current_year]
                    matched = previous_records[["Student_ID", "Class"]].merge(
                        current_records[["Student_ID", "Class"]],
                        on="Student_ID",
                        suffixes=("_previous", "_current"),
                    )
                    matched["_same_class"] = (
                        matched["Class_previous"].str.casefold()
                        == matched["Class_current"].str.casefold()
                    )
                    repeated_count = int(matched["_same_class"].sum())
                    comparable_count = len(matched)
                    summary_rows.append({
                        "Previous School Year": previous_year,
                        "School Year": current_year,
                        "Repeating Students": repeated_count,
                        "Students Recorded in Both Years": comparable_count,
                        "Previous-year Students": len(previous_records),
                        "Current-year Students": len(current_records),
                        "Repeating %": (
                            round(repeated_count / comparable_count * 100, 1)
                            if comparable_count else None
                        ),
                    })
                if summary_rows:
                    repeat_summary = pd.DataFrame(summary_rows)
                    st.caption(
                        "Repeating % = students whose latest recorded class stayed the same "
                        "÷ students with class records in both adjacent school years. "
                        "The date range filters records in both years."
                    )
                    chart_data = repeat_summary.dropna(subset=["Repeating %"])
                    if not chart_data.empty:
                        st.bar_chart(chart_data.set_index("School Year")["Repeating %"])
                    else:
                        st.info("No comparable students were found for the selected year and date filters.")
                    st.dataframe(
                        repeat_summary,
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.info("No adjacent school-year pairs with records match the selected filters.")
    st.dataframe(performance, use_container_width=True)

with tab4:
    st.subheader("Items Distributed")
    if not items.empty and "Item_Received" in items.columns:
        st.write("**Items Distributed (count)**")
        st.bar_chart(items["Item_Received"].value_counts())
    st.dataframe(items, use_container_width=True)

    st.subheader("Food Database")
    if not food.empty and "Food_Item" in food.columns:
        food_numeric = food.copy()
        food_numeric["Meals_Served"] = pd.to_numeric(food_numeric.get("Meals_Served"), errors="coerce")
        st.write("**Meals Served by Food Item**")
        meals_by_item = food_numeric.groupby("Food_Item")["Meals_Served"].sum()
        meals_by_item = meals_by_item[meals_by_item > 0]
        if meals_by_item.empty:
            st.info("No food items have Meals Served greater than zero.")
        else:
            st.bar_chart(meals_by_item.sort_values(ascending=False))
    st.dataframe(food, use_container_width=True)

with tab5:
    st.subheader("Sponsorship")
    if not sponsorship.empty and "Sponsor_Name" in sponsorship.columns:
        st.write("**Students per Sponsor**")
    sponsor_counts=(sponsorship.groupby("Sponsor_Name", as_index=False).agg(Count=("Sponsor_Name", "size")).sort_values(by="Count", ascending=False).reset_index(drop=True))
    fig = px.bar(sponsor_counts, x="Sponsor_Name", y="Count",title="Students per Sponsor")

    fig.update_xaxes(categoryorder="array", categoryarray=sponsor_counts["Sponsor_Name"].tolist())

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(sponsorship, use_container_width=True)
