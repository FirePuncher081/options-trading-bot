import pandas as pd
import pytest


@pytest.fixture
def history_file(tmp_path):
    """Synthetic quotes for code verification only, never dashboard evidence."""
    rows = []
    for day in range(32):
        for contract in range(8):
            mid = 2 + (.025 if contract % 2 else -.015)*day
            rows.append(dict(contractSymbol=f'TEST_CALL_{contract}', ticker=f'T{contract%3}',
                date_collected=(pd.Timestamp('2026-01-01', tz='UTC') + pd.Timedelta(days=day,hours=16)).isoformat(),
                expiry='2026-06-30', bid=mid-.02, ask=mid+.02, strike=90+contract*5,
                volume=100, openInterest=200, impliedVolatility=.2+contract*.03,spot_price=100,lastPrice=mid))
    path = tmp_path/'synthetic.csv'
    pd.DataFrame(rows).to_csv(path,index=False)
    return path
