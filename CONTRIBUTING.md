# Contributing to TradeSense

Thank you for your interest in contributing to TradeSense! This document provides guidelines and instructions for development.

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 20+
- Git
- Make (optional, for convenience commands)

### Initial Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd tradesense
```

2. Run setup:
```bash
make setup
# or manually:
cp .env.example .env
cd backend && pip install -r requirements.txt
cd ../frontend && npm install
```

3. Edit `.env` with your configuration

4. Start development environment:
```bash
make dev-up
# or manually:
docker-compose -f docker/compose/docker-compose.dev.yml up -d
```

## Project Structure

```
tradesense/
├── backend/              # Python backend
│   ├── agents/          # Agent implementations
│   ├── api/             # FastAPI REST API
│   ├── core/            # Core business logic
│   ├── db/              # Database models
│   ├── llm/             # LLM client interfaces
│   ├── mcp/             # MCP integration
│   ├── voice/           # Voice processing
│   └── zenml/           # ZenML pipelines
├── frontend/            # TypeScript frontend
│   ├── mcp-client/      # MCP client SDK
│   └── voice-pipeline/  # Voice orchestration
├── docker/              # Docker configurations
├── tests/               # Test suites
└── docs/                # Documentation
```

## Development Workflow

### Running Tests

```bash
# All tests
make test

# Unit tests only
cd backend && pytest tests/unit/

# Integration tests
cd backend && pytest tests/integration/

# Property-based tests
cd backend && pytest tests/property/
```

### Code Quality

```bash
# Lint code
make lint

# Format code
make format

# Type checking
cd backend && mypy .
cd frontend && npm run type-check
```

### Running Services

```bash
# Start all infrastructure
make dev-up

# Start backend API
cd backend && uvicorn api.main:app --reload

# Start voice services
cd backend && python voice/server.py

# Start frontend (if applicable)
cd frontend && npm run dev
```

## Coding Standards

### Python

- Follow PEP 8 style guide
- Use type hints for all functions
- Maximum line length: 100 characters
- Use Black for formatting
- Use isort for import sorting
- Write docstrings for all public functions

Example:
```python
def calculate_carbon_footprint(job: Job) -> CarbonFootprint:
    """
    Calculate carbon footprint for a completed job.

    Args:
        job: Completed job with parts and travel data

    Returns:
        Carbon footprint with emissions breakdown

    Raises:
        ValueError: If job is not completed
    """
    pass
```

### TypeScript

- Follow TypeScript best practices
- Use strict mode
- Maximum line length: 100 characters
- Use Prettier for formatting
- Write JSDoc comments for exported functions

Example:
```typescript
/**
 * Execute MCP tool call
 * @param serverId - MCP server identifier
 * @param toolName - Tool name to execute
 * @param params - Tool parameters
 * @returns Tool execution result
 */
export async function executeTool(
  serverId: string,
  toolName: string,
  params: Record<string, any>
): Promise<any> {
  // Implementation
}
```

## Testing Guidelines

### Unit Tests

- Test individual functions in isolation
- Mock external dependencies
- Aim for 85%+ code coverage
- Use descriptive test names

```python
def test_calculate_carbon_footprint_with_valid_job():
    """Test carbon calculation with valid completed job."""
    job = create_test_job()
    result = calculate_carbon_footprint(job)
    assert result.total_emissions > 0
    assert len(result.breakdown) > 0
```

### Property-Based Tests

- Use Hypothesis (Python) or fast-check (TypeScript)
- Test universal properties
- Run with 1000+ generated inputs

```python
from hypothesis import given, strategies as st

@given(st.floats(min_value=0, max_value=1000))
def test_carbon_calculation_monotonicity(additional_distance: float):
    """Test that more travel increases carbon footprint."""
    base_job = create_test_job(distance=10)
    extended_job = create_test_job(distance=10 + additional_distance)
    
    base_carbon = calculate_carbon_footprint(base_job)
    extended_carbon = calculate_carbon_footprint(extended_job)
    
    assert extended_carbon.total_emissions >= base_carbon.total_emissions
```

### Integration Tests

- Test end-to-end workflows
- Use real database (test instance)
- Clean up after each test

```python
@pytest.mark.integration
async def test_voice_to_database_flow(test_db, test_redis):
    """Test complete voice interaction workflow."""
    # Setup
    session = await create_voice_session()
    
    # Execute
    result = await process_voice_input(session, "Log job completion")
    
    # Verify
    assert result.success
    job = await test_db.query(Job).filter_by(id=result.job_id).first()
    assert job is not None
    assert job.status == JobStatus.COMPLETED
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Example:
```
feat(voice): add Piper TTS integration

Implement local text-to-speech using Piper TTS with sub-100ms latency.
Includes voice model preloading and quality configuration.

Closes #123
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes
3. Write/update tests
4. Ensure all tests pass
5. Update documentation
6. Submit pull request
7. Address review feedback

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted and linted
- [ ] All tests passing
- [ ] No merge conflicts
- [ ] Descriptive PR title and description

## Questions or Issues?

- Open a GitHub issue for bugs or feature requests
- Join our community discussions
- Check existing documentation

## License

By contributing, you agree that your contributions will be licensed under the project's license.
