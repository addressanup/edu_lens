# EduLens Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying EduLens smart glasses software in various environments, including on-device deployment, cloud services setup, scaling strategies, and monitoring configuration.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [On-Device Deployment](#on-device-deployment)
3. [Cloud Services Setup](#cloud-services-setup)
4. [Hybrid Deployment](#hybrid-deployment)
5. [Scaling Considerations](#scaling-considerations)
6. [Monitoring Setup](#monitoring-setup)
7. [Security Configuration](#security-configuration)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Hardware Requirements

#### Smart Glasses Device (On-Device)
- **CPU**: ARM Cortex-A76 (quad-core) or equivalent x86-64
- **GPU**: Mali-G78, Adreno 650, or NVIDIA Jetson series
- **RAM**: 4-8 GB LPDDR5
- **Storage**: 64-128 GB UFS 3.1 or NVMe
- **Battery**: 3000 mAh minimum
- **Operating System**: Linux (Ubuntu 22.04 LTS) or Android 11+

#### Cloud Infrastructure (Optional)
- **Compute**: 4-8 vCPUs per service instance
- **Memory**: 8-16 GB RAM per service instance
- **Storage**: 100 GB+ SSD for databases and models
- **Network**: 1 Gbps+ bandwidth

### Software Requirements

- **Python**: 3.11 or higher
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **Git**: 2.30 or higher

### API Keys and Credentials

- Anthropic API key (for Claude LLM) or OpenAI API key
- Cloud provider credentials (AWS/GCP/Azure)
- SSL/TLS certificates for production

## On-Device Deployment

### 1. System Preparation

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system dependencies
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    build-essential \
    cmake \
    git \
    libopencv-dev \
    libportaudio2 \
    libasound2-dev \
    libusb-1.0-0-dev

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin
```

### 2. Clone Repository

```bash
# Clone the EduLens repository
git clone https://github.com/org/edulens.git
cd edulens

# Checkout specific version (recommended for production)
git checkout v1.0.0
```

### 3. Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional, for testing)
pip install -r requirements-dev.txt
```

### 4. Configuration

```bash
# Copy default configuration
cp configs/system/default_config.yaml configs/system/local_config.yaml

# Edit configuration for your device
nano configs/system/local_config.yaml
```

Key configuration changes for on-device deployment:

```yaml
environment: production
debug: false

camera:
  fps: 30
  resolution_width: 1920
  resolution_height: 1080
  device_id: 0

performance:
  max_workers: 4
  gpu_enabled: true
  gpu_device_id: 0
  model_quantization: true

cloud:
  enabled: false  # Disable for fully on-device deployment

storage:
  database_type: sqlite
  database_path: ./data/edulens.db
```

### 5. Model Download

```bash
# Create models directory
mkdir -p models

# Download quantized models for on-device inference
python scripts/download_models.py --target on-device

# Models will be downloaded to:
# - models/yolov8n-int8.tflite (object detection)
# - models/whisper-tiny.onnx (speech recognition)
# - models/easyocr-en.onnx (OCR)
```

### 6. Database Initialization

```bash
# Initialize database schema
python -m edulens.scripts.init_db --config configs/system/local_config.yaml

# Verify database
sqlite3 data/edulens.db ".tables"
```

### 7. Run Application

```bash
# Start EduLens application
python -m edulens.main --config configs/system/local_config.yaml

# Or using Docker (recommended)
docker-compose -f docker-compose.device.yml up -d

# View logs
docker-compose -f docker-compose.device.yml logs -f
```

### 8. Verify Deployment

```bash
# Check service health
curl http://localhost:8080/health

# Expected response:
# {
#   "status": "healthy",
#   "components": {
#     "camera": true,
#     "audio": true,
#     "vision_pipeline": true,
#     "ai_engine": true
#   }
# }
```

### 9. Auto-Start Configuration

For automatic startup on device boot:

```bash
# Create systemd service
sudo nano /etc/systemd/system/edulens.service
```

```ini
[Unit]
Description=EduLens Smart Glasses Service
After=network.target

[Service]
Type=simple
User=edulens
WorkingDirectory=/home/edulens/edulens
ExecStart=/home/edulens/edulens/venv/bin/python -m edulens.main --config configs/system/local_config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable edulens.service
sudo systemctl start edulens.service
sudo systemctl status edulens.service
```

## Cloud Services Setup

### 1. Infrastructure Provisioning

#### Using AWS

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure

# Deploy infrastructure using Terraform
cd infrastructure/terraform/aws
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### Using GCP

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Deploy infrastructure
cd infrastructure/terraform/gcp
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

### 2. Kubernetes Deployment

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Configure cluster access
export KUBECONFIG=~/.kube/edulens-cluster-config

# Create namespace
kubectl create namespace edulens-prod

# Apply Kubernetes manifests
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmaps/
kubectl apply -f infrastructure/k8s/secrets/
kubectl apply -f infrastructure/k8s/deployments/
kubectl apply -f infrastructure/k8s/services/
kubectl apply -f infrastructure/k8s/ingress.yaml

# Verify deployments
kubectl get pods -n edulens-prod
kubectl get services -n edulens-prod
```

### 3. Database Setup

#### PostgreSQL (Cloud)

```bash
# Connect to database instance
psql -h edulens-db.cluster.us-east-1.rds.amazonaws.com -U edulens_admin -d edulens_prod

# Run migrations
python -m alembic upgrade head

# Verify schema
\dt
```

#### Redis (Cache)

```bash
# Install Redis client
pip install redis

# Test connection
python -c "import redis; r = redis.Redis(host='edulens-cache.redis.cache.windows.net', port=6380, ssl=True); print(r.ping())"
```

### 4. Object Storage Setup

```bash
# Configure S3 bucket (AWS)
aws s3 mb s3://edulens-models-prod
aws s3 mb s3://edulens-user-data-prod

# Upload model files
aws s3 sync models/ s3://edulens-models-prod/models/ --acl private

# Set lifecycle policies
aws s3api put-bucket-lifecycle-configuration \
  --bucket edulens-user-data-prod \
  --lifecycle-configuration file://s3-lifecycle.json
```

### 5. API Gateway Configuration

```bash
# Deploy API Gateway (AWS)
cd infrastructure/api-gateway
serverless deploy --stage prod

# Or using Kong Gateway
docker run -d --name kong-gateway \
  --network=edulens-network \
  -e "KONG_DATABASE=postgres" \
  -e "KONG_PG_HOST=db" \
  -e "KONG_PG_USER=kong" \
  -e "KONG_PG_PASSWORD=kong" \
  -e "KONG_PROXY_ACCESS_LOG=/dev/stdout" \
  -e "KONG_ADMIN_ACCESS_LOG=/dev/stdout" \
  -e "KONG_PROXY_ERROR_LOG=/dev/stderr" \
  -e "KONG_ADMIN_ERROR_LOG=/dev/stderr" \
  -e "KONG_ADMIN_LISTEN=0.0.0.0:8001" \
  -p 8000:8000 \
  -p 8443:8443 \
  -p 8001:8001 \
  kong:3.0
```

## Hybrid Deployment

Hybrid deployment combines on-device processing with cloud services for optimal performance and scalability.

### Architecture

```
Device (Edge)              Cloud (Backend)
├── Vision Pipeline   →    ├── LLM API Service
├── Audio Pipeline    →    ├── RAG Pipeline
├── Privacy Layer     →    ├── Knowledge Base
└── Basic AI         ←→    ├── User Management
                           ├── Analytics
                           └── Content Delivery
```

### Configuration

```yaml
# configs/system/hybrid_config.yaml

environment: production

cloud:
  enabled: true
  api_endpoint: https://api.edulens.com
  sync_interval_seconds: 300
  retry_attempts: 3
  timeout_seconds: 30

ai_engine:
  llm_provider: anthropic
  llm_model: claude-3-5-sonnet-20241022
  fallback_to_local: true  # Use local model if cloud unavailable
  local_model: phi-2-quantized

performance:
  prefer_edge_processing: true
  cloud_offload_threshold: 0.8  # CPU usage threshold for cloud offload
```

### Device-Cloud Communication

```python
# Example: Hybrid inference with fallback

from edulens.core.configuration import get_config
from edulens.ai.hybrid_llm import HybridLLMProvider

async def process_query(query: str):
    config = get_config().get_system_config()
    llm = HybridLLMProvider(config)

    try:
        # Try cloud inference first
        response = await llm.generate_cloud(query)
    except Exception as e:
        logger.warning(f"Cloud inference failed: {e}, falling back to local")
        # Fallback to on-device inference
        response = await llm.generate_local(query)

    return response
```

## Scaling Considerations

### Horizontal Scaling

#### Auto-scaling Configuration (Kubernetes)

```yaml
# k8s/hpa/ai-service-hpa.yaml

apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-service-hpa
  namespace: edulens-prod
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-service
  minReplicas: 3
  maxReplicas: 20
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
      selectPolicy: Max
```

### Load Balancing

```nginx
# nginx/load-balancer.conf

upstream ai_service {
    least_conn;
    server ai-service-1:8080 max_fails=3 fail_timeout=30s;
    server ai-service-2:8080 max_fails=3 fail_timeout=30s;
    server ai-service-3:8080 max_fails=3 fail_timeout=30s;
}

server {
    listen 443 ssl http2;
    server_name api.edulens.com;

    ssl_certificate /etc/ssl/certs/edulens.crt;
    ssl_certificate_key /etc/ssl/private/edulens.key;

    location /api/v1/ai/ {
        proxy_pass http://ai_service;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
```

### Database Scaling

#### Read Replicas

```yaml
# PostgreSQL read replicas configuration

primary:
  host: edulens-db-primary.cluster.us-east-1.rds.amazonaws.com
  port: 5432

replicas:
  - host: edulens-db-replica-1.cluster.us-east-1.rds.amazonaws.com
    port: 5432
    weight: 1
  - host: edulens-db-replica-2.cluster.us-east-1.rds.amazonaws.com
    port: 5432
    weight: 1
```

#### Sharding Strategy

```python
# Database sharding by user_id

def get_shard_id(user_id: str) -> int:
    """Determine shard based on user_id hash"""
    return int(hashlib.md5(user_id.encode()).hexdigest(), 16) % NUM_SHARDS

def get_database_connection(user_id: str):
    """Get database connection for user's shard"""
    shard_id = get_shard_id(user_id)
    return database_pool[shard_id]
```

### Caching Strategy

```yaml
# Multi-level caching configuration

cache:
  levels:
    # L1: In-memory cache (device)
    - type: memory
      max_size_mb: 100
      ttl_seconds: 300

    # L2: Redis (cloud)
    - type: redis
      host: edulens-cache.redis.cache.windows.net
      port: 6380
      ssl: true
      ttl_seconds: 3600

    # L3: CDN (global)
    - type: cdn
      provider: cloudflare
      zones:
        - us-east
        - eu-west
        - ap-southeast
      ttl_seconds: 86400
```

## Monitoring Setup

### 1. Prometheus & Grafana

```bash
# Install Prometheus
docker run -d --name prometheus \
  -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Install Grafana
docker run -d --name grafana \
  -p 3000:3000 \
  -e "GF_SECURITY_ADMIN_PASSWORD=admin" \
  grafana/grafana

# Import EduLens dashboards
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @dashboards/edulens-overview.json
```

### 2. Application Metrics

```python
# Expose Prometheus metrics

from prometheus_client import Counter, Histogram, Gauge, start_http_server

# Metrics
frame_processing_duration = Histogram(
    'edulens_frame_processing_seconds',
    'Time spent processing frames'
)

audio_transcription_total = Counter(
    'edulens_audio_transcriptions_total',
    'Total number of audio transcriptions'
)

active_sessions = Gauge(
    'edulens_active_sessions',
    'Number of active user sessions'
)

# Start metrics server
start_http_server(8000)
```

### 3. Logging (ELK Stack)

```bash
# Deploy Elasticsearch
docker run -d --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Deploy Logstash
docker run -d --name logstash \
  -p 5000:5000 \
  -v /path/to/logstash.conf:/usr/share/logstash/pipeline/logstash.conf \
  docker.elastic.co/logstash/logstash:8.11.0

# Deploy Kibana
docker run -d --name kibana \
  -p 5601:5601 \
  -e "ELASTICSEARCH_HOSTS=http://elasticsearch:9200" \
  docker.elastic.co/kibana/kibana:8.11.0
```

### 4. Distributed Tracing (Jaeger)

```bash
# Deploy Jaeger all-in-one
docker run -d --name jaeger \
  -e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
  -p 5775:5775/udp \
  -p 6831:6831/udp \
  -p 6832:6832/udp \
  -p 5778:5778 \
  -p 16686:16686 \
  -p 14268:14268 \
  -p 14250:14250 \
  -p 9411:9411 \
  jaegertracing/all-in-one:1.51
```

### 5. Alerting Rules

```yaml
# prometheus/alerts.yml

groups:
  - name: edulens_alerts
    interval: 30s
    rules:
      - alert: HighCPUUsage
        expr: cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage on {{ $labels.instance }}"

      - alert: LowMemory
        expr: memory_available_mb < 500
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Low memory on {{ $labels.instance }}"

      - alert: FrameProcessingLatency
        expr: histogram_quantile(0.95, rate(edulens_frame_processing_seconds_bucket[5m])) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Frame processing latency above 100ms"
```

## Security Configuration

### 1. TLS/SSL Setup

```bash
# Generate self-signed certificate (development)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Production: Use Let's Encrypt
sudo certbot certonly --standalone -d api.edulens.com
```

### 2. Secrets Management

```bash
# Using Kubernetes Secrets
kubectl create secret generic edulens-secrets \
  --from-literal=anthropic-api-key=YOUR_API_KEY \
  --from-literal=db-password=YOUR_DB_PASSWORD \
  -n edulens-prod

# Using HashiCorp Vault
vault kv put secret/edulens/prod \
  anthropic_api_key=YOUR_API_KEY \
  db_password=YOUR_DB_PASSWORD
```

### 3. Network Security

```yaml
# k8s/network-policy.yaml

apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: edulens-network-policy
  namespace: edulens-prod
spec:
  podSelector:
    matchLabels:
      app: edulens
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: edulens-prod
    ports:
    - protocol: TCP
      port: 8080
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
    - protocol: TCP
      port: 5432
```

## Troubleshooting

### Common Issues

#### 1. Camera Not Detected

```bash
# Check camera devices
ls -la /dev/video*

# Test camera with v4l2
v4l2-ctl --list-devices
v4l2-ctl --device=/dev/video0 --all

# Grant permissions
sudo usermod -aG video $USER
```

#### 2. GPU Not Available

```bash
# Check GPU status
nvidia-smi  # For NVIDIA GPUs
rocm-smi    # For AMD GPUs

# Install GPU drivers
sudo apt install nvidia-driver-525  # NVIDIA
```

#### 3. Memory Issues

```bash
# Monitor memory usage
free -h
top -o %MEM

# Increase swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

#### 4. Network Connectivity

```bash
# Test cloud API connectivity
curl -v https://api.edulens.com/health

# Check DNS resolution
nslookup api.edulens.com

# Test with different DNS
dig @8.8.8.8 api.edulens.com
```

### Log Analysis

```bash
# View application logs
tail -f logs/edulens.log

# Search for errors
grep -i "error" logs/edulens.log

# View Docker container logs
docker logs -f edulens-core

# View Kubernetes pod logs
kubectl logs -f <pod-name> -n edulens-prod
```

### Performance Profiling

```python
# Profile application performance
python -m cProfile -o profile.stats -m edulens.main

# Analyze profile
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
```

## Maintenance

### Backup Strategy

```bash
# Backup database
pg_dump -h edulens-db.cluster.us-east-1.rds.amazonaws.com \
  -U edulens_admin -d edulens_prod > backup_$(date +%Y%m%d).sql

# Backup configuration
tar -czf config_backup_$(date +%Y%m%d).tar.gz configs/

# Upload to S3
aws s3 cp backup_$(date +%Y%m%d).sql s3://edulens-backups/
```

### Update Procedure

```bash
# Pull latest changes
git pull origin main

# Backup current version
cp -r . ../edulens_backup_$(date +%Y%m%d)

# Update dependencies
pip install -r requirements.txt --upgrade

# Run database migrations
python -m alembic upgrade head

# Restart services
sudo systemctl restart edulens.service
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-10
**Authors**: Integration Agent (INT-001)
**Status**: Production Ready
