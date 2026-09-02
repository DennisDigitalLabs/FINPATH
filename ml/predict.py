from pathlib import Path
import json
import joblib
import numpy as np
import pandas as pd
from .feature_engineering import engineer_features
from .recommendation import recommendations
ROOT = Path(__file__).resolve().parents[1]

DEFAULTS = {
    'Sex': 1, 'county': 47, 'A20': 5, 'A21': 1, 'Savings_usage': 0, 'Loan_usage': 0,
    'Loan_formal': 0, 'Loan_informal': 0, 'Digital_credit_usage': 0, 'defaulted': 0,
    'loan_app_2': 0, 'loan_fuliza_2': 0, 'chama_usage': 0, 'sacco_use': 3,
    'mobile_money_use': 1, 'experienced_shock': 0, 'Financial_literacy_index_fnl': 3,
    'accessto_13k_1month': 0, 'S7_2': 4, 'saving_for_emergencies': 0, 'CountLivelihood': 1
}

class FinpathPredictor:
    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir or ROOT / 'models' / 'v1')
        self.model = joblib.load(self.model_dir / 'finpath_model.joblib')
        self.label_encoder = joblib.load(self.model_dir / 'label_encoder.joblib')
        self.metadata = json.loads((self.model_dir / 'metadata.json').read_text())

    @staticmethod
    def _normalize(payload):
        p = dict(payload)
        age = p.get('Age', p.get('age'))
        if age is None:
            raise ValueError('Age is required.')
        age = int(age)
        if age in (1,2,3,4,5,6):
            age_code = age
        elif 18 <= age <= 25:
            age_code = 2
        elif 26 <= age <= 35:
            age_code = 3
        else:
            raise ValueError('Age must be between 18 and 35 for the FINPATH youth model.')
        p['Age'] = age_code
        aliases = {'gender':'Sex','county_code':'county','education':'A20','marital_status':'A21',
                   'has_chama':'chama_usage','mobile_loan_usage':'Digital_credit_usage'}
        for src,dst in aliases.items():
            if src in p and dst not in p: p[dst] = p[src]
        for k,v in DEFAULTS.items(): p.setdefault(k,v)
        return p

    def predict(self, payload):
        p = self._normalize(payload)
        x = engineer_features(pd.DataFrame([p]))
        probs_arr = self.model.predict_proba(x)[0]
        classes = [str(c) for c in self.label_encoder.classes_]
        probs = {c: float(v) for c,v in zip(classes, probs_arr)}
        pred_class = classes[int(np.argmax(probs_arr))]
        risk_score = float(probs.get('High Risk',0.0) + 0.5*probs.get('Moderate Risk',0.0))
        factors = []
        try:
            from .explain_model import explain
            factors = explain(p, model_dir=self.model_dir)
        except Exception:
            pass
        return {'risk_score':risk_score,'risk_category':pred_class,'class_probabilities':probs,
                'top_contributing_factors':factors[:3],'recommendations':recommendations(p,factors),
                'model_version':self.metadata.get('model_version','v1')}
