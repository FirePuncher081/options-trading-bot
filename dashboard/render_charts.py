"""Refresh research figures from the included data; no notebook outputs are overwritten."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import ConfusionMatrixDisplay
from xgboost import XGBClassifier
ROOT=Path(__file__).resolve().parents[1]
nb=json.loads((ROOT/'notebooks/model_baseline.ipynb').read_text())
style=next(c for c in nb['cells'] if c['cell_type']=='code' and c.get('metadata',{}).get('options_lab_presentation'))
exec(''.join(style['source']))
df=pd.read_csv(ROOT/'data/processed/combined_options_clean.csv')
X=df[['strike','lastPrice','moneyness','days_to_exp','impliedVolatility','volume']]
a,b,c,d=train_test_split(X,df.target,test_size=.2,random_state=42)
model=LogisticRegression(max_iter=1000,class_weight='balanced').fit(a,c)
ConfusionMatrixDisplay.from_estimator(model,b,d,cmap='cividis',colorbar=False)
plt.title('Baseline · held-out classification');plt.figtext(.5,.01,'Historical random split · not a trading backtest',ha='center',fontsize=9,color='#9aaabd');plt.tight_layout(rect=(0,.04,1,1));plt.savefig(ROOT/'images/baseline_confusion.png');plt.close('all')
df=pd.read_csv(ROOT/'data/processed/multi_ticker_options_clean.csv').sort_values(['ticker','date_collected'])
df['future_price']=df.groupby('ticker').lastPrice.shift(-1)
df['target']=(df.future_price>df.lastPrice).astype(int);df=df.dropna(subset=['future_price','target'])
X=df.select_dtypes(include='number').drop(columns=['target','future_price','return_1d'],errors='ignore')
a,b,c,d=train_test_split(X,df.target,test_size=.2,random_state=42)
model=XGBClassifier(eval_metric='logloss',n_jobs=2).fit(a,c)
ConfusionMatrixDisplay.from_estimator(model,b,d,cmap='cividis',colorbar=False)
plt.title('XGBoost · held-out classification');plt.figtext(.5,.01,'Exploratory next-row target · random split',ha='center',fontsize=9,color='#9aaabd');plt.tight_layout(rect=(0,.04,1,1));plt.savefig(ROOT/'images/xgboost_confusion.png');plt.close('all')
importance=pd.Series(model.feature_importances_,index=X.columns).sort_values().tail(10)
fig,ax=plt.subplots(figsize=(10,6));ax.barh(importance.index,importance.values,color='#61d6be',height=.6);ax.set_title('Which inputs shape the experiment?');ax.set_xlabel('XGBoost feature importance');ax.grid(axis='x');ax.set_axisbelow(True);fig.text(.5,.01,'Historical sample · importance does not imply causation',ha='center',fontsize=9,color='#9aaabd');fig.tight_layout(rect=(0,.04,1,1));fig.savefig(ROOT/'images/feature_importance.png');plt.close('all')
print('Rendered three research figures.')
