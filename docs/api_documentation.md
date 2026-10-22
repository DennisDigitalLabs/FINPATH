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

Administrator API access requires both the `admin` database role and an email matching the `ADMIN_OWNER_EMAIL` environment setting. If that setting is empty, administrator endpoints fail closed. There is no public API for creating additional administrator accounts.

Provision the configured owner through a trusted operator command: set `ADMIN_OWNER_EMAIL`, then run `python -m backend.create_admin` in an environment configured for the target database. The command can create the owner account or, after explicit confirmation, promote an existing active account with that exact email. If other active administrators exist, the operator must explicitly type `REVOKE` before their admin roles are removed. The command will not create or promote a different account or silently demote another administrator.

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
