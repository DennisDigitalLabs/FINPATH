import numpy as np
from sklearn.metrics import accuracy_score,precision_score,recall_score,f1_score,roc_auc_score,classification_report,confusion_matrix
def evaluate(model,X,y):
 p=model.predict(X); out={'accuracy':accuracy_score(y,p),'precision_macro':precision_score(y,p,average='macro',zero_division=0),'recall_macro':recall_score(y,p,average='macro',zero_division=0),'f1_macro':f1_score(y,p,average='macro',zero_division=0)}
 if hasattr(model,'predict_proba'):
  out['roc_auc_ovr_macro']=roc_auc_score(y,model.predict_proba(X),multi_class='ovr',average='macro')
 else: out['roc_auc_ovr_macro']=float('nan')
 out['confusion_matrix']=confusion_matrix(y,p).tolist(); out['classification_report']=classification_report(y,p,zero_division=0)
 return out
