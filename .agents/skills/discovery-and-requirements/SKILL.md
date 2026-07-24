---
name: discovery-and-requirements
description: Guidelines and playbooks for requirements discovery, open-source ERP scanning, design-partner validation, and scorecard tracking.
---

# Discovery & Requirements Skill

## Purpose
This skill guides the discovery process, requirements traceability, design partner validation, and scorecard tracking for the AI ERP Demo platform.

## Key Principles & Workflow
1. **Requirements Traceability**:
   - Reference `docs/product/field-service-9-target.md` and `config/field-service-9-scorecard.json`.
   - Verify requirements using `scripts/check-field-service-9-scorecard.py`.
   - Ensure every implemented feature directly links back to user stories defined in `docs/product/mvp-scope.md`.

2. **Design Partner Validation**:
   - Use `docs/discovery/design-partner-validation-template.md` to format feedback from field-service operations managers.
   - Focus validation on evidence replay, invoice readiness speed, margin visibility, and technician execution simplicity.

3. **Open-Source ERP Scanning**:
   - Consult `docs/discovery/open-source-erp-scan-2026-07.md` when evaluating upstream Frappe/ERPNext features vs. custom extensions.
   - Prefer reusing native Frappe DocTypes (Customer, Item, Warehouse, Sales Invoice, Stock Entry) over inventing parallel core entities.
