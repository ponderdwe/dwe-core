### Requirement: Alembic manages all schema migrations
dwe-hub SHALL use Alembic for all database schema changes. The `run_migrations()` function in `database.py` SHALL be removed.

#### Scenario: run_migrations removed from database.py
- **WHEN** reviewing `database.py` after the change
- **THEN** no `run_migrations` function exists; the file contains only engine creation and session management

#### Scenario: Migration history exists as versioned files
- **WHEN** reviewing `alembic/versions/`
- **THEN** one or more `.py` migration files exist representing the complete schema history

### Requirement: entrypoint.sh runs alembic upgrade head before app start
`entrypoint.sh` SHALL run `alembic upgrade head` as the first step before starting the Flask app.

#### Scenario: Migrations run on container start
- **WHEN** the dwe-hub Docker container starts
- **THEN** `alembic upgrade head` runs and exits 0 before Flask starts

#### Scenario: Failed migration prevents app start
- **WHEN** `alembic upgrade head` exits non-zero
- **THEN** the container exits with an error before Flask starts, making the failure visible

### Requirement: Migrations are idempotent for already-applied versions
Running `alembic upgrade head` on a database that is already at head SHALL be a no-op.

#### Scenario: Re-running upgrade is safe
- **WHEN** `alembic upgrade head` is run on a database at head
- **THEN** it exits 0 with "already at head" message, no schema changes made
