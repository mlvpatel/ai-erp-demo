---
name: mcp-and-erp-connectors
description: Protocol guidelines for Model Context Protocol (MCP) servers, FastAPI AI endpoints, and Frappe REST connectors.
---

# MCP & ERP Connectors Skill

## Purpose
Governs integration protocols for Model Context Protocol (MCP) tools, AI control plane API endpoints, and Frappe REST API connectors.

## Integration Protocols & Standards

1. **AI Control Plane REST Connector**:
   - The FastAPI control plane exposes `/healthz`, `/readyz`, and `/api/v1/proposals/generate`.
   - Payload shapes must strictly match Pydantic schemas in `services/ai_control_plane/src/ai_erp_control_plane/models.py`.

2. **Frappe Permission-Scoped Retrieval Connector**:
   - Structured record retrieval for AI proposals is implemented in `apps/ai_erp_service/ai_erp_service/retrieval.py`.
   - Connector calls MUST pass the active user session context to enforce Frappe permission filters (`frappe.has_permission`).

3. **Local MCP Server Interface**:
   - Local MCP servers must operate read-only for catalog inspection (`search_skills`, `get_skill`, `inspect_stack`).
   - Any state changes or file modifications require explicit CLI or agent tool confirmation.
