# Sync gauge database from Raspberry Pi and view updated plot

Write-Host "Syncing database from Raspberry Pi..." -ForegroundColor Green
uv run sync_database_from_pi.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nRegenerating plots with combined data..." -ForegroundColor Green
    uv run gauge_cli.py --plot --pressure-unit bar --all-time
    
    Write-Host "`nOpening plot..." -ForegroundColor Green
    lightningview.exe .\gauge_plots.png
} else {
    Write-Host "Error: Database sync failed" -ForegroundColor Red
}