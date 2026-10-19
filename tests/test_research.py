import json
import joblib
import numpy as np
import pandas as pd
import pytest
from options_lab.data import FEATURES, load_snapshots, make_labels, chronological_split
from options_lab.research import run_research


def test_labels_never_cross_contracts_or_dates(history_file):
    frame,_=load_snapshots([history_file]); labeled=make_labels(frame)
    for _,group in labeled.groupby('contractSymbol'):
        assert group.target.isna().sum()==1
        expected=int(int(group.contractSymbol.iloc[0].split('_')[-1])%2==1)
        assert set(group.target.dropna())=={expected}
        assert (group.dropna(subset=['target']).exit_snapshot_date > group.dropna(subset=['target']).snapshot_date).all()
    # Repeated intraday collection is not a next-session label.
    intraday=frame.iloc[:1].copy();intraday.date_collected += pd.Timedelta(hours=1)
    path=history_file.parent/'intraday.csv';pd.concat([frame,intraday]).to_csv(path,index=False)
    dedup,audit=load_snapshots([path]);assert len(dedup)==len(frame);assert audit['excluded_or_duplicate_rows']==1


def test_horizon_and_purging(history_file):
    frame,_=load_snapshots([history_file]);labeled=make_labels(frame)
    train,val,test=chronological_split(labeled)
    assert train.exit_date_collected.max() < val.snapshot_date.min()
    assert val.exit_date_collected.max() < test.snapshot_date.min()
    assert not set(train.snapshot_date)&set(val.snapshot_date)
    sparse=frame[frame.snapshot_date.isin([frame.snapshot_date.min(),frame.snapshot_date.max()])]
    assert make_labels(sparse).target.notna().sum()==0


def test_conflicting_identity_is_rejected(history_file):
    d=pd.read_csv(history_file);d.loc[0,'strike']=999;d.to_csv(history_file,index=False)
    with pytest.raises(ValueError,match='Conflicting'):
        load_snapshots([history_file])


def test_end_to_end_trains_saves_and_explains(history_file,tmp_path):
    report=run_research([history_file],tmp_path/'run',models=('logistic','xgboost','lightgbm'))
    assert report['status']=='ready'
    assert set(report['models'])=={'majority','logistic','xgboost','lightgbm'}
    assert report['models']['logistic']['test']['roc_auc']>.9
    assert len(report['feature_importance'])==len(FEATURES)
    assert report['models'][report['selected_model']]['test']['roc']
    bundle=joblib.load(tmp_path/'run/model.joblib')
    frame,_=load_snapshots([history_file]);train,_,test=chronological_split(make_labels(frame))
    # Scaling statistics prove future data wasn't included in preprocessing.
    np.testing.assert_allclose(bundle['pipeline'].steps[1][1].mean_[1],train.mid.mean())
    predicted=pd.read_csv(tmp_path/'run/predictions.csv')
    np.testing.assert_allclose(predicted.probability,bundle['pipeline'].predict_proba(test[FEATURES])[:,1])
    assert json.loads((tmp_path/'run/report.json').read_text())['inputs'][0]['sha256']
    assert report['backtest']['trades']>0


def test_no_labels_does_not_preserve_stale_model(history_file,tmp_path):
    output=tmp_path/'run';run_research([history_file],output,models=('logistic',))
    d=pd.read_csv(history_file);d=d[d.date_collected==d.date_collected.min()];d.to_csv(history_file,index=False)
    report=run_research([history_file],output,models=('logistic',))
    assert report['status']=='insufficient_data';assert report['labeled_rows']==0
    assert not (output/'model.joblib').exists();assert not (output/'predictions.csv').exists()
    assert not report['models'];assert report['backtest']['status']=='not_run'


def test_features_exclude_targets_and_exit_quotes():
    assert not any('exit' in f or 'future' in f or 'target' in f for f in FEATURES)


def test_dashboard_rejects_stale_report(history_file,tmp_path):
    from dashboard.build_data import build
    output=tmp_path/'run';run_research([history_file],output,models=('logistic',))
    payload=build(output/'report.json',tmp_path/'data.js',paths=[history_file])
    assert payload['research']['status']=='ready'
    with history_file.open('a') as handle: handle.write('\n')
    with pytest.raises(ValueError,match='stale'):
        build(output/'report.json',tmp_path/'data.js',paths=[history_file])


def test_single_class_holdout_does_not_invent_auc():
    from options_lab.research import metrics
    result=metrics([0,0],np.array([.1,.2]))
    assert result['roc_auc'] is None
    assert result['balanced_accuracy'] is None
    assert result['roc']==[]


def test_dashboard_rejects_changed_pipeline_hash(history_file,tmp_path):
    from dashboard.build_data import build
    output=tmp_path/'run';report=run_research([history_file],output,models=('logistic',))
    report['code_sha256']='old_code'
    (output/'report.json').write_text(json.dumps(report))
    with pytest.raises(ValueError,match='stale'):
        build(output/'report.json',tmp_path/'data.js',paths=[history_file])


def test_legacy_and_live_timestamp_formats_merge(history_file,tmp_path):
    live=pd.read_csv(history_file)
    legacy=live.iloc[:8].copy()
    legacy['retrieved']='2025-12-31 16:00:00.123456'
    legacy['expiration']=legacy.pop('expiry')
    legacy=legacy.drop(columns=['date_collected'])
    path=tmp_path/'legacy.csv';legacy.to_csv(path,index=False)
    combined,audit=load_snapshots([path,history_file])
    assert audit['usable_rows']==len(live)+len(legacy)
    assert audit['collection_dates']==33
    assert len(make_labels(combined).dropna(subset=['target']))==32*8
