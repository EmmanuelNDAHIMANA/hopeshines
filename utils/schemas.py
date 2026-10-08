"""
Schema definitions for every dataset in the RH Database.
Each schema drives: the single-entry form, bulk-upload validation,
and the MySQL table that the data is written to.

field types:
    "text"     -> free text input
    "number"   -> numeric input
    "date"     -> date picker, stored as YYYY-MM-DD string
    "select"   -> dropdown, needs "options"
    "computed" -> not entered by the user, calculated automatically
"""

from utils.food_catalog import FOOD_ITEMS, PURCHASE_UNITS, FOOD_CATEGORIES

SCHOOL_YEARS = [
    "2020-2021", "2021-2022", "2022-2023", "2023-2024", "2024-2025",
    "2025-2026", "2026-2027", "2027-2028", "2028-2029",
]

SCHEMAS = {
    "Student Database": {
        "table": "student_database",
        "pk": "Student_Id",
        "autoincrement_pk": False,
        "foreign_key": None,
        "fields": [
            {"name": "Student_Id", "type": "text", "required": True},
            {"name": "Student_Name", "type": "text", "required": True},
            {"name": "Student_DoB", "type": "date", "required": False},
            {"name": "Student_Gender", "type": "select", "options": ["Male", "Female"], "required": True},
            {"name": "Student_Parent", "type": "text", "required": False},
            {"name": "Parent_Phone", "type": "text", "required": False},
            {"name": "Parental_Status", "type": "select", "options": ["Mother", "Father", "Both", "Guardian", "Orphan"], "required": False},
            {"name": "Disability_Status", "type": "select", "options": ["No", "Yes"], "required": False},
            {"name": "Sponsorship_Status", "type": "select", "options": ["YES", "NO"], "required": False},
        ],
    },
    "Center Attendence": {
        "table": "center_attendance",
        "pk": "id",
        "autoincrement_pk": True,
        "foreign_key": {"column": "Students_ID", "references_dataset": "Student Database"},
        "fields": [
            {"name": "Date", "type": "date", "required": True},
            {"name": "Students_ID", "type": "text", "required": True},
            {"name": "Holiday", "type": "select", "options": ["No", "Yes"], "required": True},
            {"name": "Interventions", "type": "select", "options":["English Proficiency","Computer Leteracy" ,"Music and Dance","Arts and Crafts","Soap Making","Tailoring","Hair Dressing","Snacks making"], "required": False},
        ],
    },
    "Students Performance": {
        "table": "students_performance",
        "pk": "id",
        "autoincrement_pk": True,
        "foreign_key": {"column": "Student_ID", "references_dataset": "Student Database"},
        "fields": [
            {"name": "Date", "type": "date", "required": True},
            {"name": "School_Year", "type": "select", "options": SCHOOL_YEARS, "required": True},
            {"name": "Student_ID", "type": "text", "required": True},
            {"name": "School", "type": "text", "required": False},
            {"name": "Class", "type": "select", "options":["ECD1","ECD2","ECD3", "NS1", "NS2", "NS3", "P1", "P2", "P3", "P4", "P5", "P6", "S1", "S2", "S3", "S4", "S5", "S6", "Level1", "Level2", "Level3", "Level4", "Level5"], "required": False},
            {"name": "Term1_Score", "type": "number", "required": False},
            {"name": "Term2_Score", "type": "number", "required": False},
            {"name": "Term3_Score", "type": "number", "required": False},
            {"name": "Yearly_Average", "type": "computed", "required": False},
        ],
    },
    "Students Item": {
        "table": "students_item",
        "pk": "id",
        "autoincrement_pk": True,
        "foreign_key": {"column": "Student_Id", "references_dataset": "Student Database"},
        "fields": [
            {"name": "School_Year", "type": "select", "options": SCHOOL_YEARS, "required": True},
            {"name": "Term", "type": "select", "options": ["First Term", "Second Term", "Third Term"], "required": True},
            {"name": "Student_Id", "type": "text", "required": True},
            {"name": "Item_Received", "type": "text", "required": True},
            {"name": "Quantity", "type": "number", "required": False},
            {"name": "Price", "type": "number", "required": False},
            {"name": "Total_Cost", "type": "computed", "required": False},
        ],
    },
    "Food Database": {
        "table": "food_database",
        "pk": "id",
        "autoincrement_pk": True,
        "foreign_key": None,
        "fields": [
            {"name": "Date", "type": "date", "required": True},
            {"name": "Food_Item", "type": "select", "options": FOOD_ITEMS, "cascade": "food_item", "required": True},
            {"name": "Purchase_Unit", "type": "select", "options": PURCHASE_UNITS, "cascade": "purchase_unit", "required": False},
            {"name": "Food_Category", "type": "select", "options": FOOD_CATEGORIES, "cascade": "food_category", "required": False},
            {"name": "Opening_Balance", "type": "number", "required": False},
            {"name": "Purchased_Quantity", "type": "number", "required": False},
            {"name": "Purchase_Unity_Cost", "type": "number", "required": False},
            {"name": "Total_Cost", "type": "computed", "required": False},
            {"name": "Quantity_Used", "type": "number", "required": False},
            {"name": "Meals_Served", "type": "computed", "required": False},
        ],
    },
    "Food Items": {
        "table": "food_items",
        "pk": "Food_Item",
        "autoincrement_pk": False,
        "foreign_key": None,
        "fields": [
            {"name": "Food_Item", "type": "text", "required": True},
            {"name": "Unity", "type": "text", "required": False},
            {"name": "Category", "type": "text", "required": False},
        ],
    },
    "Sponsorship": {
        "table": "sponsorship",
        "pk": "Student_ID",
        "autoincrement_pk": False,
        "foreign_key": {"column": "Student_ID", "references_dataset": "Student Database"},
        "fields": [
            {"name": "Student_ID", "type": "text", "required": True},
            {"name": "Sponsor_Name", "type": "text", "required": True},
        ],
    },
}

# Roles that may create/edit records in each dataset.
# Admin always has full access; this only restricts the "staff" role.
STAFF_ALLOWED_DATASETS = list(SCHEMAS.keys())  # staff can enter data into all datasets by default

# Datasets must be created in this order so foreign keys resolve correctly.
CREATION_ORDER = [
    "Student Database",
    "Food Items",
    "Center Attendence",
    "Students Performance",
    "Students Item",
    "Food Database",
    "Sponsorship",
]
