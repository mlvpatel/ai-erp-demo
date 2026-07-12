# Industry pack design template

Copy this outline into `docs/discovery/` before creating a new industry app or
expanding a reserved industry folder. Keep the answers short and evidence-based.

## 1. Industry and user

- Industry:
- Primary business size:
- Primary user role:
- Secondary user roles:
- Design partner or evidence source:

## 2. Business job

Describe the job in one sentence:

> When ..., the user needs to ..., so that ...

## 3. First proof workflow

Start state:

End state:

Workflow steps:

1.
2.
3.

## 4. ERPNext reuse map

| Need | ERPNext module/record reused | Configuration first? | Custom gap |
| --- | --- | --- | --- |
|  |  |  |  |

## 5. Custom behavior

Only list behavior that cannot be met safely through ERPNext configuration,
custom fields, workflows, permissions, reports, or print formats.

- 

## 6. AI assistance

Allowed AI behavior:

- [ ] Retrieve
- [ ] Classify
- [ ] Summarize
- [ ] Draft
- [ ] Explain exception
- [ ] Propose action for human approval

Forbidden AI behavior for this pack:

- [ ] Direct financial posting
- [ ] Direct inventory posting
- [ ] Direct payroll mutation
- [ ] Direct permission/access mutation
- [ ] Direct compliance filing or regulated external submission

## 7. Permissions and approval

| Role | Can create | Can update | Can approve | Cannot do |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

## 8. Records and contracts

New DocTypes:

- 

ERPNext DocTypes reused:

- 

External APIs or events:

- 

## 9. Synthetic fixtures

Describe the non-customer fixture data needed for tests and demos.

## 10. Acceptance tests

- [ ] Non-admin user can complete their allowed steps.
- [ ] Unauthorized role is blocked from restricted transaction.
- [ ] Required exception or approval blocks unsafe progression.
- [ ] Idempotent action cannot duplicate external/ERP transaction.
- [ ] AI proposal is cited, immutable, and draft-only.

## 11. Exit decision

- [ ] Ready to generate or expand a Frappe app.
- [ ] Needs more discovery.
- [ ] Should be handled through ERPNext configuration only.

