"""Apply a shared presentation layer without changing research calculations."""
import json
import hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
STYLE = '''# Shared presentation settings; calculations below remain unchanged.
import matplotlib.pyplot as plt
plt.rcParams.update({
    "figure.figsize": (9, 5), "figure.dpi": 120,
    "figure.facecolor": "#111e2d", "axes.facecolor": "#111e2d",
    "savefig.facecolor": "#111e2d", "text.color": "#edf2f6",
    "axes.labelcolor": "#b6c4d4", "xtick.color": "#9aaabd",
    "ytick.color": "#9aaabd", "axes.edgecolor": "#314156",
    "grid.color": "#314156", "grid.alpha": 0.35,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titleweight": "medium", "axes.titlepad": 18,
    "axes.prop_cycle": plt.cycler(color=["#61d6be", "#799acb", "#ed9696", "#e7c583"]),
    "image.cmap": "cividis", "font.size": 11,
})
'''
INTRO = {
'feature_engineering': ('Feature engineering', 'Turn the saved call-option chains into model inputs.', 'Inspect moneyness, days to expiry, and target construction. The shifted next-row price can refer to a different contract; it does not establish a future return for the same instrument. Running this notebook overwrites the processed CSV.'),
'clean_multi_ticker_data': ('Prepare the research dataset', 'Clean the saved multi-ticker options sample.', 'Compare row counts before and after removing missing values and duplicates. Running this notebook overwrites the processed CSV.'),
'multi_ticker_scraper': ('Collect options chains', 'Capture a dated snapshot of the options universe.', 'Requires Yahoo Finance network access. Quotes are historical snapshots after collection. Running this notebook overwrites the raw multi-ticker CSV.'),
'model_baseline': ('Establish a baseline', 'Inspect a logistic regression experiment before moving to more complex models.', 'Review class balance and the confusion matrix together. The random split is exploratory, not a trading backtest. The final save cell references undefined lgb_model and needs a separate code fix.'),
'model_xgboost': ('Compare model experiments', 'Explore boosted trees, resampling, feature importance, and explanations.', 'Fit transforms only on training data. Random splits and next-row targets do not establish out-of-time trading performance. Search cells can be expensive; this notebook also writes model and image files.'),
}
def cell(kind, text):
 return {'cell_type':kind,'metadata':{'options_lab_presentation':True},'source':text.splitlines(keepends=True), **({'execution_count':None,'outputs':[]} if kind=='code' else {})}
for path in (ROOT/'notebooks').glob('*.ipynb'):
 nb=json.loads(path.read_text()); old=[c for c in nb['cells'] if not c.get('metadata',{}).get('options_lab_presentation')]
 title,description,note=INTRO[path.stem]
 cells=[cell('markdown',f'# {title}\n\n**OPTIONS LAB / RESEARCH NOTEBOOK**\n\n{description}\n\n> **Before you run:** {note}\n'),cell('markdown','## Presentation settings\n\nA shared navy and teal palette keeps plots consistent across experiments.\n'),cell('code',STYLE)]
 for i,c in enumerate(old):
  if c['cell_type']=='code' and ''.join(c['source']).strip():
   src=''.join(c['source'])
   if i==0: heading='Load data and dependencies'
   elif 'RandomizedSearchCV' in src: heading='Search model parameters'
   elif 'shap.Explainer' in src: heading='Explain model predictions'
   elif 'joblib.dump' in src: heading='Save the model artifact'
   elif 'to_csv' in src: heading='Save the prepared dataset'
   elif 'roc_curve' in src: heading='Inspect the ROC curve'
   elif 'plot_importance' in src: heading='Inspect feature importance'
   elif 'ConfusionMatrixDisplay' in src or 'sns.heatmap' in src: heading='Evaluate predictions'
   elif 'train_test_split' in src: heading='Split the experiment data'
   elif 'SMOTE' in src: heading='Scale and rebalance training data'
   else: heading=f'Research step {i+1:02d}'
   cells.append(cell('markdown',f'## {heading}\n'))
   c.setdefault('metadata',{})['scrolled']=True
   c['metadata']['jupyter']={'outputs_hidden':True}
   # Match the baseline heatmap to the common chart palette.
   c['source']=[line.replace("cmap='Blues'", "cmap='cividis'") for line in c['source']]
  cells.append(c)
 cells.append(cell('markdown','## Read the result\n\nRecord the dataset date, sample size, split method, and limitations alongside any chart. Classification scores describe this experiment; they do not measure executable trading returns.\n'))

 for i, c in enumerate(cells):
  c.setdefault('id', hashlib.sha256(f'{path.stem}:{i}'.encode()).hexdigest()[:12])
 nb['cells']=cells;path.write_text(json.dumps(nb,indent=1,ensure_ascii=False)+'\n')
print('Styled five notebooks.')
