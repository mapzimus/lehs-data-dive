# LEHS Data Information Center

A public, integrated data dashboard for **Lynn English High School** (Lynn, MA) and its peer high schools across the 26 Massachusetts Gateway Cities.

This project aggregates every relevant public dataset DESE publishes — MCAS, demographics, attendance, discipline, finance, teacher workforce, college outcomes, and more — into a single school-level narrative with cross-domain correlation analysis no DESE tool currently provides.

**Status:** Early development. Built standalone first at `data.maxwellhowegis.com`, eventually migrating into the LEHS howe2math area.

---

## Why this exists

DESE publishes excellent data but in silos. The School & District Performance Power BI, the Teach Mass educator dashboard, the E2C Hub, the WIDA reports, the statereport bulk downloads, RADAR comparable districts, profiles.doe.mass.edu — each holds a piece of the picture, and none of them are joined together at the school level for Lynn English.

This dashboard pulls everything into one Python environment, joins it on `(school_code, year)`, and exposes:

- **Integration**: Demographics → MCAS → graduation → college, with ELL outcomes threaded throughout
- **Three peer cohorts**: Lynn sibling HS (Classical, Tech, Fecteau-Leary, Frederick Douglass), full Lynn district, and 25 gateway-city main high schools
- **Cross-domain correlations**: per-pupil spending vs. MCAS, teacher diversity vs. subgroup growth, 9th-grade absenteeism vs. college persistence, etc.

---

## Tech stack

- Python 3.12 (conda env)
- pandas / numpy / scipy / statsmodels — data
- Streamlit — web app
- Plotly — interactive charts
- GitHub + Streamlit Community Cloud — hosting

---

## Data sources

See `data/raw/` subfolders and `pages/99_Methodology.py` for full citations. Categories:

- **E2C Hub** (educationtocareer.data.mass.gov) — Socrata API, ~15 datasets
- **DESE Profiles statereport** — bulk CSVs for discipline, climate, staffing detail
- **Federal CRDC, IPEDS, NCES** — civil rights, postsecondary, school-level federal data
- **Census ACS / SAIPE** — Lynn community context
- **EPA EJScreen / CDC PLACES** — environment and health context
- **Local downloads** — `reporting-element4.xlsx` (former-EL MCAS), `state.docx` (WIDA)

---

## Local development

```powershell
# Create the conda environment (one-time)
conda env create -f environment.yml
# or:
conda create -n lehs python=3.12 -y
conda activate lehs
pip install -r requirements.txt

# Refresh data (annual or as DESE releases updates)
python scripts/refresh_all.py

# Run the app
streamlit run app.py
```

---

## Repository structure

```
lehs-data-dive/
├── app.py                    # Streamlit landing page
├── pages/                    # 12 dashboard pages + methodology
├── data/
│   ├── raw/                  # Downloaded source files (gitignored)
│   └── processed/            # Joined Parquet files (committed)
├── scripts/                  # Data download + processing pipeline
├── utils/                    # Shared helpers (loaders, charts, interpretation)
└── reports/                  # Annual PDF "State of LEHS" snapshots
```

---

## Data refresh cadence

DESE updates most E2C Hub datasets annually (typically August–October for prior school year). The GitHub Action in `.github/workflows/refresh-data.yml` runs `scripts/refresh_all.py` on a schedule and opens a PR with updated data; merging triggers a Streamlit Cloud redeploy.

---

## License

Data is sourced from public DESE, federal, and state agency datasets. Code is MIT-licensed. Attribution requested when reusing.
