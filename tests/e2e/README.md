# Browser E2E

The browser smoke uses Playwright 1.61.0 in its matching official container. It
creates only synthetic `.localhost` users and work orders, authenticates each
role in an isolated browser context, opens the real Frappe Desk routes, and
checks permission-scoped API results from that browser session.

Run after the local Bench web process is available:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh e2e-test
```

The helper prepares local users, runs Chromium in the Compose network, and
removes the test container. Authentication state, traces, videos, screenshots,
reports, and `node_modules` are ignored and must never be committed. The test
does not grant a Service Manager standard accounting permissions, draft an
invoice, or claim full user acceptance. Finance role separation and the full
technician/dispatcher/manager/finance walkthrough remain human UAT gates.

Sources:

- <https://playwright.dev/docs/docker>
- <https://playwright.dev/docs/auth>
