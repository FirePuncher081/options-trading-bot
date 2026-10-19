from dataclasses import replace
import pandas as pd
import pytest
from options_lab.backtest import BacktestConfig,simulate


def quotes(**overrides):
    row=dict(contractSymbol='CALL',ticker='TEST',date_collected='2026-01-01T16:00Z',
        exit_date_collected='2026-01-02T16:00Z',bid=1.9,ask=2.,exit_bid=2.2,exit_ask=2.3,
        volume=100,openInterest=100,probability=.8)
    row.update(overrides);return row


def test_costs_fill_sides_and_full_cash_reconciliation():
    config=BacktestConfig(initial_cash=1000,allocation=.5,slippage_bps=100)
    report,trades=simulate(pd.DataFrame([quotes()]),config)
    assert len(trades)==1;assert trades.quantity.iloc[0]==2
    expected=(2.2*.99*100-.65)*2-(2*1.01*100+.65)*2
    assert report['net_profit']==pytest.approx(expected)
    assert report['equity_curve'][-1]['cash']==pytest.approx(1000+expected)
    assert report['max_drawdown_pct']>0


def test_no_future_cash_position_limits_and_overlaps():
    config=BacktestConfig(initial_cash=1000,allocation=.8,max_positions=1)
    report,trades=simulate(pd.DataFrame([quotes(exit_bid=10,exit_ask=10.1),quotes(contractSymbol='OTHER',ticker='OTHER',probability=.7)]),config)
    assert len(trades)==1;assert report['skipped']['limits_or_cash']==1
    assert trades.quantity.iloc[0]==3
    assert min(p['cash'] for p in report['equity_curve'])>=0


def test_liquidity_signals_and_unaffordable_contracts():
    config=BacktestConfig(initial_cash=1000,allocation=.05)
    for changes,bucket in [({'probability':.1},'signal'),({'volume':0},'liquidity'),({},'limits_or_cash'),({'ask':3},'liquidity')]:
        report,trades=simulate(pd.DataFrame([quotes(**changes)]),config)
        assert report['trades']==0;assert report['skipped'][bucket]==1


def test_invalid_time_duplicate_and_config():
    with pytest.raises(ValueError): BacktestConfig(initial_cash=-1)
    with pytest.raises(ValueError): BacktestConfig(slippage_bps=float('nan'))
    with pytest.raises(ValueError,match='exit must follow'):
        simulate(pd.DataFrame([quotes(exit_date_collected='2025-01-01')]))
    with pytest.raises(ValueError,match='Duplicate'):
        simulate(pd.DataFrame([quotes(),quotes()]))


def test_ticker_cap_and_reserved_closing_fees():
    config=BacktestConfig(initial_cash=1000,allocation=1,max_positions=5,max_per_ticker=1,
                          slippage_bps=10_000)
    report,trades=simulate(pd.DataFrame([quotes(),quotes(contractSymbol='OTHER',probability=.7)]),config)
    assert len(trades)==1;assert report['skipped']['limits_or_cash']==1
    assert all(event['cash']>=0 for event in report['equity_curve'])
