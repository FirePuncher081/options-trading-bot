# scripts/pull_options_data.py
print("🚀 Script started")

import yfinance as yf
import pandas as pd
from datetime import datetime

def fetch_option_chain(ticker, max_expiries=5, save=True):
    print(f"📥 Starting fetch_option_chain for {ticker}")
    
    stock = yf.Ticker(ticker)
    expirations = stock.options
    print(f"📦 Expirations found: {expirations}")

    all_calls = []

    for exp in expirations[:max_expiries]:
        try:
            print(f"⏳ Fetching options for expiry: {exp}")
            calls = stock.option_chain(exp).calls.copy()
            calls["expiration"] = exp
            calls["retrieved"] = datetime.now()
            all_calls.append(calls)
        except Exception as e:
            print(f"⚠️ Error fetching {exp}: {e}")

    if not all_calls:
        print(f"❌ No options data collected for {ticker}")
        return None

    df = pd.concat(all_calls)
    df["ticker"] = ticker
    df.reset_index(drop=True, inplace=True)

    if save:
        path = f"data/raw/{ticker}_calls_raw.csv"
        print(f"💾 Saving to: {path}")
        df.to_csv(path, index=False)
        print(f"✅ Saved to {path}")

    return df


if __name__ == "__main__":
    print("🔧 Running script directly")
    ticker = "AAPL"
    df = fetch_option_chain(ticker)
    if df is not None:
        print("📊 Sample data:")
        print(df.head())
    else:
        print("⚠️ No data returned.")
