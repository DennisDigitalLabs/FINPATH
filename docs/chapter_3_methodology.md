# Chapter Three: Methodology

## 3.1 Introduction

This chapter describes the methodology used to design, develop, test, and evaluate FINPATH.

## 3.2 Research Approach

The project followed an applied system-development approach. Data analysis and machine-learning techniques were combined with software engineering practices to develop an operational decision-support system.

## 3.3 Data

The project uses financial inclusion data relevant to the Kenyan context. Data preparation included cleaning, validation, transformation, feature engineering, and preparation of modelling datasets.

## 3.4 Data Preprocessing

The preprocessing workflow included:

1. Data acquisition
2. Data inspection
3. Data cleaning
4. Handling of relevant missing or invalid values
5. Feature transformation
6. Feature engineering
7. Target definition
8. Preparation of training and evaluation datasets

## 3.5 Exploratory Data Analysis

Exploratory Data Analysis was used to understand distributions, relationships, categorical variables, financial-service usage patterns, and potential factors associated with the target outcome.

Visualizations were produced to support interpretation of the dataset.

## 3.6 Machine-Learning Models

Multiple classification approaches were evaluated, including:

- Logistic Regression
- Random Forest
- XGBoost
- Baseline/dummy classification

Model performance was evaluated using appropriate classification metrics and validation procedures.

## 3.7 Model Evaluation

Evaluation included comparison of model performance using metrics such as accuracy, precision, recall, F1-score, ROC-AUC, and confusion matrices where applicable.

Cross-validation and model tuning were also used during the modelling process.

## 3.8 Explainability

Explainability techniques were incorporated to help identify the factors contributing to model predictions. SHAP-based analysis was used for global and local interpretation.

## 3.9 System Development

The backend was implemented using FastAPI, SQLAlchemy, Pydantic, and Alembic. The frontend was implemented as a web interface using HTML, CSS, JavaScript, and Bootstrap.

The machine-learning layer uses Python-based data science libraries and serialized model artifacts.

## 3.10 Testing

Testing covered database functionality, authentication, API behavior, schemas, security, model integration, recommendations, and related system components.

## 3.11 Deployment

The system is prepared for deployment using Render. PostgreSQL is intended for production persistence while SQLite can be used during development.

## 3.12 Summary

The methodology combines data science, machine learning, explainability, software engineering, security, and deployment practices to develop FINPATH as an integrated decision-support system.
