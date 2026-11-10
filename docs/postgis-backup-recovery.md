# Encrypted database backups for the dedicated Rahsu stack

The PostGIS DB contains sensitive trip histories and user/obstacle moderation
records. Backup files must be encrypted before leaving the database container.

## Setup

Generate a public/private age key pair using age-keygen on a **trusted host**.
Store the private key away from the Rahsu server and never commit it.
Copy only the **public recipient** into a protected deployment environment:

```bash
# Set BACKUP_AGE_RECIPIENT=age1... through the operator's shell/environment.
# A recipient is public metadata, but its matching identity file is secret.
bash scripts/backup_postgis.sh /srv/rahsu-backups
```

The script streams `pg_dump --format=custom` through authenticated `age`
encryption without creating a plaintext dump file on the host. Files are
written with restrictive permissions and an adjacent SHA256 manifest; failed
pipelines do not publish a completed snapshot. Back up and retain the
manifest and encrypted file together.

## Integrity verification (non-destructive)

```bash
# Set BACKUP_AGE_IDENTITY_FILE=/secure/off-server/location/age-identity.txt
bash scripts/verify_postgis_backup.sh /srv/rahsu-backups/<snapshot>.dump.age
```

Verification checks SHA256, age authentication and PostgreSQL custom dump
structure via `pg_restore --list`; no production table is restored, deleted
or overwritten. The verification host must have access to an appropriate
PostgreSQL `pg_restore` command through the Rahsu Docker Compose database
container. Perform separate **full restore drills to a disposable,
isolated database** before declaring disaster recovery tested.

## Operational rules

- Create a regular schedule with a systemd timer or operator scheduler after
  checking available storage and monitoring; **no background scheduler is
  installed by this repository**.
- Rotate snapshots according to retention and keep encrypted off-site copies.
- Test that the age private identity is recoverable after a host failure.
- Never store the age secret identity under the Git repo, inside `.env` or in
  a public issue. The public recipient can be provided as an environment
  variable at execution time.
- Backup scripts use the `db` service of *this* Compose project only. Do
  not run them in another project's working directory.
