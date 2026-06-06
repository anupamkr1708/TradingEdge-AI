"""
Prometheus Metrics

Defines all application metrics for monitoring and observability.
"""

from prometheus_client import Counter, Histogram, Gauge


# System Health
health_status = Gauge(
    'trademind_health_status',
    'Service health (1=healthy, 0=unhealthy)',
    ['service']
)

# API Metrics
api_requests = Counter(
    'trademind_api_requests_total',
    'HTTP requests',
    ['method', 'endpoint', 'status_code']
)

api_latency = Histogram(
    'trademind_api_latency_seconds',
    'API response time',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# Database Metrics
db_queries = Counter(
    'trademind_db_queries_total',
    'Database queries executed',
    ['operation']
)

db_query_latency = Histogram(
    'trademind_db_query_latency_seconds',
    'Database query execution time',
    ['operation'],
    buckets=[0.001, 0.01, 0.05, 0.1, 0.5]
)

# Cache Metrics
cache_operations = Counter(
    'trademind_cache_operations_total',
    'Cache operations',
    ['cache_type', 'operation']
)

# Agent Metrics
agent_executions = Counter(
    'trademind_agent_executions_total',
    'Agent execution count',
    ['agent_name', 'status']
)

agent_latency = Histogram(
    'trademind_agent_latency_seconds',
    'Agent execution time',
    ['agent_name'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

agent_confidence = Histogram(
    'trademind_agent_confidence',
    'Agent confidence score distribution',
    ['agent_name'],
    buckets=[0, 30, 50, 70, 85, 100]
)


class MetricsCollector:
    """Centralized metrics collection"""
    
    def update_health_status(self, service: str, healthy: bool):
        """Update service health"""
        health_status.labels(service=service).set(1 if healthy else 0)
    
    def record_api_request(self, method: str, endpoint: str, status_code: int):
        """Record API request"""
        api_requests.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    
    def record_api_latency(self, endpoint: str, latency_seconds: float):
        """Record API latency"""
        api_latency.labels(endpoint=endpoint).observe(latency_seconds)
    
    def record_db_query(self, operation: str, latency_seconds: float):
        """Record database query"""
        db_queries.labels(operation=operation).inc()
        db_query_latency.labels(operation=operation).observe(latency_seconds)
    
    def record_cache_operation(self, cache_type: str, operation: str):
        """Record cache operation"""
        cache_operations.labels(cache_type=cache_type, operation=operation).inc()
    
    def record_agent_execution(self, agent_name: str, success: bool, latency_seconds: float, confidence: int):
        """Record agent execution"""
        status = "success" if success else "failure"
        agent_executions.labels(agent_name=agent_name, status=status).inc()
        agent_latency.labels(agent_name=agent_name).observe(latency_seconds)
        if success:
            agent_confidence.labels(agent_name=agent_name).observe(confidence)


metrics = MetricsCollector()
