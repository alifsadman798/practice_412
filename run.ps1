Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "        Starting SmartRoute BD Local Server...              " -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$port = 8001
$venvPy = "$PSScriptRoot\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPy)) {
    Write-Host "ERROR: Virtual environment not found at $venvPy" -ForegroundColor Red
    Write-Host "Please create and initialize the environment first:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host "  pip install -r requirements.txt"
    exit 1
}

# Check if port 8001 is already in use
$conn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($conn) {
    Write-Host "ERROR: Port $port is already in use by process PID $($conn[0].OwningProcess)!" -ForegroundColor Red
    Write-Host "Please close the process using port $port before running SmartRoute BD." -ForegroundColor Yellow
    exit 1
}

Write-Host "Application URL: http://127.0.0.1:$port" -ForegroundColor Yellow
Write-Host "Admin Portal:    http://127.0.0.1:$port/admin (admin / 12345678)" -ForegroundColor Yellow
Write-Host "Swagger Docs:    http://127.0.0.1:$port/docs" -ForegroundColor Yellow
Write-Host ""
Write-Host "Press CTRL+C to stop the server anytime."
Write-Host ""

& "$venvPy" -m uvicorn src.api.main:app --host 127.0.0.1 --port $port --reload
