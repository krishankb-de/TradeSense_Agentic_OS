# TradeSense Development Startup Script (Windows PowerShell)
# This script starts all required services for local development

Write-Host "Starting TradeSense Development Environment..." -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker is running" -ForegroundColor Green
Write-Host ""

# Start Docker services
Write-Host "Starting Docker services (PostgreSQL + Redis)..." -ForegroundColor Yellow
docker-compose -f docker-compose.lightweight.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to start Docker services" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Docker services started" -ForegroundColor Green
Write-Host ""

# Wait for services to be healthy
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Check if virtual environment exists
if (-Not (Test-Path "venv\Scripts\Activate.ps1")) {
    Write-Host "[WARN] Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
    
    # Activate and install dependencies
    Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
    & "venv\Scripts\Activate.ps1"
    pip install --upgrade pip
    Set-Location backend
    pip install -r requirements.txt
    Set-Location ..
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& "venv\Scripts\Activate.ps1"
Write-Host "[OK] Virtual environment activated" -ForegroundColor Green
Write-Host ""

# Check if .env exists
if (-Not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found. Copying from .env.cloud.example..." -ForegroundColor Yellow
    Copy-Item ".env.cloud.example" ".env"
    Write-Host "[OK] .env file created. Please edit it with your credentials!" -ForegroundColor Green
    Write-Host ""
}

# Display service status
Write-Host "Service Status:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Write-Host ""

# Display next steps
Write-Host "Development environment is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Edit .env file with your Azure/Gemini credentials" -ForegroundColor White
Write-Host "2. Run: cd backend" -ForegroundColor White
Write-Host "3. Run: uvicorn api.main:app --reload" -ForegroundColor White
Write-Host "4. Open: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "To stop services: docker-compose -f docker-compose.lightweight.yml down" -ForegroundColor Yellow
Write-Host ""
Write-Host "Happy coding!" -ForegroundColor Green
