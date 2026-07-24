---
name: erp-build-and-minimal-change
description: Instructions for surgical, non-invasive custom Frappe app development and AI control plane extension.
---

# ERP Build & Minimal Change Skill

## Purpose
Enforces surgical, minimal, non-invasive code modifications across custom Frappe apps and the AI microservice without bloating the codebase or altering upstream ERPNext source.

## Directives & Development Playbooks

1. **Clean Custom App Structure**:
   - Custom Frappe code MUST reside in `apps/ai_erp_core/` (cross-industry AI proposals) or `apps/ai_erp_service/` (field-service ERP domain).
   - Distribution and manufacturing configured demos reside as `configured_demo` stubs, not bloated custom apps.

2. **Frappe DocType & Script Conventions**:
   - Standardize server scripts (`.py`), client scripts (`.js`), and DocType definitions (`.json`).
   - Export custom fields cleanly into `fixtures/custom_field.json`.
   - Implement server-side logic in Python controller classes with explicit permission checks (`has_permission`).

3. **Deterministic Business State Modifications**:
   - Stock entries (`Stock Entry`) for parts issues must be created via deterministic Frappe Python methods.
   - Draft Sales Invoices (`Sales Invoice`) must be generated only when a work order transitions to `invoice_ready`.

4. **AI Control Plane Handlers**:
   - AI service endpoints live in `services/ai_control_plane/src/ai_erp_control_plane/app.py`.
   - Maintain strict decoupling: the control plane returns typed `AI Proposal` objects, which Frappe Desk users or deterministic ERP methods validate.
