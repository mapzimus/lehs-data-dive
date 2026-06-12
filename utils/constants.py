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
ASSETS_DIR = PROJECT_ROOT / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

# ---------------------------------------------------------------------------
# Focus school + district
# ---------------------------------------------------------------------------

LEHS_SCHOOL_NAME = "Lynn English High"
LEHS_SCHOOL_CODE = "01630510"          # verified 2026-05-18 from MCAS dataset
LCHS_SCHOOL_NAME = "Classical High"
LCHS_SCHOOL_CODE = "01630505"          # Lynn Classical High — Lynn's other comprehensive HS
LYNN_DISTRICT_CODE = "01630000"
LYNN_DISTRICT_NAME = "Lynn Public Schools"   # the district — distinct from LEHS the school

# Reminder: "Lynn" by itself almost always refers to the DISTRICT (16,000+
# students, 22 schools). When you want to talk about Lynn English High
# specifically, use LEHS. When the comparison is school-to-school
# (e.g., gateway-city main HS) use LEHS_SCHOOL_CODE. When the comparison
# is district-to-district, use LYNN_DISTRICT_CODE. LCHS is the other
# major comprehensive HS in the same district and belongs alongside LEHS
# in any school-to-school chart.

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

# Accountability GROUP label -> the STU_GRP label used by the multi-year trend
# parquets (graduation_rates / dropout / student_attendance /
# advanced_course_completion / mcas_achievement / el_access). "English Learners"
# is the nearest *published* trend series for the combined EL+Former-EL
# accountability group — a proxy, not an identity; callers should note that in a
# caption. mcas_achievement also carries an NBSP variant of the combined label,
# so normalize STU_GRP with .str.replace("\xa0", " ") before matching.
# "Lowest Performing" is intentionally absent: it is an accountability-internal
# construct with no trend series anywhere.
ACCT_GROUP_TO_STU_GRP = {
    "All Students": "All Students",
    "English Learners and Former English Learners": "English Learners",
    "Low Income": "Low Income",
    "Students with Disabilities": "Students with Disabilities",
    "High Needs": "High Needs",
    "Hispanic or Latino": "Hispanic or Latino",
    "Black or African American": "Black or African American",
    "Asian": "Asian",
    "White": "White",
    "Multi-Race, Not Hispanic or Latino": "Multi-Race, Not Hispanic or Latino",
    "American Indian or Alaska Native": "American Indian or Alaska Native",
    "Native Hawaiian or Other Pacific Islander": "Native Hawaiian or Other Pacific Islander",
}

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
# Chart colors — pastels.
#
# Per Max (2026-05-26): "lean towards lighter pastel colors". Brand cue is
# still LEHS navy + gold, but muted/lifted so neighboring charts read as a
# calmer surface. Subgroup palette pastel-pivoted to match.
#
# CONTRAST NOTE (2026-06-05): the five tokens below are used mainly as chart
# LINES / MARKERS / reference lines on a near-white plot bg (#FAFBFD/#FFFFFF).
# The original pastels were so light they failed WCAG and were nearly invisible
# as 1-2px lines, so they have been darkened to a muted-but-legible tone while
# staying in the same hue family (gold / slate-blue). Each now clears ~3:1
# against white (LEHS_NAVY clears ~4.5:1 for use as chart text), verified with
# the standard WCAG relative-luminance formula. The pastel FILL palettes below
# (SUBGROUP_PALETTE / GENDER_PALETTE / MOBILITY_PALETTE) are deliberately left
# pastel — they're large bar fills, not thin lines, so they read fine.
# Old values are preserved as comments in case we ever want to revert.
# ---------------------------------------------------------------------------

LEHS_NAVY = "#5C74A6"           # 4.66:1 vs #FFF (text-grade) — was "#7A8FB8" (3.26:1), orig "#0A1F44" — dusty navy
LEHS_GOLD = "#B68C1B"           # 3.11:1 vs #FFF — was "#F4D88A" (1.40:1), orig "#FFB81C" — muted antique gold
LYNN_SIBLING_COLOR = "#8294AE"  # 3.09:1 vs #FFF — was "#C2CCD9" (1.62:1), orig "#7B8FA1" — mid pastel slate
GATEWAY_PEER_COLOR = "#8595A6"  # 3.07:1 vs #FFF — was "#DBE2E8" (1.31:1), orig "#B0BEC5" — light neutral slate so LEHS pops
STATE_COLOR = "#76869A"         # 3.72:1 vs #FFF — was "#A8B5BD" (2.10:1), orig "#455A64" — darker slate reference line

SUBGROUP_PALETTE = {
    "All Students":                    "#7A8FB8",  # dusty navy
    "African American/Black":          "#E89B9B",  # pastel coral
    "Asian":                           "#C5A8D6",  # pastel violet
    "Hispanic/Latino":                 "#F5C28B",  # pastel orange
    "White":                           "#A6C8E8",  # pastel sky
    "Multi-Race, Non-Hispanic/Latino": "#9CCFC4",  # pastel teal
    "English Learner":                 "#B5D6A8",  # pastel leaf
    "Former English Learner":          "#C8DEA8",  # lighter leaf
    "Students w/ Disabilities":        "#C2A99E",  # dusty taupe
    "Low Income":                      "#E8A8C2",  # pastel rose
    "High Needs":                      "#BDAFD9",  # pastel lavender
    "Economically Disadvantaged":      "#D6B89C",  # pastel tan
    "First Lang Not English":          "#AAB4E8",  # pastel periwinkle
}

# Gender + student-mobility series palettes — pastel, brand-adjacent, so the
# School Profile charts stop reaching for ad-hoc saturated hex values.
GENDER_PALETTE = {
    "Female":     "#E8A8C2",  # pastel rose
    "Male":       "#A6C8E8",  # pastel sky
    "Non-binary": "#F4D88A",  # cream gold
}

# Lynn Vocational Technical Institute — a teal distinct from navy + gold, so the
# three Lynn comprehensive HS read apart on finance / discipline charts. Was
# defined inline in pages 7 + 8; centralized here so a rebrand is one edit.
LVTI_COLOR = "#26A69A"

# Sequential blue ramp for the five MCAS / AP score levels (ordinal 1-5). Was
# defined inline in pages/4; centralized for cross-page consistency.
AP_SCORE_COLORS = {
    "1": "#DEEBF7", "2": "#9ECAE1", "3": "#6BAED6", "4": "#3182BD", "5": "#08519C",
}
MOBILITY_PALETTE = {
    "Stability":       LEHS_NAVY,
    "Churn":           "#E89B9B",  # pastel coral — muted "negative"
    "Mid-year intake": "#F5C28B",  # pastel orange
}
