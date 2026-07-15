# Railway Migration Plan — Lynn Data Dive

This runbook cuts the Streamlit dashboard over to Railway while keeping the
public URL on the portfolio:

<https://maxwellhowegis.com/lynndata/>

Railway is the iframe backend. No Railway custom domain or Wix DNS change is
required or desired. A DNS record cannot create the `/lynndata/` path; that
path belongs in the GitHub Pages portfolio repository.

## Target architecture

```text
Visitor
  -> https://maxwellhowegis.com/lynndata/
     GitHub Pages wrapper; remains in the address bar
  -> https://lehs-data-dive-production.up.railway.app/?embed=true
     Railway-hosted Streamlit backend
```

## Railway state

- Repository: `mapzimus/lehs-data-dive`
- Branch: `main`
- Deployment files: `Dockerfile` and `railway.json`
- Environment variable: `PORT=8501`
- Public-network target port: `8501`
- Health check: `/_stcore/health`
- Serverless/App Sleeping: disabled

PR #107 introduced the Railway deployment files.

## Cutover procedure

1. Confirm the Railway health endpoint:

   ```bash
   curl --fail https://lehs-data-dive-production.up.railway.app/_stcore/health
   ```

   Expected response: `ok`.

2. In `mapzimus/maxwellhowegis`, create `lynndata/index.html` from the
   canonical wrapper and set its iframe source to:

   ```html
   src="https://lehs-data-dive-production.up.railway.app/?embed=true"
   ```

3. Set the wrapper canonical and Open Graph URL to
   `https://maxwellhowegis.com/lynndata/`.

4. Replace `Lynn-data-dive/index.html` with a redirect to `/lynndata/`.
   Preserve `Lynn-data-dive/maps/`.

5. Update portfolio dashboard links to `/lynndata/`, while leaving links
   that intentionally target `/Lynn-data-dive/maps/` unchanged.

6. Merge the portfolio PR and wait for the GitHub Pages deployment.

7. Verify the public wrapper, navigation, charts, maps, CSV downloads,
   websocket connection, browser console, legacy redirect, and standalone
   maps path.

8. Remove the obsolete Streamlit keepalive artifacts after Railway and the
   portfolio iframe pass verification. Completed during this cutover after
   the live checks passed.

## Canonical wrapper

`deploy/maxwellhowegis-Lynn-data-dive.html` is the application repository's
canonical copy of `lynndata/index.html`. Keep its Railway iframe source and
`/lynndata/` metadata synchronized with the portfolio.

## Rollback

If Railway fails, diagnose or roll back the Railway deployment while keeping
the public portfolio path unchanged. Do not introduce a custom domain or DNS
change as a workaround. If an emergency iframe rollback is necessary, make it
in `lynndata/index.html` and preserve the public `/lynndata/` URL.
