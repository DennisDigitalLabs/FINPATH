from pathlib import Path
import sys, pandas as pd, numpy as np, joblib, matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.feature_engineering import engineer_features
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta'; FIG=ROOT/'reports/figures'; D=ROOT/'models/v1'
d=pd.read_stata(RAW,convert_categoricals=False); sample=d[d.Age.isin([2,3])].head(200).copy(); x=engineer_features(sample); pipe=joblib.load(D/'finpath_model.joblib'); pre=pipe.named_steps['preprocessor']; est=pipe.named_steps['model']; xt=pre.transform(x); names=pre.get_feature_names_out()
import shap
sv=shap.TreeExplainer(est)(xt).values
# Normalize shape to samples x features x classes
if sv.ndim==3: mat=sv.mean(axis=2)
else: mat=sv
mean_abs=np.abs(mat).mean(axis=0); order=np.argsort(mean_abs)[-20:][::-1]
fig,ax=plt.subplots(figsize=(8,6)); ax.barh(range(15),mean_abs[order[:15]][::-1]); ax.set_yticks(range(15)); ax.set_yticklabels(names[order[:15]][::-1]); ax.set_title('Global SHAP Mean Absolute Contribution'); ax.set_xlabel('Mean |SHAP value|'); fig.tight_layout(); fig.savefig(FIG/'shap_summary.png',dpi=180); plt.close(fig)
# local top-10 contribution for first respondent
local=mat[0]; oi=np.argsort(np.abs(local))[-10:][::-1]
fig,ax=plt.subplots(figsize=(8,5)); ax.barh(range(10),local[oi][::-1]); ax.set_yticks(range(10)); ax.set_yticklabels(names[oi][::-1]); ax.set_title('Local SHAP Contributions — Example Youth Assessment'); ax.set_xlabel('SHAP contribution'); fig.tight_layout(); fig.savefig(FIG/'shap_local_example.png',dpi=180); plt.close(fig)
pd.DataFrame({'feature':names[order[:20]],'mean_abs_shap':mean_abs[order[:20]]}).to_csv(ROOT/'reports/shap_global_importance.csv',index=False)
print('SHAP evidence generated')
