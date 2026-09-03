from pathlib import Path
import sys,pandas as pd,matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ml.target_definition import make_target
ROOT=Path(__file__).resolve().parents[1]; d=pd.read_stata(ROOT/'data/raw/finaccess_2024/2024_Finaccess_Publicdata.dta',convert_categoricals=False); d=d[d.Age.isin([2,3])].copy(); fig=ROOT/'reports/figures'; fig.mkdir(parents=True,exist_ok=True)
for name,s in [('target_distribution',make_target(d)),('savings_usage',d.Savings_usage),('loan_usage',d.Loan_usage),('digital_credit',d.Digital_credit_usage),('defaulted',d.defaulted),('mobile_money_use',d.mobile_money_use)]:
 s.value_counts(dropna=False).plot(kind='bar'); plt.title(name); plt.tight_layout(); plt.savefig(fig/f'{name}.png',dpi=160); plt.close()
