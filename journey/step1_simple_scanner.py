import yfinance as yf
import datetime

TICKER = "AAPL"
# Choose target stock

def fetch_options_chain(ticker):
    stock = yf.Ticker(ticker)
    print(f"\nFetching options for: {ticker}")

    #Get most recent expiration date
    try:
        expiry = stock.options[0]
    except IndexError:
        print("no options data available.")
        return
    
    print (f"using expiry: {expiry}")

    #Fetch option chain for the date
    opt_chain = stock.option_chain(expiry)
    calls = opt_chain.calls

    #Filter high volume calls
    high_volume = calls[calls['volume'] > 100]

    #Show Result
    print("\nTop Call Options by Volume:\n")
    print(high_volume[['contractSymbol', 'strike', 'lastPrice', 'volume', 'impliedVolatility']].head(10))

if __name__ == "__main__":
    fetch_options_chain(TICKER)
    