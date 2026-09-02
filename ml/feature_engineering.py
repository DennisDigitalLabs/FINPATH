import numpy as np
import pandas as pd

AGE_MID = {1:16.5, 2:21.5, 3:30.5, 4:40.5, 5:50.5, 6:60.0}
COUNTY = {1:'Mombasa',2:'Kwale',3:'Kilifi',4:'Tana River',5:'Lamu',6:'Taita-Taveta',7:'Garissa',8:'Wajir',9:'Mandera',10:'Marsabit',11:'Isiolo',12:'Meru',13:'Tharaka-Nithi',14:'Embu',15:'Kitui',16:'Machakos',17:'Makueni',18:'Nyandarua',19:'Nyeri',20:'Kirinyaga',21:"Murang'a",22:'Kiambu',23:'Turkana',24:'West Pokot',25:'Samburu',26:'Trans Nzoia',27:'Uasin Gishu',28:'Elgeyo-Marakwet',29:'Nandi',30:'Baringo',31:'Laikipia',32:'Nakuru',33:'Narok',34:'Kajiado',35:'Kericho',36:'Bomet',37:'Kakamega',38:'Vihiga',39:'Bungoma',40:'Busia',41:'Siaya',42:'Kisumu',43:'Homabay',44:'Migori',45:'Kisii',46:'Nyamira',47:'Nairobi City'}

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x['age_midpoint'] = x['Age'].map(AGE_MID)
    x['sex'] = x['Sex'].map({1:'Male', 2:'Female'}).fillna('Unknown')
    x['county'] = x['county'].map(COUNTY).fillna('Unknown')
    x['education'] = x['A20'].replace({98:np.nan,99:np.nan}).map({1:'None',2:'Some primary',3:'Primary completed',4:'Some secondary',5:'Secondary completed',6:'Some technical training',7:'Completed technical training',8:'Some university',9:'University completed',10:'Other'}).fillna('Unknown')
    x['marital_status'] = x['A21'].replace({98:np.nan,99:np.nan}).map({1:'Single/Never Married',2:'Divorced/separated',3:'Widowed',4:'Married/Living with partner'}).fillna('Unknown')

    for src, out in [('Savings_usage','savings_usage'),('Loan_usage','loan_usage'),('Loan_formal','loan_formal'),('Loan_informal','loan_informal'),('Digital_credit_usage','digital_credit_usage'),('defaulted','defaulted'),('loan_app_2','loan_app_usage'),('loan_fuliza_2','fuliza_usage'),('chama_usage','chama_usage'),('sacco_use','sacco_use'),('mobile_money_use','mobile_money_use'),('experienced_shock','experienced_shock')]:
        x[out] = x[src].fillna(-1).astype(str)

    x['financial_literacy_code'] = pd.to_numeric(x['Financial_literacy_index_fnl'], errors='coerce')

    # Exact guide ratios require monetary income and total financial-asset amounts.
    # Those exact amount fields were not identified in the supplied public .dta, so they remain NaN.
    x['debt_to_income_ratio'] = np.nan
    x['informal_financial_ratio'] = np.nan

    # FinAccess S7_2 records mobile-money transaction frequency as an ordinal response.
    # Convert it to a normalized engagement score and combine it with digital-app-loan usage.
    tx = pd.to_numeric(x.get('S7_2'), errors='coerce')
    tx_score = tx.map({1:1.0, 2:0.75, 3:0.50, 4:0.0})
    app_score = pd.to_numeric(x['loan_app_usage'], errors='coerce').replace({-1:np.nan, 0:0.0, 1:1.0})
    x['digital_footprint_score'] = (tx_score.fillna(0.0) + app_score.fillna(0.0)) / 2.0

    # Operationalization from available FinAccess variables: saving for emergencies AND
    # more than one livelihood activity (CountLivelihood > 1). This is explicitly a proxy
    # for the guide's 'multi-source income' component, not a fabricated income measure.
    emergency = pd.to_numeric(x['saving_for_emergencies'], errors='coerce').fillna(0).eq(1)
    livelihoods = pd.to_numeric(x['CountLivelihood'], errors='coerce').fillna(0)
    x['financial_resilience_index'] = (emergency & (livelihoods > 1)).astype(int)
    x['emergency_access'] = emergency.astype(int).astype(str)
    return x
