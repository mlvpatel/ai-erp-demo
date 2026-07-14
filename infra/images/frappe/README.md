# Production Frappe image contract

Both Dockerfiles require reviewed upstream base images supplied as immutable
`@sha256:` references. The backend build context is the repository root. It
adds only the two implemented custom apps and the fixed runtime command; it does
not patch or vendor Frappe or ERPNext. The frontend remains the reviewed
upstream Frappe nginx image because the current apps add no compiled frontend
assets.

Build into ECR, scan the images, and pass the resulting ECR digest references
to Terraform. Tags are never accepted by the balanced-pilot variables.

The `configure`, `migrate`, `backup`, and `restore` modes are on-demand tasks. `configure`
requires an already provisioned tenant site, writes shared connection endpoints,
and selects that site; it never creates a site or database. `migrate` also
requires the existing tenant site. `backup` creates the
site-scoped logical backup on encrypted EFS; promotion to the SSE-KMS S3 bucket
remains an operator-controlled recovery step until a tested uploader is added.
`restore` additionally requires `ALLOW_RESTORE=YES` and an operator-selected
database backup path. No task is scheduled or run by Terraform.
