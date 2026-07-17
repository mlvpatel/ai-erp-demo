# ADR-0008: Use pinned Playwright for browser smoke tests

- Status: Accepted
- Date: 2026-07-14
- Owners: AI ERP Demo

## Context

Unit and Frappe integration tests do not prove that role-authenticated browser
sessions can load the actual Desk routes. The service workflow needs a small,
repeatable browser gate without committing cookies, credentials, screenshots,
or customer data.

## Decision

Use `@playwright/test` 1.61.0 and the matching digest-pinned official Chromium
container. Prepare only synthetic users and work orders on an explicitly
enabled `.localhost` site. Run serially with isolated browser contexts, log in
through Frappe's API, load real Desk routes, and verify permission-scoped list
results from the same authenticated browser context.

Keep credentials in the local environment, never in the package or stored
browser state. Ignore authentication state, traces, video, screenshots,
reports, `node_modules`, and test results. Retain failure media only as private
CI evidence with a short deletion period. The smoke does not grant finance
permissions, execute stock/invoice actions, or replace human UAT.

## Consequences

- Browser and package versions move together and updates require E2E proof.
- The image is large but avoids browser drift across contributor machines.
- A blocked browser test blocks pilot readiness; it does not justify weakening
  roles, exposing a public test site, or storing credentials.

## Sources

- Playwright Docker version-matching and CI guidance:
  <https://playwright.dev/docs/docker>
- Playwright authentication-state security guidance:
  <https://playwright.dev/docs/auth>
