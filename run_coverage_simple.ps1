# Simple coverage analysis script for TradeSense
# Task 18.11: Verify code coverage

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "TRADESENSE CODE COVERAGE ANALYSIS" -ForegroundColor Cyan
Write-Host "Task 18.11: Verify Code Coverage" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# Python Coverage
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "PYTHON COVERAGE ANALYSIS" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host ""

Push-Location backend

# Run coverage
Write-Host "Running Python tests with coverage..." -ForegroundColor Green
python -m coverage run -m pytest tests/ -v --tb=short -q
python -m coverage report -m
python -m coverage json -o coverage.json
python -m coverage html -d htmlcov

Write-Host ""
Write-Host "Python coverage report generated:" -ForegroundColor Green
Write-Host "  - JSON: backend/coverage.json"
Write-Host "  - HTML: backend/htmlcov/index.html"

Pop-Location

# TypeScript Coverage
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host "TYPESCRIPT COVERAGE ANALYSIS" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Yellow
Write-Host ""

Push-Location frontend

if (!(Test-Path "node_modules")) {
    Write-Host "Installing frontend dependencies..." -ForegroundColor Green
    npm install
}

Write-Host "Running TypeScript tests with coverage..." -ForegroundColor Green
npm run test -- --coverage --run

Write-Host ""
Write-Host "TypeScript coverage report generated:" -ForegroundColor Green
Write-Host "  - HTML: frontend/coverage/index.html"

Pop-Location

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "COVERAGE ANALYSIS COMPLETE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "View detailed reports:" -ForegroundColor Green
Write-Host "  - Python: backend/htmlcov/index.html"
Write-Host "  - TypeScript: frontend/coverage/index.html"
