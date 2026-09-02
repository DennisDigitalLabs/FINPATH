from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from .config import NUMERIC_FEATURES,CATEGORICAL_FEATURES

def build_preprocessor():
    num=Pipeline([('imputer',SimpleImputer(strategy='median')),('scaler',StandardScaler())])
    cat=Pipeline([('imputer',SimpleImputer(strategy='most_frequent')),('encoder',OneHotEncoder(handle_unknown='ignore',sparse_output=False))])
    return ColumnTransformer([('num',num,NUMERIC_FEATURES),('cat',cat,CATEGORICAL_FEATURES)],remainder='drop')
