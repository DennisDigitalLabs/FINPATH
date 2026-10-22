# FINPATH API Documentation

## Overview

FINPATH provides a RESTful API implemented with FastAPI. The API supports authentication, financial assessment, risk prediction, recommendations, dashboard information, and analytics.

## Base URL

Development:

`http://localhost:8000`

Production:

`https://finpath-backend.onrender.com`

## API Documentation

When the FastAPI application is running, interactive API documentation is available through:

- `/docs` — Swagger UI
- `/redoc` — ReDoc

## Main API Areas

### Authentication

Provides user registration, authentication, and authorization.

- `POST /api/v1/auth/register` creates a normal user; client-supplied role fields are rejected.
- `POST /api/v1/auth/login` authenticates active users, including administrators.

Administrator API access requires an active account with the `admin` database role and a configured `ADMIN_OWNER_EMAIL`. The owner email setting must be present or administrator endpoints fail closed. Public registration never creates administrator accounts.

Bootstrap the first configured owner only from an authenticated, trusted backend operator shell. Set `ADMIN_OWNER_EMAIL` and a temporary random `ADMIN_BOOTSTRAP_TOKEN` of at least 32 characters in the backend environment, apply the normal deployment migrations, then run `python -m backend.create_admin`. The command requires the configured email and token, validates the email and password, and stores only a password hash. It cannot create an owner for another email. Once the configured account is active with the `admin` role, the command refuses further bootstrap attempts. Remove `ADMIN_BOOTSTRAP_TOKEN` from the deployment environment after successful setup.

If an account already exists for the configured owner email but is inactive or has an inconsistent role, the same trusted-shell command supports recovery only after the operator enters the bootstrap token and types `REPAIR OWNER`; it sets a new password, reactivates only that configured account, and grants it the admin role. It refuses recovery if another active admin account would make the state ambiguous; it does not revoke or alter other accounts. Resolve duplicate case-insensitive owner email records through an authorized database operator before retrying. Do not add a public bootstrap route or use public registration to claim admin access.

For Render setup, configure `ADMIN_OWNER_EMAIL` to the intended owner email and set a securely generated, temporary `ADMIN_BOOTSTRAP_TOKEN` (at least 32 characters) in the API service environment. Open the API web service's authenticated Shell, run `python -m backend.create_admin`, enter the configured owner email, the token, the owner's name, and a strong password twice. After the command reports success, remove `ADMIN_BOOTSTRAP_TOKEN` from the Render environment and allow the service to restart. Sign in at the frontend login page using the configured owner email and password, then open Admin. This setup changes only the configured owner account and does not reset or migrate the database.

Password-reset email delivery requires `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_FROM_EMAIL` to be configured. `FRONTEND_URL` must point to the deployed frontend so reset links return to the correct site. If SMTP is missing or delivery fails, the API returns `503` rather than reporting a false success.

### Assessments

Supports:

- Creating financial assessments
- Retrieving assessments
- Retrieving an individual assessment
- Updating assessments
- Deleting assessments

### Predictions

Supports:

- Generating financial inclusion risk predictions
- Retrieving prediction results
- Retrieving predictions associated with an assessment

### Recommendations

Provides personalized recommendations based on assessment and prediction results.

### Dashboard

Provides user-oriented financial risk and assessment information for dashboard presentation.

### Analytics

Provides aggregated information required by the analytics interface.

- `GET /api/v1/analytics/system` returns the existing system totals and distributions and requires configured administrator-owner authorization.

### Administration

Every endpoint in this section requires a bearer token for an active account whose role is `admin`. If `ADMIN_OWNER_EMAIL` is missing, administrator endpoints fail closed with `503`. Bootstrap the first configured owner through the authenticated operator-shell process described above. After signing in, an authorized administrator can create the second administrator through the protected dashboard; the database migration enforces the two-active-admin cap even for simultaneous requests.

- `GET /api/v1/admin/users` lists account summaries. Optional `search` matches full name or email; `page` defaults to `1`, and `page_size` defaults to `10` with a maximum of `100`. The response contains `items`, `total`, `page`, and `page_size`. Password hashes and credentials are never included.
- `POST /api/v1/admin/users` creates an active standard user account from `full_name`, `email`, and `password`, using the same validation and password hashing as public registration. It returns `201` and a safe account summary; duplicate email addresses return `409`. The request rejects extra fields, including `role`, so this cannot create or promote administrators. The created user can sign in through `POST /api/v1/auth/login`.
- `POST /api/v1/admin/admins` creates an active administrator account from `full_name`, `email`, and `password`. It requires an authenticated administrator, uses the standard email/password validation and password hashing, and returns a safe account summary. When two active administrators already exist, it returns `409` with a message advising the requester to contact the system administrator. The database trigger is the concurrency-safe final guard.
- `PATCH /api/v1/admin/users/{user_id}/status` takes `{"is_active": true}` or `{"is_active": false}` and persists the account's active status. Deactivation prevents subsequent authentication. It does not change account roles; administrator accounts cannot be managed by this endpoint. Missing users return `404`; protected administrator accounts return `409`.
- `GET /api/v1/admin/health` performs a database connectivity query and returns backend/database status and check time. A failed database check returns `503` without exposing connection details.

The admin dashboard uses the protected system analytics endpoint and these administration endpoints. Account search is paginated, and active status can be changed and reversed for standard users. Admin creation is a separate form and endpoint from standard-user creation. No user deletion, password reset, or role escalation through the standard-user form is exposed.
## Error Handling

The API uses standard HTTP status codes and structured JSON responses. Authentication and authorization failures are rejected appropriately, while invalid input is handled through Pydantic validation.

## Security

The API uses password hashing, JWT-based authentication, ownership checks, restricted CORS configuration, production security validation, and security headers.

## Database

SQLAlchemy is used as the ORM and Alembic is used for database migrations.

## Machine Learning

The prediction service communicates with the machine-learning layer through defined adapters and model artifacts. The API is designed to return an appropriate service error when the required model artifact is unavailable.

## Deployment

The backend is designed for deployment on Render using the project's `render.yaml` configuration.
