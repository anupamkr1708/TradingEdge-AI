# TradeMind AI - Phase 1 Foundation Setup

## ✅ What Has Been Built

The **Phase 1 Foundation Layer** is complete and production-ready:

### Core Infrastructure
- ✅ FastAPI application with lifecycle management
- ✅ Pydantic-based configuration system
- ✅ Structured logging (JSON for production, colored for dev)
- ✅ Supabase PostgreSQL integration with connection pooling
- ✅ Redis caching layer with graceful degradation
- ✅ Prometheus metrics collection
- ✅ Comprehensive health check endpoints
- ✅ Docker containerization
- ✅ CORS middleware
- ✅ Global exception handling
- ✅ Request timing middleware

### Monitoring & Observability
- ✅ `/metrics` endpoint for Prometheus scraping
- ✅ `/health` comprehensive health check
- ✅ `/health/live` Kubernetes liveness probe
- ✅ `/health/ready` Kubernetes readiness probe
- ✅ Metrics for API requests, latency, database, cache

### Development Tools
- ✅ pytest test suite with fixtures
- ✅ Validation scripts
- ✅ Windows startup script
- ✅ Docker Compose for full stack

---

## 🚀 Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Supabase account** (free tier: https://supabase.com)
3. **Docker** (optional, for containerized deployment)

### Step 1: Supabase Setup

1. Go to https://supabase.com and create a new project
2. Wait for project initialization (~2 minutes)
3. Go to **Settings** → **Database**
4. Copy the **Connection String** (Session mode)
   - Format: `postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres`

### Step 2: Environment Configuration

```bash
# Copy environment template
copy .env.example .env

# Edit .env and paste your Supabase connection string
# SUPABASE_DATABASE_URL=postgresql://postgres...
```

### Step 3: Validation

```bash
# Run setup validation
python scripts/validate_setup.py
```

Expected output:
```
✓ Configuration valid
✓ Database connection healthy
✓ Redis connection healthy (or warning if not running locally)
✓ All critical checks passed!
```

### Step 4: Start Application

**Option A: Local Development (Windows)**
```bash
run.bat
```

**Option B: Local Development (Linux/Mac)**
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Option C: Docker (Full Stack)**
```bash
docker-compose up --build
```

---

## 🧪 Testing

### Run Tests
```bash
pytest
```

### Test Health Endpoints
```bash
# Root
curl http://localhost:8001/

# Health check
curl http://localhost:8001/health

# Liveness probe
curl http://localhost:8001/health/live

# Metrics
curl http://localhost:8001/metrics
```

---

## 📊 Monitoring

### Prometheus
- Local: http://localhost:9090
- Docker: http://localhost:9090

### Grafana
- Local: Not running (Phase 2)
- Docker: http://localhost:3000 (admin/admin)

### Available Metrics
- `trademind_health_status{service="supabase|redis"}`
- `trademind_api_requests_total{method, endpoint, status_code}`
- `trademind_api_latency_seconds{endpoint}`
- `trademind_db_queries_total{operation}`
- `trademind_cache_operations_total{cache_type, operation}`

---

## 📁 Repository Structure

```
TradeMind-AI/
├── app/
│   ├── core/
│   │   ├── config.py          # Pydantic settings
│   │   └── logging.py         # Structured logging
│   ├── db/
│   │   └── supabase.py        # Database integration
│   ├── integrations/
│   │   └── redis_client.py    # Redis integration
│   ├── monitoring/
│   │   └── metrics.py         # Prometheus metrics
│   ├── routers/
│   │   └── health.py          # Health endpoints
│   ├── services/              # (Phase 2)
│   ├── agents/                # (Phase 2)
│   └── main.py                # FastAPI application
├── config/
│   └── prometheus.yml         # Prometheus config
├── scripts/
│   ├── init_db.py             # Database initialization
│   └── validate_setup.py      # Setup validation
├── tests/
│   ├── conftest.py            # pytest fixtures
│   └── test_health.py         # Health endpoint tests
├── .env.example               # Environment template
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── requirements.txt
├── run.bat                    # Windows startup
├── README.md
└── SETUP.md                   # This file
```

---

## 🔧 Configuration

All configuration is managed via environment variables in `.env`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | No | `development` | Runtime environment |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `API_PORT` | No | `8001` | API server port |
| `SUPABASE_DATABASE_URL` | **Yes** | - | PostgreSQL connection string |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string |
| `PROMETHEUS_ENABLED` | No | `true` | Enable metrics export |

---

## 🐛 Troubleshooting

### Issue: "Database health check failed"

**Solution:**
1. Verify Supabase connection string is correct
2. Check if Supabase project is running (not paused)
3. Test connection: `python scripts/init_db.py`

### Issue: "Redis connection failed"

**Solution:**
1. Redis is **optional** for Phase 1
2. Install Redis locally: https://redis.io/download
3. Or use Docker: `docker run -d -p 6379:6379 redis:7-alpine`

### Issue: "Import errors"

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Issue: "Port 8001 already in use"

**Solution:**
```bash
# Change port in .env
API_PORT=8002

# Or kill existing process (Windows)
netstat -ano | findstr :8001
taskkill /PID <PID> /F
```

---

## 📝 Next Steps: Phase 2

Once foundation is validated, Phase 2 will add:

1. **AI Agents**
   - Technical Analysis Agent
   - News Intelligence Agent
   - Decision Agent

2. **Recommendation Engine**
   - Signal enrichment pipeline
   - Agent orchestration
   - Recommendation APIs

3. **NSE Integration**
   - WebSocket signal consumer
   - Signal queue processing

4. **Business Logic**
   - Enrichment service
   - Recommendation storage
   - Agent thought persistence

**Timeline:** Phase 2 implementation begins after Phase 1 validation.

---

## ✅ Phase 1 Checklist

- [x] Configuration system
- [x] Logging system
- [x] Database integration
- [x] Redis integration
- [x] Monitoring setup
- [x] Health endpoints
- [x] FastAPI application
- [x] Docker containerization
- [x] Test suite
- [x] Documentation

**Status:** Phase 1 Complete ✅

---

## 📞 Support

For issues or questions:
1. Check this SETUP.md document
2. Review logs in console
3. Run validation: `python scripts/validate_setup.py`
4. Check Supabase dashboard for database status

---

**Built with:** Python 3.11, FastAPI, Supabase, Redis, Prometheus, Docker
