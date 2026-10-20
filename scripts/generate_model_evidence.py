from pathlib import Path
import sys, pandas as pd, numpy as np, matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_curve, auc
from xgboost import XGBClassifier
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.feature_engineering import engineer_features
from ml.data_preprocessing import build_preprocessor
from ml.target_definition import make_target
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta'; FIG=ROOT/'reports/figures'
d=pd.read_stata(RAW,convert_categoricals=False); d=d[d.Age.isin([2,3])].copy(); X=engineer_features(d); le=LabelEncoder(); y=le.fit_transform(make_target(d)); Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.2,stratify=y,random_state=42)
models=[('Logistic Regression',LogisticRegression(max_iter=2000,class_weight='balanced',random_state=42)),('Random Forest',RandomForestClassifier(n_estimators=150,class_weight='balanced',random_state=42,n_jobs=-1)),('XGBoost',XGBClassifier(n_estimators=150,max_depth=5,learning_rate=.05,subsample=.9,colsample_bytree=.9,objective='multi:softprob',eval_metric='mlogloss',random_state=42,n_jobs=2))]
for name,est in models:
 pipe=Pipeline([('preprocessor',build_preprocessor()),('model',est)]); pipe.fit(Xtr,ytr); prob=pipe.predict_proba(Xte)
 fig,ax=plt.subplots();
 for i,cls in enumerate(le.classes_):
  fpr,tpr,_=roc_curve((yte==i).astype(int),prob[:,i]); ax.plot(fpr,tpr,label=str(cls))
 ax.plot([0,1],[0,1],linestyle='--'); ax.set_title(f'{name} One-vs-Rest ROC'); ax.set_xlabel('False Positive Rate'); ax.set_ylabel('True Positive Rate'); ax.legend(); fig.tight_layout(); fig.savefig(FIG/f'roc_{name.lower().replace(" ","_")}.png',dpi=180); plt.close(fig)
print('ROC evidence generated')
