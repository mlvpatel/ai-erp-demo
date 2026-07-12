# Tests

- `contract/`: prove external API and event compatibility.
- `e2e/`: exercise complete ERP user workflows.
- `fixtures/`: synthetic tenant, customer, product, and document data only.
- `performance/`: realistic record-volume and concurrency checks.
  Start with `performance/service-operations-load-profile.example.json` before
  making public performance or scalability claims.

Run contract tests from the repository root after installing the relevant
service package:

```sh
python -m pip install ./services/ai_control_plane
python -m unittest discover -s tests/contract -v
```

The broader quality-gate workflow is documented in
`docs/workflows/quality-gates.md`.
