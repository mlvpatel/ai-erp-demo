# Disposable recovery stack

This separate Terraform root creates a temporary MariaDB instance, EFS file
system, security groups, log group, and restore task definition. It consumes
only non-secret production outputs and an AWS-managed database credential. The
protected recovery workflow gives each run a separate encrypted state key,
validates the logical backup inside this isolated stack, and destroys every
temporary resource even when validation fails. It never restores into the
production RDS instance or production EFS file system.
