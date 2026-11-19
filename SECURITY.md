## FINPATH Security Architecture

### Authentication and authorization

- Passwords are hashed with bcrypt through Passlib and are never stored or returned in plaintext.
- JWT bearer tokens use the configured secret, algorithm, and expiration settings.
- Invalid, malformed, expired, and inactive-account credentials return safe `401` responses.
- Administrator access is enforced by the backend through role dependencies.
- Assessment, prediction, recommendation, dashboard, and user analytics queries are scoped to the authenticated user. System analytics are administrator-only.

### Input, database, and error handling

- Pydantic schemas reject invalid values and unexpected fields at API boundaries.
- New assessment submissions use an explicit frontend/ML field allowlist, flat scalar values, and numeric range checks. Existing stored assessment JSON is still returned to its owner without being rewritten or revalidated.
- Database access uses SQLAlchemy query parameterization; no user input is interpolated into SQL.
- Validation errors omit submitted values. Unexpected exceptions return a generic `500`; logs contain the exception class but not its message or traceback.
- Resource ownership failures intentionally return `404` to avoid revealing another user's records.
- Password reset, bootstrap repair, and administrator account-state changes increment the user's token version so previously issued access tokens stop working.
- Login, password-reset requests, and public administrator bootstrap have bounded process-local rate limits keyed by a secret-derived identifier. These limits are not shared across workers or replicas and are reset by process restarts; use an owner-approved shared/edge limiter before scaling horizontally.

### HTTP and CORS hardening

- CORS origins are configuration-driven. Production rejects wildcard origins and debug mode.
- Production also requires HTTPS CORS/frontend URLs and a PostgreSQL psycopg URL with TLS (`sslmode=require` is added when no stronger SSL mode is configured). SQL echo is rejected in production.
- API methods and headers are restricted to the methods and headers used by the backend.
- Responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a restrictive Content Security Policy. HSTS is enabled only when `ENVIRONMENT=production`.

### Secrets and ML artifacts

- Secrets must be supplied through environment configuration. `.env` is ignored by Git; `.env.example` contains placeholders only.
- ML artifact paths come from trusted configuration, are local-file validated, and cannot be supplied by API clients. Before deserialization, model files are checked against the reviewed `models/v1/artifact_manifest.json`; retraining updates this manifest. The manifest is a checksum control, not a digital signature or proof of artifact provenance.
- Production startup does not create database tables; the deployment command must apply Alembic migrations before starting the API.

### Administrator account lifecycle

- After applying database migrations, an operator creates the initial administrator with `python -m backend.create_admin`, using the same deployment database configuration as the API. The command prompts for credentials and only runs while there are zero active administrators.
- An active administrator creates the second administrator with `POST /api/v1/auth/admins` and a bearer token. Public registration remains user-only.
- The API checks the active-admin count for a clear conflict response; the Alembic database trigger is authoritative for concurrent writes. Do not provision admins by manually editing the role column.
- Render and the Docker image run Alembic before starting Uvicorn. A deployment must also provide a persistent PostgreSQL `DATABASE_URL`; the checked-in Render blueprint does not provision or attach a database itself.
- The local Compose PostgreSQL and pgAdmin ports bind only to loopback and require operator-supplied passwords; do not reuse production credentials for local development.

### Production-owner decisions and evidence still required

- Confirm the lawful purposes and bases for processing, privacy notice content, consent requirements, automated-decision transparency/human review, and data-subject request procedures with qualified privacy/legal reviewers. No privacy policy or retention period is inferred here.
- Approve retention and deletion/anonymization rules before enabling account deletion; current account cascades would remove related assessment, prediction, and recommendation records.
- Approve the minimum fields administrators need to see in record/user-management endpoints and a browser session strategy. The frontend currently stores access tokens in Web Storage; moving to HttpOnly cookies requires a compatible CSRF/session design.
- Verify database-provider encryption at rest, backup encryption/access/retention, recovery testing, log access/retention, and incident-response ownership directly with the infrastructure operators. These controls are not confirmed by application source.
- The Docker build path is not the Render blueprint's deployment runtime. Its build context now excludes `data/` and `reports/`; the model artifacts and application code remain included.

### Dependencies and reporting

Authentication dependencies are pinned in the requirements files, including `bcrypt<5` for compatibility with Passlib 1.7.4. The current test environment emits a Starlette/httpx deprecation warning from Starlette's TestClient integration recommending `httpx2`; tests remain functional. No upgrade was made because the repository's declared FastAPI/Starlette/httpx pins require a compatibility decision as a group, not a blind single-package upgrade.

To report a security issue, do not disclose it publicly first. Contact the project maintainers with reproduction details and avoid including real credentials or personal data.
