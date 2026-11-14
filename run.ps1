Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "        Starting SmartRoute BD Local Server...              " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Application URL: http://localhost:8080" -ForegroundColor Yellow
Write-Host "Admin Portal:    http://localhost:8080/admin (admin / 12345678)" -ForegroundColor Yellow
Write-Host "Swagger Docs:    http://localhost:8080/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press CTRL+C to stop the server anytime."
Write-Host ""
& "$PSScriptRoot\.venv\Scripts\python.exe" -m uvicorn src.api.main:app --host 127.0.0.1 --port 8080 --reload
