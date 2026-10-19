"""Export current dataset and verified research report to the static dashboard."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from options_lab import __version__, code_fingerprint
from options_lab.data import load_snapshots


def build(report_path=None, output=None, paths=None):
    report_path = Path(report_path or ROOT/'artifacts/research/report.json')
    output = Path(output or ROOT/'dashboard/data.js')
    paths = sorted(map(Path, paths or [*ROOT.glob('data/raw/*.csv'), *ROOT.glob('data/snapshots/*.csv')]))
    report = json.loads(report_path.read_text())
    fingerprints = [{'file': p.name, 'sha256': sha256(p.read_bytes()).hexdigest()} for p in paths]
    if (report.get('inputs') != fingerprints or report.get('pipeline_version') != __version__
        or report.get('code_sha256') != code_fingerprint()):
        raise ValueError('Research report is stale. Run python -m options_lab research first.')
    if report.get('status') not in {'ready', 'insufficient_data'}:
        raise ValueError('Unsupported research report status.')
    snapshots, _ = load_snapshots(paths)
    # Explorer shows the latest saved observation per contract.
    latest = snapshots.sort_values('date_collected').drop_duplicates('contractSymbol', keep='last')
    fields = ['contractSymbol', 'ticker', 'expiry', 'date_collected', 'strike', 'lastPrice',
              'bid', 'ask', 'volume', 'openInterest', 'impliedVolatility', 'spot_price']
    if 'lastPrice' not in latest:
        latest['lastPrice'] = None
    # pandas encodes missing values as JSON null, never NaN.
    contracts = json.loads(latest[fields].to_json(orient='records', date_format='iso'))
    payload = {'contracts': contracts, 'tickerCounts': latest.ticker.value_counts().to_dict(),
        'latestCollection': report['dataset']['latest_collection'],
        'trainingRows': report['labeled_rows'], 'research': report}
    output.write_text('window.OPTIONS_DATA = '+json.dumps(payload,separators=(',',':'),allow_nan=False)+';\n')
    print(f"Exported {len(contracts)} contracts; research status: {report['status']}.")
    return payload


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path)
    parser.add_argument('--output', type=Path)
    args=parser.parse_args()
    build(args.report,args.output)
