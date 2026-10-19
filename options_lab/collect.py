"""Append-only collection. Network requests occur only when explicitly invoked."""
from datetime import datetime, timezone
from pathlib import Path
import re


def collect(tickers, output='data/snapshots', max_expiries=4):
    import pandas as pd
    import yfinance as yf
    if max_expiries < 1:
        raise ValueError('max_expiries must be positive.')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for symbol in tickers:
        if not re.fullmatch(r'[A-Za-z0-9.^=-]{1,20}', symbol):
            raise ValueError(f'Invalid ticker: {symbol}')
        stock = yf.Ticker(symbol)
        history = stock.history(period='1d')
        if history.empty:
            raise ValueError(f'No underlying price returned for {symbol}.')
        spot = float(history.Close.iloc[-1])
        for expiry in stock.options[:max_expiries]:
            calls = stock.option_chain(expiry).calls.copy()
            if calls.empty:
                continue
            captured = datetime.now(timezone.utc)
            calls['ticker'], calls['expiry'] = symbol.upper(), expiry
            calls['spot_price'], calls['date_collected'] = spot, captured.isoformat()
            # Exclusive creation protects earlier snapshots even on retries.
            path = output/f'{symbol}_{expiry}_{captured.strftime("%Y%m%dT%H%M%S%fZ")}.csv'
            with path.open('x') as handle:
                calls.to_csv(handle, index=False)
            files.append(path)
    if not files:
        raise ValueError('No options returned; no snapshot files written.')
    return files
