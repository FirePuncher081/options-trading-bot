"""Cash-constrained historical long-call simulation with explicit fill assumptions."""
from dataclasses import asdict, dataclass
import math
import pandas as pd

TRADE_COLUMNS = ['contract', 'ticker', 'entry_time', 'exit_time', 'entry_price',
                 'exit_price', 'quantity', 'cost', 'entry_bid', 'pnl']


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000
    allocation: float = .05
    max_positions: int = 5
    max_per_ticker: int = 2
    min_volume: int = 10
    min_open_interest: int = 10
    max_spread_pct: float = .20
    fee_per_contract: float = .65
    slippage_bps: float = 10
    probability_threshold: float = .55
    multiplier: int = 100

    def __post_init__(self):
        if not self.initial_cash > 0 or not 0 < self.allocation <= 1:
            raise ValueError('Cash must be positive and allocation must be in (0, 1].')
        if any(not math.isfinite(float(v)) for v in asdict(self).values()):
            raise ValueError('Backtest parameters must be finite.')
        if not 0 <= self.probability_threshold <= 1 or not 0 <= self.max_spread_pct <= 1:
            raise ValueError('Threshold and spread limit must be in [0, 1].')
        if self.slippage_bps > 10_000:
            raise ValueError('Slippage cannot exceed 10,000 basis points.')
        if any(v < 0 for v in [self.min_volume, self.min_open_interest, self.fee_per_contract, self.slippage_bps]):
            raise ValueError('Liquidity limits, fees, and slippage must be nonnegative.')
        if any(not isinstance(v, int) or v <= 0 for v in [self.max_positions, self.max_per_ticker, self.multiplier]):
            raise ValueError('Position limits and multiplier must be positive integers.')


def simulate(predictions, config=BacktestConfig()):
    cash = config.initial_cash
    open_positions, trades, curve = [], [], []
    skipped = {'signal': 0, 'liquidity': 0, 'limits_or_cash': 0}
    if predictions.empty:
        return {'status': 'no_trades', 'config': asdict(config), 'trades': 0,
                'net_profit': 0., 'return_pct': 0., 'max_drawdown_pct': 0.,
                'equity_curve': [], 'skipped': skipped}, pd.DataFrame(columns=TRADE_COLUMNS)
    required = ['contractSymbol', 'ticker', 'date_collected', 'exit_date_collected',
                'ask', 'bid', 'exit_bid', 'exit_ask', 'volume', 'openInterest', 'probability']
    if not set(required) <= set(predictions):
        raise ValueError('Backtest predictions are missing required quote or signal fields.')
    frame = predictions.copy()
    for col in ['date_collected', 'exit_date_collected']:
        frame[col] = pd.to_datetime(frame[col], utc=True)
    if frame.duplicated(['contractSymbol', 'date_collected']).any():
        raise ValueError('Duplicate contract entry timestamps.')
    if (frame.exit_date_collected <= frame.date_collected).any():
        raise ValueError('Each exit must follow its entry.')
    # Every entry and exit is an event; future exits cannot fund earlier entries.
    times = sorted(set(frame.date_collected) | set(frame.exit_date_collected))
    peak, max_drawdown = cash, 0.
    for time in times:
        for position in open_positions[:]:
            if position['exit_time'] <= time:
                proceeds = position['exit_price'] * config.multiplier * position['quantity'] - config.fee_per_contract * position['quantity']
                cash += proceeds
                trades.append({**position, 'pnl': proceeds - position['cost']})
                open_positions.remove(position)
        entries = frame[frame.date_collected == time].sort_values(['probability', 'contractSymbol'], ascending=[False, True])
        for _, row in entries.iterrows():
            if not math.isfinite(row.probability) or row.probability < config.probability_threshold:
                skipped['signal'] += 1
                continue
            values = [row.bid, row.ask, row.exit_bid, row.exit_ask, row.volume, row.openInterest]
            if (not all(math.isfinite(float(v)) for v in values)
                or row.bid <= 0 or row.ask < row.bid or row.exit_bid <= 0 or row.exit_ask < row.exit_bid
                or row.volume < config.min_volume or row.openInterest < config.min_open_interest
                or (row.ask-row.bid)/((row.ask+row.bid)/2) > config.max_spread_pct):
                skipped['liquidity'] += 1
                continue
            if (len(open_positions) >= config.max_positions
                or sum(p['ticker'] == row.ticker for p in open_positions) >= config.max_per_ticker
                or any(p['contract'] == row.contractSymbol for p in open_positions)):
                skipped['limits_or_cash'] += 1
                continue
            # Snapshot execution assumes fills immediately after signal generation.
            # Entry ask + slippage, exit bid - slippage, fees on both legs.
            entry = row.ask * (1 + config.slippage_bps/10_000)
            exit_price = max(0, row.exit_bid * (1-config.slippage_bps/10_000))
            per_contract = entry*config.multiplier + config.fee_per_contract
            # Cost basis allocation prevents future exit marks from affecting sizing.
            cost_equity = cash + sum(p['cost'] for p in open_positions)
            reserved_fees = sum(p['quantity']*config.fee_per_contract for p in open_positions)
            quantity = int(min(cash-reserved_fees, cost_equity*config.allocation)
                           // (per_contract+config.fee_per_contract))
            if quantity < 1:
                skipped['limits_or_cash'] += 1
                continue
            cost = per_contract*quantity
            cash -= cost
            open_positions.append({'contract': row.contractSymbol, 'ticker': row.ticker,
                'entry_time': time.isoformat(), 'exit_time': row.exit_date_collected,
                'entry_price': float(entry), 'exit_price': float(exit_price), 'quantity': quantity,
                'cost': cost, 'entry_bid': float(row.bid)})
        # Conservatively carry open positions at entry bid less closing costs.
        # No intermediate quotes are assumed: this is NOT daily marked-to-market.
        equity = cash + sum((p['entry_bid']*(1-config.slippage_bps/10_000)*config.multiplier
                            - config.fee_per_contract)*p['quantity'] for p in open_positions)
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, (peak-equity)/peak)
        curve.append({'date': time.isoformat(), 'equity': round(equity, 2), 'cash': round(cash, 2), 'positions': len(open_positions)})
    result = pd.DataFrame(trades, columns=TRADE_COLUMNS)
    if len(result):
        result['exit_time'] = result.exit_time.map(lambda t: t.isoformat())
    summary = {'status': 'completed' if trades else 'no_trades', 'config': asdict(config),
        'trades': len(trades), 'net_profit': round(cash-config.initial_cash, 2),
        'return_pct': (cash/config.initial_cash-1)*100, 'max_drawdown_pct': max_drawdown*100,
        'drawdown_method': 'event-time equity; open positions held at entry bid less liquidation costs, not daily market marks',
        'equity_curve': curve, 'skipped': skipped}
    return summary, result
