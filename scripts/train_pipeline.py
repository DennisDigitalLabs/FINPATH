from pathlib import Path
import sys,json,joblib,pandas as pd,numpy as np,matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split,StratifiedKFold,RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import ConfusionMatrixDisplay,roc_curve,auc
from xgboost import XGBClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.feature_engineering import engineer_features
from ml.data_preprocessing import build_preprocessor
from ml.target_definition import make_target
from ml.evaluate_model import evaluate
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta'; OUT=ROOT/'data/processed/youth_finpath_modeling.csv'; MD=ROOT/'models/v1'; FIG=ROOT/'reports/figures'; RANDOM_STATE=42
def main():
 raw=pd.read_stata(RAW,convert_categoricals=False); raw=raw[raw.Age.isin([2,3])].copy(); X=engineer_features(raw); y=make_target(raw); le=LabelEncoder(); yy=le.fit_transform(y); Xtr,Xte,ytr,yte=train_test_split(X,yy,test_size=.2,stratify=yy,random_state=RANDOM_STATE)
 models={'Baseline Dummy':DummyClassifier(strategy='prior',random_state=42),'Logistic Regression':LogisticRegression(max_iter=2000,class_weight='balanced',random_state=42),'Random Forest':RandomForestClassifier(n_estimators=150,class_weight='balanced',random_state=42,n_jobs=-1),'XGBoost':XGBClassifier(n_estimators=150,max_depth=5,learning_rate=.05,subsample=.9,colsample_bytree=.9,objective='multi:softprob',eval_metric='mlogloss',random_state=42,n_jobs=2)}
 results=[]
 for name,est in models.items():
  pipe=Pipeline([('preprocessor',build_preprocessor()),('model',est)]); pipe.fit(Xtr,ytr); m=evaluate(pipe,Xte,yte); results.append({'model':name,**{k:v for k,v in m.items() if k not in ['confusion_matrix','classification_report']}})
  ConfusionMatrixDisplay.from_predictions(yte,pipe.predict(Xte)); plt.tight_layout(); plt.savefig(FIG/f'confusion_{name.lower().replace(" ","_")}.png',dpi=160); plt.close()
 comp=pd.DataFrame(results); comp.to_csv(ROOT/'reports/model_comparison.csv',index=False)
 base=XGBClassifier(objective='multi:softprob',eval_metric='mlogloss',random_state=42,n_jobs=2); pipe=Pipeline([('preprocessor',build_preprocessor()),('model',base)])
 params={'model__n_estimators':[100,150,200],'model__max_depth':[3,4,5,6],'model__learning_rate':[.03,.05,.1],'model__subsample':[.75,.9,1.0],'model__colsample_bytree':[.75,.9,1.0]}
 cv=StratifiedKFold(5,shuffle=True,random_state=42); search=RandomizedSearchCV(pipe,params,n_iter=4,scoring='f1_macro',cv=cv,random_state=42,n_jobs=1,refit=True); search.fit(Xtr,ytr); tuned=evaluate(search.best_estimator_,Xte,yte); pd.DataFrame(search.cv_results_).sort_values('rank_test_score').to_csv(ROOT/'reports/tuning_results.csv',index=False)
 MD.mkdir(parents=True,exist_ok=True); joblib.dump(search.best_estimator_,MD/'finpath_model.joblib'); joblib.dump(le,MD/'label_encoder.joblib'); pre=search.best_estimator_.named_steps['preprocessor']; joblib.dump(pre.named_transformers_['num'].named_steps['scaler'],MD/'scaler.joblib'); joblib.dump(pre.named_transformers_['cat'].named_steps['encoder'],MD/'encoder.joblib'); (MD/'feature_names.json').write_text(json.dumps(list(pre.get_feature_names_out()),indent=2))
 meta={'model_version':'v1','dataset_file':'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta','raw_rows':int(len(pd.read_stata(RAW,convert_categoricals=False))),'youth_rows':int(len(raw)),'train_rows':int(len(Xtr)),'test_rows':int(len(Xte)),'target':'nfh_categories','target_labels':list(le.classes_),'random_state':42,'best_params':search.best_params_,'test_metrics':{k:v for k,v in tuned.items() if k not in ['confusion_matrix','classification_report']},'required_features_unavailable':['debt_to_income_ratio','informal_financial_ratio'],'note':'No income amount or financial-asset amount field was identified in the supplied public file, so those two guide-defined ratios are not fabricated or used.'}; (MD/'metadata.json').write_text(json.dumps(meta,indent=2,default=str))
 print(comp.to_string(index=False)); print('Tuned:',tuned); print('Best:',search.best_params_)
if __name__=='__main__': main()
