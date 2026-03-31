# Requirements Document: TradeSense Agentic Field Service Management System

## Introduction

TradeSense is an open-source, voice-first agentic operating system for field service management that achieves zero operational costs through local LLM inference, self-hosted infrastructure, and open-source tooling. The system addresses the 2026 field service crisis by reducing cognitive load on technicians through autonomous intake, diagnostics, parts sourcing, scheduling, and sustainability compliance. By eliminating $11,400-$46,800 in annual SaaS costs while maintaining production-grade performance, TradeSense enables field service businesses of all sizes to achieve complete data sovereignty and operational independence.

## Glossary

- **System**: The TradeSense agentic field service management platform
- **Voice_Pipeline**: Local speech-to-speech processing subsystem using Faster-Whisper and Piper TTS
- **ZenML_Orchestrator**: Production-grade pipeline orchestration framework
- **Intake_Agent**: CrewAI-based agent handling lead capture and triage
- **Diagnostic_Agent**: LangGraph + AutoGen agent performing troubleshooting and parts sourcing
- **Fulfillment_Agent**: CrewAI-based agent managing job completion and scheduling
- **Local_LLM**: Locally-hosted language model (Llama 4, DeepSeek-V3, Qwen 3, Gemma 3, Command R+)
- **MCP_Server**: Model Context Protocol server providing tool integration
- **InvenTree**: Open-source Python/Django inventory ERP system
- **Part-DB**: Open-source electronic component database
- **KiCost**: Zero-cost distributor scraping tool
- **Kabaun**: Open-source carbon impact analysis library
- **Langfuse**: Self-hosted agent tracing and observability platform
- **Technician**: Field service professional using the system
- **Customer**: End user requesting service
- **Lead**: Initial service request requiring triage
- **Job**: Scheduled service appointment with assigned technician
- **Distributor**: Parts supplier (Digi-Key, Mouser, Arrow, Newark, TME)

## Requirements

### Requirement 1: Zero-Cost Local LLM Inference

**User Story:** As a field service business owner, I want to use local LLM inference instead of cloud APIs, so that I can eliminate token costs and maintain data sovereignty.

#### Acceptance Criteria

1. THE System SHALL use only locally-hosted LLMs for all natural language processing tasks
2. WHEN processing any user input, THE System SHALL route requests to Ollama, vLLM, or LocalAI
3. THE System SHALL support Llama 4, DeepSeek-V3, Qwen 3, Gemma 3, and Command R+ models
4. WHEN hardware resources are limited, THE System SHALL use quantized models (int8, int4)
5. THE System SHALL NOT make API calls to OpenAI, Anthropic, or other cloud LLM providers
6. WHEN selecting a model, THE System SHALL choose based on task complexity and latency requirements
7. THE System SHALL use Llama 4 Scout for latency-critical tasks requiring <100ms inference
8. THE System SHALL use DeepSeek-V3 for complex reasoning tasks requiring high accuracy

### Requirement 2: Local Voice Processing Pipeline

**User Story:** As a technician, I want hands-free voice interaction with sub-500ms latency, so that I can log jobs and request information while working.

#### Acceptance Criteria

1. THE Voice_Pipeline SHALL process all audio locally without cloud API calls
2. WHEN audio input is received, THE Voice_Pipeline SHALL use Silero VAD for speech detection
3. WHEN speech is detected, THE Voice_Pipeline SHALL transcribe using Faster-Whisper
4. THE Voice_Pipeline SHALL achieve first-token latency of less than 500 milliseconds
5. WHEN generating speech output, THE Voice_Pipeline SHALL use Piper TTS
6. THE Voice_Pipeline SHALL synthesize speech responses in less than 100 milliseconds
7. WHEN background noise exceeds 60dB, THE Voice_Pipeline SHALL adapt VAD threshold
8. THE Voice_Pipeline SHALL support both CPU and GPU acceleration
9. WHEN GPU is unavailable, THE Voice_Pipeline SHALL use int8 quantization for CPU inference
10. THE Voice_Pipeline SHALL maintain 95% or greater turn-taking accuracy

### Requirement 3: ZenML Pipeline Orchestration

**User Story:** As a system administrator, I want production-grade pipeline orchestration with governance, so that I can manage workflows and maintain audit trails.

#### Acceptance Criteria

1. THE ZenML_Orchestrator SHALL coordinate all agent execution through declarative pipelines
2. WHEN a voice interaction begins, THE ZenML_Orchestrator SHALL execute the intake pipeline
3. THE ZenML_Orchestrator SHALL manage secrets for WebRTC, Jitsi, email, and database credentials
4. WHEN a pipeline step fails, THE ZenML_Orchestrator SHALL retry according to configured policy
5. THE ZenML_Orchestrator SHALL track all pipeline artifacts and lineage
6. THE ZenML_Orchestrator SHALL provide a dashboard for monitoring pipeline execution
7. WHEN caching is enabled, THE ZenML_Orchestrator SHALL reuse artifacts from previous runs
8. THE ZenML_Orchestrator SHALL emit telemetry to Langfuse and Arize Phoenix

### Requirement 4: CrewAI Intake Agent

**User Story:** As a customer, I want 24/7 automated lead capture via phone or SMS, so that I can request service at any time.

#### Acceptance Criteria

1. WHEN a customer calls the service number, THE Intake_Agent SHALL answer within 3 rings
2. THE Intake_Agent SHALL extract structured information using PydanticAI and Local_LLM
3. WHEN issue description is provided, THE Intake_Agent SHALL classify service type and urgency
4. THE Intake_Agent SHALL classify urgency as emergency, urgent, or routine within 60 seconds
5. WHEN urgency is classified as emergency, THE Intake_Agent SHALL prioritize scheduling
6. THE Intake_Agent SHALL query InvenTree API for initial parts availability
7. WHEN parts are unavailable, THE Intake_Agent SHALL query Part-DB for alternatives
8. THE Intake_Agent SHALL create lead records in PostgreSQL database
9. THE Intake_Agent SHALL notify assigned technicians via SMS or push notification
10. THE Intake_Agent SHALL use CrewAI role-based collaboration for complex intake scenarios

### Requirement 5: LangGraph + AutoGen Diagnostic Agent

**User Story:** As a technician, I want intelligent diagnostic assistance with equipment image recognition, so that I can quickly identify issues and required parts.

#### Acceptance Criteria

1. WHEN an issue description is provided, THE Diagnostic_Agent SHALL analyze using LangGraph reasoning chains
2. THE Diagnostic_Agent SHALL use DeepSeek-V3 for complex diagnostic reasoning
3. WHEN an equipment image is uploaded, THE Diagnostic_Agent SHALL parse labels using Qwen 3 Omni or Gemma 3
4. THE Diagnostic_Agent SHALL extract manufacturer, model number, and serial number from equipment images
5. WHEN equipment information is extracted, THE Diagnostic_Agent SHALL query InvenTree for compatible parts
6. THE Diagnostic_Agent SHALL use KiCost to compare prices across Digi-Key, Mouser, Arrow, Newark, and TME
7. WHEN primary parts are unavailable, THE Diagnostic_Agent SHALL suggest compatible alternatives
8. THE Diagnostic_Agent SHALL generate step-by-step repair guides using Llama 4
9. WHEN collaborative troubleshooting is needed, THE Diagnostic_Agent SHALL use AutoGen conversational agents
10. THE Diagnostic_Agent SHALL access technical documentation via FileSystem MCP and LlamaIndex RAG
11. THE Diagnostic_Agent SHALL update diagnosis confidence based on technician feedback

### Requirement 6: CrewAI Fulfillment Agent

**User Story:** As a dispatcher, I want automated schedule optimization and route planning, so that I can maximize technician utilization and minimize travel time.

#### Acceptance Criteria

1. WHEN jobs are ready for scheduling, THE Fulfillment_Agent SHALL optimize assignments and routes
2. THE Fulfillment_Agent SHALL ensure all assigned technicians have required skills for their jobs
3. THE Fulfillment_Agent SHALL achieve 75% or greater technician utilization rate
4. THE Fulfillment_Agent SHALL minimize total travel time across all routes
5. WHEN emergency jobs are added, THE Fulfillment_Agent SHALL re-optimize schedule
6. THE Fulfillment_Agent SHALL prioritize emergency jobs over routine jobs
7. WHEN a job is completed, THE Fulfillment_Agent SHALL log details via voice input
8. THE Fulfillment_Agent SHALL calculate carbon footprint using Kabaun and open emission datasets
9. THE Fulfillment_Agent SHALL track AI infrastructure emissions using CodeCarbon
10. THE Fulfillment_Agent SHALL generate sustainability compliance reports
11. THE Fulfillment_Agent SHALL use CrewAI role-based agents for complex fulfillment workflows

### Requirement 7: Open-Source Inventory Management

**User Story:** As an inventory manager, I want integrated inventory tracking with automated parts sourcing, so that I can maintain optimal stock levels without manual data entry.

#### Acceptance Criteria

1. THE System SHALL integrate with InvenTree for inventory ERP functionality
2. WHEN parts are used on a job, THE System SHALL update InvenTree inventory levels
3. THE System SHALL integrate with Part-DB for electronic component specifications
4. WHEN searching for parts, THE System SHALL query both InvenTree and Part-DB
5. THE System SHALL use KiCost for automated distributor price comparison
6. WHEN generating a BOM, THE System SHALL execute KiCost to find best pricing
7. THE System SHALL support Digi-Key, Mouser, Arrow, Newark, and TME distributors
8. WHEN inventory falls below reorder point, THE System SHALL generate purchase recommendations
9. THE System SHALL provide REST API access to inventory data for MCP integration

### Requirement 8: Open-Source Carbon Tracking

**User Story:** As a sustainability officer, I want automated carbon footprint calculation using open datasets, so that I can ensure regulatory compliance without subscription fees.

#### Acceptance Criteria

1. THE System SHALL calculate carbon emissions using Kabaun library
2. WHEN calculating travel emissions, THE System SHALL use eGRID electricity generation data
3. WHEN calculating logistics emissions, THE System SHALL use EPA GHG Emission Factors Hub
4. WHEN calculating international trade emissions, THE System SHALL use ADEME datasets
5. THE System SHALL track AI infrastructure emissions using CodeCarbon
6. WHEN a job is completed, THE System SHALL calculate total carbon footprint
7. THE System SHALL break down emissions by category: travel, parts, disposal, AI infrastructure
8. THE System SHALL determine compliance status against configured regulations
9. WHEN emissions exceed thresholds, THE System SHALL provide reduction recommendations
10. THE System SHALL NOT use proprietary carbon tracking APIs

### Requirement 9: Self-Hosted Observability

**User Story:** As a DevOps engineer, I want self-hosted observability and monitoring, so that I can debug issues and track performance without SaaS fees.

#### Acceptance Criteria

1. THE System SHALL use Langfuse for agent graph visualization and DAG tracing
2. THE System SHALL use Arize Phoenix for OpenTelemetry-based debugging
3. THE System SHALL use ZenML Dashboard for pipeline monitoring
4. WHEN an agent executes, THE System SHALL emit traces to Langfuse
5. WHEN errors occur, THE System SHALL log detailed context to Arize Phoenix
6. THE System SHALL track voice latency (p50, p95, p99) metrics
7. THE System SHALL track agent response time metrics
8. THE System SHALL track MCP tool call success rate
9. THE System SHALL track first-time fix rate and job completion rate
10. THE System SHALL NOT send telemetry to external SaaS platforms

### Requirement 10: MCP Integration Layer

**User Story:** As a system integrator, I want universal tool integration via Model Context Protocol, so that I can extend functionality without custom code.

#### Acceptance Criteria

1. THE System SHALL support FileSystem MCP for local file access
2. THE System SHALL support Database MCP for PostgreSQL and SQLite integration
3. THE System SHALL support KiCad MCP for PCB design through natural language
4. THE System SHALL support Puppeteer MCP for browser automation
5. THE System SHALL support Sequential Thinking MCP for dynamic problem-solving
6. WHEN connecting to MCP servers, THE System SHALL use stdio or SSE transport
7. WHEN executing MCP tools, THE System SHALL validate parameters against input schema
8. WHEN receiving MCP results, THE System SHALL validate against output schema
9. THE System SHALL handle MCP connection failures with exponential backoff retry
10. THE System SHALL cache idempotent MCP tool results for 5 minutes

### Requirement 11: Data Sovereignty and Privacy

**User Story:** As a business owner, I want complete data sovereignty with no cloud dependencies, so that I can protect customer information and maintain regulatory compliance.

#### Acceptance Criteria

1. THE System SHALL process all voice data locally without cloud API calls
2. THE System SHALL store all customer data in self-hosted PostgreSQL database
3. THE System SHALL encrypt sensitive data at rest using AES-256
4. THE System SHALL encrypt all network communication using TLS 1.3
5. THE System SHALL use WebRTC for web-based voice and Jitsi for video consultations (optional: FreeSWITCH for traditional phone)
6. THE System SHALL NOT send conversation transcripts to cloud services
7. THE System SHALL NOT send equipment images to cloud vision APIs
8. WHEN processing PII, THE System SHALL anonymize data for analytics
9. THE System SHALL support GDPR and CCPA data deletion requests
10. THE System SHALL maintain audit logs for all data access for 7 years

### Requirement 12: Scalable Hardware Requirements

**User Story:** As a business owner, I want flexible hardware requirements that scale from solo operation to 50-person shop, so that I can start small and grow.

#### Acceptance Criteria

1. WHERE deployment is solo technician, THE System SHALL run on laptop with 32GB RAM
2. WHERE deployment is small workshop (2-10 techs), THE System SHALL run on 8-core CPU with RTX 4060 Ti 16GB
3. WHERE deployment is medium shop (10-25 techs), THE System SHALL run on 16-core CPU with RTX 4090 24GB
4. WHERE deployment is precision manufacturing (25-50 techs), THE System SHALL run on server with 80GB+ VRAM GPU
5. WHEN GPU is unavailable, THE System SHALL fall back to CPU inference with quantization
6. THE System SHALL support WSL2 on Windows for solo technician deployment
7. THE System SHALL support Docker Compose for single-server deployment
8. THE System SHALL support Kubernetes for distributed production deployment
9. THE System SHALL support LiveKit Agents for distributed voice processing

### Requirement 13: Economic Performance

**User Story:** As a CFO, I want to eliminate recurring SaaS costs while maintaining performance, so that I can achieve ROI within 3 months.

#### Acceptance Criteria

1. THE System SHALL incur zero costs for LLM token usage
2. THE System SHALL incur zero costs for orchestration services
3. THE System SHALL incur zero costs for observability platforms
4. THE System SHALL incur zero costs for inventory ERP software
5. THE System SHALL incur zero costs for carbon tracking services
6. WHEN calculating monthly costs, THE System SHALL only include optional FreeSWITCH ($2-5/month) and electricity
7. THE System SHALL achieve total monthly costs of $20-$105 (vs $950-$3,900 with SaaS)
8. THE System SHALL achieve annual savings of $11,400-$46,800 compared to proprietary stack
9. WHERE deployment is solo/small, THE System SHALL achieve ROI within 1-3 months
10. WHERE deployment is medium, THE System SHALL achieve ROI within 2-4 months

### Requirement 14: Performance Targets

**User Story:** As a technician, I want responsive system performance that doesn't slow me down, so that I can maintain productivity in the field.

#### Acceptance Criteria

1. THE Voice_Pipeline SHALL achieve end-to-end latency of less than 500 milliseconds
2. THE Voice_Pipeline SHALL achieve p95 latency of less than 600 milliseconds under load
3. THE Diagnostic_Agent SHALL generate diagnosis within 5 seconds for simple issues
4. THE Diagnostic_Agent SHALL generate diagnosis within 30 seconds for complex issues
5. THE Fulfillment_Agent SHALL optimize schedule for 50 jobs within 5 seconds
6. WHEN using vLLM, THE System SHALL achieve 19x faster inference than Ollama
7. THE System SHALL support 100 concurrent voice sessions on medium shop hardware
8. THE System SHALL process 10,000 jobs per day on medium shop hardware
9. THE System SHALL handle 100,000 MCP tool calls per hour
10. THE System SHALL maintain 99.5% MCP tool call success rate

### Requirement 15: Reliability and Error Handling

**User Story:** As a system administrator, I want robust error handling and recovery, so that the system remains operational during failures.

#### Acceptance Criteria

1. WHEN Voice_Pipeline fails, THE System SHALL fall back to text input mode
2. WHEN MCP server becomes unresponsive, THE System SHALL return cached results if available
3. WHEN MCP connection drops, THE System SHALL retry with exponential backoff
4. WHEN intent classification confidence is below 0.6, THE System SHALL ask clarifying questions
5. WHEN required parts are not found, THE System SHALL search for compatible alternatives
6. WHEN no technician is available, THE System SHALL propose alternative time slots
7. WHEN carbon calculation fails, THE System SHALL use cached emission factors
8. WHEN database transaction fails, THE System SHALL retry up to 3 times
9. WHEN observability service is unavailable, THE System SHALL buffer telemetry locally
10. THE System SHALL continue normal operation when observability fails (non-blocking)

### Requirement 16: Testing and Quality Assurance

**User Story:** As a QA engineer, I want comprehensive testing coverage including property-based tests, so that I can ensure system correctness.

#### Acceptance Criteria

1. THE System SHALL achieve 85% or greater code coverage
2. THE System SHALL achieve 100% critical path coverage
3. THE System SHALL include property-based tests for voice latency
4. THE System SHALL include property-based tests for agent routing consistency
5. THE System SHALL include property-based tests for schedule optimization validity
6. THE System SHALL include property-based tests for MCP tool call idempotency
7. THE System SHALL include property-based tests for carbon calculation monotonicity
8. THE System SHALL run property tests with 1000 or more generated inputs per property
9. THE System SHALL include integration tests for voice-to-database flow
10. THE System SHALL include load tests for 100 concurrent voice sessions

### Requirement 17: Deployment and Operations

**User Story:** As a DevOps engineer, I want containerized deployment with infrastructure-as-code, so that I can deploy and manage the system reliably.

#### Acceptance Criteria

1. THE System SHALL provide Docker Compose configuration for single-server deployment
2. THE System SHALL provide Kubernetes manifests for distributed deployment
3. THE System SHALL provide Terraform or Pulumi templates for infrastructure provisioning
4. WHEN deploying, THE System SHALL automatically configure database schemas
5. WHEN deploying, THE System SHALL automatically load LLM models
6. THE System SHALL provide health check endpoints for all services
7. THE System SHALL provide readiness probes for Kubernetes deployment
8. THE System SHALL support rolling updates without downtime
9. THE System SHALL provide backup and restore procedures for PostgreSQL
10. THE System SHALL provide monitoring dashboards for Grafana

### Requirement 18: Security and Compliance

**User Story:** As a security officer, I want comprehensive security controls and audit trails, so that I can protect sensitive data and maintain compliance.

#### Acceptance Criteria

1. THE System SHALL implement role-based access control (RBAC)
2. THE System SHALL support OAuth 2.0 authentication for technicians
3. THE System SHALL verify customer identity via phone number verification
4. THE System SHALL use JWT tokens with 1-hour expiration for API access
5. THE System SHALL use mutual TLS for remote MCP server connections
6. THE System SHALL log all data access and modifications to audit trail
7. THE System SHALL sign audit logs to prevent tampering
8. THE System SHALL retain audit logs for 7 years
9. THE System SHALL redact sensitive information (SSN, credit cards) from transcriptions
10. THE System SHALL support voice biometrics for technician verification (optional)

### Requirement 19: Multimodal Capabilities

**User Story:** As a technician, I want to send equipment photos for automatic identification, so that I can quickly find compatible parts without manual lookup.

#### Acceptance Criteria

1. WHEN an equipment image is uploaded, THE Diagnostic_Agent SHALL parse using local vision model
2. THE Diagnostic_Agent SHALL use Qwen 3 Omni or Gemma 3 for image understanding
3. THE Diagnostic_Agent SHALL extract manufacturer name from equipment labels
4. THE Diagnostic_Agent SHALL extract model number from equipment labels
5. THE Diagnostic_Agent SHALL extract serial number from equipment labels
6. THE Diagnostic_Agent SHALL achieve 98% or greater OCR accuracy on equipment labels
7. WHEN image quality is poor, THE Diagnostic_Agent SHALL request clearer image
8. THE Diagnostic_Agent SHALL support JPEG, PNG, and HEIC image formats
9. THE Diagnostic_Agent SHALL process images locally without cloud vision APIs
10. THE Diagnostic_Agent SHALL use extracted information to query InvenTree and Part-DB

### Requirement 20: Documentation and Knowledge Management

**User Story:** As a technician, I want instant access to technical manuals and repair guides, so that I can reference documentation hands-free while working.

#### Acceptance Criteria

1. THE System SHALL integrate FileSystem MCP for local manual access
2. THE System SHALL use LlamaIndex for event-driven RAG over technical documentation
3. WHEN a technician asks a question, THE System SHALL search relevant manuals
4. THE System SHALL support PDF, Markdown, and HTML documentation formats
5. THE System SHALL index documentation for fast retrieval (sub-second)
6. THE System SHALL provide source citations for all retrieved information
7. THE System SHALL update documentation index when new files are added
8. THE System SHALL support full-text search across all documentation
9. THE System SHALL use local LLM for semantic search and summarization
10. THE System SHALL cache frequently accessed documentation sections

