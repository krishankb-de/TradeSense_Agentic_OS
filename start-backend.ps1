#!/usr/bin/env pwsh
# Start TradeSense Backend Server

Write-Host "🚀 Starting TradeSense Backend..." -ForegroundColor Cyan

# Check if PostgreSQL is running
Write-Host "Checking PostgreSQL..." -ForegroundColor Yellow
$postgres = docker ps --filter "expose=5432" --format "{{.Names}}" | Select-String "postgres"
if (-not $postgres) {
    Write-Host "❌ PostgreSQL is not running. Starting it..." -ForegroundColor Red
    docker-compose -f docker-compose.local.yml up -d postgres
    Start-Sleep -Seconds 5
}
Write-Host "✅ PostgreSQL is running" -ForegroundColor Green

# Check if Redis is running
Write-Host "Checking Redis..." -ForegroundColor Yellow
$redis = docker ps --filter "expose=6379" --format "{{.Names}}" | Select-String "redis"
if (-not $redis) {
    Write-Host "❌ Redis is not running. Starting it..." -ForegroundColor Red
    docker-compose -f docker-compose.local.yml up -d redis
    Start-Sleep -Seconds 3
}
Write-Host "✅ Redis is running" -ForegroundColor Green

# Activate virtual environment if it exists
if (Test-Path "venv/Scripts/Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & venv/Scripts/Activate.ps1
} elseif (Test-Path ".venv/Scripts/Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & .venv/Scripts/Activate.ps1
}

# Set working directory to backend
Set-Location backend

# Start the backend server
Write-Host "Starting FastAPI server on http://localhost:8000..." -ForegroundColor Cyan
Write-Host "API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "" -ForegroundColor White
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host "" -ForegroundColor White

python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
