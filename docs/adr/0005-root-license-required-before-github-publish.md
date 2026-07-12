# ADR-0005: Resolve the repository license before GitHub publication

- Status: Accepted
- Date: 2026-07-10
- Decision date: 2026-07-12
- Owners: AI ERP Demo contributors

## Context

The generated Frappe apps initially declared MIT with placeholder ownership,
while the supplied blueprint proposed AGPL-3.0 for a hosted open-source
product. The repository needed one explicit, compatible policy before GitHub
publication.

## Decision

License the repository-owned code, both custom Frappe apps, and the AI control
plane under `AGPL-3.0-only`. Use DCO sign-off for contributions. ERPNext's
GPL-3.0 and Frappe's MIT licenses remain upstream and unchanged; their source is
not vendored here.

AGPL-3.0-only was selected because the product is designed for network-hosted
ERP use and should keep deployed modifications available to users. Section 13
of AGPLv3 expressly permits combining AGPLv3-covered work with GPLv3-covered
work while each part retains its license.

## Consequences

- Hosted modifications are subject to AGPLv3's network-source obligations.
- Commercial use remains permitted under the license terms.
- Public release still requires the non-license publication, CI, fresh-clone,
  security-contact, and operational gates in the publication runbook.
