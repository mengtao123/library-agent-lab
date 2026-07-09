from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
import time

REQUESTS = Counter('http_requests_total', 'Total HTTP requests', ['service', 'method', 'endpoint'])
LATENCY = Histogram('http_request_duration_seconds', 'Request latency', ['service', 'method', 'endpoint'])

def track_request(service, method, endpoint, duration):
    REQUESTS.labels(service, method, endpoint).inc()
    LATENCY.labels(service, method, endpoint).observe(duration)

def get_metrics():
    return generate_latest(REGISTRY)