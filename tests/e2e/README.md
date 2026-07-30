# Browser E2E

The browser suite uses Playwright 1.61.0 in its matching official container. It
creates only synthetic `.localhost` users and work orders, authenticates each
role in an isolated browser or API context, opens real Frappe Desk routes, and
exercises the controlled service transaction path.

Run after the local Bench web process is available:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh e2e-test
```

The helper prepares local Technician, Dispatcher, Service Manager, Accounts
User, and AI Proposal Approver identities, runs Chromium in the Compose network,
and removes the test container. Primary role journeys use visible Frappe forms
and controls at desktop and mobile viewports, including keyboard focus,
validation feedback, attachment upload, the 390 by 844 technician journey
(time, parts, inspection, closeout, cannot-close, forbidden-field matrix),
draft-only AI review, manager invoice denial, and finance-only idempotent draft
invoicing. Offline IndexedDB helpers stay gated off. The stock race gate uses
ten concurrent calls across five authenticated sessions because concurrency is
a transport-level invariant rather than a single-browser interaction.
The synthetic Service Manager receives Stock User but deliberately receives no
Accounts role. It also verifies the standard-record distribution and light
manufacturing configured demos expose their deterministic shortage states in
both permission-scoped API data and visible standard ERPNext forms.

Authentication state, traces, videos, screenshots, reports, and `node_modules`
are ignored and must never be committed. This automated suite is release
evidence, not human user-acceptance testing; the signed human UAT gate remains
separate.

Sources:

- <https://playwright.dev/docs/docker>
- <https://playwright.dev/docs/auth>
