# RH Database App

A local Streamlit app for recording your RH Database data (Students, Attendance,
Performance, Items, Food, Sponsorship) via **single entry** or **bulk upload**,
writing straight to a **MySQL database**, with **login + role-based access**
(admin vs staff) and an **admin dashboard**.

---

## 1. Install

Requires Python 3.10+.

```bash
cd rh_app
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Connect it to your MySQL database

Your database connection details already live in `.streamlit/secrets.toml`,
pre-filled for the  MySQL server you provided:



If you ever need to point the app at a different MySQL server, copy
`config/secrets.toml.example` to `.streamlit/secrets.toml` and fill in the
new values — never commit the real `secrets.toml` to version control (it's
already in `.gitignore`).


### Create the tables

Run this once to create all 7 tables (Student Database, Center Attendance,
Students Performance, Students Item, Food Database, Food Items, Sponsorship):

```bash
python init_db.py
```

The initializer creates missing tables, ensures `student_database.Student_DoB`
and `student_database.Student_Parent` are nullable, and removes the obsolete
`students_performance.Name` column from existing installations. Removing that
column also removes any names previously stored in it; use `Student_ID` as the
student reference. You should see
`All tables created (or already existed).` when it succeeds.
If it times out or refuses the connection, check that your network/firewall
allows outbound connections to port 15575, and double-check the credentials
in `secrets.toml`.

### How the tables are structured

- **student_database** — `Student_Id` is the **primary key**.
- **center_attendance**, **students_performance**, **students_item**,
  **sponsorship** — each has a foreign key back to `student_database.Student_Id`.
  This means: **you must add a student to Student Database before you can
  record attendance, performance, items, or sponsorship for them.** If you
  try to enter a Student_Id that doesn't exist yet, the app will tell you
  clearly instead of failing silently.
- **food_items**, **food_database** — standalone, no dependency on students.



**Change these before real use.** Log in as an admin and open **User
Management** in the sidebar to create accounts, change names/emails/roles and
passwords, or delete accounts. Passwords are stored as bcrypt hashes. The
last admin cannot be demoted or deleted, and admins cannot delete their own
account. Alternatively, add/update users from the command line with:

```bash
python utils/manage_users.py
```

Follow the prompts to add a user with a chosen role (`admin` or `staff`).
Remove demo accounts from **User Management** after creating your own accounts.

Also change the `cookie.key` value in `config/users.yaml` to any random
string — this secures the login session cookie.



This opens the app in your browser (usually `http://localhost:8501`).
Log in, then use the sidebar to reach:

- **Single Entry** — pick a dataset, fill the form, submit one record.
- **Bulk Upload** — pick a dataset, download the Excel template, fill it in
  (in Excel or Google Sheets), upload it, preview, and submit many records
  at once. Rows that fail (e.g. missing student, duplicate ID) are reported
  individually rather than failing the whole batch.
- **Dashboard** *(admin only)* — KPIs and charts across all datasets, pulled
  live from the database.

## Roles

- **admin** — Single Entry, Bulk Upload, Dashboard, and User Management.
- **staff** — Single Entry and Bulk Upload only (no Dashboard access).

Excel templates include dropdowns for schema choice fields and date validation
for date columns.

## Notes

- Computed columns (`Yearly_Average`, `Total_Cost`, `Meals_Served`) are calculated
  automatically by the app — don't include them in your bulk-upload files.
- Students Item records use `School_Year` and a `Term` dropdown (`First Term`,
  `Second Term`, `Third Term`). Running `python init_db.py` migrates existing
  item dates to a school year based on the date's calendar year (for example,
  2021 becomes `2021-2022`).
- In Food Database, `Total_Cost` is `Purchased_Quantity × Purchase_Unity_Cost`.
  `Meals_Served` is computed as `Quantity_Used × 5` for Rice and
  `Quantity_Used × 13` for Mixed Porridge Flour; it is blank for other items.
  Run `python init_db.py` to recalculate existing Food Database rows.
- Because of the foreign key relationships, always **load Student Database
  first** (single entry or bulk) before loading Attendance, Performance,
  Items, or Sponsorship data for those same students.
- Dashboard data is cached for 30 seconds to reduce database load; use the
  "Refresh data" button for the latest numbers.
- To add a brand-new field to a dataset, edit `utils/schemas.py`, then
  re-run `python init_db.py` (existing tables are left alone; you'd need to
  `ALTER TABLE` manually to add a column to data already in production).
