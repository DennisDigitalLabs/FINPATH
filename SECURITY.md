## FINPATH Security Architecture

### Authentication and authorization

- Passwords are hashed with bcrypt through Passlib and are never stored or returned in plaintext.
- JWT bearer tokens use the configured secret, algorithm, and expiration settings.
- Invalid, malformed, expired, and inactive-account credentials return safe `401` responses.
- Administrator access is enforced by the backend through role dependencies.
- Assessment, prediction, recommendation, dashboard, and user analytics queries are scoped to the authenticated user. System analytics are administrator-only.

### Input, database, and error handling

- Pydantic schemas reject invalid values and unexpected fields at API boundaries.
- Database access uses SQLAlchemy query parameterization; no user input is interpolated into SQL.
- Unexpected exceptions return a generic `500` response without stack traces, SQL, filesystem paths, credentials, or hashes.
- Resource ownership failures intentionally return `404` to avoid revealing another user's records.

### HTTP and CORS hardening

- CORS origins are configuration-driven. Production rejects wildcard origins and debug mode.
- API methods and headers are restricted to the methods and headers used by the backend.
- Responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and a restrictive Content Security Policy. HSTS is enabled only when `ENVIRONMENT=production`.

### Secrets and ML artifacts

- Secrets must be supplied through environment configuration. `.env` is ignored by Git; `.env.example` contains placeholders only.
- ML artifact paths come from trusted configuration, are local-file validated, and cannot be supplied by API clients. The default predictor fails closed with `503` when unavailable.

### Administrator account lifecycle

- After applying database migrations, an operator creates the initial administrator with `python -m backend.create_admin`, using the same deployment database configuration as the API. The command prompts for credentials and only runs while there are zero active administrators.
- An active administrator creates the second administrator with `POST /api/v1/auth/admins` and a bearer token. Public registration remains user-only.
- The API checks the active-admin count for a clear conflict response; the Alembic database trigger is authoritative for concurrent writes. Do not provision admins by manually editing the role column.
- Render and the Docker image run Alembic before starting Uvicorn. A deployment must also provide a persistent PostgreSQL `DATABASE_URL`; the checked-in Render blueprint does not provision or attach a database itself.
- The local Compose PostgreSQL and pgAdmin ports bind only to loopback and require operator-supplied passwords; do not reuse production credentials for local development.

### Dependencies and reporting

Authentication dependencies are pinned in the requirements files, including `bcrypt<5` for compatibility with Passlib 1.7.4. The current test environment emits a Starlette/httpx deprecation warning from Starlette's TestClient integration recommending `httpx2`; tests remain functional. No upgrade was made because the repository's declared FastAPI/Starlette/httpx pins require a compatibility decision as a group, not a blind single-package upgrade.

To report a security issue, do not disclose it publicly first. Contact the project maintainers with reproduction details and avoid including real credentials or personal data.
