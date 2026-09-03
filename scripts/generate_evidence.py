from pathlib import Path
import json, pandas as pd, numpy as np, matplotlib.pyplot as plt
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.feature_engineering import engineer_features
from ml.data_preprocessing import build_preprocessor
from ml.target_definition import make_target
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta'; FIG=ROOT/'reports/figures'; FIG.mkdir(parents=True,exist_ok=True)
d=pd.read_stata(RAW,convert_categoricals=False); youth=d[d.Age.isin([2,3])].copy(); y=make_target(youth)
# Target distribution
counts=y.value_counts().reindex(['High Risk','Moderate Risk','Low Risk'])
ax=counts.plot(kind='bar'); ax.set_title('FINPATH Youth Target Distribution'); ax.set_xlabel('Risk category'); ax.set_ylabel('Respondents'); plt.tight_layout(); plt.savefig(FIG/'target_distribution.png',dpi=180); plt.close()
# Required EDA variables
for c,title in [('Savings_usage','Savings usage'),('Loan_usage','Loan usage'),('Digital_credit_usage','Digital credit usage'),('defaulted','Loan default'),('mobile_money_use','Mobile money use'),('experienced_shock','Experienced financial shock')]:
 ax=youth[c].value_counts(dropna=False).sort_index().plot(kind='bar'); ax.set_title(title); ax.set_xlabel(c); ax.set_ylabel('Respondents'); plt.tight_layout(); plt.savefig(FIG/f'{c}.png',dpi=180); plt.close()
# Numeric correlation on actual usable continuous/ordinal indicators
num_cols=['Financial_literacy_index_fnl','CountLivelihood','S7_2','Age']
cor=youth[num_cols].corr(method='spearman'); fig,ax=plt.subplots(figsize=(6,5)); im=ax.imshow(cor.values); ax.set_xticks(range(len(num_cols))); ax.set_yticks(range(len(num_cols))); ax.set_xticklabels(num_cols,rotation=45,ha='right'); ax.set_yticklabels(num_cols); ax.set_title('Spearman Correlation of Key FINPATH Indicators');
for i in range(len(num_cols)):
 for j in range(len(num_cols)): ax.text(j,i,f'{cor.iloc[i,j]:.2f}',ha='center',va='center')
fig.tight_layout(); fig.savefig(FIG/'correlation_heatmap.png',dpi=180); plt.close(fig)
# Cross tabs / stacked bars
for c in ['Digital_credit_usage','Savings_usage','Loan_usage']:
 ct=pd.crosstab(youth[c],youth['nfh_categories'],normalize='index')
 ct.columns=['High','Medium','Low']
 ct.plot(kind='bar',stacked=True); plt.title(f'Risk Category by {c}'); plt.xlabel(c); plt.ylabel('Proportion'); plt.tight_layout(); plt.savefig(FIG/f'risk_by_{c}.png',dpi=180); plt.close()
# ROC curves from persisted comparison cannot reconstruct; create final-model CV validation profile
X=engineer_features(youth); yy=pd.Series(y).map({'High Risk':0,'Low Risk':1,'Moderate Risk':2}).astype(int)
# Use the final estimator settings reported in metadata
meta=json.loads((ROOT/'models/v1/metadata.json').read_text()); bp={k.replace('model__',''):v for k,v in meta['best_params'].items()}
model=XGBClassifier(objective='multi:softprob',eval_metric='mlogloss',random_state=42,n_jobs=2,**bp)
pipe=Pipeline([('preprocessor',build_preprocessor()),('model',model)])
cv=StratifiedKFold(5,shuffle=True,random_state=42)
res=cross_validate(pipe,X,yy,cv=cv,scoring=['accuracy','f1_macro'],return_train_score=True,n_jobs=1)
val=pd.DataFrame({'fold':range(1,6),'train_f1_macro':res['train_f1_macro'],'validation_f1_macro':res['test_f1_macro'],'train_accuracy':res['train_accuracy'],'validation_accuracy':res['test_accuracy']})
val.to_csv(ROOT/'reports/cv_validation_results.csv',index=False)
ax=val.set_index('fold')[['train_f1_macro','validation_f1_macro']].plot(marker='o'); ax.set_title('5-Fold Training vs Validation F1'); ax.set_xlabel('Fold'); ax.set_ylabel('Macro F1'); plt.tight_layout(); plt.savefig(FIG/'validation_curve.png',dpi=180); plt.close()
# Audit
summary={
 'raw_rows':int(len(d)),'raw_variables':int(d.shape[1]),'youth_rows':int(len(youth)),'target_counts':{str(k):int(v) for k,v in counts.items()},
 'target_missing':int(y.isna().sum()),'age_codes':{str(k):int(v) for k,v in youth.Age.value_counts().sort_index().items()},
 'key_missingness':{c:int(youth[c].isna().sum()) for c in ['Age','Sex','county','Savings_usage','Loan_usage','sacco_use','mobile_money_use','Financial_literacy_index_fnl']}
}
(ROOT/'reports/data_audit.json').write_text(json.dumps(summary,indent=2))
(ROOT/'reports/DATA_AUDIT.md').write_text(f'''# Data Audit — supplied FinAccess 2024 public dataset\n\n- Raw records: **{len(d):,}**\n- Raw variables: **{d.shape[1]:,}**\n- FINPATH youth scope: **{len(youth):,}** records with Age codes 2 (18–25) or 3 (26–35).\n- Target: `nfh_categories`, observed labels High/Medium/Low; no fourth class fabricated.\n- Youth target counts: High Risk **{counts['High Risk']:,}**, Moderate Risk **{counts['Moderate Risk']:,}**, Low Risk **{counts['Low Risk']:,}**.\n- Target missingness: **{y.isna().sum()}**.\n\n## Feature availability limitation\nThe guide's `debt_to_income_ratio` and `informal_financial_ratio` require exact monetary income, monthly debt and total financial-asset amounts. Those exact source fields were not identified in the supplied public file. They are therefore retained as documented unavailable features and are **not fabricated**.\n\n`financial_resilience_index` is operationalized using the available FinAccess `saving_for_emergencies` indicator AND `CountLivelihood > 1` as a documented proxy for multiple livelihood sources. `digital_footprint_score` combines the available mobile-money transaction-frequency variable `S7_2` and digital-app-loan usage.\n''')
print('Evidence generated')
