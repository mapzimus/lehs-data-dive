# Deploying the LEHS Data Dive

End state: visitors hit **`https://maxwellhowegis.com/Lynn-data-dive`** and see the
full dashboard embedded inline on a child page of your existing GitHub Pages site.

Architecture:

```
GitHub Pages (maxwellhowegis.com)
    └── /Lynn-data-dive/index.html   ← static HTML page with full-bleed iframe
            ↓
            iframe embed of
            ↓
Railway (always-on service)
    └── generated Railway domain      ← backend URL is not shown in the address bar
            ↓
            sourced from
            ↓
GitHub: mapzimus/lehs-data-dive       ← code + processed Parquet/GeoJSON files
```

This works because the data is already committed (~53 MB processed Parquet + GeoJSON).
No additional download step is required at app start.

---

## Step 1 — Deploy to Railway

1. Go to <https://railway.com/new> and sign in with GitHub.
2. Choose **Deploy from GitHub repo**, then select `mapzimus/lehs-data-dive`.
3. Railway detects `railway.json` and builds the included `Dockerfile`.
4. In the service's **Settings → Networking**, click **Generate Domain**.
5. Open the generated URL and confirm the dashboard loads.

The service listens on Railway's injected `PORT`, exposes Streamlit's health endpoint,
and restarts automatically after failures. Keep at least one replica running so the
dashboard never sleeps.

---

## Step 2 — Add the child page to your GitHub Pages site

This step lives in **your maxwellhowegis.com repository**, not the `lehs-data-dive` repo.

1. Find your maxwellhowegis.com source repo on GitHub (e.g.
   `mapzimus/mapzimus.github.io` or whatever you set up).
2. Clone it locally (or edit on github.com directly).
3. Create a folder `Lynn-data-dive/` at the repo root.
4. Inside that folder, drop the `index.html` file in this repo at
   `deploy/maxwellhowegis-Lynn-data-dive.html` (rename to `index.html`).
5. **Edit one line** in `index.html`: set

   ```html
   <iframe src="https://YOUR-RAILWAY-DOMAIN/?embed=true">
   ```

   …using the generated Railway URL from Step 1. The browser address remains
   `maxwellhowegis.com/Lynn-data-dive/`; visitors do not navigate to Railway.
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

Railway automatically rebuilds and redeploys after a push to the connected branch.

---

## Notes

- The Streamlit app is **public** — anyone with the backend URL can view it. There's
  no login layer (intentional, since this is meant to be a public resource).
- Railway usage is billed according to the selected plan and service resources.
- **Catchment Research** page images (the static PNGs from your PDF) are in
  `data/processed/lehs_research/` and committed to the repo. They render at
  full resolution inside the deployed app.
- If you ever want to move from the iframe approach to a true subpath
  (`maxwellhowegis.com/Lynn-data-dive` as the streamlit app itself, not in
  an iframe), you'd need to host on your own server with an nginx reverse
  proxy. That's noticeably more work; iframe-on-GitHub-Pages is the right
  tradeoff for now.
