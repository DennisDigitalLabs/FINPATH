from pathlib import Path
import joblib, pandas as pd, numpy as np
from .feature_engineering import engineer_features
ROOT=Path(__file__).resolve().parents[1]

def explain(payload, model_dir=None):
    import shap
    d=Path(model_dir or ROOT/'models'/'v1')
    model=joblib.load(d/'finpath_model.joblib')
    x=engineer_features(pd.DataFrame([payload]))
    pre=model.named_steps['preprocessor']; est=model.named_steps['model']
    xt=pre.transform(x); names=pre.get_feature_names_out()
    vals=shap.TreeExplainer(est)(xt).values
    pred=int(est.predict(xt)[0])
    if vals.ndim == 3:
        arr=vals[0,:,pred]
    elif vals.ndim == 2:
        arr=vals[0]
    else:
        arr=np.asarray(vals).reshape(-1)
    order=sorted(zip(names,arr),key=lambda z:abs(float(z[1])),reverse=True)[:3]
    return [{'feature':str(n),'impact':float(v)} for n,v in order]
