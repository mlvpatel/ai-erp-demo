# Tests

- `contract/`: prove external API and event compatibility.
- `e2e/`: exercise complete ERP user workflows.
- `fixtures/`: synthetic tenant, customer, product, and document data only.
- `performance/`: synthetic record-volume profiles and the Docker-backed,
  rollback-only scaled smoke command. Start with
  `performance/service-operations-load-profile.example.json`; the smoke check
  is explicitly not a full-profile benchmark and cannot support public
  performance or scalability claims.

Run contract tests from the repository root after installing the relevant
service package:

```sh
python -m pip install ./services/ai_control_plane
python -m unittest discover -s tests/contract -v
```

The broader quality-gate workflow is documented in
`docs/workflows/quality-gates.md`.

Run the synthetic performance smoke check after the local site is migrated:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh performance-smoke
```
