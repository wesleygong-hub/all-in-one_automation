$ErrorActionPreference = "Stop"

Write-Host "========================="
Write-Host "Start data uploading..."
Write-Host "========================="

$env:DSN_USERNAME = "your_username"
$env:DSN_PASSWORD = "your_password"

python .\main.py run --config .\config.yaml --tasks .\task.csv --headed

Write-Host ""
Write-Host "Execution complete. Please check the results log."
