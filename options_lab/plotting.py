"""Consistent research figures, generated only from current pipeline reports."""
from pathlib import Path
import matplotlib.pyplot as plt


def set_theme():
    plt.rcParams.update({'figure.figsize': (9, 5), 'figure.dpi': 120,
        'figure.facecolor': '#111e2d', 'axes.facecolor': '#111e2d', 'savefig.facecolor': '#111e2d',
        'text.color': '#edf2f6', 'axes.labelcolor': '#b6c4d4', 'xtick.color': '#9aaabd',
        'ytick.color': '#9aaabd', 'axes.edgecolor': '#314156', 'grid.color': '#314156',
        'grid.alpha': .35, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.titlepad': 18, 'font.size': 11})


def plot_report(report, output=None):
    set_theme()
    if output:
        Path(output).mkdir(parents=True, exist_ok=True)
    figures = []
    if report['status'] != 'ready':
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.axis('off')
        ax.text(.02,.8,'More contract history needed',fontsize=20,color='#61d6be')
        ax.text(.02,.5,f"{report['labeled_rows']} matched future observations · no verified model metrics",fontsize=12)
        ax.text(.02,.2,'Collect the same unexpired contracts across multiple dates.',fontsize=11,color='#9aaabd')
        figures.append(('research_status',fig))
    else:
        fig, ax = plt.subplots()
        for name, model in report['models'].items():
            points=model['test']['roc']
            if points:
                ax.plot([p['fpr'] for p in points],[p['tpr'] for p in points],label=f"{name} (AUC {model['test']['roc_auc']:.3f})")
        ax.plot([0,1],[0,1],'--',color='#9aaabd',linewidth=1)
        ax.set(title='Chronological test ROC',xlabel='False positive rate',ylabel='True positive rate')
        ax.legend();fig.tight_layout();figures.append(('verified_roc',fig))
        fig,ax=plt.subplots()
        items=report['feature_importance'][::-1]
        ax.barh([r['feature'] for r in items],[r['importance'] for r in items],
                xerr=[r['std'] for r in items],color='#61d6be',error_kw={'ecolor':'#9aaabd'})
        ax.set(title=f"Permutation importance · {report['selected_model']}",xlabel='Increase in held-out Brier loss')
        fig.tight_layout();figures.append(('verified_importance',fig))
    for name,fig in figures:
        if output:
            fig.savefig(Path(output)/f'{name}.png')
    return [fig for _,fig in figures]
