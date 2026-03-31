# Implementation Plan: TradeSense Agentic Field Service Management System

## Overview

This implementation plan transforms the TradeSense design into actionable coding tasks using a hybrid Python/TypeScript stack with cloud-based AI services optimized for GitHub Student Pack benefits. The system achieves minimal operational costs through cloud LLM APIs (Google Gemini Free Tier + GitHub Copilot), cloud voice processing (Azure Speech Services), and lightweight local infrastructure. Implementation follows a bottom-up approach: infrastructure → cloud integrations → agent frameworks → MCP integrations → observability → integration testing.

**Tech Stack**: Python (FastAPI, CrewAI, AutoGen), TypeScript (LangGraph, MCP SDK), Docker, PostgreSQL (local), Redis (local), Google Gemini API (Free Tier), Azure OpenAI (GitHub Student), Azure Speech Services (GitHub Student), WebRTC + Jitsi (open-source voice), Web Push + Email + Discord (notifications).

**Hardware Requirements**: Lenovo SlimPad 5 (AMD Ryzen 7000, AMD Radeon Graphics) - Lightweight local development with cloud AI services. No heavy local AI models required.

**GitHub Student Pack Services Used**:
- Azure for Students ($100 credit) - Azure OpenAI, Azure Speech Services
- Google Gemini API (Free Tier) - 1500 requests/day
- GitHub Copilot (Free) - Development assistance
- DigitalOcean ($200 credit) - Production hosting
- Datadog (Free 2 years) - Monitoring and observability
- Sentry (500k events/month free) - Error tracking

**Open-Source Communication Stack**:
- WebRTC + Jitsi (Primary) - Web-based voice interactions (free)
- FreeSWITCH (Optional) - Traditional phone system ($2-5/month)
- Web Push Notifications (free)
- Email Notifications (free)
- Discord Webhooks (free)

## Tasks

- [x] 1. Set up foundational infrastructure and development environment
  - Create project directory structure with Python and TypeScript workspaces
  - Initialize Docker Compose configuration for local development (PostgreSQL + Redis only)
  - Set up PostgreSQL database with initial schema
  - Set up Redis for caching and session management
  - Configure environment variables and secrets management
  - Create shared TypeScript types and Python models for cross-language compatibility
  - _Requirements: 12.1, 12.6, 12.7, 17.1, 17.4_

- [x] 2. Implement cloud LLM integration infrastructure
  - [x] 2.1 Set up Google Gemini API integration
    - Create Gemini API client with free tier support (1500 requests/day)
    - Implement rate limiting and quota management
    - Add request/response caching to maximize free tier usage
    - Configure fallback to GitHub Copilot API when quota exceeded
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 12.5_

  - [x] 2.2 Set up Azure OpenAI integration (GitHub Student)
    - Create Azure OpenAI client using student credits
    - Configure GPT-4 and GPT-3.5-turbo endpoints
    - Implement authentication with Azure credentials
    - Add cost tracking and budget alerts
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.3 Create unified LLM client interface (Python)
    - Implement abstract LLMClient base class
    - Create GeminiClient and AzureOpenAIClient implementations
    - Add intelligent routing: Gemini (free) → Azure OpenAI (student credits) → GitHub Copilot
    - Implement request/response logging and cost tracking
    - _Requirements: 1.6, 1.7, 1.8_

  - [ ] 2.4 Write unit tests for LLM client
    - Test model selection logic
    - Test fallback behavior when quota exceeded
    - Test rate limiting and caching
    - _Requirements: 1.3, 1.4, 12.5_

  - [x] 2.5 Comprehensive testing for Task 2 (Cloud LLM Integration)
    - [ ] 2.5.1 Unit tests
      - Test Gemini API client initialization and configuration
      - Test Azure OpenAI client initialization and configuration
      - Test unified client routing logic
      - Test rate limiting and quota management
      - Test caching mechanisms
      - Test error handling and fallback behavior
    - [ ] 2.5.2 Integration tests
      - Test end-to-end LLM request flow (Gemini → Azure → Copilot)
      - Test quota exhaustion and automatic fallback
      - Test cost tracking across multiple providers
      - Test concurrent request handling
    - [ ] 2.5.3 System tests
      - Test LLM integration with real API endpoints
      - Test performance under load (100+ concurrent requests)
      - Test cost optimization strategies
      - Verify all LLM-related requirements are met
    - [ ] 2.5.4 End-to-end tests
      - Test complete workflow: user request → LLM processing → response
      - Test multi-turn conversations with context preservation
      - Test error recovery and graceful degradation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 1.8, 12.5_


- [ ] 3. Implement cloud voice processing pipeline
  - [x] 3.1 Set up Azure Speech Services STT (Python)
    - Install Azure Speech SDK with GitHub Student credits
    - Create FastAPI endpoint for audio transcription
    - Implement streaming transcription with <500ms first-token latency
    - Configure speech recognition for noisy environments
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.2 Set up Azure Speech Services TTS (Python)
    - Configure Azure Neural TTS with natural voices
    - Create FastAPI endpoint for speech synthesis
    - Implement sub-100ms synthesis latency
    - Add voice customization options
    - _Requirements: 2.5, 2.6_

  - [x] 3.3 Implement Azure Speech VAD (Python)
    - Use Azure Speech SDK's built-in VAD
    - Create adaptive threshold logic for noisy environments
    - Implement speech boundary detection
    - _Requirements: 2.2, 2.7_

  - [x] 3.4 Create voice pipeline orchestrator (Python/TypeScript)
    - Initialize voice pipeline with Azure Speech components
    - Implement turn-taking and interruption handling
    - Add session management and state tracking
    - Integrate with FastAPI voice services
    - _Requirements: 2.8, 2.9, 2.10_

  - [x] 3.5 Write property test for voice latency
    - **Property 1: Voice Latency Guarantee (Cloud Processing)**
    - **Validates: Requirements 2.4, 14.1**

  - [x] 3.6 Write property test for TTS performance
    - **Property 2: Voice TTS Performance**
    - **Validates: Requirements 2.6**

  - [x] 3.7 Write property test for turn-taking accuracy
    - **Property 3: Turn-Taking Accuracy**
    - **Validates: Requirements 2.10**

  - [x] 3.8 Comprehensive testing for Task 3 (Cloud Voice Processing)
    - [ ] 3.8.1 Unit tests
      - Test Azure Speech STT initialization and configuration
      - Test Azure Speech TTS initialization and configuration
      - Test VAD threshold detection and adaptation
      - Test voice pipeline state management
      - Test session lifecycle management
      - Test error handling for each component
    - [ ] 3.8.2 Integration tests
      - Test STT → LLM → TTS complete flow
      - Test VAD integration with STT
      - Test pipeline orchestration with all components
      - Test interruption handling and turn-taking
      - Test streaming transcription and synthesis
    - [ ] 3.8.3 System tests
      - Test voice pipeline with real Azure Speech Services
      - Test performance under various network conditions
      - Test with different audio qualities and noise levels
      - Test with multiple concurrent voice sessions
      - Verify latency requirements (<500ms p95)
    - [ ] 3.8.4 End-to-end tests
      - Test complete voice interaction: audio in → transcription → LLM → synthesis → audio out
      - Test multi-turn conversations with context
      - Test error recovery and fallback to text mode
      - Test with various accents and speaking styles
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 14.1_

- [x] 4. Implement core data models and database layer
  - [x] 4.1 Create PostgreSQL schema and migrations (Python)
    - Define tables: leads, jobs, customers, technicians, parts, conversations, audit_logs
    - Create indexes for frequently queried fields
    - Implement partitioning for audit logs (monthly)
    - _Requirements: 11.2, 18.6, 18.8_

  - [x] 4.2 Implement Pydantic data models (Python)
    - Create models: Lead, Job, Customer, Technician, Part, ConversationContext, MCPToolCall
    - Add validation rules from design document
    - Implement serialization/deserialization
    - _Requirements: 4.2, 5.1, 6.1_

  - [x] 4.3 Create database access layer with SQLAlchemy (Python)
    - Implement repository pattern for each entity
    - Add connection pooling (min: 5, max: 20)
    - Implement transaction management with retry logic
    - _Requirements: 15.8, 17.9_

  - [x] 4.4 Set up Redis caching layer (Python)
    - Create Redis client with connection pooling
    - Implement caching for session state, technician schedules, customer data
    - Configure TTLs: 15min (schedules), 1hr (customer data)
    - _Requirements: 3.7, 15.9_

  - [x] 4.5 Write unit tests for data models
    - Test validation rules for all models
    - Test serialization/deserialization
    - Test database CRUD operations
    - _Requirements: 4.2, 5.1, 6.1_

  - [x] 4.6 Comprehensive testing for Task 4 (Data Models and Database)
    - [x] 4.6.1 Unit tests
      - Test Pydantic model validation for all entities
      - Test model serialization/deserialization
      - Test database repository CRUD operations
      - Test connection pooling and transaction management
      - Test Redis caching operations
      - Test cache TTL and invalidation
    - [x] 4.6.2 Integration tests
      - Test database migrations and schema changes
      - Test data integrity constraints
      - Test concurrent database access
      - Test cache synchronization with database
      - Test transaction rollback and retry logic
    - [x] 4.6.3 System tests
      - Test database performance under load
      - Test connection pool behavior under stress
      - Test cache hit/miss ratios
      - Test data consistency across cache and database
      - Verify partitioning for audit logs
    - [x] 4.6.4 End-to-end tests
      - Test complete data flow: API → validation → database → cache
      - Test data retrieval with caching
      - Test audit log creation and querying
    - _Requirements: 4.2, 5.1, 6.1, 11.2, 15.8, 15.9, 17.9, 18.6, 18.8_

- [x] 5. Checkpoint - Verify infrastructure and data layer
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 6. Implement lightweight pipeline orchestration
  - [x] 6.1 Set up FastAPI-based orchestration (Python)
    - Create FastAPI application for workflow coordination
    - Implement simple pipeline execution with async/await
    - Configure secrets management with environment variables
    - Set up basic retry policies
    - _Requirements: 3.1, 3.3, 3.6_

  - [x] 6.2 Create base pipeline components (Python)
    - Implement pipeline steps for agent execution
    - Create workflow templates for intake, diagnostic, fulfillment
    - Add basic artifact tracking
    - _Requirements: 3.2, 3.5_

  - [x] 6.3 Implement telemetry integration (Python)
    - Add Langfuse cloud tracing integration
    - Add Datadog monitoring (GitHub Student - free 2 years)
    - Add Sentry error tracking (500k events/month free)
    - _Requirements: 3.8, 9.1, 9.2, 9.3_

  - [x] 6.4 Write property test for pipeline retry behavior
    - **Property 16: Pipeline Retry Behavior**
    - **Validates: Requirements 3.4**

  - [x] 6.5 Write unit tests for orchestration
    - Test pipeline execution and artifact tracking
    - Test secrets management
    - Test retry policies
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 6.6 Comprehensive testing for Task 6 (Pipeline Orchestration)
    - [x] 6.6.1 Unit tests
      - Test FastAPI application initialization
      - Test pipeline step execution
      - Test workflow template creation
      - Test artifact tracking
      - Test secrets management
      - Test retry policy configuration
    - [x] 6.6.2 Integration tests
      - Test complete pipeline execution with multiple steps
      - Test telemetry integration (Langfuse, Datadog, Sentry)
      - Test error propagation and handling
      - Test concurrent pipeline execution
    - [x] 6.6.3 System tests
      - Test pipeline performance under load
      - Test observability data collection
      - Test retry behavior with real failures
      - Verify all telemetry is captured correctly
    - [x] 6.6.4 End-to-end tests
      - Test complete workflow: trigger → execution → completion → telemetry
      - Test pipeline failure and recovery
      - Test artifact persistence and retrieval
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8, 9.1, 9.2, 9.3_

- [ ] 7. Implement MCP integration layer
  - [x] 7.1 Create MCP client manager (TypeScript)
    - Implement MCP SDK integration for stdio and SSE transports
    - Create connection pooling and lifecycle management
    - Add JSON-RPC 2.0 message serialization/deserialization
    - Implement tool schema caching
    - _Requirements: 10.6, 10.9_

  - [x] 7.2 Implement FileSystem MCP integration (TypeScript)
    - Connect to FileSystem MCP server for local manuals/drawings
    - Implement file search and retrieval
    - Add support for PDF, Markdown, HTML formats
    - _Requirements: 10.1, 20.1, 20.4_

  - [x] 7.3 Implement Database MCP integration (TypeScript)
    - Connect to Database MCP for PostgreSQL/SQLite access
    - Implement query execution and result parsing
    - _Requirements: 10.2_

  - [x] 7.4 Implement InvenTree API integration (Python)
    - Create InvenTree REST API client
    - Implement inventory queries, updates, and part searches
    - Add authentication and error handling
    - _Requirements: 7.1, 7.2, 7.9_

  - [x] 7.5 Implement Part-DB integration (Python)
    - Create Part-DB REST API client
    - Implement component specification queries
    - Add KiCad symbol/footprint retrieval
    - _Requirements: 7.3, 7.4_

  - [x] 7.6 Implement KiCost distributor scraping (Python)
    - Integrate KiCost library for BOM pricing
    - Configure distributors: Digi-Key, Mouser, Arrow, Newark, TME
    - Implement price comparison and best-price selection
    - _Requirements: 7.5, 7.6, 7.7_

  - [x] 7.7 Implement Kabaun carbon tracking (Python)
    - Integrate Kabaun library for emission factors
    - Add eGRID, EPA GHG, ADEME dataset queries
    - Implement CodeCarbon for AI infrastructure emissions
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [x] 7.8 Write property test for MCP tool schema validation
    - **Property 6: MCP Tool Schema Validation**
    - **Validates: Requirements 10.7, 10.8**

  - [ ] 7.9 Write property test for MCP caching behavior
    - **Property 19: MCP Caching Behavior**
    - **Validates: Requirements 15.2**

  - [ ]* 7.10 Write property test for MCP retry with exponential backoff
    - **Property 20: MCP Retry with Exponential Backoff**
    - **Validates: Requirements 15.3**

  - [x]* 7.11 Write unit tests for MCP integrations
    - Test connection management and failover
    - Test tool execution and result validation
    - Test InvenTree, Part-DB, KiCost, Kabaun integrations
    - _Requirements: 10.1, 10.2, 10.9, 15.2, 15.3_

  - [x] 7.12 Comprehensive testing for Task 7 (MCP Integration)
    - [x] 7.12.1 Unit tests
      - Test MCP client initialization and connection
      - Test tool schema parsing and validation
      - Test JSON-RPC message serialization
      - Test connection pooling and lifecycle
      - Test each MCP integration (FileSystem, Database, InvenTree, Part-DB, KiCost, Kabaun)
      - Test error handling for each integration
    - [x] 7.12.2 Integration tests
      - Test MCP tool execution with real servers
      - Test tool chaining and composition
      - Test caching behavior across multiple calls
      - Test retry logic with exponential backoff
      - Test failover between MCP servers
    - [x] 7.12.3 System tests
      - Test MCP throughput (1000+ calls/minute)
      - Test concurrent tool execution
      - Test performance with large result sets
      - Test memory usage with connection pooling
      - Verify all MCP-related requirements are met
    - [x] 7.12.4 End-to-end tests
      - Test complete workflow: agent request → MCP tool call → result processing
      - Test multi-tool workflows (e.g., search parts → check inventory → get pricing)
      - Test error recovery and fallback mechanisms
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.9, 8.1, 8.2, 8.3, 8.4, 8.5, 10.1, 10.2, 10.6, 10.7, 10.8, 10.9, 15.2, 15.3, 20.1, 20.4_


- [x] 8. Implement CrewAI Intake Agent
  - [x] 8.1 Create Intake Agent with CrewAI (Python)
    - Define intake agent roles and goals
    - Implement lead capture from voice/SMS/web sources
    - Add PydanticAI integration for structured output extraction
    - Connect to Gemini API (free tier) with Azure OpenAI fallback
    - _Requirements: 4.1, 4.2, 4.9_

  - [x] 8.2 Implement triage and classification logic (Python)
    - Create urgency classifier (emergency, urgent, routine)
    - Implement service type detection
    - Add confidence scoring
    - _Requirements: 4.3, 4.4_

  - [x] 8.3 Integrate with cloud inventory services (Python)
    - Create simple inventory tracking in PostgreSQL
    - Implement parts availability checking
    - Add basic parts search functionality
    - _Requirements: 4.6, 4.7_

  - [x] 8.4 Implement WebRTC + notification integration (Python)
    - Set up WebRTC signaling server for voice interactions
    - Implement web push notifications for technician alerts
    - Create email notification system for customer updates
    - Add Discord webhook integration for team notifications
    - (Optional) Set up FreeSWITCH for traditional phone system integration
    - _Requirements: 4.1, 4.8_

  - [x] 8.5 Create lead creation and notification logic (Python)
    - Implement lead record creation in PostgreSQL
    - Add technician notification via SMS/push
    - Integrate with FastAPI pipeline
    - _Requirements: 4.8, 4.10_

  - [ ]* 8.6 Write property test for intake classification performance
    - **Property 17: Intake Classification Performance**
    - **Validates: Requirements 4.4**

  - [ ]* 8.7 Write unit tests for Intake Agent
    - Test lead capture from multiple sources
    - Test triage classification accuracy
    - Test WebRTC voice integration
    - Test notification delivery (email, push, Discord)
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 8.8 Comprehensive testing for Task 8 (Intake Agent)
    - [x] 8.8.1 Unit tests
      - Test CrewAI agent initialization and configuration
      - Test lead capture from voice, SMS, web sources
      - Test urgency classification logic
      - Test service type detection
      - Test confidence scoring
      - Test parts availability checking
      - Test notification creation (email, push, Discord)
    - [x] 8.8.2 Integration tests
      - Test complete intake flow: capture → classify → create lead → notify
      - Test WebRTC voice integration with STT
      - Test inventory service integration
      - Test notification delivery across all channels
      - Test LLM integration (Gemini/Azure) for classification
    - [x] 8.8.3 System tests
      - Test intake performance under load (100+ concurrent requests)
      - Test classification accuracy with real data
      - Test notification delivery reliability
      - Test WebRTC session management
      - Verify all intake-related requirements are met
    - [x] 8.8.4 End-to-end tests
      - Test complete customer intake: voice call → transcription → classification → lead creation → technician notification
      - Test multi-channel intake (voice, SMS, web)
      - Test error handling and fallback mechanisms
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.6, 4.7, 4.8, 4.9, 4.10_

- [x] 9. Implement LangGraph + AutoGen Diagnostic Agent
  - [x] 9.1 Create LangGraph diagnostic workflow (TypeScript)
    - Define diagnostic state graph with reasoning chains
    - Implement issue analysis nodes
    - Add state persistence to Redis
    - Connect to Gemini API with Azure OpenAI fallback
    - _Requirements: 5.1, 5.2_

  - [x] 9.2 Implement multimodal image parsing (Python)
    - Integrate Gemini Vision API for image understanding
    - Create equipment label OCR pipeline
    - Extract manufacturer, model number, serial number
    - _Requirements: 5.3, 5.4, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

  - [x] 9.3 Implement parts sourcing with alternatives (Python)
    - Query PostgreSQL inventory for primary parts
    - Implement simple parts database
    - Create basic price comparison logic
    - Find compatible alternatives when unavailable
    - _Requirements: 5.5, 5.6, 7.5, 7.6, 7.7_

  - [x] 9.4 Create repair guide generation (Python)
    - Use Gemini API for step-by-step instructions
    - Add safety warnings and best practices
    - Include parts list and tools required
    - _Requirements: 5.7_

  - [x] 9.5 Implement AutoGen collaborative troubleshooting (Python)
    - Create AutoGen conversational agents
    - Implement multi-turn troubleshooting dialogue
    - Add technician feedback integration
    - _Requirements: 5.8, 5.11_

  - [x] 9.6 Integrate simple documentation RAG (Python)
    - Set up basic document indexing with embeddings
    - Index technical manuals from local filesystem
    - Implement semantic search with Gemini embeddings
    - Add source citations
    - _Requirements: 5.9, 20.2, 20.3, 20.6, 20.9_

  - [ ]* 9.7 Write property test for equipment image extraction
    - **Property 18: Equipment Image Extraction**
    - **Validates: Requirements 5.4, 19.6**

  - [ ]* 9.8 Write property test for parts availability accuracy
    - **Property 9: Parts Availability Accuracy**
    - **Validates: Requirements 5.6, 7.7**

  - [ ]* 9.9 Write unit tests for Diagnostic Agent
    - Test issue diagnosis accuracy
    - Test image parsing and OCR
    - Test parts sourcing and alternatives
    - Test repair guide generation
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 9.10 Comprehensive testing for Task 9 (Diagnostic Agent)
    - [x] 9.10.1 Unit tests
      - Test LangGraph workflow initialization
      - Test diagnostic reasoning chain logic
      - Test Gemini Vision API integration
      - Test OCR for equipment labels
      - Test parts sourcing logic
      - Test alternative parts finding
      - Test repair guide generation
      - Test AutoGen agent collaboration
      - Test documentation RAG search
    - [x] 9.10.2 Integration tests
      - Test complete diagnostic flow: issue → analysis → parts → repair guide
      - Test multimodal image processing pipeline
      - Test parts sourcing with inventory and pricing APIs
      - Test documentation retrieval and citation
      - Test LLM integration (Gemini/Azure) for diagnosis
    - [x] 9.10.3 System tests
      - Test diagnostic performance under load
      - Test image processing accuracy with real equipment photos
      - Test parts availability accuracy
      - Test documentation retrieval performance (<1s)
      - Verify all diagnostic-related requirements are met
    - [x] 9.10.4 End-to-end tests
      - Test complete diagnostic workflow: technician photo → equipment identification → parts sourcing → repair guide
      - Test multi-turn troubleshooting with AutoGen
      - Test error handling and fallback mechanisms
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.11, 7.5, 7.6, 7.7, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 20.2, 20.3, 20.6, 20.9_


- [x] 10. Implement CrewAI Fulfillment Agent
  - [x] 10.1 Create Fulfillment Agent with CrewAI (Python)
    - Define fulfillment agent roles and goals
    - Implement job completion logging
    - Add voice-driven data capture
    - Connect to Gemini API with Azure OpenAI fallback
    - _Requirements: 6.7, 6.11_

  - [x] 10.2 Implement schedule optimization algorithm (Python)
    - Create job assignment logic with skill matching
    - Implement route optimization to minimize travel time
    - Add constraint satisfaction (time windows, skills)
    - Calculate utilization rate (target: 75%+)
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 10.3 Implement emergency job prioritization (Python)
    - Add priority-based scheduling
    - Implement schedule re-optimization for emergencies
    - _Requirements: 6.5, 6.6_

  - [x] 10.4 Implement basic carbon footprint calculation (Python)
    - Create simple emission calculation formulas
    - Calculate travel emissions using distance and vehicle type
    - Track basic job-related emissions
    - Sum all emission sources
    - _Requirements: 6.8, 8.6, 8.7, 8.9_

  - [x] 10.5 Create compliance reporting (Python)
    - Generate sustainability reports
    - Determine compliance status against regulations
    - Provide emission reduction recommendations
    - _Requirements: 6.10, 8.8_

  - [x] 10.6 Implement KPI tracking (Python)
    - Track first-time fix rate
    - Track job completion rate
    - Track technician utilization
    - Store metrics in PostgreSQL
    - _Requirements: 9.7, 9.8_

  - [ ]* 10.7 Write property test for schedule optimization constraints
    - **Property 7: Schedule Optimization Constraints**
    - **Validates: Requirements 6.2, 6.3**

  - [ ]* 10.8 Write property test for schedule travel optimization
    - **Property 8: Schedule Travel Optimization**
    - **Validates: Requirements 6.4**

  - [ ]* 10.9 Write property test for carbon calculation completeness
    - **Property 11: Carbon Calculation Completeness**
    - **Validates: Requirements 8.6, 8.10**

  - [ ]* 10.10 Write property test for inventory synchronization
    - **Property 10: Inventory Synchronization**
    - **Validates: Requirements 7.2**

  - [ ]* 10.11 Write unit tests for Fulfillment Agent
    - Test schedule optimization algorithm
    - Test carbon footprint calculation
    - Test compliance reporting
    - Test KPI tracking
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.8_

  - [x] 10.12 Comprehensive testing for Task 10 (Fulfillment Agent)
    - [x] 10.12.1 Unit tests
      - Test CrewAI agent initialization
      - Test job assignment logic with skill matching
      - Test route optimization algorithm
      - Test constraint satisfaction (time windows, skills)
      - Test emergency job prioritization
      - Test carbon footprint calculation formulas
      - Test compliance reporting logic
      - Test KPI tracking and metrics
    - [x] 10.12.2 Integration tests
      - Test complete fulfillment flow: job → schedule → optimize → assign → track
      - Test schedule re-optimization for emergencies
      - Test carbon calculation with real job data
      - Test compliance report generation
      - Test voice-driven job completion logging
    - [x] 10.12.3 System tests
      - Test schedule optimization with 50+ jobs and 10+ technicians
      - Test optimization performance (<5s for 100 jobs)
      - Test utilization rate calculation (target 75%+)
      - Test carbon tracking accuracy
      - Verify all fulfillment-related requirements are met
    - [x] 10.12.4 End-to-end tests
      - Test complete workflow: job completion → schedule update → carbon tracking → KPI update
      - Test emergency job insertion and re-optimization
      - Test compliance reporting with real data
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.10, 6.11, 8.6, 8.7, 8.8, 8.9, 9.7, 9.8_

- [x] 11. Checkpoint - Verify agent implementations
  - Ensure all tests pass, ask the user if questions arise.


- [x] 12. Implement agent routing and conversation management
  - [x] 12.1 Create intent classification service (Python)
    - Implement intent classifier using Gemini API
    - Define intent types: JOB_COMPLETION, LEAD_INTAKE, DIAGNOSIS, PARTS_QUERY, SCHEDULING
    - Add confidence scoring (threshold: 0.6)
    - _Requirements: 15.4_

  - [x] 12.2 Implement agent routing logic (Python)
    - Create routeToAgent function with intent-to-agent mapping
    - Add agent capability matching
    - Implement fallback to clarifying questions when confidence < 0.6
    - Log routing decisions to audit trail
    - _Requirements: 15.4_

  - [x] 12.3 Create conversation context manager (Python)
    - Implement ConversationContext model
    - Add session state management in Redis
    - Track conversation history and entities
    - Implement context passing between agents
    - _Requirements: 3.2, 4.10_

  - [x] 12.4 Implement audit trail logging (Python)
    - Log all conversation turns with timestamps
    - Log all API calls and costs
    - Log all agent routing decisions
    - Store in PostgreSQL with partitioning
    - _Requirements: 11.6, 18.6, 18.7, 18.8_

  - [ ]* 12.5 Write property test for agent routing correctness
    - **Property 5: Agent Routing Correctness**
    - **Validates: Requirements 3.1, 3.2**

  - [ ]* 12.6 Write property test for conversation audit trail
    - **Property 12: Conversation Audit Trail**
    - **Validates: Requirements 11.6, 18.6**

  - [ ]* 12.7 Write unit tests for routing and conversation management
    - Test intent classification accuracy
    - Test agent routing logic
    - Test conversation context management
    - Test audit trail logging
    - _Requirements: 3.1, 3.2, 15.4, 18.6_

  - [x] 12.8 Comprehensive testing for Task 12 (Agent Routing and Conversation)
    - [x] 12.8.1 Unit tests
      - Test intent classification with various inputs
      - Test confidence scoring accuracy
      - Test agent routing decision logic
      - Test conversation context creation and updates
      - Test context passing between agents
      - Test audit trail logging format and completeness
    - [x] 12.8.2 Integration tests
      - Test complete routing flow: input → classify → route → execute → log
      - Test multi-turn conversations with context preservation
      - Test agent handoff scenarios
      - Test fallback to clarifying questions
      - Test audit trail persistence to database
    - [x] 12.8.3 System tests
      - Test routing performance under load
      - Test classification accuracy with real conversations
      - Test context management with concurrent sessions
      - Test audit trail query performance
      - Verify all routing-related requirements are met
    - [x] 12.8.4 End-to-end tests
      - Test complete conversation: user input → intent → routing → agent execution → response → audit
      - Test complex multi-agent workflows
      - Test error handling and recovery
    - _Requirements: 3.1, 3.2, 3.3, 4.10, 11.6, 15.4, 18.6, 18.7, 18.8_

- [~] 13. Implement voice-to-agent integration
  - [ ] 13.1 Create voice session manager (Python)
    - Implement VoiceSession model
    - Add session lifecycle management
    - Track session metrics (latency, turn count, API costs)
    - _Requirements: 2.8, 2.9_

  - [ ] 13.2 Integrate voice pipeline with FastAPI orchestration (Python)
    - Create FastAPI endpoints for voice interactions
    - Connect Azure Speech pipeline to agent routing
    - Implement voice-to-text-to-agent-to-speech flow
    - Add error handling and fallback to text mode
    - _Requirements: 3.1, 3.2, 15.1_

  - [ ] 13.3 Implement streaming response handling (Python)
    - Stream partial transcriptions for responsiveness
    - Implement interruption handling
    - Add turn-taking detection
    - _Requirements: 2.10_

  - [ ]* 13.4 Write integration test for voice-to-database flow
    - Test complete voice interaction workflow
    - Verify data integrity across pipeline
    - Test with various accents and noise levels
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ] 13.5 Comprehensive testing for Task 13 (Voice-to-Agent Integration)
    - [ ] 13.5.1 Unit tests
      - Test VoiceSession model and lifecycle
      - Test session metrics tracking
      - Test FastAPI endpoint creation
      - Test voice-to-text-to-agent-to-speech flow components
      - Test streaming response handling
      - Test interruption detection
    - [ ] 13.5.2 Integration tests
      - Test complete voice pipeline integration with agent routing
      - Test voice session management with multiple concurrent sessions
      - Test error handling and fallback to text mode
      - Test turn-taking and interruption handling
      - Test streaming transcription and synthesis
    - [ ] 13.5.3 System tests
      - Test voice-to-agent performance under load
      - Test latency requirements (<500ms p95)
      - Test with various audio qualities and environments
      - Test session metrics accuracy
      - Verify all voice integration requirements are met
    - [ ] 13.5.4 End-to-end tests
      - Test complete workflow: voice input → STT → agent → LLM → TTS → voice output
      - Test multi-turn voice conversations
      - Test error recovery and graceful degradation
      - Test data persistence from voice interactions
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 2.9, 2.10, 3.1, 3.2, 15.1_

- [~] 14. Implement security and authentication
  - [ ] 14.1 Set up OAuth 2.0 authentication (Python)
    - Implement OAuth 2.0 provider integration
    - Create JWT token generation and validation
    - Set token expiration to 1 hour
    - _Requirements: 18.2, 18.4_

  - [ ] 14.2 Implement RBAC (Python)
    - Define roles: technician, dispatcher, customer, admin
    - Define permissions: read-jobs, write-jobs, access-reports, manage-users
    - Implement permission checking middleware
    - _Requirements: 18.1_

  - [ ] 14.3 Implement identity verification (Python)
    - Use email verification for customer identity
    - Implement verification code generation and validation
    - Add optional phone verification via FreeSWITCH (if configured)
    - _Requirements: 18.3_

  - [ ] 14.4 Add encryption for sensitive data (Python)
    - Implement AES-256 encryption for PII at rest
    - Add TLS 1.3 for all network communication
    - Encrypt voice recordings and transcriptions
    - _Requirements: 11.3, 11.4_

  - [ ] 14.5 Implement PII redaction (Python)
    - Create PII detection patterns (SSN, credit cards)
    - Redact sensitive information from transcriptions
    - Anonymize data for analytics
    - _Requirements: 11.8, 18.9_

  - [ ]* 14.6 Write unit tests for security features
    - Test authentication and authorization
    - Test encryption and decryption
    - Test PII redaction
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.9_

  - [ ] 14.7 Comprehensive testing for Task 14 (Security and Authentication)
    - [ ] 14.7.1 Unit tests
      - Test OAuth 2.0 token generation and validation
      - Test JWT token expiration handling
      - Test RBAC role and permission definitions
      - Test permission checking logic
      - Test identity verification code generation
      - Test AES-256 encryption/decryption
      - Test PII detection and redaction patterns
    - [ ] 14.7.2 Integration tests
      - Test complete authentication flow: login → token → access
      - Test authorization across all API endpoints
      - Test identity verification workflow
      - Test encryption for data at rest and in transit
      - Test PII redaction in transcriptions and logs
    - [ ] 14.7.3 System tests
      - Test authentication performance under load
      - Test authorization with complex permission hierarchies
      - Test encryption performance impact
      - Test PII redaction accuracy with real data
      - Verify all security requirements are met
    - [ ] 14.7.4 End-to-end tests
      - Test complete secure workflow: authentication → authorization → encrypted data access → PII redaction
      - Test security across all user roles
      - Test attack scenarios (unauthorized access, token tampering)
    - _Requirements: 11.3, 11.4, 11.8, 18.1, 18.2, 18.3, 18.4, 18.9_


- [ ] 15. Implement observability and monitoring
  - [ ] 15.1 Set up Langfuse cloud integration
    - Create Langfuse cloud account (already done)
    - Configure API keys and authentication
    - Set up project and environment
    - _Requirements: 9.1, 9.4_

  - [ ] 15.2 Set up Datadog monitoring (GitHub Student)
    - Activate Datadog with GitHub Student Pack (free 2 years)
    - Configure APM and infrastructure monitoring
    - Set up log aggregation
    - _Requirements: 9.2, 9.5_

  - [ ] 15.3 Integrate Langfuse tracing (Python)
    - Add Langfuse SDK to FastAPI application
    - Instrument agent execution with traces
    - Track agent workflows and reasoning chains
    - _Requirements: 9.4_

  - [ ] 15.4 Integrate Datadog tracing (Python)
    - Add Datadog APM instrumentation
    - Emit traces for all agent operations
    - Track errors and exceptions
    - _Requirements: 9.5_

  - [ ] 15.5 Implement metrics collection (Python)
    - Track voice latency (p50, p95, p99)
    - Track agent response time
    - Track API call success rate and costs
    - Track first-time fix rate and job completion rate
    - _Requirements: 9.6, 9.7, 9.8_

  - [ ] 15.6 Set up Sentry error tracking
    - Activate Sentry (500k events/month free)
    - Configure error capture and reporting
    - Set up performance monitoring
    - _Requirements: 9.6, 9.7, 9.8_

  - [ ] 15.7 Implement alerting (Python)
    - Configure alerts for voice latency > 600ms (p95)
    - Configure alerts for API failure rate > 1%
    - Configure alerts for agent error rate > 5%
    - Configure budget alerts for cloud costs
    - _Requirements: 9.6, 9.7, 9.8_

  - [ ]* 15.8 Write unit tests for observability integration
    - Test Langfuse trace emission
    - Test Datadog trace emission
    - Test metrics collection
    - _Requirements: 9.1, 9.2, 9.4, 9.5_

  - [ ] 15.9 Comprehensive testing for Task 15 (Observability and Monitoring)
    - [ ] 15.9.1 Unit tests
      - Test Langfuse SDK initialization and configuration
      - Test Datadog APM initialization and configuration
      - Test Sentry initialization and configuration
      - Test trace creation and emission
      - Test metrics collection logic
      - Test alert configuration
    - [ ] 15.9.2 Integration tests
      - Test complete tracing flow: operation → trace → Langfuse/Datadog
      - Test metrics collection and aggregation
      - Test error capture and reporting to Sentry
      - Test alert triggering conditions
      - Test log aggregation in Datadog
    - [ ] 15.9.3 System tests
      - Test observability performance impact (<5% overhead)
      - Test trace completeness for all operations
      - Test metrics accuracy under load
      - Test alert delivery and timing
      - Verify all observability requirements are met
    - [ ] 15.9.4 End-to-end tests
      - Test complete observable workflow: operation → traces → metrics → alerts
      - Test distributed tracing across multiple services
      - Test error tracking and debugging workflow
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8_

- [ ] 16. Implement error handling and recovery
  - [ ] 16.1 Add voice pipeline error handling (Python)
    - Implement fallback to text input mode
    - Add automatic recovery after 30 seconds
    - Log errors with audio samples
    - Track Azure Speech API errors
    - _Requirements: 15.1_

  - [ ] 16.2 Add API error handling (Python)
    - Implement exponential backoff retry (1s, 2s, 4s, 8s, 16s)
    - Handle rate limiting for Gemini free tier
    - Fallback to Azure OpenAI when Gemini quota exceeded
    - Alert admin if all APIs fail
    - _Requirements: 15.2, 15.3_

  - [ ] 16.3 Add database error handling (Python)
    - Implement transaction retry (up to 3 times)
    - Store data in Redis cache temporarily
    - Verify data consistency after recovery
    - _Requirements: 15.8_

  - [ ] 16.4 Add parts not found handling (Python)
    - Search for compatible alternatives
    - Provide estimated lead time for ordering
    - Update job status to 'parts-pending'
    - _Requirements: 15.5_

  - [ ] 16.5 Add scheduling conflict handling (Python)
    - Propose alternative time slots
    - Re-run optimization with relaxed constraints
    - Escalate emergency jobs to on-call technician
    - _Requirements: 15.6_

  - [ ]* 16.6 Write unit tests for error handling
    - Test voice pipeline fallback
    - Test API retry logic
    - Test database transaction retry
    - Test parts not found handling
    - _Requirements: 15.1, 15.2, 15.3, 15.8_

  - [ ] 16.7 Comprehensive testing for Task 16 (Error Handling and Recovery)
    - [ ] 16.7.1 Unit tests
      - Test voice pipeline error detection and fallback
      - Test exponential backoff retry logic
      - Test API rate limiting handling
      - Test database transaction retry
      - Test parts not found handling
      - Test scheduling conflict resolution
    - [ ] 16.7.2 Integration tests
      - Test complete error recovery flows
      - Test fallback mechanisms across all components
      - Test error propagation and logging
      - Test graceful degradation scenarios
      - Test data consistency after recovery
    - [ ] 16.7.3 System tests
      - Test error handling under load
      - Test recovery time objectives
      - Test cascading failure prevention
      - Test error rate thresholds and alerts
      - Verify all error handling requirements are met
    - [ ] 16.7.4 End-to-end tests
      - Test complete failure and recovery scenarios
      - Test multi-component failure handling
      - Test user experience during errors and recovery
    - _Requirements: 15.1, 15.2, 15.3, 15.5, 15.6, 15.8_

- [ ] 17. Checkpoint - Verify complete system integration
  - Ensure all tests pass, ask the user if questions arise.


- [ ] 18. Implement comprehensive testing suite
  - [ ] 18.1 Create property-based test framework setup
    - Set up fast-check for TypeScript
    - Set up hypothesis for Python
    - Create custom generators for domain models
    - Configure to run 1000+ inputs per property
    - _Requirements: 16.8_

  - [ ]* 18.2 Write property test for data sovereignty
    - **Property 14: Data Sovereignty**
    - **Validates: Requirements 11.1, 11.6, 11.7**

  - [ ]* 18.3 Write property test for zero-cost operation
    - **Property 15: Zero-Cost Operation**
    - **Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5**

  - [ ]* 18.4 Write property test for first-time fix tracking
    - **Property 13: First-Time Fix Tracking**
    - **Validates: Requirements 6.7**

  - [ ]* 18.5 Write property test for performance under load
    - **Property 21: Performance Under Load**
    - **Validates: Requirements 14.2**

  - [ ]* 18.6 Write property test for MCP throughput
    - **Property 22: MCP Throughput**
    - **Validates: Requirements 14.9**

  - [ ]* 18.7 Write property test for documentation retrieval performance
    - **Property 23: Documentation Retrieval Performance**
    - **Validates: Requirements 20.5**

  - [ ]* 18.8 Write property test for GPU fallback behavior
    - **Property 24: GPU Fallback Behavior**
    - **Validates: Requirements 12.5**

  - [ ]* 18.9 Create integration test suite
    - Test voice-to-database flow end-to-end
    - Test multi-agent coordination (intake → diagnostic → fulfillment)
    - Test MCP server integration with real servers
    - Test WebRTC voice integration
    - Test notification delivery (email, push, Discord)
    - _Requirements: 16.9_

  - [ ]* 18.10 Create load testing suite
    - Test 100 concurrent voice sessions
    - Test 1000 MCP tool calls per minute
    - Test 500 jobs scheduled simultaneously
    - Verify p95 latency < 600ms under load
    - _Requirements: 14.2, 14.7, 14.8_

  - [ ] 18.11 Verify code coverage
    - Run coverage analysis for Python and TypeScript
    - Ensure 85%+ overall coverage
    - Ensure 100% critical path coverage
    - _Requirements: 16.1, 16.2_

- [ ] 19. Create deployment configurations
  - [ ] 19.1 Create Docker Compose for local development
    - Define services: PostgreSQL, Redis (lightweight - ~2-3GB RAM total)
    - Configure networking and volumes
    - Add health checks for all services
    - _Requirements: 17.1, 17.4_

  - [ ] 19.2 Create deployment configuration for Azure
    - Set up Azure App Service for FastAPI backend
    - Configure Azure Database for PostgreSQL
    - Set up Azure Cache for Redis
    - Configure environment variables and secrets
    - _Requirements: 17.2, 17.9_

  - [ ] 19.3 Create deployment configuration for DigitalOcean
    - Set up DigitalOcean App Platform deployment
    - Configure managed PostgreSQL database
    - Set up managed Redis cluster
    - Use $200 student credit
    - _Requirements: 12.8, 17.3, 17.7, 17.8_

  - [ ] 19.4 Create infrastructure-as-code templates
    - Create Terraform templates for Azure deployment
    - Create Terraform templates for DigitalOcean deployment
    - Include database and cache configuration
    - _Requirements: 17.3_

  - [ ] 19.5 Create deployment documentation
    - Document GitHub Student Pack activation steps
    - Document Azure and DigitalOcean deployment steps
    - Document environment variable configuration
    - Document monitoring and alerting setup
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 17.10_

  - [ ] 19.6 Comprehensive testing for Task 19 (Deployment Configurations)
    - [ ] 19.6.1 Unit tests
      - Test Docker Compose configuration validity
      - Test Terraform template syntax
      - Test environment variable loading
      - Test health check configurations
    - [ ] 19.6.2 Integration tests
      - Test Docker Compose service startup and connectivity
      - Test Terraform deployment to test environments
      - Test database and cache connectivity
      - Test service health checks
    - [ ] 19.6.3 System tests
      - Test complete local deployment with Docker Compose
      - Test Azure deployment with Terraform
      - Test DigitalOcean deployment with Terraform
      - Test production environment configuration
      - Verify all deployment requirements are met
    - [ ] 19.6.4 End-to-end tests
      - Test complete deployment workflow: infrastructure → services → verification
      - Test deployment rollback scenarios
      - Test zero-downtime deployment
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.8, 17.1, 17.2, 17.3, 17.4, 17.7, 17.8, 17.9, 17.10_


- [ ] 20. Implement documentation and knowledge management
  - [ ] 20.1 Set up simple documentation indexing (Python)
    - Create document ingestion pipeline
    - Index PDF, Markdown, HTML formats from local filesystem
    - Store document embeddings in PostgreSQL
    - _Requirements: 20.1, 20.2, 20.4, 20.7_

  - [ ] 20.2 Implement semantic search (Python)
    - Use Gemini embeddings API for document vectors
    - Implement vector search with PostgreSQL pgvector
    - Add full-text search fallback
    - Achieve sub-second retrieval
    - _Requirements: 20.3, 20.5, 20.8, 20.9_

  - [ ] 20.3 Add source citation and context (Python)
    - Extract and return source citations
    - Provide context snippets with search results
    - Link to original documents
    - _Requirements: 20.6_

  - [ ]* 20.4 Write unit tests for documentation management
    - Test document indexing
    - Test semantic search accuracy
    - Test retrieval performance
    - _Requirements: 20.2, 20.3, 20.5_

  - [ ] 20.5 Comprehensive testing for Task 20 (Documentation and Knowledge Management)
    - [ ] 20.5.1 Unit tests
      - Test document ingestion pipeline
      - Test PDF, Markdown, HTML parsing
      - Test embedding generation with Gemini
      - Test vector storage in PostgreSQL
      - Test semantic search logic
      - Test full-text search fallback
      - Test source citation extraction
    - [ ] 20.5.2 Integration tests
      - Test complete indexing flow: document → parse → embed → store
      - Test search flow: query → embed → search → retrieve → cite
      - Test retrieval performance with large document sets
      - Test search accuracy with various query types
    - [ ] 20.5.3 System tests
      - Test indexing performance with 1000+ documents
      - Test search latency (<1s requirement)
      - Test search accuracy and relevance
      - Test concurrent search requests
      - Verify all documentation requirements are met
    - [ ] 20.5.4 End-to-end tests
      - Test complete workflow: document upload → indexing → search → retrieval → citation
      - Test documentation integration with diagnostic agent
      - Test multi-document search and synthesis
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.9_

- [ ] 21. Implement API layer and external integrations
  - [ ] 21.1 Create FastAPI REST API (Python)
    - Define endpoints for leads, jobs, technicians, schedules
    - Add request validation with Pydantic
    - Implement authentication middleware
    - Add rate limiting
    - _Requirements: 7.9, 18.1, 18.2_

  - [ ] 21.2 Create WebSocket API for real-time updates (Python)
    - Implement WebSocket server for live notifications
    - Add technician status updates
    - Add job status updates
    - _Requirements: 4.9_

  - [ ] 21.3 Implement WebRTC and notification handlers (Python)
    - Create WebRTC signaling endpoints for voice sessions
    - Create endpoints for web push notifications
    - Create email notification handlers
    - Create Discord webhook handlers
    - Add WebSocket support for real-time communication
    - (Optional) Create FreeSWITCH event handlers for phone system
    - _Requirements: 4.1, 4.8_

  - [ ]* 21.4 Write unit tests for API layer
    - Test REST endpoints
    - Test WebSocket connections
    - Test WebRTC signaling
    - Test notification delivery (email, push, Discord)
    - Test authentication and authorization
    - _Requirements: 4.1, 7.9, 18.1, 18.2_

  - [ ] 21.5 Comprehensive testing for Task 21 (API Layer and External Integrations)
    - [ ] 21.5.1 Unit tests
      - Test FastAPI endpoint definitions
      - Test request validation with Pydantic
      - Test authentication middleware
      - Test rate limiting logic
      - Test WebSocket connection handling
      - Test WebRTC signaling logic
      - Test notification handlers (email, push, Discord)
    - [ ] 21.5.2 Integration tests
      - Test complete REST API flows
      - Test WebSocket real-time updates
      - Test WebRTC session establishment
      - Test notification delivery across all channels
      - Test API authentication and authorization
    - [ ] 21.5.3 System tests
      - Test API performance under load (1000+ requests/minute)
      - Test WebSocket scalability (100+ concurrent connections)
      - Test WebRTC session management
      - Test notification delivery reliability
      - Verify all API requirements are met
    - [ ] 21.5.4 End-to-end tests
      - Test complete API workflows: request → validation → processing → response
      - Test real-time notification delivery
      - Test WebRTC voice session via API
    - _Requirements: 4.1, 4.8, 4.9, 7.9, 18.1, 18.2_

- [ ] 22. Implement cloud cost optimization
  - [ ] 22.1 Implement API quota management (Python)
    - Track Gemini API usage (1500 requests/day free tier)
    - Implement intelligent caching to reduce API calls
    - Add fallback routing when quota exceeded
    - _Requirements: 12.5, 12.8_

  - [ ] 22.2 Implement cost tracking and budgeting (Python)
    - Track Azure OpenAI API costs
    - Track Azure Speech Services costs
    - Track Twilio usage costs
    - Set budget alerts and limits
    - _Requirements: 1.4, 12.5_

  - [ ] 22.3 Create cost optimization strategies
    - Implement response caching for repeated queries
    - Use cheaper models for simple tasks
    - Batch API requests when possible
    - Monitor and optimize token usage
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 22.4 Write cost optimization tests
    - Test caching effectiveness
    - Test quota management
    - Test fallback routing
    - _Requirements: 12.5, 12.6_

  - [ ] 22.5 Comprehensive testing for Task 22 (Cloud Cost Optimization)
    - [ ] 22.5.1 Unit tests
      - Test API quota tracking logic
      - Test caching mechanisms
      - Test fallback routing logic
      - Test cost calculation formulas
      - Test budget alert triggers
    - [ ] 22.5.2 Integration tests
      - Test complete cost tracking flow
      - Test quota exhaustion and fallback
      - Test caching effectiveness across requests
      - Test budget alert delivery
      - Test cost optimization strategies
    - [ ] 22.5.3 System tests
      - Test cost tracking accuracy with real API usage
      - Test caching hit rates
      - Test quota management under load
      - Test cost projections accuracy
      - Verify all cost optimization requirements are met
    - [ ] 22.5.4 End-to-end tests
      - Test complete cost-optimized workflow: request → cache check → API call → cost tracking
      - Test multi-provider fallback scenarios
      - Test budget limit enforcement
    - _Requirements: 1.4, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.8_


- [ ] 23. Implement economic tracking and reporting
  - [ ] 23.1 Create cost tracking system (Python)
    - Track Gemini API usage (free tier)
    - Track Azure OpenAI costs (student credits)
    - Track Azure Speech costs (student credits)
    - Track optional FreeSWITCH/SIP provider costs (if used)
    - Calculate monthly operational costs
    - _Requirements: 13.6, 13.7_

  - [ ] 23.2 Implement student credit monitoring (Python)
    - Track Azure student credit balance ($100)
    - Track DigitalOcean credit balance ($200)
    - Alert when credits running low
    - _Requirements: 13.8, 13.9, 13.10_

  - [ ] 23.3 Create economic reporting dashboard
    - Display monthly costs breakdown by service
    - Display remaining student credits
    - Display cost projections
    - Show cost per job/technician metrics
    - _Requirements: 13.7, 13.8_

  - [ ]* 23.4 Write unit tests for economic tracking
    - Test cost calculation accuracy
    - Test credit monitoring
    - _Requirements: 13.6, 13.7, 13.8_

  - [ ] 23.5 Comprehensive testing for Task 23 (Economic Tracking and Reporting)
    - [ ] 23.5.1 Unit tests
      - Test cost tracking for each service (Gemini, Azure OpenAI, Azure Speech, FreeSWITCH)
      - Test monthly cost calculation
      - Test student credit balance tracking
      - Test credit alert triggers
      - Test cost projection formulas
    - [ ] 23.5.2 Integration tests
      - Test complete cost tracking flow across all services
      - Test credit monitoring and alerts
      - Test dashboard data aggregation
      - Test cost per job/technician calculations
    - [ ] 23.5.3 System tests
      - Test cost tracking accuracy with real usage data
      - Test credit monitoring reliability
      - Test dashboard performance
      - Test cost projection accuracy
      - Verify all economic tracking requirements are met
    - [ ] 23.5.4 End-to-end tests
      - Test complete economic workflow: usage → cost tracking → reporting → alerts
      - Test multi-service cost aggregation
      - Test credit exhaustion scenarios
    - _Requirements: 13.6, 13.7, 13.8, 13.9, 13.10_

- [ ] 24. Implement data privacy and compliance
  - [ ] 24.1 Implement GDPR compliance features (Python)
    - Add data export functionality
    - Add data deletion functionality
    - Implement consent management
    - _Requirements: 11.9_

  - [ ] 24.2 Implement CCPA compliance features (Python)
    - Add data access request handling
    - Add opt-out mechanisms
    - Implement data sale prohibition
    - _Requirements: 11.9_

  - [ ] 24.3 Implement recording consent (Python)
    - Add call recording notification
    - Obtain explicit consent before recording
    - Store consent records with recordings
    - Provide opt-out mechanism
    - _Requirements: 11.6_

  - [ ] 24.4 Implement automatic data retention (Python)
    - Delete voice recordings after 90 days (configurable)
    - Retain audit logs for 7 years
    - Implement data archival for compliance
    - _Requirements: 11.9, 18.8_

  - [ ]* 24.5 Write unit tests for compliance features
    - Test GDPR data export and deletion
    - Test CCPA compliance
    - Test recording consent
    - Test data retention policies
    - _Requirements: 11.9, 18.8_

  - [ ] 24.6 Comprehensive testing for Task 24 (Data Privacy and Compliance)
    - [ ] 24.6.1 Unit tests
      - Test GDPR data export functionality
      - Test GDPR data deletion functionality
      - Test consent management logic
      - Test CCPA data access request handling
      - Test opt-out mechanisms
      - Test recording consent workflow
      - Test data retention policy enforcement
    - [ ] 24.6.2 Integration tests
      - Test complete GDPR compliance flow: request → export/delete → verify
      - Test complete CCPA compliance flow
      - Test recording consent integration with voice pipeline
      - Test automatic data retention and deletion
    - [ ] 24.6.3 System tests
      - Test compliance feature performance
      - Test data export completeness
      - Test data deletion thoroughness
      - Test retention policy accuracy
      - Verify all compliance requirements are met
    - [ ] 24.6.4 End-to-end tests
      - Test complete compliance workflows
      - Test user rights exercise scenarios
      - Test data lifecycle from creation to deletion
    - _Requirements: 11.6, 11.9, 18.8_

- [ ] 25. Final integration and end-to-end testing
  - [ ] 25.1 Create end-to-end test scenarios
    - Scenario 1: Customer calls for emergency service (intake → diagnostic → scheduling)
    - Scenario 2: Technician logs job completion via voice (fulfillment → carbon tracking)
    - Scenario 3: Equipment image analysis and parts sourcing (diagnostic → InvenTree → KiCost)
    - Scenario 4: Schedule optimization for 50 jobs across 10 technicians
    - _Requirements: 4.1, 5.1, 6.1, 6.8_

  - [ ]* 25.2 Run comprehensive integration tests
    - Test all end-to-end scenarios
    - Verify data consistency across all components
    - Test error recovery and fallback mechanisms
    - _Requirements: 16.9_

  - [ ]* 25.3 Run load and performance tests
    - Test 100 concurrent voice sessions
    - Test 10,000 jobs per day processing
    - Test 100,000 MCP tool calls per hour
    - Verify all performance targets met
    - _Requirements: 14.2, 14.7, 14.8, 14.9_

  - [ ] 25.4 Verify all correctness properties
    - Run all property-based tests
    - Verify all 24 correctness properties pass
    - Document any property violations
    - _Requirements: 16.3, 16.4, 16.5, 16.6, 16.7, 16.8_

  - [ ] 25.5 Create system validation report
    - Document test results and coverage
    - Document performance benchmarks
    - Document hardware compatibility
    - Document economic analysis
    - _Requirements: 16.1, 16.2, 14.1, 14.2, 13.7, 13.8_

- [ ] 26. Final checkpoint - Production readiness verification
  - Ensure all tests pass, ask the user if questions arise.


## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP development
- Each task references specific requirements for traceability
- Property-based tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end workflows
- Load tests ensure performance targets are met under realistic conditions
- Checkpoints ensure incremental validation at key milestones
- Implementation uses hybrid Python/TypeScript stack with cloud AI services
- All LLM inference uses cloud APIs: Gemini (free tier) → Azure OpenAI (student credits) → GitHub Copilot
- All voice processing uses Azure Speech Services (student credits)
- Observability uses Langfuse (cloud), Datadog (student - free 2 years), Sentry (free tier)
- Local infrastructure: PostgreSQL + Redis only (~2-3GB RAM)
- System optimized for Lenovo SlimPad 5 (AMD Ryzen 7000, AMD Radeon Graphics)
- GitHub Student Pack provides $300+ in credits (Azure $100, DigitalOcean $200)
- First year operational cost: ~$0 (using student credits + open-source tools)
- After credits: ~$25-45/month (Gemini free tier + minimal Azure costs + optional FreeSWITCH)

## Implementation Strategy

1. **Phase 1 (Tasks 1-5)**: Foundation - Infrastructure, cloud LLM integration, cloud voice pipeline, data models
2. **Phase 2 (Tasks 6-11)**: Core Agents - FastAPI orchestration, CrewAI/LangGraph/AutoGen agents, basic inventory
3. **Phase 3 (Tasks 12-17)**: Integration - Agent routing, voice-to-agent flow, security, observability, error handling
4. **Phase 4 (Tasks 18-26)**: Testing & Deployment - Comprehensive testing, cloud deployment configs, documentation, compliance, validation

## Success Criteria

- Voice latency < 500ms (p95 < 600ms under load) using Azure Speech + WebRTC
- Support 50+ concurrent voice sessions on cloud infrastructure
- Process 1,000+ jobs per day
- Gemini API free tier: 1500 requests/day (sufficient for 50-100 jobs/day)
- Azure student credits last 6-12 months depending on usage
- Total first-year cost: $0 (using student credits + open-source)
- After credits: $25-45/month operational cost
- System runs on lightweight hardware (Lenovo SlimPad 5, 2-3GB RAM for local services)
- Complete data sovereignty for customer data (stored in local PostgreSQL)
- API calls to Gemini/Azure for AI processing only (no customer PII sent)

## GitHub Student Pack Services

**Free Services Used:**
- Azure for Students: $100 credit (Azure OpenAI, Azure Speech, Azure Database)
- DigitalOcean: $200 credit (production hosting)
- Datadog: Free for 2 years (monitoring)
- Sentry: 500k events/month free (error tracking)
- GitHub Copilot: Free (development assistance)
- Langfuse: Cloud free tier (LLM observability)

**Open-Source Communication Stack:**
- WebRTC + Jitsi: Free (web-based voice)
- FreeSWITCH: Free software, optional SIP provider $2-5/month
- Web Push Notifications: Free
- Email Notifications: Free
- Discord Webhooks: Free

**Additional Free Tier:**
- Google Gemini API: 1500 requests/day free
- PostgreSQL: Local installation (free)
- Redis: Local installation (free)

