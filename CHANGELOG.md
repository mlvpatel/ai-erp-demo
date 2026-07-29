# Changelog

Dates use `YYYY-MM-DD`.

## Unreleased

### Demo Version product packaging

- Labelled the local synthetic product as Demo Version `2026.07.30-demo` in
  `config/demo-version.json`.
- Added facilitator loop graph and pin-accurate stack/AI boundary docs under
  `docs/product/demo-version-*.md`, linked from README, AGENTS, docs index,
  roadmap, and the design-partner facilitator runbook.
- Scorecard lever `governed-demo-to-pilot-release` evidence paths updated for
  those docs; demo average remains 7.4 / 10.

## Release policy

No public release should be tagged until the root `LICENSE` decision is complete,
`scripts/check-open-source-ready.sh --release` passes, GitHub CI passes, and a
fresh clone can complete the local demo runbook.
The detailed versioning and release checklist lives in
`docs/workflows/release-process.md` and is validated by
`python3 scripts/check-release-policy.py`.
