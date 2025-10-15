# Earnings Miss Rebound Prototype

This repository now contains a lightweight research prototype for studying how
stocks behave after missing earnings expectations. It is intended as a starting
point for a more sophisticated modeling effort that combines event detection,
sentiment measures, and probabilistic forecasts.

## Getting Started

1. Create a virtual environment and install dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the analysis script with one or more tickers. The tool queries Yahoo
   Finance for earnings history and price data, focusing on events where the
   reported EPS fell short of consensus estimates.

   ```bash
   python scripts/earnings_rebound_analysis.py --tickers PYPL SQ SHOP \
       --limit 8 --trough-window 10 --rebound-window 30 \
       --output-csv per_event.csv --summary-csv summary.csv
   ```

   The console output lists each qualifying earnings miss, the time it took to
   find a trough, the rebound magnitude, and whether the stock regained the
   pre-miss close within the specified window. Summary statistics report the
   empirical recovery rate with a Wilson confidence interval, plus median
   drawdown and rebound metrics.

## Next Steps

- Extend the feature set with options-implied volatility, short interest, and
  news sentiment to capture market tone.
- Train probabilistic classifiers or survival models that predict recovery odds
  for upcoming earnings misses.
- Integrate with a data warehouse (e.g., DuckDB or PostgreSQL) for repeatable
  backtests and monitoring.

Consult `docs/modeling_plan.md` for a more detailed modeling roadmap.

