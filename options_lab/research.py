"""Auditable chronological experiments and verified, machine-readable reports."""
from dataclasses import asdict
from hashlib import sha256
import json
from importlib.metadata import version
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, brier_score_loss,
                             confusion_matrix, roc_auc_score, roc_curve)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import __version__, code_fingerprint
from .backtest import BacktestConfig, simulate
from .data import FEATURES, chronological_split, load_snapshots, make_labels

TARGET = 'Next observed same-contract midpoint return > 0 within 7 calendar days; not expiration ITM.'
LIMITATIONS = [
    'Quotes are saved snapshots, not guaranteed executable fills. Collection time is not exchange quote time.',
    'Labels require a usable later quote and exclude contracts without one; this can introduce survivorship bias.',
    'The horizon is the next observed date, not necessarily the next trading session.',
    'Backtest assumes immediate entry at ask plus slippage and exit at the next saved bid minus slippage.',
    'Drawdown uses event-time entry-bid marks for open positions, not a full daily mark-to-market series.',
    'No exercise, assignment, financing, dividends, taxes, market impact, or broker execution is modeled.',
]


def estimator(name):
    if name == 'majority':
        model = DummyClassifier(strategy='most_frequent')
    elif name == 'logistic':
        model = LogisticRegression(max_iter=2000, random_state=42)
    elif name == 'xgboost':
        from xgboost import XGBClassifier
        model = XGBClassifier(n_estimators=100, max_depth=3, eval_metric='logloss',
                              learning_rate=.05, n_jobs=2, random_state=42)
    elif name == 'lightgbm':
        from lightgbm import LGBMClassifier
        model = LGBMClassifier(n_estimators=100, max_depth=3, num_leaves=7,
                               learning_rate=.05, n_jobs=2, random_state=42, verbosity=-1)
    else:
        raise ValueError(f'Unknown model: {name}')
    # Imputation and scaling are fitted on training rows only. No SMOTE is
    # applied: resampling would distort the probabilities used by the strategy.
    return make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True), StandardScaler(), model)


def metrics(y, probability):
    y = np.asarray(y, dtype=int)
    predicted = (probability >= .5).astype(int)
    both_classes = len(np.unique(y)) == 2
    result = {'observations': len(y), 'positive_rate': float(y.mean()),
        'accuracy': float(accuracy_score(y, predicted)),
        'balanced_accuracy': float(balanced_accuracy_score(y, predicted)) if both_classes else None,
        'brier_score': float(brier_score_loss(y, probability)),
        'roc_auc': float(roc_auc_score(y, probability)) if both_classes else None,
        'confusion_matrix': confusion_matrix(y, predicted, labels=[0, 1]).tolist(), 'roc': []}
    if both_classes:
        fpr, tpr, _ = roc_curve(y, probability)
        result['roc'] = [{'fpr': float(a), 'tpr': float(b)} for a, b in zip(fpr, tpr)]
    return result


def save_report(output, report):
    (output/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    return report


def run_research(paths, output='artifacts/research', models=('logistic', 'xgboost', 'lightgbm'), config=None):
    config = config or BacktestConfig()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    paths = sorted(map(Path, paths))
    models = tuple(models)
    if not models or len(set(models)) != len(models) or any(m not in {'logistic', 'xgboost', 'lightgbm'} for m in models):
        raise ValueError('Choose one or more unique models: logistic, xgboost, lightgbm.')
    # Never leave a previous run looking current if this run cannot train.
    for name in ['report.json', 'model.joblib', 'predictions.csv', 'trades.csv', 'labeled.csv']:
        (output/name).unlink(missing_ok=True)
    fingerprints = [{'file': p.name, 'sha256': sha256(p.read_bytes()).hexdigest()} for p in paths]
    frame, audit = load_snapshots(paths)
    labeled = make_labels(frame)
    labeled.to_csv(output/'labeled.csv', index=False)
    count = int(labeled.target.notna().sum())
    report = {'schema_version': 1, 'pipeline_version': __version__, 'code_sha256': code_fingerprint(), 'status': 'insufficient_data',
        'dataset': audit, 'inputs': fingerprints, 'labeled_rows': count, 'features': FEATURES,
        'library_versions': {name: version(name) for name in ['numpy', 'pandas', 'scikit-learn', 'xgboost', 'lightgbm']},
        'target': TARGET, 'split_method': 'Whole-date 60/20/20 chronological split; purge labels reaching the following split.',
        'model_selection': 'Lowest validation Brier score. Test data is not used for model or threshold selection.',
        'decision_threshold': config.probability_threshold, 'models': {},
        'backtest': {'status': 'not_run', 'config': asdict(config)}, 'limitations': LIMITATIONS}
    try:
        train, validation, test = chronological_split(labeled)
    except ValueError as error:
        report['reason'] = str(error)
        report['next_step'] = 'Collect the same unexpired contracts on multiple dates; retain original snapshots. Aim for at least 10 labeled dates and 20/5/5 purged train/validation/test observations with both training classes.'
        return save_report(output, report)
    split = {}
    for name, subset in [('train', train), ('validation', validation), ('test', test)]:
        split[name] = {'rows': len(subset), 'start': subset.date_collected.min().isoformat(),
                       'end': subset.date_collected.max().isoformat(),
                       'last_label': subset.exit_date_collected.max().isoformat()}
    report['split'] = split
    fitted = {}
    for name in ('majority',) + models:
        model = estimator(name).fit(train[FEATURES], train.target.astype(int))
        val_probability = model.predict_proba(validation[FEATURES])[:, 1]
        test_probability = model.predict_proba(test[FEATURES])[:, 1]
        report['models'][name] = {'validation': metrics(validation.target, val_probability),
                                  'test': metrics(test.target, test_probability)}
        fitted[name] = model
    # The baseline competes too: complexity is not rewarded over a better
    # calibrated majority predictor. The strategy threshold is fixed in config.
    selected = min(fitted, key=lambda n: report['models'][n]['validation']['brier_score'])
    best = fitted[selected]
    importance = permutation_importance(best, test[FEATURES], test.target.astype(int),
        scoring='neg_brier_score', n_repeats=5, random_state=42, n_jobs=1)
    report['feature_importance'] = sorted([
        {'feature': name, 'importance': float(mean), 'std': float(std)}
        for name, mean, std in zip(FEATURES, importance.importances_mean, importance.importances_std)
    ], key=lambda r: r['importance'], reverse=True)
    report['importance_method'] = 'Test permutation importance: increase in Brier loss when a feature is shuffled; negative values retained.'
    predictions = test.copy()
    predictions['probability'] = best.predict_proba(test[FEATURES])[:, 1]
    predictions.to_csv(output/'predictions.csv', index=False)
    report['backtest'], trades = simulate(predictions, config)
    trades.to_csv(output/'trades.csv', index=False)
    joblib.dump({'pipeline': best, 'features': FEATURES, 'target': TARGET,
                 'pipeline_version': __version__, 'inputs': fingerprints, 'selected_model': selected}, output/'model.joblib')
    report.update(status='ready', selected_model=selected)
    return save_report(output, report)
