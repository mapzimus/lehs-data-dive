# sync_public_maps.ps1 — publish the Lynn map + MA atlas to the public site.
#
# The lehs-data-dive and ma-education-atlas repos are PRIVATE; the live copies
# are served from the public maxwellhowegis repo (GitHub Pages). This script
# mirrors the serve-only files there. Run it after any map/atlas change or
# data refresh, then review the diff in the maxwellhowegis clone, commit, push.
#
# Usage (from the lehs-data-dive repo root):
#   powershell -ExecutionPolicy Bypass -File deploy\sync_public_maps.ps1
#
# Dev files (scripts/, plans/, analysis tooling, postmortems, .git*) are
# deliberately excluded — they are the private pipeline.

$ErrorActionPreference = "Stop"

$lehsMaps  = Join-Path $PSScriptRoot "..\maps"
$atlasRepo = "C:\Users\Calen\ma-education-atlas"
$siteRepo  = "C:\Users\Calen\maxwellhowegis"

foreach ($p in @($lehsMaps, $atlasRepo, $siteRepo)) {
    if (-not (Test-Path $p)) { throw "Missing expected path: $p" }
}

Write-Host "`n=== Lynn map -> $siteRepo\Lynn-data-dive\maps ===" -ForegroundColor Cyan
robocopy $lehsMaps "$siteRepo\Lynn-data-dive\maps" /MIR /XD .git .github /XF DATA_PARITY.md /NFL /NDL /NJH
if ($LASTEXITCODE -ge 8) { throw "robocopy (Lynn map) failed with code $LASTEXITCODE" }

Write-Host "`n=== MA atlas -> $siteRepo\ma-atlas ===" -ForegroundColor Cyan
robocopy $atlasRepo "$siteRepo\ma-atlas" /MIR /XD .git .github scripts plans raw /XF AGENTS.md .gitattributes .gitignore /NFL /NDL /NJH
if ($LASTEXITCODE -ge 8) { throw "robocopy (atlas) failed with code $LASTEXITCODE" }

# NOTE: the public copies carry sanitized attribution (no links to the private
# repos). If you overwrite index.html footers with fresh dev copies, re-check
# that no github.com/mapzimus/lehs-data-dive or /ma-education-atlas links
# reappear (they would 404 for visitors):
$leaks = Select-String -Path "$siteRepo\Lynn-data-dive\maps\index.html", "$siteRepo\ma-atlas\index.html" `
    -Pattern "github\.com/mapzimus/(lehs-data-dive|ma-education-atlas)" -ErrorAction SilentlyContinue
if ($leaks) {
    Write-Warning "Private-repo links found in served HTML — fix before pushing:"
    $leaks | ForEach-Object { Write-Warning "  $($_.Path):$($_.LineNumber)" }
}

Write-Host "`n=== maxwellhowegis status (review, then commit + push) ===" -ForegroundColor Cyan
git -C $siteRepo status --short -- Lynn-data-dive/maps ma-atlas
Write-Host @"

Next steps:
  git -C $siteRepo add Lynn-data-dive/maps ma-atlas
  git -C $siteRepo commit -m "Sync public map copies"
  git -C $siteRepo push origin main
"@ -ForegroundColor Yellow
