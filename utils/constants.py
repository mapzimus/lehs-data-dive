"""
Project-wide constants: school codes, gateway cities, dataset IDs, colors.

Codes marked with `# TODO verify` are placeholders to confirm during the first
data-pipeline run by querying the E2C Hub MCAS dataset.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"

# ---------------------------------------------------------------------------
# Focus school + district
# ---------------------------------------------------------------------------

LEHS_SCHOOL_NAME = "Lynn English High"
LEHS_SCHOOL_CODE = "01630510"          # verified 2026-05-18 from MCAS dataset
LYNN_DISTRICT_CODE = "01630000"
LYNN_DISTRICT_NAME = "Lynn"

# ---------------------------------------------------------------------------
# Lynn sibling high schools — the closest comparison group
# (Same district, same city, same policies. Differences isolate
#  school-level effects rather than city-level demographics.)
# ---------------------------------------------------------------------------

LYNN_SIBLING_HS = {
    # All verified from MCAS dataset 2026-05-18
    "Lynn English High":                       "01630510",  # focus school
    "Classical High":                          "01630505",  # Lynn Classical
    "Lynn Vocational Technical Institute":     "01630605",  # Lynn Tech
    "Fredrick Douglass Collegiate Academy":    "01630575",  # alternative HS (note 'Fredrick' spelling)
    "Harold Durgin Success Academy":           "01630525",  # alternative HS
    # Fecteau-Leary Junior/Senior HS — no grade-10 MCAS rows in dataset;
    # serves grades 7-9, look up enrollment via demographics file instead
}

# ---------------------------------------------------------------------------
# All 26 Massachusetts Gateway Cities
# ---------------------------------------------------------------------------

GATEWAY_CITIES = [
    "Attleboro", "Barnstable", "Brockton", "Chelsea", "Chicopee",
    "Everett", "Fall River", "Fitchburg", "Haverhill", "Holyoke",
    "Lawrence", "Leominster", "Lowell", "Lynn", "Malden",
    "Methuen", "New Bedford", "Peabody", "Pittsfield", "Quincy",
    "Revere", "Salem", "Springfield", "Taunton", "Westfield",
    "Worcester",
]  # 26 official MA Gateway Cities per state designation

# District codes for each gateway city — populated during peer-ID step.
# Lynn confirmed = "01630000".
GATEWAY_DISTRICT_CODES: dict[str, str | None] = {city: None for city in GATEWAY_CITIES}
GATEWAY_DISTRICT_CODES["Lynn"] = LYNN_DISTRICT_CODE

# Main comprehensive HS for each gateway city.
# Identified as: school with grade-9 through grade-12 enrollment AND
# highest grade-10 enrollment in the district. Cached after first lookup.
GATEWAY_MAIN_HS: dict[str, dict] = {
    # "Lawrence": {"name": "Lawrence High School", "school_code": "..."},
    # populated by scripts/07_identify_peer_schools.py
}

# ---------------------------------------------------------------------------
# E2C Hub Socrata dataset IDs (4x4 format, e.g., "abcd-1234")
# Discovered/confirmed during first run of scripts/01_download_e2c.py
# ---------------------------------------------------------------------------

E2C_DOMAIN = "educationtocareer.data.mass.gov"

E2C_DATASETS = {
    # name in plan                            : dataset_id  (filled in by discovery)
    "mcas_achievement":                       None,   # MCAS Achievement Results
    "dart_success_after_hs":                  None,   # DART: Success After High School
    "enrollment_demographics":                None,   # Enrollment: Grade/Race/Gender/Selected Populations
    "student_attendance":                     None,   # Student Attendance
    "ap_performance":                         None,   # Advanced Placement (AP) Performance
    "masscore_completion":                    None,   # MassCore Completion
    "staffing_race_gender":                   None,   # Staffing: Race/Ethnicity and Gender
    "school_expenditures":                    None,   # School Expenditures by Spending Category
    "district_expenditures":                  None,   # District Expenditures by Spending Category
    "graduation_rates":                       None,   # High School Graduation Rates
    "pathways_enrollment":                    None,   # Pathways/Programs Enrollment
    "plans_of_graduates":                     None,   # Plans of High School Graduates
    "special_ed_indicators":                  None,   # Special Education Indicators
    "early_college_credits":                  None,   # Early College Credits
    "early_college_participation":            None,   # Early College Participation
    "college_career_outcomes":                None,   # College and Career Outcomes of HS Graduates
    "earnings_by_industry":                   None,   # Average Earnings of HS Graduates by Industry
    "postsecondary_fall_enrollment":          None,   # Public Postsecondary Fall Enrollment
    "postsecondary_retention":                None,   # Public Postsecondary First Year Retention
    "postsecondary_awards":                   None,   # Public Postsecondary Awards Conferred
    "postsecondary_tuition":                  None,   # Public Postsecondary Tuition and Fees
    "dlcs_course_taking":                     None,   # DLCS Course Taking Dashboard
    "student_progression_hs_to_postsec":      None,   # Student Progression HS → Postsecondary
}

# ---------------------------------------------------------------------------
# Year ranges
# ---------------------------------------------------------------------------

CURRENT_SCHOOL_YEAR = 2025
EARLIEST_YEAR = 2017          # most datasets start here
ENROLLMENT_EARLIEST = 1994    # demographic file goes back furthest

# ---------------------------------------------------------------------------
# Student groups (standardized DESE labels)
# ---------------------------------------------------------------------------

STUDENT_GROUPS = [
    "All Students",
    "Female", "Male",
    "African American/Black",
    "Asian",
    "Hispanic/Latino",
    "White",
    "Multi-Race, Non-Hispanic/Latino",
    "Native American",
    "Native Hawaiian/Pacific Islander",
    "English Learner",
    "Former English Learner",
    "Students w/ Disabilities",
    "High Needs",
    "Low Income",
    "Economically Disadvantaged",
]

# ---------------------------------------------------------------------------
# Chart colors (Lynn English: navy + gold)
# ---------------------------------------------------------------------------

LEHS_NAVY = "#0A1F44"
LEHS_GOLD = "#FFB81C"
LYNN_SIBLING_COLOR = "#7B8FA1"
GATEWAY_PEER_COLOR = "#B0BEC5"
STATE_COLOR = "#455A64"

SUBGROUP_PALETTE = {
    "All Students":                    "#0A1F44",
    "African American/Black":          "#D32F2F",
    "Asian":                           "#7B1FA2",
    "Hispanic/Latino":                 "#F57C00",
    "White":                           "#1976D2",
    "Multi-Race, Non-Hispanic/Latino": "#00897B",
    "English Learner":                 "#388E3C",
    "Former English Learner":          "#689F38",
    "Students w/ Disabilities":        "#5D4037",
    "Low Income":                      "#C2185B",
    "High Needs":                      "#7E57C2",
}
