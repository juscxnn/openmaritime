"""
Prometheus metrics for OpenMaritime.

Exposes /metrics endpoint with custom metrics for AI pipeline, API calls, and system health.
"""
from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from typing import Optional
import time

router = APIRouter(tags=["observability"])

# Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

# AI Pipeline metrics
ai_pipeline_runs = Counter(
    "ai_pipeline_runs_total",
    "Total AI pipeline executions",
    ["agent_type", "status"]
)

ai_pipeline_duration_seconds = Histogram(
    "ai_pipeline_duration_seconds",
    "AI pipeline execution time",
    ["agent_type"]
)

ai_tokens_used = Counter(
    "ai_tokens_used_total",
    "Total tokens used by AI models",
    ["model", "prompt_type"]
)

# Fixture metrics
fixtures_created_total = Counter(
    "fixtures_created_total",
    "Total fixtures created",
    ["source"]  # email, api, manual
)

fixtures_enriched_total = Counter(
    "fixtures_enriched_total",
    "Total fixtures enriched",
    ["plugin", "status"]
)

fixtures_ranked_total = Counter(
    "fixtures_ranked_total",
    "Total fixtures ranked",
    ["model"]
)

# Plugin metrics
plugin_calls_total = Counter(
    "plugin_calls_total",
    "Total plugin invocations",
    ["plugin_name", "hook", "status"]
)

plugin_duration_seconds = Histogram(
    "plugin_duration_seconds",
    "Plugin execution time",
    ["plugin_name"]
)

plugin_errors_total = Counter(
    "plugin_errors_total",
    "Total plugin errors",
    ["plugin_name", "error_type"]
)

# Database metrics
db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections"
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"]
)

# Cost tracking
api_costs_total = Counter(
    "api_costs_total",
    "Total API costs in USD",
    ["provider", "service"]
)

# Email sync metrics
emails_synced_total = Counter(
    "emails_synced_total",
    "Total emails synced",
    ["status"]  # success, failed
)

fixtures_extracted_from_email = Counter(
    "fixtures_extracted_from_email_total",
    "Total fixtures extracted from emails",
    ["status"]  # success, failed
)

# Auth metrics
auth_logins_total = Counter(
    "auth_logins_total",
    "Total authentication events",
    ["method", "status"]  # password, oauth, saml, success, failure
)

# Queue metrics (Celery)
celery_task_runs = Counter(
    "celery_task_runs_total",
    "Total Celery task executions",
    ["task_name", "status"]
)

celery_task_duration_seconds = Histogram(
    "celery_task_duration_seconds",
    "Celery task execution time",
    ["task_name"]
)


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


class MetricsCollector:
    """Helper class for collecting metrics throughout the app"""
    
    @staticmethod
    def record_request(method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_ai_run(agent_type: str, status: str, duration: float):
        """Record AI pipeline execution"""
        ai_pipeline_runs.labels(agent_type=agent_type, status=status).inc()
        ai_pipeline_duration_seconds.labels(agent_type=agent_type).observe(duration)
    
    @staticmethod
    def record_tokens(model: str, prompt_type: str, tokens: int):
        """Record AI token usage"""
        ai_tokens_used.labels(model=model, prompt_type=prompt_type).inc(tokens)
    
    @staticmethod
    def record_fixture_created(source: str):
        """Record fixture creation"""
        fixtures_created_total.labels(source=source).inc()
    
    @staticmethod
    def record_fixture_enriched(plugin: str, status: str):
        """Record fixture enrichment"""
        fixtures_enriched_total.labels(plugin=plugin, status=status).inc()
    
    @staticmethod
    def record_plugin_call(plugin_name: str, hook: str, status: str, duration: float):
        """Record plugin invocation"""
        plugin_calls_total.labels(plugin_name=plugin_name, hook=hook, status=status).inc()
        plugin_duration_seconds.labels(plugin_name=plugin_name).observe(duration)
    
    @staticmethod
    def record_api_cost(provider: str, service: str, cost: float):
        """Record API cost"""
        api_costs_total.labels(provider=provider, service=service).inc(cost)
    
    @staticmethod
    def record_email_sync(status: str):
        """Record email sync"""
        emails_synced_total.labels(status=status).inc()
    
    @staticmethod
    def record_auth(method: str, status: str):
        """Record authentication event"""
        auth_logins_total.labels(method=method, status=status).inc()
    
    @staticmethod
    def record_celery_task(task_name: str, status: str, duration: float):
        """Record Celery task execution"""
        celery_task_runs.labels(task_name=task_name, status=status).inc()
        celery_task_duration_seconds.labels(task_name=task_name).observe(duration)


metrics_collector = MetricsCollector()
