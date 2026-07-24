---
name: security-pii-and-isolation
description: Security auditing, PII and credential redaction, secret scanning, authorization matrix verification, and tenant isolation protocols.
---

# Security, PII & Tenant Isolation Skill

## Purpose
Enforces strict security boundaries, PII/credential redaction prior to AI model calls, secret scanning, role-based authorization verification, and multi-tenant isolation.

## Security Directives & Audit Playbooks

1. **PII & Credential Redaction**:
   - Before invoking external AI LLM providers (e.g. OpenAI adapter), run data through the redaction layer in `services/ai_control_plane/src/ai_erp_control_plane/render.py`.
   - Strip names, phone numbers, email addresses, credit cards, and API keys.
   - Verify PII redaction rules via `scripts/check-ai-data-boundary.py`.

2. **Secret & Sensitive Data Scanning**:
   - Zero tolerance for committing AWS keys, OpenAI API keys, database passwords, or private customer data.
   - Run publication secret scans via `scripts/check-publication-secrets.py`.

3. **Role Authorization Matrix**:
   - Enforce permission matrices defined in `config/authorization-matrix.json`.
   - Technicians MUST NOT have read or write access to financial fields (`hourly_rate`, `margin`, `part_cost`, `total_amount`).
   - Run authorization checks via `scripts/check-authorization-matrix.py`.

4. **Multi-Tenant Site Isolation**:
   - Frappe site-based isolation must prevent cross-site or cross-tenant record leakage.
   - Verify isolation via `scripts/check-tenant-isolation.py`.
