# Deploying the LEHS Data Dive to maxwellhowegis.com/Lynn-data-dive

End state: visitors hit **`https://maxwellhowegis.com/Lynn-data-dive`** and see the
full dashboard embedded inline on a child page of your existing GitHub Pages site.

Architecture:

```
GitHub Pages (maxwellhowegis.com)
    └── /Lynn-data-dive/index.html   ← static HTML page with full-bleed iframe
            ↓
            iframe embed of
            ↓
Streamlit Community Cloud
    └── lynn-data-dive.streamlit.app  ← actual dashboard, served from your GitHub repo
            ↓
            sourced from
            ↓
GitHub: mapzimus/lehs-data-dive       ← code + processed Parquet/GeoJSON files
```

This works because the data is already committed (~53 MB processed Parquet + GeoJSON).
No additional download step is required at app start.

---

## Step 1 — Deploy to Streamlit Community Cloud (free)

1. Go to <https://share.streamlit.io/> and sign in with GitHub.
2. Click **"New app"** (top right).
3. Fill in:
   - **Repository**: `mapzimus/lehs-data-dive`
   - **Branch**: `main`
   - **Main file path**: `Home.py`
   - **App URL** (custom subdomain): `lehs-data-dive` *(or whatever you like)*
4. Click **"Advanced settings"**:
   - **Python version**: `3.12`
   - Leave everything else default
5. Click **"Deploy!"**.

First deploy takes ~5–10 minutes (installs all dependencies from `requirements.txt`).
When it finishes, you'll have a public URL like `https://lynn-data-dive.streamlit.app`.

**If deployment fails** because of `geopandas` install errors, add a file at the
repo root called `packages.txt` with one line:

```
libgeos-dev
```

…then commit, push, and click "Reboot app" in Streamlit Cloud.

---

## Step 2 — Add the child page to your GitHub Pages site

This step lives in **your maxwellhowegis.com repository**, not the `lehs-data-dive` repo.

1. Find your maxwellhowegis.com source repo on GitHub (e.g.
   `mapzimus/mapzimus.github.io` or whatever you set up).
2. Clone it locally (or edit on github.com directly).
3. Create a folder `Lynn-data-dive/` at the repo root.
4. Inside that folder, drop the `index.html` file in this repo at
   `deploy/maxwellhowegis-Lynn-data-dive.html` (rename to `index.html`).
5. **Edit one line** in `index.html`: change

   ```html
   const STREAMLIT_URL = "https://lynn-data-dive.streamlit.app";
   ```

   …to your actual Streamlit Cloud URL from Step 1.
6. Commit and push.
7. GitHub Pages republishes within 1–2 minutes. Visit
   <https://maxwellhowegis.com/Lynn-data-dive> to verify.

---

## Step 3 — Ongoing data refreshes (when DESE releases new data)

When DESE updates a dataset (annually, usually August–October):

```powershell
cd C:\Users\Calen\lehs-data-center

# Re-pull the source CSVs
python scripts\01_download_e2c.py

# Re-process to filtered Parquet
python scripts\08_build_master_panel.py

# Test locally
streamlit run Home.py

# Commit + push
git add data/processed
git commit -m "Refresh data — SY 20XX–YY"
git push
```

Streamlit Cloud auto-redeploys within ~30 seconds of the push.

---

## Notes

- The Streamlit app is **public** — anyone with the URL can view it. There's
  no login layer (intentional, since this is meant to be a public resource).
- The Streamlit Cloud **free tier** allows 1 app per workspace, 1 GB RAM, and
  community-shared compute. Should be plenty for this dashboard.
- **Catchment Research** page images (the static PNGs from your PDF) are in
  `data/processed/lehs_research/` and committed to the repo. They render at
  full resolution inside the deployed app.
- If you ever want to move from the iframe approach to a true subpath
  (`maxwellhowegis.com/Lynn-data-dive` as the streamlit app itself, not in
  an iframe), you'd need to host on your own server with an nginx reverse
  proxy. That's noticeably more work; iframe-on-GitHub-Pages is the right
  tradeoff for now.
