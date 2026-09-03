# Data Audit — supplied FinAccess 2024 public dataset

- Raw records: **20,871**
- Raw variables: **3,816**
- FINPATH youth scope: **9,358** records with Age codes 2 (18–25) or 3 (26–35).
- Target: `nfh_categories`, observed labels High/Medium/Low; no fourth class fabricated.
- Youth target counts: High Risk **2,543**, Moderate Risk **4,122**, Low Risk **2,693**.
- Target missingness: **0**.

## Feature availability limitation
The guide's `debt_to_income_ratio` and `informal_financial_ratio` require exact monetary income, monthly debt and total financial-asset amounts. Those exact source fields were not identified in the supplied public file. They are therefore retained as documented unavailable features and are **not fabricated**.

`financial_resilience_index` is operationalized using the available FinAccess `saving_for_emergencies` indicator AND `CountLivelihood > 1` as a documented proxy for multiple livelihood sources. `digital_footprint_score` combines the available mobile-money transaction-frequency variable `S7_2` and digital-app-loan usage.
