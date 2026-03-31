# TradeSense Quick Start Guide - Cloud Edition

## What Has Been Completed

✅ **Task 1: Foundational Infrastructure** - COMPLETE

The project foundation is now ready for cloud-based development. You have:

1. **Complete project structure** with Python backend and TypeScript frontend
2. **Lightweight Docker Compose** (PostgreSQL + Redis only, ~2-3GB RAM)
3. **Cloud service integration templates** for Gemini, Azure, Langfuse
4. **Shared data models** for cross-language compatibility
5. **Development tooling** (Makefile, linting, formatting)
6. **Documentation** (README, CLOUD_ARCHITECTURE, implementation status)

## Prerequisites Checklist

Before starting, ensure you have:

- [ ] **GitHub Student Pack activated** (https://education.github.com/pack)
- [ ] **Docker Desktop installed** ✅ (you have this)
- [ ] **PostgreSQL installed locally** ✅ (you have this)
- [ ] **Azure account created** ✅ (you have this)
- [ ] **Langfuse account created** ✅ (you have this)
- [ ] **Google Cloud account** (for Gemini API)
- [ ] **Discord account** (optional, for team notifications)

## Getting Started (15 Minutes)

### Step 1: Activate GitHub Student Pack Services

1. **Azure for Students** ($100 credit)
   - Visit: https://azure.microsoft.com/en-us/free/students/
   - Sign in with your student email
   - Activate $100 credit (no credit card required)

2. **DigitalOcean** ($200 credit)
   - Visit: https://www.digitalocean.com/github-students
   - Sign up with GitHub Student Pack
   - Get $200 credit for 1 year

3. **Datadog** (Free for 2 years)
   - Visit: https://www.datadoghq.com/partner/github-students/
   - Sign up with student email
   - Get Pro plan free for 2 years

### Step 2: Set Up Cloud AI Services

#### Google Gemini API (Free Tier - 1500 requests/day)

```bash
# 1. Visit Google AI Studio
open https://makersuite.google.com/app/apikey

# 2. Create API key
# 3. Copy the key (starts with "AIza...")
```

#### Azure OpenAI (Student Credits)

```bash
# 1. Visit Azure Portal
open https://portal.azure.com

# 2. Create Azure OpenAI resource:
#    - Resource group: tradesense-rg
#    - Region: East US (or closest to you)
#    - Name: tradesense-openai
#    - Pricing tier: Standard S0

# 3. Deploy a model:
#    - Go to Azure OpenAI Studio
#    - Deploy GPT-3.5-turbo or GPT-4
#    - Copy endpoint and key
```

#### Azure Speech Services (Student Credits)

```bash
# 1. In Azure Portal, create Speech Services resource:
#    - Resource group: tradesense-rg
#    - Region: East US
#    - Name: tradesense-speech
#    - Pricing tier: Free F0 (or Standard S0)

# 2. Copy key and region from "Keys and Endpoint"
```

#### Langfuse (Cloud Free Tier)

```bash
# 1. Visit Langfuse Cloud (already done ✅)
open https://cloud.langfuse.com

# 2. Create project: "tradesense"
# 3. Copy API keys:
#    - Public Key
#    - Secret Key
```

### Step 3: Local Setup

```bash
# Clone and enter project
cd tradesense

# Copy cloud environment template
cp .env.cloud.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

**Required environment variables:**

```bash
# Google Gemini API
GEMINI_API_KEY=AIza...your-key-here

# Azure OpenAI
AZURE_OPENAI_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://tradesense-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-35-turbo  # or gpt-4

# Azure Speech Services
AZURE_SPEECH_KEY=your-speech-key
AZURE_SPEECH_REGION=eastus  # or your region

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# WebRTC Configuration (for voice interactions)
WEBRTC_SIGNALING_PORT=8443
WEBRTC_STUN_SERVER=stun:stun.l.google.com:19302

# Notification Services (all free)
# Email notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Discord webhooks (optional, for team notifications)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# FreeSWITCH (optional, for traditional phone system)
# FREESWITCH_HOST=localhost
# FREESWITCH_PORT=8021
# FREESWITCH_PASSWORD=ClueCon
# SIP_PROVIDER_HOST=sip.voip.ms
# SIP_PROVIDER_USER=your_username
# SIP_PROVIDER_PASSWORD=your_password

# Database (local)
DATABASE_URL=postgresql://tradesense:tradesense@localhost:5432/tradesense
REDIS_URL=redis://localhost:6379/0
```

### Step 4: Start Lightweight Local Services

```bash
# Start PostgreSQL + Redis only (~2-3GB RAM)
docker-compose -f docker-compose.lightweight.yml up -d

# Verify services are running
docker ps

# You should see 2 containers:
# - tradesense-postgres
# - tradesense-redis
```

### Step 5: Install Dependencies and Run

```bash
# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn api.main:app --reload

# Backend will be available at http://localhost:8000
```

### Step 6: Verify Cloud Integrations

```bash
# Test Gemini API
curl -X POST http://localhost:8000/api/test/gemini \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'

# Test Azure OpenAI
curl -X POST http://localhost:8000/api/test/azure-openai \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello, how are you?"}'

# Test Azure Speech (STT)
curl -X POST http://localhost:8000/api/test/speech-stt \
  -F "audio=@test-audio.wav"

# Check Langfuse dashboard
open https://cloud.langfuse.com
```

## What to Do Next

### Option 1: Continue with Task 2 (Cloud LLM Integration)

```bash
# Create LLM client implementations
cd backend/llm

# Files to create:
# - base.py (abstract LLM client)
# - gemini_client.py (Gemini API client)
# - azure_openai_client.py (Azure OpenAI client)

# Write and run tests
cd ../../tests/unit/llm
pytest test_llm_client.py -v
```

**Estimated Time**: 1-2 days  
**Requirements Validated**: 1.1, 1.2, 1.3, 1.4

### Option 2: Continue with Task 3 (Cloud Voice Processing)

```bash
# Create Azure Speech integration
cd backend/voice

# Files to create:
# - azure_speech_stt.py (Speech-to-Text)
# - azure_speech_tts.py (Text-to-Speech)
# - voice_pipeline.py (orchestration)

# Write and run tests
cd ../../tests/unit/voice
pytest test_voice_pipeline.py -v
```

**Estimated Time**: 1-2 days  
**Requirements Validated**: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6

### Option 3: Continue with Task 4 (Data Models)

```bash
# Create database models
cd backend/db

# Implement models.py with SQLAlchemy models
# Create and apply migrations
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head

# Write and run tests
cd ../../tests/unit/db
pytest test_models.py -v
```

**Estimated Time**: 1-2 days  
**Requirements Validated**: 4.2, 5.1, 6.1, 11.2, 18.6

## Development Commands

```bash
# Start lightweight local services
docker-compose -f docker-compose.lightweight.yml up -d

# Stop local services
docker-compose -f docker-compose.lightweight.yml down

# Run backend
cd backend
uvicorn api.main:app --reload

# Run tests
pytest tests/ -v

# Lint code
flake8 backend/
pylint backend/

# Format code
black backend/
isort backend/
```

## Project Structure (Cloud Edition)

```
tradesense/
├── backend/                 # Python backend (FastAPI, CrewAI, LangGraph)
│   ├── agents/             # Agent implementations (CrewAI, LangGraph, AutoGen)
│   ├── api/                # REST API endpoints
│   ├── core/               # ✅ Core config and models (DONE)
│   ├── db/                 # ✅ Database session (DONE)
│   ├── llm/                # ⏳ Cloud LLM clients (Task 2)
│   │   ├── base.py         # Abstract LLM client
│   │   ├── gemini_client.py    # Gemini API client
│   │   └── azure_openai_client.py  # Azure OpenAI client
│   ├── voice/              # ⏳ Azure Speech integration (Task 3)
│   │   ├── azure_speech_stt.py
│   │   ├── azure_speech_tts.py
│   │   └── voice_pipeline.py
│   └── requirements.txt    # Python dependencies
├── frontend/               # TypeScript frontend
│   └── src/types/          # ✅ Shared types (DONE)
├── docker/                 # Docker configs
│   └── compose/            # Lightweight compose files
├── docker-compose.lightweight.yml  # ✅ PostgreSQL + Redis (DONE)
├── .env.cloud.example      # ✅ Cloud environment template (DONE)
├── tests/                  # ⏳ Test suites (Tasks 2-26)
└── docs/                   # Documentation
    ├── QUICK_START.md      # ✅ This guide (DONE)
    ├── CLOUD_ARCHITECTURE.md  # ✅ Cloud setup guide (DONE)
    └── IMPLEMENTATION_STATUS.md  # ✅ Progress tracking (DONE)
```

## Resource Usage (Your Lenovo SlimPad 5)

**Local Services (Lightweight):**
- PostgreSQL: ~1GB RAM
- Redis: ~500MB RAM
- Docker overhead: ~500MB RAM
- **Total: ~2-3GB RAM** ✅ Your system can handle this!

**Cloud Services (No local resources):**
- Gemini API: Cloud processing
- Azure OpenAI: Cloud processing
- Azure Speech: Cloud processing
- Langfuse: Cloud observability
- Datadog: Cloud monitoring

**Your AMD Ryzen 7000 + AMD Radeon Graphics:**
- Perfect for development and testing
- No heavy AI workloads locally
- All AI processing happens in the cloud

## Cost Tracking

### First Year (Using Student Credits + Open-Source)

| Service | Monthly Usage | Cost | Credit Source |
|---------|---------------|------|---------------|
| Gemini API | 1500 req/day | $0 | Free tier |
| Azure OpenAI | ~10k tokens/day | $0 | $100 student credit |
| Azure Speech | ~100 min/day | $0 | Included in Azure |
| DigitalOcean | Basic droplet | $0 | $200 student credit |
| Datadog | Pro plan | $0 | Free 2 years (student) |
| Sentry | 500k events | $0 | Free tier |
| Langfuse | Basic usage | $0 | Free tier |
| **WebRTC + Jitsi** | **Unlimited** | **$0** | **Free & open-source** |
| **Web Push** | **Unlimited** | **$0** | **Free** |
| **Email** | **Reasonable use** | **$0** | **Free (Gmail/SMTP)** |
| **Discord** | **Unlimited** | **$0** | **Free webhooks** |
| **Total** | | **$0/month** | **GitHub Student Pack + Open-Source** |

### After Credits Expire (Year 2+)

| Service | Monthly Cost |
|---------|--------------|
| Gemini API | $0 (free tier) |
| Azure OpenAI | ~$20-30 |
| Azure Speech | ~$5-10 |
| Hosting | ~$5-10 |
| **WebRTC/Jitsi** | **$0** |
| **Notifications** | **$0** |
| **FreeSWITCH (optional)** | **$2-5** |
| **Total** | **~$30-45/month** |

**Budget Alert Setup:**
```bash
# Set up Azure budget alerts
# 1. Go to Azure Portal > Cost Management
# 2. Create budget: $50/month
# 3. Set alert at 80% ($40)
# 4. Get email notifications
```

## Common Issues and Solutions

### Issue: Gemini API quota exceeded

```bash
# Check your quota usage
curl "https://generativelanguage.googleapis.com/v1/models?key=$GEMINI_API_KEY"

# Solution: Implement caching in backend/llm/gemini_client.py
# - Cache responses for 1 hour
# - Use Redis for caching
# - Fallback to Azure OpenAI when quota exceeded
```

### Issue: Azure credits running low

```bash
# Check Azure credit balance
# 1. Go to Azure Portal
# 2. Click "Cost Management + Billing"
# 3. View "Credits" section

# Solution: Optimize usage
# - Use GPT-3.5-turbo instead of GPT-4 (10x cheaper)
# - Implement response caching
# - Use Gemini free tier first, Azure as fallback
```

### Issue: WebRTC connection fails

```bash
# Check STUN server connectivity
# Test in browser console:
const pc = new RTCPeerConnection({
  iceServers: [{urls: 'stun:stun.l.google.com:19302'}]
});

# Solution: Use alternative STUN servers
# - stun:stun1.l.google.com:19302
# - stun:stun2.l.google.com:19302
# - stun:stun.stunprotocol.org:3478
```

### Issue: Email notifications not sending

```bash
# Test SMTP connection
python -c "import smtplib; smtplib.SMTP('smtp.gmail.com', 587).starttls()"

# Solution: Use Gmail App Password
# 1. Go to Google Account > Security
# 2. Enable 2-Step Verification
# 3. Generate App Password
# 4. Use app password in SMTP_PASSWORD
```

## Next Steps Summary

1. ✅ **Foundation Complete** - Lightweight infrastructure ready
2. ⏳ **Task 2** - Implement cloud LLM integration (1-2 days)
3. ⏳ **Task 3** - Implement Azure Speech integration (1-2 days)
4. ⏳ **Task 4** - Create database models and migrations (1-2 days)
5. ⏳ **Task 5** - Checkpoint: Verify infrastructure (1 day)

**Total Estimated Time to Core Infrastructure**: 4-7 days

## Resources

- **Spec Files**: `.kiro/specs/tradesense-agentic-fsm/`
- **Cloud Architecture Guide**: `CLOUD_ARCHITECTURE.md`
- **Implementation Status**: `IMPLEMENTATION_STATUS.md`
- **Contributing Guide**: `CONTRIBUTING.md`
- **Task List**: `.kiro/specs/tradesense-agentic-fsm/tasks.md`

## GitHub Student Pack Resources

- **Main Page**: https://education.github.com/pack
- **Azure for Students**: https://azure.microsoft.com/en-us/free/students/
- **DigitalOcean**: https://www.digitalocean.com/github-students
- **Datadog**: https://www.datadoghq.com/partner/github-students/

## Open-Source Communication Resources

- **WebRTC Documentation**: https://webrtc.org/getting-started/overview
- **Jitsi Meet**: https://jitsi.github.io/handbook/docs/intro
- **FreeSWITCH**: https://freeswitch.org/confluence/
- **Discord Webhooks**: https://discord.com/developers/docs/resources/webhook
- **Complete Guide**: See `OPEN_SOURCE_COMMUNICATION.md`

## Support

For questions or issues:
1. Check `CLOUD_ARCHITECTURE.md` for cloud setup details
2. Review `IMPLEMENTATION_STATUS.md` for current progress
3. Consult task details in `.kiro/specs/tradesense-agentic-fsm/tasks.md`
4. Open GitHub issue for bugs or blockers

---

**You're ready to start building TradeSense with cloud AI!** 🚀

Your Lenovo SlimPad 5 is perfect for this cloud-based architecture. All heavy AI processing happens in the cloud, and you only run lightweight local services.

