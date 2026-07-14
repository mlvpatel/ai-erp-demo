# Quality gates

Use these gates to decide whether a change is ready for a pull request, a demo,
or a public release. Keep the gate proportional to the change: documentation
edits do not need the full Frappe integration stack, but ERP transaction changes
do.

## Static gate

Run from the repository root:

```sh
scripts/run-quality-gates.sh
```

Equivalent helper command:

```sh
scripts/dev.sh quality
```

This checks:

- open-source readiness,
- repository structure consistency,
- publication source guardrails,
- publication secret and sensitive-data scan,
- reproducible development pins,
- dependency update policy consistency,
- upstream upgrade readiness consistency,
- Python lint policy consistency,
- shell syntax,
- developer helper smoke output,
- local generated artifact counting,
- local Markdown links,
- contract catalog consistency,
- contract lifecycle/versioning consistency,
- integration and connector safety consistency,
- operations and recovery readiness consistency,
- observability readiness consistency,
- performance readiness consistency,
- AI data-boundary consistency,
- AI workflow registry consistency,
- tenant isolation consistency,
- migration safety consistency,
- GitHub repository metadata consistency,
- GitHub Actions workflow consistency,
- GitHub label manifest consistency,
- first public issue manifest consistency,
- MVP acceptance evidence consistency,
- authorization and approval matrix consistency,
- transaction safety invariant consistency,
- audit evidence consistency,
- fresh-clone demo runbook and `demo-info` output-safety consistency,
- public demo script consistency,
- release-readiness blocker manifest consistency,
- release policy and versioning consistency,
- owner-decision template consistency,
- license metadata reconciliation consistency,
- industry-pack manifest consistency,
- industry-pack lifecycle consistency,
- credential-free AWS production-IaC invariants,
- synthetic service-pilot evidence and pending-gate consistency,
- public claim/release-blocker consistency,
- Python syntax for custom apps, the AI control plane, and contract tests.

## Python lint gate

GitHub CI runs this as the required `Python lint` check. The version matches
both custom-app pre-commit configurations, and cache writes are disabled so the
repository-structure gate sees no generated root entry.

```sh
python -m pip install ruff==0.14.10
ruff check --no-cache apps/ services/
```

## Control-plane gate

Run when changing `services/ai_control_plane/`, `contracts/openapi/`, or the
Frappe code that calls the control plane:

```sh
python -m pip install ./services/ai_control_plane
python -m unittest discover -s services/ai_control_plane/tests -v
python -m unittest discover -s tests/contract -v
```

The local Python interpreter must satisfy the repository requirement in
`services/ai_control_plane/pyproject.toml`. If the host Python is older, use the
Docker-backed `scripts/dev.sh control-plane-test` and
`scripts/dev.sh contract-test` helpers instead.

In the Docker dev stack, the equivalent contract-test path is:

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace frappe \
  python -m pip install ./services/ai_control_plane

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace frappe \
  python -m unittest discover -s services/ai_control_plane/tests -v

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace frappe \
  python -m pip install ./services/ai_control_plane

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace frappe \
  python -m unittest discover -s tests/contract -v
```

## ERP service workflow gate

Run when changing `apps/ai_erp_core/`, `apps/ai_erp_service/`, fixtures,
permissions, workflows, or any code that touches stock, invoices, closeout, or
AI Proposal records:

```sh
docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost migrate

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost run-tests --app ai_erp_core \
  --test-category integration --failfast

docker compose --env-file development/.env \
  -f infra/compose/docker-compose.dev.yml exec \
  --workdir /workspace/development/frappe-bench frappe \
  bench --site ai-erp.localhost run-tests --app ai_erp_service \
  --test-category integration --failfast
```

This gate must prove:

- AI Proposal requesters cannot list or directly read another requester's proposal,
- Service Location creation enforces its required Customer link,
- non-admin technician scope,
- manager-only close/parts issue actions and finance-only invoice drafting,
- idempotent Stock Entry and draft Sales Invoice creation,
- draft-only cited AI proposal behavior,
- no AI approval side effect on ERP transactions.

GitHub CI does not currently execute this Docker-backed Frappe behavioral gate.
Accordingly, `implemented` in `config/mvp-acceptance.json` means the cited source
and evidence anchors are verified by the static gate; it does not mean the
behavior has been executed in CI. Run `scripts/dev.sh service-test` locally and
record its result for behavior-sensitive changes and releases. Run
`scripts/dev.sh e2e-test` for the pinned synthetic Chromium role/route smoke;
this browser smoke is not human UAT.

## Synthetic performance smoke gate

Run after migration when list/search, invoice drafting, or AI closeout behavior
changes:

```sh
AI_ERP_ENV_FILE=/tmp/ai-erp-ci.env scripts/dev.sh performance-smoke
```

The command uses a local-only, rollback-scoped synthetic database transaction.
It fails before writes outside a `.localhost` site or deterministic local
template control plane, and fails on latency or safety-invariant regression,
but its successful status is deliberately
`SMOKE_PASS_NOT_FULL_PROFILE`. Native link search, queue clearing, and the
profitability report are measured; true concurrent parts issue is executed by
the five-session browser suite and is reported here as `EXTERNAL_CROSS_SESSION_GATE`, so this gate
is not evidence for a public capacity claim. Database rollback does not cover
external effects; the local/template preflight prevents external provider use.

## Release gate

Run before a public release tag:

```sh
scripts/check-open-source-ready.sh --release
python3 scripts/check-release-readiness.py --strict
python3 scripts/check-release-policy.py
python3 scripts/check-owner-decisions.py --strict
python3 scripts/check-license-metadata.py --strict
scripts/check-publication-source.sh --strict
python3 scripts/check-publication-secrets.py
python3 scripts/check-upstream-upgrade-readiness.py
python3 scripts/check-operations-readiness.py
python3 scripts/check-observability-readiness.py
python3 scripts/check-performance-readiness.py
scripts/run-quality-gates.sh
```

Then run the control-plane and ERP service workflow gates above in a fresh clone
or clean local checkout. The release gate is intentionally blocked until the
root `LICENSE` is chosen and committed.

For the local service-operations demo path, see
`docs/runbooks/local-demo.md`.
