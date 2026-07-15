# Deploying the LEHS Data Dive

The public dashboard is:

<https://maxwellhowegis.com/lynndata/>

The browser stays on that GitHub Pages URL. Railway is only the iframe
backend; do not configure a Railway custom domain or change Wix DNS. DNS
cannot create the `/lynndata/` path.

## Architecture

```text
https://maxwellhowegis.com/lynndata/
  GitHub Pages wrapper in mapzimus/maxwellhowegis
    -> iframe
https://lehs-data-dive-production.up.railway.app/?embed=true
  Railway service built from mapzimus/lehs-data-dive main
```

The legacy portfolio path
`https://maxwellhowegis.com/Lynn-data-dive/` redirects to `/lynndata/`.
The standalone maps remain at
`https://maxwellhowegis.com/Lynn-data-dive/maps/`.

## Railway configuration

- Source repository: `mapzimus/lehs-data-dive`
- Source branch: `main`
- Builder: root `Dockerfile`, selected by `railway.json`
- `PORT=8501`
- Public-network target port: `8501`
- Health check: `/_stcore/health`
- Serverless/App Sleeping: disabled

The Dockerfile starts Streamlit on `0.0.0.0:$PORT`. Railway rebuilds after
changes reach `main`.

Verify the backend before every portfolio cutover:

```bash
curl --fail https://lehs-data-dive-production.up.railway.app/_stcore/health
```

The expected response is `ok`.

## Portfolio deployment

The wrapper is maintained in `mapzimus/maxwellhowegis` at
`lynndata/index.html`. Its iframe source must be:

```html
src="https://lehs-data-dive-production.up.railway.app/?embed=true"
```

The canonical source copy in this repository is
`deploy/maxwellhowegis-Lynn-data-dive.html`. Keep the two wrappers in sync.
GitHub Pages publishes the portfolio through its Pages workflow after changes
merge to `main`.

## Post-deploy verification

Verify:

- `/lynndata/` loads and stays in the address bar;
- the iframe connects to Railway;
- sidebar navigation, charts, maps, and CSV downloads work;
- the browser console has no iframe, websocket, or mixed-content errors;
- `/Lynn-data-dive/` redirects to `/lynndata/`; and
- `/Lynn-data-dive/maps/` still works.

## Ongoing data refreshes

Run and test the relevant refresh scripts, commit the processed-data changes,
and merge them to `main`. Railway then rebuilds the service automatically.
The public portfolio URL does not change.
