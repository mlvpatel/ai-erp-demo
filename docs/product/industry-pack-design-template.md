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

---

## Illustrative example: commercial refrigeration maintenance

This section is an illustrative walkthrough demonstrating how to complete the template above for an exploratory domain. It is an illustrative example only and does not claim a new implemented industry pack or alter existing repository boundaries in [config/industry-packs.json](../../config/industry-packs.json).

### 1. Industry and user

- Industry: Commercial refrigeration and cold-chain HVAC/R maintenance.
- Primary business size: Regional service contractors with 15 to 60 certified technicians.
- Primary user role: Refrigeration Service Technician.
- Secondary user roles: Service Dispatcher, Maintenance Contracts Manager, Compliance Inspector.
- Design partner or evidence source: Illustrative exploratory persona based on cold storage service contracts.

### 2. Business job

> When a commercial walk-in freezer triggers an emergency temperature alarm, the service technician needs to inspect refrigerant circuits, log pressures and subcooling, and replace failed expansion valves, so that food inventory remains safe and compliance logs are updated without unauthorized financial posting.

### 3. First proof workflow

Start state: Emergency breakdown request recorded with alarm telemetry and asset identifier.

End state: Leak test verified, refrigerant added, stock deducted via standard Material Issue, and draft service summary submitted for manager sign-off.

Workflow steps:

1. Dispatcher schedules certified technician based on F-gas certification and van stock availability.
2. Technician completes digital pre-work hazard check and logs suction and discharge operating pressures.
3. Technician replaces thermostatic expansion valve and records recovery cylinder weights.
4. Service manager reviews logged pressures and confirms parts deduct before invoicing handoff.

### 4. ERPNext reuse map

| Need | ERPNext module/record reused | Configuration first? | Custom gap |
| --- | --- | --- | --- |
| Customer accounts | Selling (`Customer`) | Yes | Standard customer record. |
| Refrigeration equipment | Assets (`Asset`) | Yes | Standard asset tracking. |
| Spare parts and gas cylinders | Stock (`Item`, `Stock Entry`) | Yes | Idempotent parts issue. |
| Work billing | Accounts (`Sales Invoice`) | Yes | Finance-separated draft invoice. |

### 5. Custom behavior

- EPA/F-gas cylinder tare weight and net refrigerant recovery balance tracking.
- Mandatory operating pressure and superheat/subcooling validation before closeout.

### 6. AI assistance

Allowed AI behavior:

- [x] Retrieve (read historical pressure logs on the specific refrigeration asset)
- [x] Classify (categorize alarm telemetry into sensor failure vs thermodynamic loss)
- [x] Summarize (draft diagnostic notes for the client facility manager)
- [x] Draft (generate proposal draft of work performed)
- [x] Explain exception (explain why subcooling values diverge from target range)
- [x] Propose action for human approval (draft follow-up maintenance recommendation)

Forbidden AI behavior:

- [x] Direct financial posting
- [x] Direct inventory posting
- [x] Direct payroll mutation
- [x] Direct permission/access mutation
- [x] Direct compliance filing or regulated external submission

### 7. Permissions and approval

| Role | Can create | Can update | Can approve | Cannot do |
| --- | --- | --- | --- | --- |
| Refrigeration Technician | Pressure logs, part requests | Assigned work order notes | Pre-work safety check | Post stock, invoice, view margin |
| Service Manager | Work orders, exceptions | Scheduling, priority | Closeout, parts issue | Bypass finance invoice role |
| Accounts User | Sales Invoice drafts | Billing terms | Invoice submission | Modify technician field entries |

### 8. Records and contracts

New DocTypes:

- `Refrigerant Log Entry`: Child table logging cylinder serials, gas type, charge added, and recovery weight.

ERPNext DocTypes reused:

- `Asset`, `Customer`, `Item`, `Warehouse`, `Stock Entry`, `Sales Invoice`.

External APIs or events:

- `service-operations-v1.yaml` event schema for work order status changes.

### 9. Synthetic fixtures

Synthetic fixture customer (Supermarket Chain A), synthetic walk-in condenser asset, and non-inventory cylinder records with fictitious tare weights.

### 10. Acceptance tests

- [x] Non-admin technician completes pressure log and closeout without finance visibility.
- [x] Unauthorized technician is blocked from posting stock issue.
- [x] Incomplete leak test exception blocks invoice-ready transition.
- [x] Idempotent parts issue cannot duplicate refrigerant stock deductions.
- [x] AI closeout proposal is cited, immutable, and draft-only.

### 11. Exit decision

- [x] Needs more discovery (keep in exploratory discovery before app creation).

