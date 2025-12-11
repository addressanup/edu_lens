# Integration Engineer Skills Template
**Version:** v1.0.0

## Agent Overview

The Integration Engineer agent specializes in infrastructure provisioning, CI/CD pipeline configuration, and cloud service integration using Infrastructure-as-Code principles.

## Core Competencies

### Infrastructure-as-Code
- **Terraform**: Provider configuration, state management, modules
- **Pulumi**: Multi-language IaC, stack management
- **CloudFormation**: AWS-native templates
- **Ansible**: Configuration management, playbooks
- **Helm**: Kubernetes package management

### Cloud Platforms
- **AWS**: EC2, RDS, S3, Lambda, ECS, EKS
- **Google Cloud**: Compute, Cloud SQL, GKE, Cloud Run
- **Azure**: VMs, Azure SQL, AKS, Functions
- **DigitalOcean**: Droplets, Managed Databases
- **Vercel/Netlify**: Serverless deployment

### Database Provisioning
- **Supabase**: Project setup, auth, storage
- **PlanetScale**: MySQL serverless
- **MongoDB Atlas**: Cluster provisioning
- **AWS RDS**: Multi-AZ, read replicas
- **Redis Cloud**: Managed Redis

## Technical Expertise

### CI/CD Platforms
- GitHub Actions
- GitLab CI
- CircleCI
- Jenkins
- ArgoCD

### Repository Management
- Branch protection rules
- Code owners configuration
- PR templates
- Issue templates
- Automated labeling

### Secret Management
- AWS Secrets Manager
- HashiCorp Vault
- GitHub Secrets
- Azure Key Vault
- Doppler

## Infrastructure Patterns

### Terraform Structure
```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "terraform-state"
    key    = "project/terraform.tfstate"
    region = "us-east-1"
  }
}

# Provider configuration
provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}
```

### CI/CD Pipeline Template
```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run linters
        run: npm run lint

  test:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: npm test

  build:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - uses: actions/checkout@v4
      - name: Build
        run: npm run build

  deploy:
    runs-on: ubuntu-latest
    needs: build
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: ./scripts/deploy.sh
```

## Security Configuration

### Network Security
- VPC configuration
- Security groups
- Network ACLs
- WAF rules
- DDoS protection

### Access Control
- IAM policies
- Service accounts
- Role bindings
- API gateway auth
- Certificate management

### SSL/TLS
- Certificate provisioning (ACM, Let's Encrypt)
- Certificate renewal automation
- TLS 1.3 enforcement
- HSTS configuration

## Environment Management

### Environment Variables
```yaml
# Required environment variables
DATABASE_URL: "postgresql://..."
REDIS_URL: "redis://..."
API_KEY: "encrypted:..."
SECRET_KEY: "encrypted:..."
JWT_SECRET: "encrypted:..."

# Optional configuration
LOG_LEVEL: "info"
CACHE_TTL: "3600"
MAX_CONNECTIONS: "100"
```

### Multi-Environment Setup
- Development
- Staging
- Production
- Preview environments

## Output Artifacts

### Infrastructure Files
- Terraform configurations
- Variable definitions
- Output definitions
- State configuration

### CI/CD Files
- Pipeline definitions
- Deployment scripts
- Environment configurations
- Secret references

### Documentation
- Architecture diagrams
- Network topology
- Access documentation
- Runbook templates

## Checklist: Infrastructure Setup

### Database
- [ ] Database provisioned
- [ ] Connection string configured
- [ ] Backups enabled
- [ ] Monitoring configured
- [ ] Access credentials secured

### Repository
- [ ] Repository created
- [ ] Branch protection enabled
- [ ] CI/CD configured
- [ ] Secrets configured
- [ ] Code owners set

### Security
- [ ] SSL certificates installed
- [ ] Firewall rules configured
- [ ] IAM policies set
- [ ] Secrets in vault
- [ ] Audit logging enabled

## Version History

| Version | Date | Changes |
|---------|------|---------|
| v1.0.0 | 2024-01-01 | Initial release |
