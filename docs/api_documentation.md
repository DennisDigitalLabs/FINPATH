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
- `POST /api/v1/auth/admins` creates an active administrator and requires an active administrator bearer token. The body accepts `full_name`, `email`, and `password`; it does not accept a role. It returns `201` on success, `401` for missing/invalid credentials, `403` for a normal user, and `409` for a duplicate email or active-admin limit.

The initial administrator is created by a trusted operator after migrations are applied: run `python -m backend.create_admin` in an environment configured for the target database. The command prompts for the password and only creates an account when no active administrator exists.

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
