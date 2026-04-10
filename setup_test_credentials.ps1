# Setup Test Credentials for TradeSense
# This script creates test user credentials for development

Write-Host "🔐 Setting up test credentials for TradeSense..." -ForegroundColor Cyan
Write-Host ""

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "⚠️  Virtual environment not activated!" -ForegroundColor Yellow
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "backend\venv\Scripts\Activate.ps1"
}

# Navigate to backend directory
Push-Location backend

Write-Host "📝 Creating test users..." -ForegroundColor Green
python create_test_user.py

Pop-Location

Write-Host ""
Write-Host "✅ Test credentials setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📋 You can now log in with these credentials:" -ForegroundColor Cyan
Write-Host ""
Write-Host "   1. Test User (Admin):" -ForegroundColor White
Write-Host "      Email: test@test.com" -ForegroundColor Gray
Write-Host "      Password: test" -ForegroundColor Gray
Write-Host ""
Write-Host "   2. Admin User:" -ForegroundColor White
Write-Host "      Email: admin@tradesense.com" -ForegroundColor Gray
Write-Host "      Password: admin123" -ForegroundColor Gray
Write-Host ""
Write-Host "   3. Technician User:" -ForegroundColor White
Write-Host "      Email: tech@tradesense.com" -ForegroundColor Gray
Write-Host "      Password: tech123" -ForegroundColor Gray
Write-Host ""
Write-Host "🚀 Next steps:" -ForegroundColor Cyan
Write-Host "   1. Start the backend: cd backend; uvicorn api.main:app --reload" -ForegroundColor Gray
Write-Host "   2. Start the frontend: cd frontend; npm run dev" -ForegroundColor Gray
Write-Host "   3. Open http://localhost:3000 and log in!" -ForegroundColor Gray
Write-Host ""
