# Chapter Four: System Design and Implementation

## 4.1 Introduction

This chapter describes the architecture, components, database design, machine-learning integration, frontend, backend, and implementation of FINPATH.

## 4.2 System Architecture

FINPATH follows a layered architecture consisting of:

1. Frontend presentation layer
2. FastAPI backend/API layer
3. Business-service layer
4. Machine-learning layer
5. Database layer

The frontend communicates with the backend through REST API endpoints.

## 4.3 Frontend

The frontend contains interfaces for:

- Landing page
- Registration
- Login
- Assessment
- Prediction
- Dashboard
- Recommendations
- Analytics
- Profile
- Administration

The interface is designed to support desktop, tablet, and mobile screen sizes.

## 4.4 Backend

The backend is implemented with FastAPI and provides API routes for authentication, assessments, predictions, recommendations, dashboard data, and analytics.

Business logic is organized into services to reduce coupling between API routes and implementation details.

## 4.5 Database

SQLAlchemy provides ORM functionality while Alembic manages database migrations.

The database stores user, assessment, prediction, and recommendation-related information required by the system.

## 4.6 Machine-Learning Integration

The machine-learning integration separates model-specific implementation from the API layer.

Input adapters transform assessment information into the format required by the model. Output adapters transform model results into application-level prediction results.

Model artifacts are loaded through a dedicated artifact-loading mechanism.

## 4.7 Explainability

Prediction results are designed to support understandable explanations of the factors contributing to financial risk.

SHAP-based analysis is used during model analysis and explainability development.

## 4.8 Security

Security controls include:

- Password hashing
- JWT authentication
- JWT expiration validation
- Ownership and authorization checks
- Restricted CORS
- Security headers
- Production configuration validation
- Environment-based secrets

## 4.9 Deployment

The application is configured for deployment on Render.

The backend is deployed as a Python web service, while the frontend is configured as a static web service in the Render Blueprint.

## 4.10 Implementation Summary

FINPATH integrates the user interface, API, database, machine-learning model, explainability components, and recommendation functionality into a unified financial inclusion decision-support platform.
