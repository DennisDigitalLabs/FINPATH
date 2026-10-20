# FINPATH — Final ML Handoff Report

## 1. Completion status
All ML workstream deliverables in the supplied Yvette guide are implemented as executable modules, notebooks, tests, model artifacts and evidence reports. The GitHub branch/PR step remains a repository-side action and is documented but cannot be performed inside this ZIP without repository access.

## 2. Dataset summary
- Source file: `data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta` (user-supplied).
- Raw records: **20,871**.
- Raw variables: **3,816**.
- Youth modeling population: **9,358** (FinAccess Age codes 2=18–25 and 3=26–35).
- Train/test split: **7,486/1,872**, stratified 80/20.
- Target: `nfh_categories`, mapped from official observed High/Medium/Low categories to High Risk/Moderate Risk/Low Risk.

## 3. Model evaluation

| Model | Accuracy | Precision Macro | Recall Macro | F1 Macro | ROC-AUC OVR |
|---|---:|---:|---:|---:|---:|
| Baseline Dummy | 0.4402 | 0.1467 | 0.3333 | 0.2038 | 0.5000 |\n| Logistic Regression | 0.5166 | 0.5240 | 0.5612 | 0.5161 | 0.7338 |\n| Random Forest | 0.5374 | 0.5393 | 0.5324 | 0.5349 | 0.7142 |\n| XGBoost | 0.5465 | 0.5530 | 0.5419 | 0.5446 | 0.7384 |\n

## 4. Selected model
XGBoost was selected for tuning because it had the highest holdout macro-F1 and ROC-AUC among the candidate models before tuning. Final tuning used RandomizedSearchCV with 5-fold Stratified CV.

Best parameters:
```text
{
  "model__subsample": 0.75,
  "model__n_estimators": 200,
  "model__max_depth": 5,
  "model__learning_rate": 0.03,
  "model__colsample_bytree": 0.9
}
```

Tuned holdout metrics: **accuracy=0.5470, macro-F1=0.5450, ROC-AUC=0.7394**.

## 5. Explainability
Global and local SHAP evidence is stored in `reports/figures/` and `reports/shap_global_importance.csv`. The top global drivers by mean absolute SHAP value include:

| feature                         |   mean_abs_shap |
|:--------------------------------|----------------:|
| num__financial_resilience_index |      0.113372   |
| cat__emergency_access_0         |      0.0260728  |
| num__age_midpoint               |      0.0232659  |
| cat__mobile_money_use_1.0       |      0.0182715  |
| cat__experienced_shock_0        |      0.0130231  |
| cat__defaulted_0                |      0.0114179  |
| cat__savings_usage_0            |      0.00961753 |
| cat__loan_informal_0            |      0.00867618 |
| cat__mobile_money_use_3.0       |      0.00615903 |
| cat__marital_status_4           |      0.0061002  |

## 6. Feature engineering limitations
The guide specifies exact `debt_to_income_ratio` and `informal_financial_ratio` monetary formulas. The supplied public file did not expose clearly identifiable monthly-income, monthly-debt and total-financial-asset amount fields sufficient to calculate those exact ratios. They are therefore not fabricated.

`digital_footprint_score` uses the available FinAccess mobile-money transaction-frequency indicator (`S7_2`) and digital-app-loan usage. `financial_resilience_index` uses the available emergency-saving indicator AND `CountLivelihood > 1` as a documented operational proxy for multiple livelihood sources.

## 7. Backend integration
Call `POST /api/v1/assess`. The endpoint validates the youth age range, invokes `ml/predict.py`, returns risk class/probabilities, up to three SHAP contribution factors, and up to three recommendations.

## 8. Testing
Run `pytest -q`. Tests cover preprocessing, feature engineering, artifact loading, prediction validation, recommendations and end-to-end inference.

## 9. Security and ethics
The supplied dataset is retained as provided; no credentials are included. Raw respondent records must not be exposed through API responses. The risk output is decision support, not a guaranteed financial or legal outcome. Demographic bias and survey-weight limitations should be discussed in the thesis.
