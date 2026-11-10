# AWS backup setup

This stack configures **database backups only**. It does not create or deploy the
Life EPM application, PostgreSQL, a domain, TLS, or AWS credentials. Those
resources must exist in the chosen AWS account and region before this stack is
useful.

The CloudFormation plan creates a daily AWS Backup job at 02:00 UTC and retains
recovery points for 35 days. Only resources carrying the configured selection
tag are included.

## Deploy the backup plan

Install and configure the AWS CLI locally, select the intended account and
region, and review the change set with the account administrator. Then run from
the repository root:

```powershell
aws cloudformation deploy `
  --template-file deploy/aws/backup.yaml `
  --stack-name life-epm-backups `
  --capabilities CAPABILITY_NAMED_IAM
```

Tag the production RDS database with `life-epm-backup=daily` (or use the
parameter values configured for the stack). Do not tag a development database
unless it should also be backed up. Ensure RDS encryption at rest is enabled,
and verify that a completed recovery point appears in AWS Backup after the first
scheduled run.

## Restore test

Use the AWS Backup console to restore a recovery point to a **separate
temporary database** in the same approved network. Never restore over the live
database as a test. Restrict access to the restored instance, verify the
application data and Alembic revision, then delete the temporary instance after
the test is signed off. Record the test date and outcome in the church's
operations log.

## Local Docker backup

From the project root, run:

```powershell
.\scripts\backup-postgres.ps1
```

The script writes a timestamped custom-format dump to `backups\`. Store a copy
outside the computer hosting Docker, protect it as sensitive church data, and
periodically verify restoration in a separate test database.
