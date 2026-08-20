# Compliance readiness

These documents are engineering evidence, templates, and operating checklists.
They are not legal advice, signed contracts, completed DPIAs, or certification.
Production owners and qualified counsel must approve applicable obligations
before real data is used.

## Package index

| Document | What it is | What it is not |
| --- | --- | --- |
| [Owner fill-in checklist](owner-fill-in-checklist.md) | One-page map of what the owner must supply, linked to each template | Agent-completed form or legal approval |
| [Privacy / data-flow inventory](privacy-data-flow-inventory.md) | Synthetic-demo data classes, AI visibility, retention intent | RoPA or lawful-basis decision |
| [PII handling notes](pii-handling-notes.md) | Code-aligned redaction and contributor rules | Privacy policy |
| [DPA template](dpa-template.md) | Counsel-facing processing agreement outline | Executed DPA |
| [DPIA template](dpia-template.md) | Counsel/DPO impact-assessment outline | Completed DPIA approval |
| [EU/Italy GDPR readiness gate](eu-italy-gdpr-readiness.md) | Gate table for private evidence before real pilot data | GDPR compliance claim |
| [Pilot evidence template](service-operations-pilot-evidence-template.md) | Public-safe index of demo vs pilot evidence | Human UAT or legal sign-off |
| [Support / incident / go-no-go checklist](pilot-go-no-go-checklist.md) | Empty human sign-off fields for pilot gates | Accountable go decision |

Start with [owner-fill-in-checklist.md](owner-fill-in-checklist.md) when you need
the human-owned list (people, legal fields, product decisions, optional
credentials). Agents must leave those blanks empty.

Manifest: `config/pilot-readiness.json` (demo ready; production-pilot gates
pending).
