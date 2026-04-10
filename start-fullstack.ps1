# TradeSense Full Stack Startup Script
# This script starts both backend and frontend servers

Write-Host "🚀 Starting TradeSense Full Stack..." -ForegroundColor Cyan
Write-Host ""

# Check if backend virtual environment exists
if (-not (Test-Path "backend/venv")) {
    Write-Host "❌ Backend virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup first:" -ForegroundColor Yellow
    Write-Host "  cd backend" -ForegroundColor Yellow
    Write-Host "  python -m venv venv" -ForegroundColor Yellow
    Write-Host "  .\venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Check if frontend node_modules exists
if (-not (Test-Path "frontend/node_modules")) {
    Write-Host "❌ Frontend dependencies not installed!" -ForegroundColor Red
    Write-Host "Please run setup first:" -ForegroundColor Yellow
    Write-Host "  cd frontend" -ForegroundColor Yellow
    Write-Host "  npm install" -ForegroundColor Yellow
    exit 1
}

# Check if .env file exists
if (-not (Test-Path "backend/.env")) {
    Write-Host "⚠️  Warning: backend/.env file not found!" -ForegroundColor Yellow
    Write-Host "Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item "backend/.env.example" "backend/.env"
    Write-Host "✅ Created backend/.env - Please configure it with your credentials" -ForegroundColor Green
    Write-Host ""
}

Write-Host "📦 Starting Backend Server..." -ForegroundColor Green
Write-Host "   Location: http://localhost:8000" -ForegroundColor Gray
Write-Host "   API Docs: http://localhost:8000/docs" -ForegroundColor Gray
Write-Host ""

# Start backend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; .\venv\Scripts\Activate.ps1; uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"

# Wait a bit for backend to start
Write-Host "⏳ Waiting for backend to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

Write-Host "🎨 Starting Frontend Server..." -ForegroundColor Green
Write-Host "   Location: http://localhost:3000" -ForegroundColor Gray
Write-Host ""

# Start frontend in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd frontend; npm run dev"

Write-Host ""
Write-Host "✅ Both servers are starting!" -ForegroundColor Green
Write-Host ""
Write-Host "📍 Access Points:" -ForegroundColor Cyan
Write-Host "   Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "   Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "   API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "💡 Tips:" -ForegroundColor Cyan
Write-Host "   - Two PowerShell windows will open (backend and frontend)" -ForegroundColor Gray
Write-Host "   - Press Ctrl+C in each window to stop the servers" -ForegroundColor Gray
Write-Host "   - Check the windows for any error messages" -ForegroundColor Gray
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   - User Testing Guide: USER_TESTING_GUIDE.md" -ForegroundColor Gray
Write-Host "   - Frontend Setup: FRONTEND_SETUP_GUIDE.md" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
