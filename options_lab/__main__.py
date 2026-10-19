import argparse
from dataclasses import fields
from pathlib import Path
from .backtest import BacktestConfig


def main():
    parser = argparse.ArgumentParser(description='Options Lab reproducible research')
    commands = parser.add_subparsers(dest='command', required=True)
    research = commands.add_parser('research', help='Prepare labels, train if possible, evaluate and backtest')
    research.add_argument('--input', nargs='+', default=['data/raw', 'data/snapshots'])
    research.add_argument('--output', default='artifacts/research')
    research.add_argument('--models', nargs='+', choices=['logistic', 'xgboost', 'lightgbm'], default=['logistic', 'xgboost', 'lightgbm'])
    research.add_argument('--require-ready', action='store_true', help='Exit 2 if data cannot support evaluation')
    research.add_argument('--backtest-config', type=Path, help='JSON overrides of BacktestConfig fields')
    collection = commands.add_parser('collect', help='Append Yahoo snapshots (requires network)')
    collection.add_argument('--tickers', nargs='+', default=['SPY', 'AAPL', 'QQQ', 'TSLA', 'MSFT'])
    collection.add_argument('--output', default='data/snapshots')
    collection.add_argument('--max-expiries', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'collect':
        from .collect import collect
        for path in collect(args.tickers, args.output, args.max_expiries):
            print(path)
        return 0
    import json
    from .research import run_research
    paths = []
    for item in map(Path, args.input):
        if item.is_dir():
            paths.extend(item.glob('*.csv'))
        elif item.is_file():
            paths.append(item)
        elif str(item) != 'data/snapshots':
            parser.error(f'Input not found: {item}')
    options = json.loads(args.backtest_config.read_text()) if args.backtest_config else {}
    try:
        config = BacktestConfig(**options)
        report = run_research(sorted(set(paths)), args.output, args.models, config)
    except (ValueError, TypeError) as error:
        parser.error(str(error))
    print(f"{report['status']}: {report['labeled_rows']} labeled observations; report: {args.output}/report.json")
    if report['status'] != 'ready':
        print(report['reason'])
        print(report['next_step'])
    return 2 if args.require_ready and report['status'] != 'ready' else 0


if __name__ == '__main__':
    raise SystemExit(main())
