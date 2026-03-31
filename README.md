# TradeSense - Cloud-Powered Agentic Field Service Management

> **GitHub Student Pack Optimized**: Voice-first agentic FSM system with zero first-year costs using student credits

An intelligent, voice-first field service management system that leverages cloud AI services (Google Gemini, Azure OpenAI, Azure Speech) to automate intake, diagnostics, scheduling, and compliance. Optimized for students and small businesses with lightweight local infrastructure.

## 🎓 GitHub Student Pack Benefits

**First Year: $0 operational cost** using student credits and open-source tools:
- Azure for Students: $100 credit (Azure OpenAI + Azure Speech)
- DigitalOcean: $200 credit (production hosting)
- Datadog: Free for 2 years (monitoring)
- Sentry: 500k events/month free (error tracking)
- Google Gemini: 1500 requests/day free tier
- WebRTC + Jitsi: Free & open-source (voice calls)
- Telegram Bot API: Free & unlimited (notifications)

**After Credits: ~$25-45/month** (vs $950-$3,900/month for traditional SaaS)

## ✨ Key Features

- **Voice-First Interface**: Hands-free job logging via Azure Speech Services (<500ms latency)
- **Multi-Agent AI**: CrewAI, LangGraph, AutoGen powered by Gemini API and Azure OpenAI
- **Intelligent Routing**: Automatic intent classification and agent coordination
- **Equipment Recognition**: Image-based identification using Gemini Vision
- **Smart Scheduling**: Route optimization and technician utilization
- **Compliance Tracking**: Automated carbon footprint calculation
- **Lightweight Local**: Only PostgreSQL + Redis (~2-3GB RAM)

## 🖥️ System Requirements

**Your System (Lenovo SlimPad 5):**
- AMD Ryzen 7000 series ✅
- AMD Radeon Graphics ✅
- 8GB+ RAM (for PostgreSQL + Redis) ✅
- Docker Desktop ✅
- Internet connection for cloud AI services ✅

**No heavy AI workloads locally** - all LLM and voice processing happens in the cloud!

## Tech Stack

### Cloud AI Services
- **Google Gemini API**: 1500 requests/day free tier
- **Azure OpenAI**: GPT-4/GPT-3.5 with student credits
- **Azure Speech Services**: STT + TTS with student credits
- **GitHub Copilot**: Free for students (development only)

### Orchestration & Agents
- **FastAPI**: Lightweight Python orchestration
- **CrewAI**: Role-based agent collaboration
- **LangGraph**: Graph-based diagnostic workflows
- **AutoGen**: Conversational troubleshooting
- **PydanticAI**: Typed/structured outputs

### Local Infrastructure (Lightweight)
- **PostgreSQL**: Local database (~1GB RAM)
- **Redis**: Local caching (~500MB RAM)
- **Docker**: Container management

### Observability (Cloud/Free Tier)
- **Langfuse**: Cloud LLM observability (free tier)
- **Datadog**: APM and monitoring (student - free 2 years)
- **Sentry**: Error tracking (500k events/month free)

### Communication
- **WebRTC + Jitsi**: Open-source voice calls (free)
- **Telegram Bot API**: Notifications and messaging (free)
- **FreeSWITCH**: Optional phone system integration ($2-5/month)

## 💰 Cost Breakdown

### First Year (Using Student Credits + Open-Source)
| Service | Cost | Source |
|---------|------|--------|
| Gemini API | $0/month | Free tier (1500 req/day) |
| Azure OpenAI | $0/month | $100 student credit |
| Azure Speech | $0/month | Included in Azure credit |
| DigitalOcean | $0/month | $200 student credit |
| **WebRTC/Jitsi** | **$0/month** | **Free & open-source** |
| **Telegram Bot** | **$0/month** | **Free & unlimited** |
| Datadog | $0/month | Free for 2 years (student) |
| Sentry | $0/month | Free tier |
| Langfuse | $0/month | Free tier |
| **Total** | **$0/month** | **GitHub Student Pack + Open-Source** |

### After Credits Expire
| Service | Cost |
|---------|------|
| Gemini API | $0 (free tier sufficient) |
| Azure OpenAI | ~$20-30/month |
| Azure Speech | ~$5-10/month |
| Hosting | ~$5-10/month |
| **WebRTC/Telegram** | **$0/month** |
| **FreeSWITCH (optional)** | **$2-5/month** |
| **Total** | **~$25-45/month** |

**vs Traditional SaaS: $950-$3,900/month** 💸

## Project Structure

```
tradesense/
├── backend/              # Python backend services
│   ├── agents/          # CrewAI, LangGraph, AutoGen agents
│   ├── api/             # FastAPI REST API
│   ├── core/            # Core business logic & models
│   ├── db/              # Database session management
│   ├── llm/             # Cloud LLM client interfaces
│   │   ├── base.py      # Abstract LLM client
│   │   ├── gemini_client.py    # Gemini API client
│   │   └── azure_openai_client.py  # Azure OpenAI client
│   ├── voice/           # Azure Speech Services integration
│   └── requirements.txt # Python dependencies
├── frontend/            # TypeScript frontend (optional)
│   └── src/types/       # Shared TypeScript types
├── docker/              # Docker configurations
│   └── compose/         # Lightweight Docker Compose (PostgreSQL + Redis)
├── tests/               # Test suites
│   ├── integration/     # Integration tests
│   ├── property/        # Property-based tests
│   └── unit/            # Unit tests
├── .env.cloud.example   # Cloud environment template
├── docker-compose.lightweight.yml  # Lightweight local services
└── docs/                # Documentation
    ├── QUICK_START.md
    ├── CLOUD_ARCHITECTURE.md
    └── IMPLEMENTATION_STATUS.md
```

## 🚀 Quick Start

### Step 1: Activate GitHub Student Pack

1. Visit https://education.github.com/pack
2. Verify your student status
3. Activate these services:
   - Azure for Students ($100 credit)
   - DigitalOcean ($200 credit)
   - Twilio ($50 credit)
   - Datadog (free 2 years)
   - GitHub Copilot (free)

### Step 2: Set Up Cloud Services

**Google Gemini API:**
```bash
# Visit https://makersuite.google.com/app/apikey
# Create API key
# Copy to .env file
```

**Azure OpenAI:**
```bash
# Visit https://portal.azure.com
# Create Azure OpenAI resource
# Deploy GPT-4 or GPT-3.5-turbo model
# Copy endpoint and key to .env file
```

**Azure Speech Services:**
```bash
# In Azure Portal, create Speech Services resource
# Copy key and region to .env file
```

**Langfuse:**
```bash
# Visit https://cloud.langfuse.com
# Create account (already done ✅)
# Create project and copy API keys
```

### Step 3: Local Setup

```bash
# Clone the repository
git clone <repository-url>
cd tradesense

# Copy cloud environment template
cp .env.cloud.example .env

# Edit .env with your API keys:
# - GEMINI_API_KEY
# - AZURE_OPENAI_KEY
# - AZURE_OPENAI_ENDPOINT
# - AZURE_SPEECH_KEY
# - AZURE_SPEECH_REGION
# - TWILIO_ACCOUNT_SID
# - TWILIO_AUTH_TOKEN
# - LANGFUSE_PUBLIC_KEY
# - LANGFUSE_SECRET_KEY

# Start lightweight local services (PostgreSQL + Redis)
docker-compose -f docker-compose.lightweight.yml up -d

# Install Python dependencies
cd backend
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the backend
uvicorn api.main:app --reload
```

Visit http://localhost:8000/docs for API documentation.

## 📚 Documentation

- **[Quick Start Guide](QUICK_START.md)** - Detailed setup with screenshots
- **[Cloud Architecture](CLOUD_ARCHITECTURE.md)** - Complete GitHub Student Pack integration guide
- **[Open-Source Communication](OPEN_SOURCE_COMMUNICATION.md)** - WebRTC, Telegram, FreeSWITCH alternatives (No Twilio!)
- **[Implementation Status](IMPLEMENTATION_STATUS.md)** - Current progress (Task 1/26 complete)
- **[Contributing Guide](CONTRIBUTING.md)** - How to contribute

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Voice Interface Layer                     │
│              Azure Speech Services (Cloud)                   │
│           STT + TTS + VAD (<500ms latency)                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Agent Orchestration Layer                   │
│         FastAPI + CrewAI + LangGraph + AutoGen              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Cloud LLM Services                        │
│   Gemini API (Free) → Azure OpenAI (Student) → Copilot     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Local Data Layer                            │
│            PostgreSQL + Redis (~2-3GB RAM)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Observability Layer                       │
│      Langfuse (Cloud) + Datadog (Student) + Sentry         │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Use Cases

1. **Solo Technician**: Gemini free tier, lightweight laptop setup
2. **Small Shop (2-10 techs)**: Azure student credits, basic hosting
3. **Medium Shop (10-25 techs)**: Paid Azure tier, optimized caching
4. **Enterprise (25+ techs)**: Full Azure deployment, dedicated resources

## 🔒 Security & Privacy

- Customer data stored locally (PostgreSQL)
- API calls to Gemini/Azure for AI processing only
- No customer PII sent to cloud AI services
- TLS 1.3 encryption for all network communication
- OAuth 2.0 authentication
- Role-based access control (RBAC)

## 📊 Performance Targets

- Voice latency: <500ms (p95 <600ms)
- Agent response: <5s for simple tasks
- Concurrent sessions: 50+ on cloud infrastructure
- Daily job capacity: 1,000+ jobs
- Gemini free tier: Sufficient for 50-100 jobs/day

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- GitHub Education for the Student Developer Pack
- Google for Gemini API free tier
- Microsoft Azure for Students program
- All open-source contributors

## 📞 Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/yourusername/tradesense/issues)
- Discussions: [GitHub Discussions](https://github.com/yourusername/tradesense/discussions)

---

**Built with ❤️ for students and small businesses**
