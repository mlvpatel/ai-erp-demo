# Production Frappe image contract

Both Dockerfiles require reviewed upstream base images supplied as immutable
`@sha256:` references. The backend build context is the repository root. It
adds only the two implemented custom apps and the fixed runtime command; it does
not patch or vendor Frappe or ERPNext. The frontend remains the reviewed
upstream Frappe nginx image because the current apps add no compiled frontend
assets.

Build into ECR, scan the images, and pass the resulting ECR digest references
to Terraform. Tags are never accepted by the balanced-pilot variables.

The `configure`, `migrate`, `backup`, and `restore` modes are operations tasks.
On a fresh EFS mount, `configure` creates the app registry and tenant site from
task-start secret injection, installs ERPNext and both custom apps, writes the
shared connection endpoints, and selects the site. A retry detects the existing
site and only verifies missing required apps, so it does not create a second
database. `migrate` requires the configured tenant site. `backup` creates the
site-scoped logical backup on encrypted EFS, uploads all four fresh artifacts
to the versioned SSE-KMS S3 bucket, verifies size and SHA-256 metadata, writes
the completion manifest last, and emits the backup-success metric. The AWS SDK
runs from an isolated hash-locked operations virtual environment. Production
Terraform schedules this task daily only after services are activated.
`restore` is a deletion-enforced drill, not a general production restore. It
accepts only a manifest-complete backup in the approved bucket and a generated
`restore-drill-*.internal` target, verifies every artifact before invoking the
official Bench restore interface, migrates, checks apps/roles/transaction
links, and runs `drop-site --no-backup --force` even after validation failure.
Terraform registers all operation tasks and schedules only backup; configure,
migrate, and restore remain explicitly invoked.
