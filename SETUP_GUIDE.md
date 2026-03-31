# TradeSense Setup Guide (Cloud-Based Lightweight)

**Target System**: Lenovo SlimPad 5 (AMD Ryzen 7000, Radeon Graphics)  
**Approach**: Lightweight local development + Cloud AI services (Azure/Gemini)

---

## Prerequisites Checklist

✅ You've already installed:
- Docker Desktop
- PostgreSQL (via Docker)
- Azure account
- Datadog account
- Sentry account
- Langfuse account

---

## Step 1: Check Your Python Version

```powershell
python --version
```

**Required**: Python 3.9 or higher (3.10+ recommended for future features)

If you have Python 3.8 or lower, download Python 3.11 from:
https://www.python.org/downloads/

---

## Step 2: Create Python Virtual Environment

```powershell
# Navigate to project root
cd D:\Projects\TradeSense_Agentic_OS

# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**IMPORTANT**: Always activate the virtual environment before running any Python commands!

---

## Step 3: Install Python Dependencies (Cloud-Based)

```powershell
# Make sure virtual environment is activated (you should see (venv) in prompt)
cd backend
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- ✅ FastAPI + Uvicorn (web framework)
- ✅ Azure OpenAI SDK (cloud LLM)
- ✅ Azure Speech SDK (cloud voice)
- ✅ Google Gemini API (free tier LLM)
- ✅ WebRTC (open-source communication)
- ✅ Datadog + Sentry (cloud observability)
- ✅ Langfuse (self-hosted observability)

**NOT installed** (too heavy for your system):
- ❌ ZenML (requires Python 3.10+, we'll add later)
- ❌ Ollama (local LLM - replaced by Azure OpenAI)
- ❌ Faster-Whisper (local STT - replaced by Azure Speech)
- ❌ Piper TTS (local TTS - replaced by Azure Speech)

---

## Step 4: Configure Environment Variables

```powershell
# Copy cloud-based example
cp .env.cloud.example .env

# Edit .env with your credentials
notepad .env
```

**Required credentials** (from your Azure/GitHub Student Pack):

```bash
# Azure OpenAI (FREE with $100 credit)
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4

# Azure Speech Services (FREE with $100 credit)
AZURE_SPEECH_KEY=your_azure_speech_key_here
AZURE_SPEECH_REGION=eastus

# Google Gemini API (FREE tier - 1500 requests/day)
GOOGLE_API_KEY=your_google_api_key_here

# Datadog (FREE for 2 years with Student Pack)
DATADOG_API_KEY=your_datadog_api_key
DATADOG_APP_KEY=your_datadog_app_key

# Sentry (FREE 500k events/month)
SENTRY_DSN=your_sentry_dsn_here

# Langfuse (self-hosted)
LANGFUSE_PUBLIC_KEY=your_langfuse_public_key
LANGFUSE_SECRET_KEY=your_langfuse_secret_key
LANGFUSE_HOST=http://localhost:3000
```

---

## Step 5: Start Docker Services (Lightweight)

```powershell
# Start only PostgreSQL + Redis (lightweight!)
docker-compose -f docker-compose.lightweight.yml up -d

# Verify containers are running
docker ps
```

You should see:
- ✅ `tradesense-postgres-light` (PostgreSQL)
- ✅ `tradesense-redis-light` (Redis)

**Total RAM usage**: ~768MB (512MB + 256MB)

---

## Step 6: Initialize Database

```powershell
# Make sure virtual environment is activated
cd backend

# Run database migrations
alembic upgrade head
```

---

## Step 7: Start Backend Server

```powershell
# Make sure virtual environment is activated
cd backend

# Start FastAPI server
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected output**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## Step 8: Test the API

Open browser: http://localhost:8000/docs

You should see the FastAPI Swagger UI with API documentation.

---

## Step 9: Setup Azure Services (If Not Done)

### Azure OpenAI

```powershell
# Install Azure CLI
winget install Microsoft.AzureCLI

# Login to Azure
az login

# Create resource group
az group create --name tradesense-rg --location eastus

# Create Azure OpenAI resource
az cognitiveservices account create `
  --name tradesense-openai `
  --resource-group tradesense-rg `
  --kind OpenAI `
  --sku S0 `
  --location eastus

# Get API key
az cognitiveservices account keys list `
  --name tradesense-openai `
  --resource-group tradesense-rg
```

### Azure Speech Services

```powershell
# Create Speech resource
az cognitiveservices account create `
  --name tradesense-speech `
  --resource-group tradesense-rg `
  --kind SpeechServices `
  --sku S0 `
  --location eastus

# Get API key
az cognitiveservices account keys list `
  --name tradesense-speech `
  --resource-group tradesense-rg
```

### Google Gemini API

1. Go to: https://makersuite.google.com/app/apikey
2. Create API key
3. Copy to `.env` file

---

## Step 10: Verify Setup

```powershell
# Test Azure OpenAI connection
python -c "from openai import AzureOpenAI; print('Azure OpenAI SDK installed!')"

# Test Azure Speech connection
python -c "import azure.cognitiveservices.speech as speechsdk; print('Azure Speech SDK installed!')"

# Test Google Gemini connection
python -c "import google.generativeai as genai; print('Gemini SDK installed!')"
```

---

## Common Issues & Solutions

### Issue 1: Python Version Too Old

**Error**: `ERROR: Could not find a version that satisfies the requirement...`

**Solution**: Install Python 3.11+
```powershell
# Download from python.org
# Then recreate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Issue 2: Execution Policy Error

**Error**: `cannot be loaded because running scripts is disabled`

**Solution**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Issue 3: Docker Not Running

**Error**: `Cannot connect to the Docker daemon`

**Solution**: Start Docker Desktop from Windows Start menu

### Issue 4: Port Already in Use

**Error**: `Address already in use`

**Solution**:
```powershell
# Find process using port 8000
netstat -ano | findstr :8000

# Kill process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

---

## Next Steps

1. ✅ Setup complete! Backend is running on http://localhost:8000
2. 📝 Review API documentation at http://localhost:8000/docs
3. 🔧 Configure Azure OpenAI and Speech Services
4. 🚀 Start implementing Task 2 from tasks.md

---

## Development Workflow

### Daily Development

```powershell
# 1. Start Docker services
docker-compose -f docker-compose.lightweight.yml up -d

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Start backend
cd backend
uvicorn api.main:app --reload

# 4. Make changes to code
# 5. Test at http://localhost:8000/docs

# 6. Stop services when done
docker-compose -f docker-compose.lightweight.yml down
```

### Running Tests

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run tests
cd backend
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

---

## Resource Usage (Lightweight Setup)

- Docker (PostgreSQL + Redis): ~768MB RAM
- Python backend: ~512MB RAM
- **Total**: ~1.3GB RAM

**Comfortable for your Lenovo SlimPad 5!** 🎉

---

## Cost Breakdown (First Year)

- Azure OpenAI: FREE ($100 credit)
- Azure Speech: FREE ($100 credit)
- Google Gemini: FREE (1500 requests/day)
- Datadog: FREE (2 years)
- Sentry: FREE (500k events/month)
- WebRTC/Jitsi: FREE
- **Total**: $0 for first year! 💰

---

## Questions?

- Check QUICK_START.md for detailed setup
- Check CLOUD_ARCHITECTURE.md for architecture details
- Check OPEN_SOURCE_COMMUNICATION.md for WebRTC setup
- Check README.md for project overview

Happy coding! 🚀
