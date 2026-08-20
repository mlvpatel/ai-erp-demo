# AI ERP Demo Repository Rules & Agent Guidelines

## Repository Core Directives

1. **Upstream Platform Cleanliness**:
   - Upstream ERPNext and Frappe core files MUST NOT be modified.
   - All custom ERP business logic and DocTypes live strictly in custom apps (`apps/ai_erp_core/` and `apps/ai_erp_service/`).
   - The AI control plane lives strictly in `services/ai_control_plane/`.

2. **AI Decision Boundary & Governance**:
   - AI **proposes**; deterministic ERP code and authorized humans **validate and post**.
   - AI MUST NEVER directly post accounting, stock, payroll, permissions, compliance records, or customer messages.
   - AI closeout proposals and recommendations must be draft-only, cited, immutable, review-only, and non-posting.

3. **Role & Permission Isolation**:
   - **Technicians** can only view and execute assigned work orders. Financial, margin, and cost fields remain strictly hidden from technicians.
   - **Service Managers** review closeouts, manage exceptions ("Cannot Close"), inspect margin risk, and approve invoice-ready transitions.
   - **Accounts Users** trigger idempotent draft Sales Invoices based on invoice-ready work orders.

4. **Transaction Idempotency & Safety**:
   - Parts issue via deterministic Frappe `Stock Entry` creation MUST be strictly idempotent.
   - Draft `Sales Invoice` creation MUST be finance-triggered, draft-only, idempotent, and must not modify stock balances.

5. **Security, Privacy & Data Boundaries**:
   - All personal data (PII) and credentials MUST be scrubbed before sending payloads to external AI providers.
   - Secrets, credentials, customer data, and raw AI prompt/response bodies MUST NEVER be committed to Git or written to log files.
   - Multi-tenant site isolation (`tenant_isolation`) must be strictly preserved.
   - Demo legal-readiness artifacts under `docs/compliance/` (including
     `owner-fill-in-checklist.md`) are templates and gates only; never treat
     them as legal approval or GDPR compliance.

6. **Git & Commit Attribution Rules**:
   - Default author and committer: `mlvpatel <mlvpatel@users.noreply.github.com>`.
   - When the repo owner wants GitHub Contributors credit for Cursor, author may be `Cursor Agent <cursoragent@cursor.com>` (committer stays `mlvpatel`); use a merge commit so authorship survives.
   - NO AI, LLM, bot, assistant, or generated-by attribution strings in commit messages or code comments.

7. **Prose (BEhuMan)**:
   - Apply `.agents/skills/behuman/SKILL.md` on every written deliverable:
     docs, runbooks, commit messages, PR text, summaries, comments.
   - Cursor loads the same skill from `.cursor/skills/behuman/` and the
     always-on rule `.cursor/rules/behuman.mdc`.
   - Do not announce the pass. Do not mass-rewrite unrelated historical docs
     unless asked.
