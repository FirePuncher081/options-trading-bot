"""Refresh the static dashboard from checked-in historical CSVs (standard library only)."""
import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
with (ROOT / 'data/processed/multi_ticker_options_clean.csv').open() as handle:
    rows = list(csv.DictReader(handle))
contracts = []
for row in rows:
    contracts.append({key: row[key] for key in ('contractSymbol', 'ticker', 'expiry', 'date_collected')} | {
        key: float(row[key]) for key in ('strike', 'lastPrice', 'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility', 'spot_price')
    })
with (ROOT / 'data/processed/combined_options_clean.csv').open() as handle:
    training = list(csv.DictReader(handle))
payload = {'contracts': contracts, 'tickerCounts': dict(Counter(r['ticker'] for r in contracts)),
           'latestCollection': max(r['date_collected'] for r in contracts),
           'trainingRows': len(training), 'targetCounts': dict(Counter(r['target'] for r in training))}
(ROOT / 'dashboard/data.js').write_text('window.OPTIONS_DATA = ' + json.dumps(payload, separators=(',', ':'), allow_nan=False) + ';\n')
print(f'Built dashboard for {len(contracts)} historical contracts.')
