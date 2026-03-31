# Quick Start Commands (Windows PowerShell)

## Step 1: Run the startup script

```powershell
.\start-dev.ps1
```

This will:
- ✅ Check Docker is running
- ✅ Start PostgreSQL + Redis containers
- ✅ Create virtual environment (if needed)
- ✅ Install Python dependencies
- ✅ Copy .env.cloud.example to .env (if needed)

---

## Step 2: Start the backend server

```powershell
# Activate virtual environment (if not already activated)
.\venv\Scripts\Activate.ps1

# Navigate to backend
cd backend

# Start FastAPI server
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Step 3: Test the API

Open your browser: **http://localhost:8000/docs**

You should see the FastAPI Swagger UI!

---

## Troubleshooting

### If start-dev.ps1 fails with encoding error:

Run commands manually:

```powershell
# 1. Start Docker services
docker-compose -f docker-compose.lightweight.yml up -d

# 2. Create virtual environment (if needed)
python -m venv venv

# 3. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 4. Install dependencies
cd backend
pip install --upgrade pip
pip install -r requirements.txt
cd ..

# 5. Copy .env file (if needed)
cp .env.cloud.example .env

# 6. Start backend
cd backend
python -m uvicorn api.main:app --reload
```

### If you get "execution policy" error:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### If port 8000 is already in use:

```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill the process (replace <PID> with actual process ID)
taskkill /PID <PID> /F
```

---

## Stop Services

```powershell
# Stop Docker containers
docker-compose -f docker-compose.lightweight.yml down

# Stop backend (press Ctrl+C in the terminal running uvicorn)
```

---

## Next Steps

1. ✅ Backend is running on http://localhost:8000
2. 📝 Check API docs at http://localhost:8000/docs
3. 🔧 Edit .env file with your Azure/Gemini credentials
4. 🚀 Start implementing features from tasks.md

---

## Your System Info

- **Python Version**: 3.14.2 ✅ (Perfect!)
- **System**: Lenovo SlimPad 5 (AMD Ryzen 7000)
- **RAM Usage**: ~2-3GB (lightweight setup)
- **Cloud Services**: Azure OpenAI + Azure Speech + Gemini API

---

## Useful Commands

```powershell
# Check Docker containers
docker ps

# View container logs
docker logs tradesense-postgres-light
docker logs tradesense-redis-light

# Check Python version
python --version

# Check if virtual environment is activated
# (you should see (venv) in your prompt)

# Deactivate virtual environment
deactivate

# Restart Docker services
docker-compose -f docker-compose.lightweight.yml restart
```

---

Happy coding! 🎉
