---
name: tech-stack-and-dependencies
description: Repository tech stack specifications, dependency locking, lockfile pin verification, and runtime requirements.
---

# Tech Stack & Dependencies Skill

## Purpose
Enforces repository tech stack standards, runtime version constraints, and reproducible dependency lockfile management.

## Tech Stack Overview

1. **ERP Core Platform**:
   - **Framework**: Frappe Framework (v15 / v16).
   - **Upstream ERP**: ERPNext.
   - **Language**: Python 3.11+, JavaScript (Vanilla JS / Frappe Desk).

2. **AI Control Plane**:
   - **Framework**: FastAPI (Python 3.11 / 3.14).
   - **Data Validation**: Pydantic v2.
   - **Package Manager**: `uv` package manager (`services/ai_control_plane/uv.lock`, `requirements.lock`).

3. **Infrastructure & Deployment**:
   - **IaC**: Terraform 1.5+ (`infra/aws/terraform/`).
   - **Cloud**: AWS ECS Fargate, RDS PostgreSQL / MariaDB, Valkey / Redis, ALB, Secrets Manager.
   - **Containers**: Docker, Docker Compose (`infra/compose/`).

4. **Testing Stack**:
   - **Python Testing**: `pytest`.
   - **Browser E2E**: Playwright TypeScript (`tests/e2e/package.json`).

## Lockfile & Pin Verification
- Maintain reproducible dependencies. Run `scripts/check-reproducibility.sh` and `scripts/check-dependency-updates.py` to verify lockfile integrity.
