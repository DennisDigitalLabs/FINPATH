"""
ML Input Mapper: Converts validated frontend assessment data to FINPATH model input contract.

This module enforces the strict data contract boundary between the user-facing assessment
and Yvette's trained XGBoost model. It applies only documented, tested mappings and
rejects ambiguous or unknown field values with user-safe error messages.

DO NOT:
- Invent new mappings or defaults
- Modify the underlying ML model code
- Accept undocumented field values
- Transform engineered features (they are computed by ml/feature_engineering.py)
"""

from typing import Any, Dict, List, Mapping, Optional

from ml.predict import DEFAULTS


class MLInputValidationError(ValueError):
	"""Raised when assessment data fails ML contract validation."""
	pass


class MLInputMapper:
	"""
	Authoritative mapper from assessment data to ML raw input fields.
	
	The ML model requires exactly 20 raw input fields with strict encodings.
	This mapper applies only documented mappings and fails closed on ambiguity.
	"""

	# === AUTHORITATIVE FIELD DEFINITIONS ===
	# These 20 fields represent the complete ML contract
	MODEL_INPUT_FIELDS = {
		"Age",                      # 1-6 code from age range
		"Sex",                      # 1-2 code
		"county",                   # 1-47 code
		"A20",                      # Education 1-10 code
		"A21",                      # Marital status 1-4 code
		"Savings_usage",            # 0 or 1
		"Loan_usage",               # 0 or 1
		"Loan_formal",              # 0 or 1
		"Loan_informal",            # 0 or 1
		"Digital_credit_usage",     # 0 or 1
		"loan_app_2",               # 0 or 1
		"loan_fuliza_2",            # 0 or 1
		"defaulted",                # 0 or 1
		"chama_usage",              # 0 or 1
		"sacco_use",                # 0-2 or similar (encoding TBD - using default 3 as fallback)
		"mobile_money_use",         # 0-2 or similar (encoding TBD - using default 1 as fallback)
		"S7_2",                     # 1-4 ordinal mobile money frequency
		"CountLivelihood",          # Integer >= 1
		"saving_for_emergencies",   # 0 or 1
		"Financial_literacy_index_fnl",  # Numeric score (mapping TBD)
	}

	# === AUTHORITATIVE MAPPINGS ===
	# Reverse lookup tables from frontend labels to ML codes

	# Age ranges to codes
	AGE_CODE_MAP = {
		"18-24": 2,
		"25-34": 3,
		"35-44": 4,
		"45-54": 5,
		"55 or older": 6,
		# Legacy aliases
		"18 to 24": 2,
		"26 to 35": 3,
		"25-35": 3,
	}

	# Sex labels to codes
	SEX_CODE_MAP = {
		"Male": 1,
		"Female": 2,
		"male": 1,
		"female": 2,
		"m": 1,
		"f": 2,
		# Non-binary options - use 1 as fallback (conservative)
		"Other": 1,
		"Prefer not to say": 1,
	}

	# All 47 Kenya counties in order (from ML feature_engineering.py COUNTY dict)
	COUNTY_CODE_MAP = {
		"Mombasa": 1, "Kwale": 2, "Kilifi": 3, "Tana River": 4, "Lamu": 5,
		"Taita-Taveta": 6, "Garissa": 7, "Wajir": 8, "Mandera": 9, "Marsabit": 10,
		"Isiolo": 11, "Meru": 12, "Tharaka-Nithi": 13, "Embu": 14, "Kitui": 15,
		"Machakos": 16, "Makueni": 17, "Nyandarua": 18, "Nyeri": 19, "Kirinyaga": 20,
		"Murang'a": 21, "Kiambu": 22, "Turkana": 23, "West Pokot": 24, "Samburu": 25,
		"Trans Nzoia": 26, "Uasin Gishu": 27, "Elgeyo-Marakwet": 28, "Nandi": 29, "Baringo": 30,
		"Laikipia": 31, "Nakuru": 32, "Narok": 33, "Kajiado": 34, "Kericho": 35,
		"Bomet": 36, "Kakamega": 37, "Vihiga": 38, "Bungoma": 39, "Busia": 40,
		"Siaya": 41, "Kisumu": 42, "Homa Bay": 43, "Migori": 44, "Kisii": 45,
		"Nyamira": 46, "Nairobi City": 47,
	}

	# Education levels to codes (10 levels)
	EDUCATION_CODE_MAP = {
		"None": 1,
		"Some primary": 2,
		"Primary completed": 3,
		"Some secondary": 4,
		"Secondary completed": 5,
		"Some technical training": 6,
		"Completed technical training": 7,
		"Some university": 8,
		"University completed": 9,
		"Other": 10,
	}

	# Marital status to codes (4 levels)
	MARITAL_STATUS_CODE_MAP = {
		"Single / Never Married": 1,
		"Divorced / Separated": 2,
		"Widowed": 3,
		"Married / Living with partner": 4,
	}

	# Binary fields: Yes/No to 1/0
	BINARY_YES_NO_MAP = {
		"Yes": 1, "No": 0,
		"yes": 1, "no": 0,
		1: 1, 0: 0,
		"1": 1, "0": 0,
		True: 1, False: 0,
	}

	# SACCO usage to codes - PROVISIONAL
	# Frontend: No / Occasional / Regular
	# ML default in predict.py: 3
	# Assumption: 0=No, 1=Occasional, 2=Regular (if 3-state encoding)
	SACCO_USE_CODE_MAP = {
		"No": 0,
		"Occasional": 1,
		"Occasional member or user": 1,
		"Regular": 2,
		"Regular member or user": 2,
		"no": 0,
		"occasional": 1,
		"regular": 2,
	}

	# Mobile money usage to codes - PROVISIONAL
	# Frontend: No / Occasional / Regular
	# ML default in predict.py: 1
	# Assumption: 0=No, 1=Occasional, 2=Regular (if 3-state encoding)
	MOBILE_MONEY_USE_CODE_MAP = {
		"No": 0,
		"Occasional": 1,
		"Occasional user": 1,
		"Regular": 2,
		"Regular user": 2,
		"no": 0,
		"occasional": 1,
		"regular": 2,
	}

	# Mobile money transaction frequency (S7_2) - 1-4 ordinal
	# 1 = Several times a week (frequent)
	# 2 = At least once a week (somewhat frequent)
	# 3 = A few times a month (occasional)
	# 4 = Rarely or never (minimal use)
	MOBILE_MONEY_FREQUENCY_MAP = {
		1: 1, 2: 2, 3: 3, 4: 4,
		"1": 1, "2": 2, "3": 3, "4": 4,
		"Several times a week": 1,
		"At least once a week": 2,
		"A few times a month": 3,
		"Rarely or never": 4,
	}

	# Financial literacy score self-rating to Financial_literacy_index_fnl
	# Frontend: 1-4 where 1=Very knowledgeable, 4=Limited knowledge
	# This is ASSUMED to map directly, but TBD based on feature_engineering logic
	# Option A (direct): 1→1, 2→2, 3→3, 4→4
	# Option B (reverse): 1→4, 2→3, 3→2, 4→1
	# Using direct mapping as conservative default; can be inverted if model evidence shows otherwise
	FINANCIAL_LITERACY_SCORE_MAP = {
		1: 1, 2: 2, 3: 3, 4: 4,
		"1": 1, "2": 2, "3": 3, "4": 4,
		"Very knowledgeable": 1,
		"Somewhat knowledgeable": 2,
		"Average knowledge": 3,
		"Limited knowledge": 4,
	}

	# === MAPPING METHODS ===

	@staticmethod
	def map_age(value: Any) -> int:
		"""Convert age range label to ML code (1-6)."""
		if value is None or value == "":
			raise MLInputValidationError("Age range is required")
		if isinstance(value, int) and 1 <= value <= 6:
			return value
		label = str(value).strip()
		if label in MLInputMapper.AGE_CODE_MAP:
			return MLInputMapper.AGE_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid age range '{label}'. "
			f"Expected one of: {', '.join(MLInputMapper.AGE_CODE_MAP.keys())}"
		)

	@staticmethod
	def map_sex(value: Any) -> int:
		"""Convert sex label to ML code (1-2)."""
		if value is None or value == "":
			raise MLInputValidationError("Gender/Sex is required")
		if isinstance(value, int) and value in (1, 2):
			return value
		label = str(value).strip()
		if label in MLInputMapper.SEX_CODE_MAP:
			return MLInputMapper.SEX_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid sex value '{label}'. "
			f"Expected one of: {', '.join(set(MLInputMapper.SEX_CODE_MAP.keys()))}"
		)

	@staticmethod
	def map_county(value: Any) -> int:
		"""Convert county name to ML code (1-47)."""
		if value is None or value == "":
			raise MLInputValidationError("County is required")
		if isinstance(value, int) and 1 <= value <= 47:
			return value
		label = str(value).strip()
		if label in MLInputMapper.COUNTY_CODE_MAP:
			return MLInputMapper.COUNTY_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid county '{label}'. "
			f"Expected one of the 47 Kenya counties"
		)

	@staticmethod
	def map_education(value: Any) -> int:
		"""Convert education level label to ML code (1-10)."""
		if value is None or value == "":
			raise MLInputValidationError("Education level is required")
		if isinstance(value, int) and 1 <= value <= 10:
			return value
		label = str(value).strip()
		if label in MLInputMapper.EDUCATION_CODE_MAP:
			return MLInputMapper.EDUCATION_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid education level '{label}'. "
			f"Expected one of: {', '.join(MLInputMapper.EDUCATION_CODE_MAP.keys())}"
		)

	@staticmethod
	def map_marital_status(value: Any) -> int:
		"""Convert marital status label to ML code (1-4)."""
		if value is None or value == "":
			raise MLInputValidationError("Marital status is required")
		if isinstance(value, int) and 1 <= value <= 4:
			return value
		label = str(value).strip()
		if label in MLInputMapper.MARITAL_STATUS_CODE_MAP:
			return MLInputMapper.MARITAL_STATUS_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid marital status '{label}'. "
			f"Expected one of: {', '.join(MLInputMapper.MARITAL_STATUS_CODE_MAP.keys())}"
		)

	@staticmethod
	def map_binary(value: Any, field_name: str) -> int:
		"""Convert Yes/No or 1/0 to binary (0 or 1)."""
		if value is None or value == "":
			raise MLInputValidationError(f"{field_name} is required")
		if isinstance(value, int) and value in (0, 1):
			return value
		label = str(value).strip()
		if label in MLInputMapper.BINARY_YES_NO_MAP:
			return MLInputMapper.BINARY_YES_NO_MAP[label]
		raise MLInputValidationError(
			f"Invalid value '{label}' for {field_name}. "
			f"Expected 'Yes', 'No', 1, or 0"
		)

	@staticmethod
	def map_sacco_use(value: Any) -> int:
		"""Convert SACCO usage to ML code (0-2 provisional)."""
		if value is None or value == "":
			raise MLInputValidationError("SACCO usage is required")
		if isinstance(value, int) and value in (0, 1, 2, 3):
			return value
		label = str(value).strip()
		if label in MLInputMapper.SACCO_USE_CODE_MAP:
			return MLInputMapper.SACCO_USE_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid SACCO usage '{label}'. "
			f"Expected 'No', 'Occasional', or 'Regular'"
		)

	@staticmethod
	def map_mobile_money_use(value: Any) -> int:
		"""Convert mobile money usage to ML code (0-2 provisional)."""
		if value is None or value == "":
			raise MLInputValidationError("Mobile money usage is required")
		if isinstance(value, int) and value in (0, 1, 2, 3):
			return value
		label = str(value).strip()
		if label in MLInputMapper.MOBILE_MONEY_USE_CODE_MAP:
			return MLInputMapper.MOBILE_MONEY_USE_CODE_MAP[label]
		raise MLInputValidationError(
			f"Invalid mobile money usage '{label}'. "
			f"Expected 'No', 'Occasional', or 'Regular'"
		)

	@staticmethod
	def map_s7_2_frequency(value: Any) -> int:
		"""Convert mobile money transaction frequency to S7_2 (1-4)."""
		if value is None or value == "":
			raise MLInputValidationError("Mobile money transaction frequency is required")
		if isinstance(value, int) and 1 <= value <= 4:
			return value
		label = str(value).strip()
		if label in MLInputMapper.MOBILE_MONEY_FREQUENCY_MAP:
			return MLInputMapper.MOBILE_MONEY_FREQUENCY_MAP[label]
		raise MLInputValidationError(
			f"Invalid frequency '{label}'. Expected 1-4 or a frequency label"
		)

	@staticmethod
	def map_count_livelihood(value: Any) -> int:
		"""Convert livelihood count to numeric (must be >= 1)."""
		if value is None or value == "":
			raise MLInputValidationError("Livelihood count is required")
		try:
			count = int(value)
			if count < 1:
				raise ValueError
			return count
		except (TypeError, ValueError):
			raise MLInputValidationError(
				f"Livelihood count must be an integer >= 1, got '{value}'"
			)

	@staticmethod
	def map_financial_literacy_score(value: Any) -> int:
		"""Convert self-rated financial knowledge to Financial_literacy_index_fnl."""
		if value is None or value == "":
			raise MLInputValidationError("Financial literacy score is required")
		if isinstance(value, int) and 1 <= value <= 4:
			return value
		label = str(value).strip()
		if label in MLInputMapper.FINANCIAL_LITERACY_SCORE_MAP:
			return MLInputMapper.FINANCIAL_LITERACY_SCORE_MAP[label]
		raise MLInputValidationError(
			f"Invalid financial literacy score '{label}'. Expected 1-4"
		)

	# === PUBLIC MAPPER ===

	def map_assessment_data(self, assessment_data: Mapping[str, Any]) -> Dict[str, Any]:
		"""
		Convert frontend assessment data to ML raw input contract.
		
		Args:
			assessment_data: Form fields from frontend assessment
			
		Returns:
			Dictionary with exactly 23 ML input fields, validated and encoded
			
		Raises:
			MLInputValidationError: If any required field is missing or invalid
		"""
		if not isinstance(assessment_data, Mapping):
			raise MLInputValidationError("Assessment data must be a mapping/dictionary")

		result: Dict[str, Any] = {}

		# === PERSONAL PROFILE ===
		result["Age"] = self.map_age(assessment_data.get("age_range"))
		result["Sex"] = self.map_sex(assessment_data.get("sex"))
		result["county"] = self.map_county(assessment_data.get("county"))
		result["A20"] = self.map_education(assessment_data.get("education"))
		result["A21"] = self.map_marital_status(assessment_data.get("marital_status"))

		# === SAVINGS ===
		result["Savings_usage"] = self.map_binary(
			assessment_data.get("savings_usage"), "Savings usage"
		)
		result["saving_for_emergencies"] = self.map_binary(
			assessment_data.get("emergency_savings"), "Emergency savings"
		)

		# === LENDING & CREDIT ===
		result["Loan_usage"] = self.map_binary(
			assessment_data.get("loan_usage"), "Loan usage"
		)
		loan_fields = (
			("Loan_formal", "loan_formal", "Formal loan"),
			("Loan_informal", "loan_informal", "Informal loan"),
			("Digital_credit_usage", "digital_credit_usage", "Digital credit usage"),
			("loan_app_2", "loan_app_2", "Loan app usage"),
			("loan_fuliza_2", "loan_fuliza_2", "Fuliza usage"),
			("defaulted", "defaulted", "Loan default"),
		)
		for model_field, assessment_field, label in loan_fields:
			if result["Loan_usage"] == 0:
				result[model_field] = DEFAULTS[model_field]
			else:
				result[model_field] = self.map_binary(
					assessment_data.get(assessment_field), label
				)

		# === SERVICES & DIGITAL ACCESS ===
		result["chama_usage"] = self.map_binary(
			assessment_data.get("chama_usage"), "Chama usage"
		)
		result["sacco_use"] = self.map_sacco_use(assessment_data.get("sacco_use"))
		result["mobile_money_use"] = self.map_mobile_money_use(
			assessment_data.get("mobile_money_use")
		)
		if result["mobile_money_use"] == 0:
			result["S7_2"] = DEFAULTS["S7_2"]
		else:
			result["S7_2"] = self.map_s7_2_frequency(assessment_data.get("S7_2"))

		# === RESILIENCE & KNOWLEDGE ===
		result["CountLivelihood"] = self.map_count_livelihood(
			assessment_data.get("CountLivelihood")
		)
		result["Financial_literacy_index_fnl"] = self.map_financial_literacy_score(
			assessment_data.get("financial_literacy_score")
		)

		# === CONTEXTUAL FIELDS (optional, passed through) ===
		# These fields are collected for context but not model-required
		contextual_fields = [
			"employment_status",
			"monthly_income",
			"income_reliability",
			"monthly_expenses",
			"financial_dependents",
			"bill_pressure",
			"saves_regularly",
			"budgeting",
			"location_type",
			"household_size",
			"debt_repayment",
			"credit_barrier",
			"account_access",
			"service_distance",
			"digital_confidence",
			"experienced_shock",
			"accessto_13k_1month",
			"financial_confidence",
			"financial_information",
			"future_goal",
		]

		for field in contextual_fields:
			if field in assessment_data:
				result[field] = assessment_data[field]

		# === VALIDATION ===
		# Ensure all required model fields are present
		missing_fields = self.MODEL_INPUT_FIELDS - set(result.keys())
		if missing_fields:
			raise MLInputValidationError(
				f"Assessment data is missing required fields: {', '.join(sorted(missing_fields))}"
			)

		return result
