"""Normalize snapshots and label only later observations of the same contract."""
from pathlib import Path
import numpy as np
import pandas as pd

FEATURES = ['strike', 'mid', 'spread_pct', 'volume', 'openInterest',
            'impliedVolatility', 'days_to_expiry', 'moneyness']
REQUIRED = ['contractSymbol', 'ticker', 'bid', 'ask', 'strike', 'volume',
            'openInterest', 'impliedVolatility']


def load_snapshots(paths):
    frames = []
    for path in sorted(map(Path, paths)):
        frame = pd.read_csv(path)
        frame = frame.rename(columns={k: v for k, v in
            {'retrieved': 'date_collected', 'expiration': 'expiry'}.items()
            if v not in frame.columns})
        missing = set(REQUIRED + ['date_collected', 'expiry']) - set(frame.columns)
        if missing:
            raise ValueError(f'{path.name}: missing columns {sorted(missing)}')
        frame['source_file'] = path.name
        frames.append(frame)
    if not frames:
        raise ValueError('No input CSV files found.')
    raw = pd.concat(frames, ignore_index=True)
    for name in ['date_collected', 'expiry']:
        raw[name] = pd.to_datetime(raw[name], utc=True, errors='coerce', format='mixed')
    for name in ['bid', 'ask', 'strike', 'volume', 'openInterest', 'impliedVolatility', 'spot_price', 'lastPrice']:
        if name in raw:
            raw[name] = pd.to_numeric(raw[name], errors='coerce').replace([np.inf, -np.inf], np.nan)
    raw['snapshot_date'] = raw.date_collected.dt.normalize()
    # Keep the latest snapshot for each contract/day, so intraday rows cannot
    # masquerade as next-session outcomes. A contract must not change identity.
    identities = raw.groupby('contractSymbol')[['ticker', 'strike', 'expiry']].nunique()
    if (identities > 1).any().any():
        raise ValueError('Conflicting ticker, strike, or expiry for a contract symbol.')
    valid = (raw.contractSymbol.notna() & raw.ticker.notna() & raw.date_collected.notna()
             & raw.expiry.notna() & (raw.bid > 0) & (raw.ask >= raw.bid)
             & (raw.strike > 0) & (raw.expiry.dt.normalize() >= raw.snapshot_date)
             & (raw.volume >= 0) & (raw.openInterest >= 0) & (raw.impliedVolatility > 0))
    clean = raw.loc[valid].sort_values('date_collected', kind='stable').drop_duplicates(
        ['contractSymbol', 'snapshot_date'], keep='last').copy()
    clean['mid'] = (clean.bid + clean.ask) / 2
    clean['spread_pct'] = (clean.ask - clean.bid) / clean.mid
    clean['days_to_expiry'] = (clean.expiry.dt.normalize() - clean.snapshot_date).dt.days
    if 'spot_price' not in clean:
        clean['spot_price'] = np.nan
    clean['moneyness'] = clean.strike / clean.spot_price.where(clean.spot_price > 0)
    clean = clean.sort_values(['contractSymbol', 'date_collected']).reset_index(drop=True)
    audit = {'raw_rows': len(raw), 'usable_rows': len(clean),
             'excluded_or_duplicate_rows': len(raw) - len(clean),
             'contracts': int(clean.contractSymbol.nunique()),
             'collection_dates': int(clean.snapshot_date.nunique()),
             'contracts_with_multiple_dates': int((clean.groupby('contractSymbol').snapshot_date.nunique() > 1).sum()),
             'first_collection': str(clean.date_collected.min()) if len(clean) else None,
             'latest_collection': str(clean.date_collected.max()) if len(clean) else None}
    return clean, audit


def make_labels(snapshots, max_horizon_days=7):
    if max_horizon_days < 1:
        raise ValueError('max_horizon_days must be positive.')
    result = snapshots.sort_values(['contractSymbol', 'date_collected']).copy()
    grouped = result.groupby('contractSymbol', sort=False)
    for name in ['date_collected', 'snapshot_date', 'bid', 'ask', 'mid', 'volume', 'openInterest']:
        result['exit_' + name] = grouped[name].shift(-1)
    horizon = (result.exit_snapshot_date - result.snapshot_date).dt.days
    valid = (horizon > 0) & (horizon <= max_horizon_days)
    result['future_return'] = (result.exit_mid / result.mid - 1).where(valid)
    result['target'] = pd.Series(pd.NA, index=result.index, dtype='Int64')
    result.loc[valid, 'target'] = (result.loc[valid, 'future_return'] > 0).astype(int)
    return result


def chronological_split(labeled):
    """Hold out whole UTC dates and purge outcomes reaching the next split."""
    frame = labeled.dropna(subset=['target']).copy()
    if frame.empty:
        raise ValueError('No same-contract follow-up quotes within the seven-day label horizon.')
    dates = sorted(frame.snapshot_date.unique())
    if len(dates) < 10:
        raise ValueError('Need at least 10 labeled collection dates for chronological train/validation/test splits.')
    validation_start = dates[int(len(dates) * .6)]
    test_start = dates[int(len(dates) * .8)]
    train = frame[(frame.snapshot_date < validation_start) & (frame.exit_date_collected < validation_start)]
    validation = frame[(frame.snapshot_date >= validation_start) & (frame.snapshot_date < test_start)
                       & (frame.exit_date_collected < test_start)]
    test = frame[frame.snapshot_date >= test_start]
    if len(train) < 20 or len(validation) < 5 or len(test) < 5:
        raise ValueError('Need at least 20 training, 5 validation, and 5 test observations after purging.')
    if train.target.nunique() < 2:
        raise ValueError('Training data needs both positive and negative outcomes.')
    return train, validation, test
