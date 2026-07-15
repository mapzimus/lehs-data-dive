# Railway Migration Plan — Lynn Data Dive

This runbook moves the Streamlit dashboard from Streamlit Community Cloud to
an always-on Railway service without changing the public URL visitors use:

**Public URL:** <https://maxwellhowegis.com/Lynn-data-dive/>

The portfolio page remains on GitHub Pages and embeds the dashboard in a
full-page iframe. Railway runs the Python application behind that page.

## Final architecture

```text
Visitor
  |
  v
https://maxwellhowegis.com/Lynn-data-dive/
  |  GitHub Pages wrapper; this stays in the address bar
  v
https://dashboard.maxwellhowegis.com/?embed=true
  |  Custom domain attached to Railway
  v
Railway service
  |
  v
streamlit run Home.py
```

Using `dashboard.maxwellhowegis.com` is recommended because it keeps Railway's
generated domain out of both the address bar and the iframe source. If you do
not want to configure DNS, the generated Railway domain can be used as the
iframe source instead; visitors will still see the portfolio URL in their
address bar.

## Repositories involved

| Repository | Purpose |
|---|---|
| `mapzimus/lehs-data-dive` | Streamlit source, processed data, and Railway configuration |
| `mapzimus/maxwellhowegis` | GitHub Pages portfolio and `/Lynn-data-dive/` iframe wrapper |

## Prepared deployment files

Before starting, merge the prepared Railway deployment changes into the
default branch of `mapzimus/lehs-data-dive`. Confirm that `main` contains:

- `Dockerfile`
- `.dockerignore`
- `railway.json`
- `requirements.txt`
- `Home.py`

The container:

- uses Python 3.12;
- installs GDAL, GEOS, and PROJ system packages;
- installs the Python runtime requirements;
- listens on Railway's injected `PORT`;
- exposes Streamlit's `/_stcore/health` endpoint; and
- restarts automatically after application failures.

Do not disable Streamlit Community Cloud yet. It is the rollback target until
the Railway deployment has been verified.

---

## Phase 1 — Create the Railway service

1. Sign in at <https://railway.com/> using the GitHub account that can access
   `mapzimus/lehs-data-dive`.
2. Create a new project.
3. Choose **Deploy from GitHub repo**.
4. Select `mapzimus/lehs-data-dive`.
5. If Railway asks for a branch, choose `main`.
6. If Railway asks for a root directory, use `/` or leave it blank.
7. Railway should detect `railway.json` and build the root `Dockerfile`.
8. Do not add a custom start command. The Dockerfile already supplies it.
9. Do not add a `PORT` variable manually. Railway injects it.
10. Start the deployment and watch the build logs.

The first build will take longer than later builds because it installs the
geospatial and Python dependencies.

### Expected successful startup

The deployment logs should eventually report that Streamlit is listening on
`0.0.0.0` and Railway should mark the health check healthy.

If the build fails, inspect the first actual error in the build log rather
than the final generic failure message. Common checks:

- Confirm Railway is building the `Dockerfile`, not guessing a Nixpacks build.
- Confirm the selected branch contains `Dockerfile` and `railway.json`.
- Confirm the repository root is selected.
- Confirm the service has enough memory to install and import pandas,
  pyarrow, geopandas, and Plotly.

### Keep the service always on

In the service settings:

1. Keep at least one service replica active.
2. Disable **Serverless**, **App Sleeping**, or any equivalent sleep-on-idle
   option if Railway presents one.
3. Use the paid plan required for an always-on service.
4. Leave the health-check path as:

   ```text
   /_stcore/health
   ```

5. Leave the health-check timeout at 300 seconds for cold builds and starts.

Railway changes its dashboard terminology periodically. The required outcome
is one continuously running replica with sleep-on-idle disabled.

---

## Phase 2 — Generate and test the Railway domain

1. Open the Railway service.
2. Go to **Settings → Networking**.
3. Choose **Generate Domain**.
4. Save the generated HTTPS URL. It will resemble:

   ```text
   https://some-name.up.railway.app
   ```

5. Open this URL in a private/incognito browser window.
6. Confirm the dashboard home page renders.
7. Open several pages, including a map page and a chart-heavy page.
8. Verify the health endpoint in a browser or terminal:

   ```bash
   curl --fail https://YOUR-RAILWAY-DOMAIN/_stcore/health
   ```

Expected response:

```text
ok
```

Do not cut over the portfolio iframe until the generated domain passes these
checks.

---

## Phase 3 — Add the branded backend domain

This phase is optional but recommended.

1. In Railway, open **Settings → Networking → Custom Domain**.
2. Enter:

   ```text
   dashboard.maxwellhowegis.com
   ```

3. Railway will display the DNS record it expects.
4. Sign in to the DNS provider that manages `maxwellhowegis.com`.
5. Add the exact record Railway supplies. It will usually be a CNAME similar
   to:

   | Type | Name/Host | Target/Value |
   |---|---|---|
   | CNAME | `dashboard` | Railway-provided target |

6. If the DNS is managed by Cloudflare, initially set the record to
   **DNS only** rather than proxied unless Railway's current instructions
   explicitly say otherwise.
7. Return to Railway and wait for the custom domain and TLS certificate to
   show as active.
8. Test:

   ```bash
   curl --fail https://dashboard.maxwellhowegis.com/_stcore/health
   ```

Expected response:

```text
ok
```

DNS and certificate issuance may take a little while. Keep the old iframe
unchanged while waiting.

---

## Phase 4 — Cut over the portfolio page

Clone or update the portfolio repository:

```bash
git clone https://github.com/mapzimus/maxwellhowegis.git
cd maxwellhowegis
git checkout main
git pull origin main
git checkout -b railway-dashboard-cutover
```

### Change the iframe source

Open:

```text
Lynn-data-dive/index.html
```

Replace:

```html
src="https://lynn-data-dive.streamlit.app/?embed=true"
```

with the recommended branded backend:

```html
src="https://dashboard.maxwellhowegis.com/?embed=true"
```

If you skipped the custom-domain phase, use:

```html
src="https://YOUR-RAILWAY-DOMAIN/?embed=true"
```

Update the nearby HTML comment so it describes Railway rather than Streamlit
Community Cloud.

### Keep navigation on the portfolio URL

In:

```text
Lynn-data-dive/maps/index.html
```

ensure the **LEHS Dashboard** link points to:

```html
<a href="https://maxwellhowegis.com/Lynn-data-dive/">LEHS Dashboard</a>
```

Do not link portfolio navigation directly to Railway or the branded backend
subdomain.

### Keep the source wrapper synchronized

In the `mapzimus/lehs-data-dive` repository, apply the same iframe change to:

```text
deploy/maxwellhowegis-Lynn-data-dive.html
```

That file is the canonical copy used when the portfolio wrapper is synced in
the future.

### Commit and publish

From the portfolio repository:

```bash
git add Lynn-data-dive/index.html Lynn-data-dive/maps/index.html
git commit -m "Move Lynn Data Dive backend to Railway"
git push -u origin railway-dashboard-cutover
```

Review and merge the portfolio change through GitHub. Wait for the GitHub
Pages deployment to finish before testing the public URL.

---

## Phase 5 — Verify the public site

Open a private/incognito browser window and visit:

<https://maxwellhowegis.com/Lynn-data-dive/>

Verify all of the following:

- The browser address remains `maxwellhowegis.com/Lynn-data-dive/`.
- The loading indicator disappears.
- The dashboard home page renders.
- Sidebar navigation works.
- Charts render and respond to controls.
- At least one CSV download works.
- The map pages load.
- Refreshing a nested dashboard state does not show an error.
- The browser console has no iframe, websocket, mixed-content, or certificate
  errors.
- The Railway deployment logs show a websocket session when the page opens.

Also test:

- desktop Chrome, Firefox, or Edge;
- a phone-sized browser viewport; and
- a fresh private window with no existing Streamlit cookies.

If the iframe does not load but the Railway URL works directly, check:

1. the iframe `src` spelling and trailing `/?embed=true`;
2. the custom-domain TLS status in Railway;
3. browser console errors;
4. Railway deployment logs; and
5. whether a DNS proxy or security header is blocking iframe/websocket traffic.

---

## Phase 6 — Observe before cleanup

Leave Streamlit Community Cloud deployed during the initial observation
period. Use Railway metrics and logs to confirm:

- the service remains running while idle;
- memory usage is stable;
- health checks continue to pass;
- websocket connections do not repeatedly fail;
- a new GitHub push triggers a successful redeploy; and
- the dashboard still loads after an extended idle period.

Also confirm Railway billing and usage limits are acceptable. The dashboard
loads processed files from the repository and does not need persistent disk
storage.

---

## Phase 7 — Remove the old keepalive system

Only do this after the public portfolio URL has been stable on Railway.

In `mapzimus/maxwellhowegis`:

1. Delete:

   ```text
   .github/workflows/keep-streamlit-awake.yml
   ```

2. Remove the obsolete keepalive warning from `DEPLOY.md`.
3. Update `Lynn-data-dive/README.md` to identify Railway as the app host.
4. Search for remaining direct Streamlit Cloud links:

   ```bash
   rg "lynn-data-dive\.streamlit\.app|Streamlit Community Cloud"
   ```

5. Replace old public links with:

   ```text
   https://maxwellhowegis.com/Lynn-data-dive/
   ```

In `mapzimus/lehs-data-dive`:

1. Remove `scripts/keepalive_ping.py` if it is no longer referenced.
2. Search for stale deployment instructions:

   ```bash
   rg "lynn-data-dive\.streamlit\.app|Streamlit Community Cloud|keepalive"
   ```

3. Keep Streamlit Cloud available briefly as a manual rollback target, then
   remove or disable it when you are comfortable with Railway.

Commit cleanup separately from the cutover so it can be reviewed and reverted
independently.

---

## Ongoing deployment workflow

After setup, Railway should deploy automatically from `main`:

```text
Commit or merge to mapzimus/lehs-data-dive main
  → Railway detects the push
  → Docker image is rebuilt
  → Health check passes
  → New deployment replaces the previous deployment
```

For each application update:

1. Test locally.
2. Push a feature branch.
3. Review and merge it into `main`.
4. Watch the Railway deployment logs.
5. Confirm `/_stcore/health` returns `ok`.
6. Smoke-test <https://maxwellhowegis.com/Lynn-data-dive/>.

The processed Parquet and GeoJSON files are committed to the repository, so
Railway does not need a separate startup download or database.

---

## Rollback plan

### Fastest rollback

If Railway fails after cutover, edit `Lynn-data-dive/index.html` in the
portfolio repository and restore:

```html
src="https://lynn-data-dive.streamlit.app/?embed=true"
```

Publish the portfolio repository and wait for GitHub Pages to redeploy.

### Railway application rollback

If only the newest application deployment is broken:

1. Open the Railway service's deployment history.
2. Redeploy the last known-good deployment using Railway's current rollback
   control.
3. Verify `/_stcore/health`.
4. Verify the public portfolio page.

### DNS rollback

If only `dashboard.maxwellhowegis.com` is broken, temporarily point the iframe
at Railway's generated domain. This bypasses custom-domain DNS without moving
the app.

Do not delete the old Streamlit deployment, keepalive workflow, or known-good
Railway deployment until the cutover is verified.

---

## Final checklist

- [ ] Railway deployment changes are on `lehs-data-dive/main`.
- [ ] Railway project is connected to `mapzimus/lehs-data-dive`.
- [ ] Docker build succeeds.
- [ ] Railway health check reports healthy.
- [ ] Sleep-on-idle/serverless behavior is disabled.
- [ ] Generated Railway domain loads the dashboard.
- [ ] `dashboard.maxwellhowegis.com` is active with HTTPS.
- [ ] Branded health endpoint returns `ok`.
- [ ] Portfolio iframe uses the branded backend domain.
- [ ] Portfolio navigation uses `/Lynn-data-dive/`.
- [ ] Canonical wrapper in `deploy/` matches the portfolio copy.
- [ ] GitHub Pages deployment succeeds.
- [ ] Public dashboard passes desktop and mobile smoke tests.
- [ ] Railway remains healthy after an extended idle period.
- [ ] Old keepalive workflow is removed only after verification.
- [ ] Old Streamlit deployment is retained until rollback is no longer needed.
