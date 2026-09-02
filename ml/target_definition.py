"""Target construction from the official FinAccess 2024 derived health category."""
LABELS={1:'High Risk',2:'Moderate Risk',3:'Low Risk'}
def make_target(df):
    return df['nfh_categories'].map(LABELS).rename('risk_category')
