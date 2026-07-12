# Performance tests

This directory holds synthetic, non-customer performance planning artifacts.
Do not commit production exports, real logs, trace exports, dashboard
screenshots, database dumps, or client identifiers here.

Start with `service-operations-load-profile.example.json`. It defines the first
service-operations load profile: record volumes, concurrency assumptions,
scenario IDs, target latency classes, and safety evidence required before a
public performance claim.

Real benchmark results belong in private deployment evidence unless they are
fully sanitized and approved for publication.
