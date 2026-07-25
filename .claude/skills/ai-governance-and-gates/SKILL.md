---
name: ai-governance-and-gates
description: Rules for AI decision boundaries, proposal context hashing, immutable evidence ledgers, and automated quality gate enforcement.
---

# AI Governance & Quality Gates Skill

## Purpose
Enforces non-posting AI boundaries, evidence hashing, proposal context uniqueness, and automated repository quality gate execution.

## Core Governance Directives

1. **Non-Posting AI Boundary**:
   - AI models MUST NOT perform direct ERP database mutations (posting invoices, updating stock balances, changing permissions).
   - AI outputs are stored strictly as `AI Proposal` documents with immutable `source_citations`.
   - Authorized human users review and approve proposals in Frappe Desk.

2. **Proposal Uniqueness & Idempotency**:
   - Each proposal request generates an input context hash.
   - Enforce idempotency via `apps/ai_erp_core/ai_erp_core/patches/v1_0/add_ai_proposal_context_uniqueness.py`.
   - Retries with the identical context hash return the existing `AI Proposal` record without invoking the provider again.

3. **Workflow Registry Verification**:
   - All AI workflow proposal types (closeout, exception recovery, repair memory, scheduling explanation) must be registered in `config/ai-workflow-registry.json`.
   - Verify registry via `scripts/check-ai-workflow-registry.py`.

4. **Repository Quality Gates Pipeline**:
   - Run `PYTHONPYCACHEPREFIX=./.pycache ./scripts/run-quality-gates.sh` to execute the full 40+ validation script suite before opening any pull request.
