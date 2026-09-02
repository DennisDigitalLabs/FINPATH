# FinAccess 2024 raw data

This directory contains the user-supplied public FinAccess 2024 Stata dataset. It is copied byte-for-byte into the project as `2024_Finaccess_Publicdata.dta`.

Raw records: 20,871
Raw variables: 3,816
FINPATH youth modeling population: respondents with Age codes 2 (18-25) or 3 (26-35): 9,358.

Target used for this implementation: `nfh_categories` (official derived FinAccess variable), with labels High/Medium/Low. The project does not invent a fourth class because the supplied public data's target has three observed categories.

The original public file is retained unchanged.
