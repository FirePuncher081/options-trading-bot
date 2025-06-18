import yfinance as yf
import pandas as pd
from datetime import datetime
import os

def fetch_calls(ticker, max_expiries=10):
    print(f"🔍 Fetching options for {ticker}")
    stock = yf.Ticker(ticker)
    expirations = stock.options[:max_expiries]
    all_calls = []

    for exp in expirations:
        try:
            calls = stock.option_chain(exp).calls.copy()
            calls["expiration"] = exp
            calls["retrieved"] = datetime.now()
            all_calls.append(calls)
        except Exception as e:
            print(f"⚠️ Error on {exp} for {ticker}: {e}")

    if not all_calls:
        print(f"❌ No options for {ticker}")
        return None

    df = pd.concat(all_calls)
    df["ticker"] = ticker
    df.reset_index(drop=True, inplace=True)

    # Save file
    filename = f"data/raw/{ticker}_calls_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(filename, index=False)
    print(f"✅ Saved to {filename}")
    return df

if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "TSLA", "GOOGL", "AMD"]
    for t in tickers:
        fetch_calls(t)