from types import SimpleNamespace
import sys
import pandas as pd
from options_lab.collect import collect


def test_collector_preserves_old_files_and_records_capture_time(monkeypatch,tmp_path):
    class Stock:
        options=['2026-06-30']
        def history(self,**kwargs):return pd.DataFrame({'Close':[100.]})
        def option_chain(self,expiry):return SimpleNamespace(calls=pd.DataFrame({'contractSymbol':['TEST_CALL'],'bid':[1.],'ask':[1.1]}))
    monkeypatch.setitem(sys.modules,'yfinance',SimpleNamespace(Ticker=lambda symbol:Stock()))
    first=collect(['TEST'],tmp_path)[0]
    original=first.read_bytes()
    second=collect(['TEST'],tmp_path)[0]
    assert first!=second and first.read_bytes()==original
    result=pd.read_csv(second)
    assert result.ticker.iloc[0]=='TEST'
    assert result.spot_price.iloc[0]==100.
    assert result.date_collected.iloc[0].endswith('+00:00')
