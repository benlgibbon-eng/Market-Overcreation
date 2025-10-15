# Modeling Approach for Post-Earnings Bottom Detection and Rebound Forecasting

This document outlines a practical roadmap for a trader who wants to anticipate
how far a stock may fall after an earnings miss and how strongly it might
rebound. The goal is to build a workflow that combines event detection,
price-path analysis, and statistical modeling of recovery probabilities.

## 1. Framing the Problem

1. **Event definition** – Identify a clear trigger such as an earnings report
   where the reported EPS is below the consensus estimate or where forward
   guidance is cut. Other events (FDA decisions, product recalls) can be added
   later with the same framework.
2. **Outcome variables** – For each event, measure:
   - The *drawdown* from the close immediately before the announcement to the
     subsequent trough.
   - The *rebound magnitude* from that trough to the first meaningful recovery
     point (e.g., reclaiming the pre-event close or the 20-day moving average).
   - The *timing* of the trough and rebound in trading days.
3. **Predictive objective** – Estimate the probability that a future miss will
   recover to a chosen target level within a specified time horizon, and the
   expected upside if it does.

## 2. Data Requirements

| Data set | Usage | Possible sources |
| --- | --- | --- |
| **Earnings history** (release dates, estimates, actuals, surprises, guidance) | Define events, quantify surprise magnitude | APIs like Refinitiv, FactSet, Intrinio, Polygon, Alpha Vantage, or the Yahoo Finance community API used in the prototype.
| **Daily (or intraday) OHLCV prices** | Measure pre-event baseline, trough, rebound | Same providers as above or direct exchange feeds.
| **Options implied volatility surfaces** | Gauge sentiment/hedging demand and calibrate expected move | OptionMetrics, CBOE, ORATS, Tradier, IQFeed.
| **Short interest / borrow rates** | Capture positioning stress | Exchange data, S3 Partners.
| **Analyst rating changes & news sentiment** | Refine sentiment input | Benzinga, TipRanks, RavenPack, Refinitiv News Analytics.
| **Macro controls** (index levels, sector ETFs) | Normalize for market-wide moves | FRED, Quandl, Yahoo Finance.

## 3. Sentiment & Expectation Signals

1. **Options-implied move** – Compare the earnings-night move with the
   straddle-implied move from ATM options. A larger-than-implied selloff may
   point to capitulation.
2. **Volatility term structure** – A spike in front-end implied volatility
   relative to back months can indicate panic; a quick normalization suggests
   capitulation is over.
3. **Order flow / volume anomalies** – Use volume, short-term VWAP slippage,
   and dark pool ratios as proxies for aggressive selling.
4. **Short interest and borrow cost** – Elevated borrow cost plus heavy
   covering can mark turning points.
5. **News & transcript sentiment** – NLP scores on management commentary and
   analyst questions help capture post-call tone.
6. **Relative strength vs. sector / factor indices** – A rebound that starts
   with sector leadership can highlight genuine rotation instead of a
   dead-cat bounce.

## 4. Feature Engineering

For each event, create features available either before or shortly after the
miss:

- **Magnitude of surprise**: `(Reported EPS - Estimate) / |Estimate|` and
  revenue surprise.
- **Gap size**: Opening gap relative to pre-event close.
- **Initial drawdown**: Intraday low vs. prior close on the first trading day
  after the event.
- **Volume spike**: Volume multiples vs. 20-day average.
- **Options skew & IV**: 25-delta put-call skew, implied vol percentile.
- **Market backdrop**: Same-day move of the index/sector ETF, VIX move.
- **Positioning metrics**: Short interest ratio, ETF flows.

## 5. Modeling Ideas

1. **Event-study analytics** – Build baselines by ticker, sector, and surprise
   bucket. Evaluate the empirical distribution of drawdowns and rebound
   magnitudes. This yields priors for Bayesian models.
2. **Hazard / survival models** – Model the time to trough and time to
   recovery using survival analysis with censoring (when recovery fails to
   occur within the horizon).
3. **Hierarchical Bayesian models** – Allow partial pooling across tickers and
   sectors to improve estimates for names with few misses.
4. **Classification / regression** – Train gradient-boosted trees or logistic
   regression on engineered features to predict whether the stock will recover
   to a target level within *N* days and the expected rebound magnitude.
5. **Scenario simulation** – Combine the predictive distribution of recovery
   outcomes with trade sizing rules (Kelly, risk-parity) for practical
   decision-making.

## 6. Workflow Outline

1. **Data ingestion** – Pull earnings events and daily OHLCV data. Store in a
   structured format (e.g., DuckDB or PostgreSQL) keyed by ticker and event
   date.
2. **Event labeling** – Identify misses and compute features. Label outcomes
   (recovered/not recovered) given a rebound definition (e.g., closing back
   above the 10-day EMA within 20 trading days).
3. **Exploratory analysis** – Visualize price paths and compute descriptive
   statistics by sector, market cap, and surprise magnitude.
4. **Model training** – Use cross-validation with walk-forward splits to avoid
   look-ahead bias. Evaluate AUC for classification, MAE for rebound size, and
   calibration curves for probability estimates.
5. **Deployment** – Wrap the trained model in a service or script that ingests
   the latest earnings miss, updates sentiment metrics, and outputs probability
   and expected return distributions.
6. **Monitoring** – Track model calibration over time and incorporate new
   events to refresh priors.

## 7. Prototype

The accompanying Python script (`scripts/earnings_rebound_analysis.py`) provides
an end-to-end, data-sourced example. It focuses on historical earnings misses,
identifies trough and rebound windows, and estimates empirical probabilities of
recovering to the pre-miss price. The prototype is intentionally lightweight
and uses Yahoo Finance data, making it suitable for initial research before
upgrading to institutional-grade data feeds.

