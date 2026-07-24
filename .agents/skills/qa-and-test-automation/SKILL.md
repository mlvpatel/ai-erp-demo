---
name: qa-and-test-automation
description: Test automation guidelines, pytest execution, Playwright E2E browser testing, contract validation, and capacity drills.
---

# QA & Test Automation Skill

## Purpose
Defines test automation strategy across unit, contract, E2E browser, infrastructure, and capacity testing tiers to guarantee product quality.

## Test Tiers & Execution Playbooks

1. **AI Control Plane Unit Tests**:
   - Located in `services/ai_control_plane/tests/`.
   - Run tests: `pytest services/ai_control_plane/tests/`.
   - Tests cover PII redaction, prompt rendering, live eval, and OpenAI provider adapters.

2. **Contract & Event Tests**:
   - Located in `tests/contract/`.
   - Run tests: `pytest tests/contract/test_ai_control_plane_openapi.py tests/contract/test_service_operations_events.py`.
   - Validates compliance against `contracts/openapi/ai-control-plane-v1.yaml` and `contracts/events/service-operations-v1.yaml`.

3. **Playwright E2E Browser Tests**:
   - Located in `tests/e2e/`.
   - Configuration: `tests/e2e/playwright.config.ts`.
   - Specs: `tests/e2e/service-operations.spec.ts`.
   - Run E2E tests: `npx playwright test --config tests/e2e/playwright.config.ts`.
   - Tests technician work execution, manager closeout, and accounts handoff.

4. **Infra & Recovery Drills**:
   - Located in `tests/infra/`.
   - Tests cover S3 backups, database restore drills, capacity load runs, and Terraform plan policies (`test_terraform_plan_policy.py`).

5. **Full Quality Gate Suite**:
   - Run complete static verification: `PYTHONPYCACHEPREFIX=./.pycache ./scripts/run-quality-gates.sh`.
