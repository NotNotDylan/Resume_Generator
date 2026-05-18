$ErrorActionPreference = "Stop"

Write-Host "Checking winget..." -ForegroundColor Cyan
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host "winget is not available on this machine." -ForegroundColor Red
  Write-Host "Install App Installer from Microsoft Store, then re-run this script." -ForegroundColor Yellow
  exit 1
}

Write-Host "Installing MiKTeX (this may take a while)..." -ForegroundColor Cyan
winget install --id MiKTeX.MiKTeX -e --source winget --accept-package-agreements --accept-source-agreements

if ($LASTEXITCODE -ne 0) {
  Write-Host "MiKTeX install command did not complete successfully." -ForegroundColor Red
  Write-Host "Try running PowerShell as Administrator and run this script again." -ForegroundColor Yellow
  exit $LASTEXITCODE
}

Write-Host "MiKTeX installation command completed." -ForegroundColor Green
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1) Close and reopen PowerShell." -ForegroundColor White
Write-Host "2) Run: python main.py" -ForegroundColor White
