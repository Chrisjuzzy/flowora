
# Flowora - Million Dollar Features

This document describes the six million-dollar features implemented in the Flowora backend.

## Features Overview

### 1. AI Talent Marketplace Hub
**Endpoint:** `/talent/match` (POST)

Matches SMBs with virtual agents based on business needs.

**Input:**
- Industry sector
- Role type required
- Skills needed
- Budget range
- Experience level
- Work hours preference
- Timezone
- Special requirements

**Output:**
- Ranked list of matching agents
- Match scores (0-1)
- Match reasons
- Agent profiles with ratings and experience

**Implementation:**
- Uses Ollama (qwen2.5-coder:7b) for intelligent matching
- Combines rule-based scoring with AI analysis
- Supports filtering by role type and rating
- Includes retry logic with tenacity for reliability

**Tests:** `tests/test_talent_hub.py`

---

### 2. Cyber Compliance Sentinel
**Endpoint:** `/compliance/scan` (POST)

Scans systems for vulnerabilities and provides fix recommendations.

**Input:**
- System type (web, api, mobile, desktop)
- Technology stack
- Target (URL, IP, or file path)
- Scan type (quick, full, custom)
- Custom scan options

**Output:**
- Vulnerability report with severity levels
- Fix recommendations with code examples
- Summary statistics
- Scan duration

**Implementation:**
- Uses Nmap for network scanning
- Checks for common vulnerabilities
- Uses Ollama for intelligent analysis
- Supports custom scan configurations
- Includes timeout handling

**Tests:** `tests/test_compliance.py`

---

### 3. AI Code Auditor Pro
**Endpoint:** `/code/audit` (POST)

Audits code for security, performance, and best practices.

**Input:**
- Source type (repo URL or code snippet)
- Content (repository URL or code)
- Programming language
- Audit type (quick, full, security)

**Output:**
- Detected issues with severity
- Fix recommendations
- Code before/after examples
- Summary statistics

**Implementation:**
- Uses GitPython for repository cloning
- Uses Bandit for Python security scanning
- Supports multiple programming languages
- Uses Ollama for intelligent analysis
- Includes cleanup of temporary files

**Tests:** `tests/test_code_auditor.py`

---

### 4. Dev Wellness Guardian
**Endpoint:** `/wellness/analyze` (POST)

Monitors developer activity and provides wellness recommendations.

**Input:**
- Git activity data
- Calendar/meeting data
- Work hours data
- Self-reported metrics

**Output:**
- Detected wellness issues
- Recommendations for improvement
- Actionable steps
- Wellness score

**Implementation:**
- Analyzes Git commit patterns
- Detects overwork and burnout indicators
- Uses Ollama for personalized recommendations
- Tracks weekend and late-night work
- Provides actionable wellness plans

**Tests:** `tests/test_wellness.py`

---

### 5. AI Infrastructure Optimizer
**Endpoint:** `/infra/optimize` (POST)

Optimizes infrastructure for AI workloads.

**Input:**
- Model name and type
- Number of parameters
- Framework (PyTorch, TensorFlow)
- Quantization level
- Current hardware configuration
- Performance requirements

**Output:**
- Infrastructure assessment
- Optimization suggestions
- Bottleneck identification
- Implementation steps

**Implementation:**
- Analyzes CPU, memory, and GPU resources
- Detects infrastructure bottlenecks
- Uses Ollama for optimization suggestions
- Supports multiple model types
- Provides hardware recommendations

**Tests:** `tests/test_infra_optimizer.py`

---

### 6. Ethical AI Guardian
**Endpoint:** `/ethics/audit` (POST)

Audits AI configurations for ethical concerns.

**Input:**
- System name and type
- Purpose and target users
- Data sources
- Model details
- Existing safeguards

**Output:**
- Ethical concerns by category
- Recommendations for improvement
- Risk assessment
- Implementation steps

**Implementation:**
- Checks for bias, privacy, transparency issues
- Evaluates accountability and safety
- Uses Ollama for ethical analysis
- Provides actionable recommendations
- Supports multiple AI system types

**Tests:** `tests/test_ethics_guardian.py`

---

## Running the Application

### Prerequisites
- Python 3.8+
- Ollama installed and running (with qwen2.5-coder:7b model)
- Nmap installed (for compliance scanning)
- Bandit installed (for code auditing)
- Git installed

### Installation
```bash
cd apps/backend
pip install -r requirements.txt
```

### Running Tests
```bash
# Run all tests
pytest tests/

# Run specific feature tests
pytest tests/test_talent_hub.py
pytest tests/test_compliance.py
pytest tests/test_code_auditor.py
pytest tests/test_wellness.py
pytest tests/test_infra_optimizer.py
pytest tests/test_ethics_guardian.py

# Run with coverage
pytest tests/ --cov=.

# Run with verbose output
pytest tests/ -v
```

### Starting the Server
```bash
# Development server
uvicorn main:app --reload

# Production server
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Using Docker
```bash
# Build image
docker build -t ai-agent-builder .

# Run container
docker run -p 8000:8000 ai-agent-builder
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Configuration is managed through environment variables in `.env`:

```env
# Application
APP_NAME=Flowora
DEBUG=False

# Database
DATABASE_URL=sqlite:///./app.db

# Security
SECRET_KEY=your-secret-key-here

# AI Providers
DEFAULT_AI_PROVIDER=local
OLLAMA_BASE_URL=http://localhost:11434

# Rate Limiting
RATE_LIMIT_API_PER_MINUTE=30
```

## Best Practices Implemented

1. **Security**
   - No hardcoded keys
   - Input validation with Pydantic
   - CORS protection
   - Rate limiting

2. **Reliability**
   - Retry logic with tenacity
   - Comprehensive error handling
   - Logging throughout
   - Graceful degradation

3. **Privacy**
   - Local Ollama only (no external APIs)
   - No data sent to third-party services
   - Secure database connections

4. **Scalability**
   - Async endpoints
   - Background tasks
   - Efficient database queries
   - Rate limiting

5. **Future-Proofing**
   - Comprehensive tests
   - Version pinning
   - Detailed documentation
   - Modular architecture

## Contributing

When adding new features:
1. Create a new router file in `routers/`
2. Define Pydantic models
3. Integrate with database/config
4. Use Ollama for AI logic
5. Add error handling and logging
6. Write tests in `tests/`
7. Update this documentation
8. Pin versions in requirements.txt

## License

Proprietary - All rights reserved
