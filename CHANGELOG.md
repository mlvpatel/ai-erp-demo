# Changelog

Dates use `YYYY-MM-DD`.

## Unreleased

No public release has been tagged. The project currently ships as a private,
zero-cost, local synthetic demo of a governed, AI-assisted field-service ERP.

## Release policy

No public release should be tagged until the root `LICENSE` decision is complete,
`scripts/check-open-source-ready.sh --release` passes, GitHub CI passes, and a
fresh clone can complete the local demo runbook.
The detailed versioning and release checklist lives in
`docs/workflows/release-process.md` and is validated by
`python3 scripts/check-release-policy.py`.
