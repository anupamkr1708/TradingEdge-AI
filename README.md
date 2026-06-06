# TradeMind AI

AI-powered trading intelligence platform for NSE F&O markets.

## Architecture

**Current State:** Phase 1 Foundation Layer

This repository contains the production-grade backend foundation:
- ✅ FastAPI application with lifecycle management
- ✅ Supabase PostgreSQL integration
- ✅ Redis caching layer
- ✅ Prometheus metrics
- ✅ Health check endpoints
- ✅ Structured logging
- ✅ Docker containerization

**Phase 2** (upcoming): AI agents, recommendation engine, signal enrichment

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.11, FastAPI |
| Database | Supabase PostgreSQL |
| Cache | Redis 7 |
| Monitoring | Prometheus, Grafana |
| Containerization | Docker, Docker Compose |

## Project Structure

```
TradeMind-AI/
├── app/
│   ├── core/              # Configuration, logging, utilities
│   ├── db/                # Database layer (Supabase)
│   ├── integrations/      # Redis, external APIs
│   ├── monitoring/        # Prometheus metrics
│   ├── routers/           # API endpoints
│   ├── services/          # Business logic (Phase 2)
│   ├── agents/            # AI agents (Phase 2)
│   └── main.py            # Application entry point
├── config/                # Prometheus, Grafana configs
├── tests/                 # Test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Supabase account (free tier works)

### 1. Clone Repository

```bash
cd "H:/Trademind AI"
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Supabase URL
# SUPABASE_DATABASE_URL=postgresql://postgres.[project-ref]:[password]@[host]:5432/postgres
```

### 3. Install Dependencies (Local Development)

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Run Locally

```bash
uvicorn app.main:app --reload --port 8001
```

### 5. Run with Docker

```bash
docker-compose up --build
```

## API Endpoints

### Health Checks

```bash
# Comprehensive health check
GET http://localhost:8001/health

# Liveness probe (Kubernetes)
GET http://localhost:8001/health/live

# Readiness probe (Kubernetes)
GET http://localhost:8001/health/ready
```

### Monitoring

```bash
# Prometheus metrics
GET http://localhost:8001/metrics

# Prometheus UI
http://localhost:9090

# Grafana dashboards
http://localhost:3000 (admin/admin)
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Type checking
mypy app/

# Linting
ruff check app/

# Formatting
black app/
```

### Logs

Development mode (human-readable):
```
2026-06-06 17:30:00 | INFO     | app.main | Application startup complete
```

Production mode (JSON):
```json
{"timestamp":"2026-06-06T17:30:00.123Z","level":"INFO","logger":"app.main","message":"Application startup complete"}
```

## Configuration

All configuration is managed via environment variables (see `.env.example`).

Key settings:
- `ENVIRONMENT`: `development` | `production`
- `LOG_LEVEL`: `DEBUG` | `INFO` | `WARNING` | `ERROR`
- `SUPABASE_DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string

## Monitoring

### Prometheus Metrics

- `trademind_health_status`: Service health status
- `trademind_api_requests_total`: HTTP request counter
- `trademind_api_latency_seconds`: API response time
- `trademind_db_queries_total`: Database query counter
- `trademind_cache_operations_total`: Cache operation counter

### Grafana Dashboards

Access Grafana at `http://localhost:3000` (default: admin/admin)

Dashboards will be added in Phase 2.

## Deployment

### Local Development

```bash
uvicorn app.main:app --reload --port 8001
```

### Docker (Production)

```bash
docker-compose up -d
```

### Environment Variables

Production deployment requires:
- `SUPABASE_DATABASE_URL`: Supabase connection string
- `ENVIRONMENT=production`
- `LOG_LEVEL=INFO`

## Roadmap

### ✅ Phase 1: Foundation Layer (Current)
- FastAPI application
- Database & Redis integration
- Health checks & monitoring
- Docker containerization

### 🚧 Phase 2: Intelligence Layer (Next)
- AI agents (Technical, News, Decision)
- Agent orchestrator
- Recommendation API
- Signal enrichment pipeline

### 📅 Phase 3: Enhancement Layer (Future)
- Portfolio intelligence
- Recommendation evaluation
- Backtesting framework
- Advanced dashboards

## Contributing

Phase 1 is complete. Phase 2 development will begin after foundation validation.

## License

Proprietary - All rights reserved

## Contact

For questions or issues, contact the development team.
