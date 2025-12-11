# DevOps Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The DevOps Engineer agent specializes in deployment automation, container orchestration, monitoring setup, and operational excellence for production systems.

## Core Competencies

### Container Orchestration
- Kubernetes cluster management
- Helm chart development
- Service mesh (Istio, Linkerd)
- Container runtime configuration
- Resource management

### Deployment Strategies
- Rolling deployments
- Blue-green deployments
- Canary releases
- Feature flags
- Rollback procedures

### Monitoring & Observability
- Metrics collection (Prometheus)
- Log aggregation (ELK, Loki)
- Distributed tracing (Jaeger, Zipkin)
- Alerting (PagerDuty, OpsGenie)
- Dashboards (Grafana)

## Technical Expertise

### Container Technologies
- Docker
- Podman
- containerd
- Docker Compose
- Docker Swarm

### Kubernetes Resources
- Deployments
- Services
- Ingress
- ConfigMaps
- Secrets
- HorizontalPodAutoscaler
- PodDisruptionBudget
- NetworkPolicies

### CI/CD Tools
- GitHub Actions
- GitLab CI
- ArgoCD
- Flux
- Jenkins
- Tekton

## Configuration Templates

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app-deployment
  labels:
    app: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myapp:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: database-url
```

### Dockerfile
```dockerfile
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application
COPY src/ ./src/

# Set path
ENV PATH=/root/.local/bin:$PATH

# Run as non-root
RUN useradd -m appuser
USER appuser

EXPOSE 8080

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### HPA Configuration
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: app-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: app-deployment
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Monitoring Setup

### Prometheus Alerts
```yaml
groups:
- name: app-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: High error rate detected
      description: Error rate is {{ $value | humanizePercentage }}

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High latency detected
      description: P95 latency is {{ $value }}s
```

### Grafana Dashboard
```json
{
  "title": "Application Dashboard",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total[5m])"
        }
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }
      ]
    },
    {
      "title": "Latency (P95)",
      "type": "graph",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))"
        }
      ]
    }
  ]
}
```

## Disaster Recovery

### Backup Strategy
- Database backups (daily, weekly)
- Configuration backups
- Secret rotation
- State file backups
- Cross-region replication

### Recovery Procedures
```bash
#!/bin/bash
# restore.sh - Database restoration script

set -euo pipefail

BACKUP_FILE=$1
DATABASE_URL=$2

echo "Starting database restoration..."

# Verify backup file
if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "Error: Backup file not found"
    exit 1
fi

# Restore database
pg_restore \
    --dbname="$DATABASE_URL" \
    --clean \
    --if-exists \
    --no-owner \
    "$BACKUP_FILE"

echo "Database restoration completed"
```

### SLA Targets
| Metric | Target |
|--------|--------|
| Availability | 99.9% |
| RPO | 15 minutes |
| RTO | 1 hour |
| MTTR | 30 minutes |

## Output Artifacts

### Deployment Files
- Kubernetes manifests
- Helm charts
- Docker configurations
- CI/CD pipelines

### Monitoring Files
- Prometheus rules
- Grafana dashboards
- Alert configurations

### Documentation
- Deployment guide
- Operations runbook
- Disaster recovery plan
- Incident response playbook

## Checklist: Production Readiness

### Infrastructure
- [ ] Resource limits configured
- [ ] HPA enabled
- [ ] PDB configured
- [ ] Network policies set

### Monitoring
- [ ] Metrics exported
- [ ] Dashboards created
- [ ] Alerts configured
- [ ] On-call rotation set

### Security
- [ ] Secrets in vault
- [ ] Network segmentation
- [ ] RBAC configured
- [ ] Pod security policies

### Resilience
- [ ] Health checks
- [ ] Graceful shutdown
- [ ] Circuit breakers
- [ ] Retry logic

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
