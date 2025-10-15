"""Analyze historical earnings misses for trough and rebound behavior.

This script is an initial prototype for studying how stocks behave after
negative earnings surprises. It pulls earnings history and price data from the
Yahoo Finance community API via `yfinance`, measures the trough and rebound
following earnings misses, and summarizes empirical recovery probabilities.

Example usage
-------------

    python scripts/earnings_rebound_analysis.py --tickers MSFT PYPL INTC \
        --limit 8 --trough-window 10 --rebound-window 30 --output-csv results.csv

The output includes per-event metrics (drawdown, rebound strength, timing) and
aggregate summaries per ticker, including Wilson-binomial confidence intervals
for the probability of recovering to the pre-miss close.
"""
from __future__ import annotations

import argparse
import dataclasses
import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

try:  # yfinance is an optional dependency in the repo environment
    import yfinance as yf
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise SystemExit(
        "Missing dependency `yfinance`. Install requirements.txt before running "
        "this script."
    ) from exc


@dataclass
class EventAnalysis:
    ticker: str
    earnings_date: pd.Timestamp
    eps_estimate: Optional[float]
    reported_eps: Optional[float]
    surprise_pct: Optional[float]
    pre_close: float
    event_close: Optional[float]
    trough_date: pd.Timestamp
    trough_price: float
    rebound_date: pd.Timestamp
    rebound_price: float
    drawdown_pct: float
    rebound_from_trough_pct: float
    recovery_vs_pre_pct: float
    days_to_trough: int
    days_trough_to_rebound: int
    recovered_to_pre: bool

    def as_dict(self) -> Dict[str, object]:
        data = dataclasses.asdict(self)
        data["earnings_date"] = self.earnings_date.date()
        data["trough_date"] = self.trough_date.date()
        data["rebound_date"] = self.rebound_date.date()
        return data


def wilson_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if total == 0:
        return (math.nan, math.nan)
    alpha = 1 - confidence
    z = NormalDist().inv_cdf(1 - alpha / 2)
    phat = successes / total
    denominator = 1 + z ** 2 / total
    centre = phat + z ** 2 / (2 * total)
    margin = z * math.sqrt((phat * (1 - phat) + z ** 2 / (4 * total)) / total)
    lower = (centre - margin) / denominator
    upper = (centre + margin) / denominator
    return max(0.0, lower), min(1.0, upper)


def fetch_earnings_events(ticker: str, limit: int) -> pd.DataFrame:
    ticker_obj = yf.Ticker(ticker)
    events = ticker_obj.get_earnings_dates(limit=limit)
    if events is None or events.empty:
        return pd.DataFrame()
    events = events.reset_index().rename(columns={"index": "earnings_date", "Earnings Date": "earnings_date"})
    events["earnings_date"] = pd.to_datetime(events["earnings_date"]).dt.tz_localize(None)
    events["is_miss"] = events["Reported EPS"] < events["EPS Estimate"]
    events["surprise_pct"] = events.get("Surprise(%)")
    return events


def download_price_window(
    ticker: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.Series:
    history = yf.download(
        ticker,
        start=start,
        end=end + pd.Timedelta(days=1),  # inclusive of final day
        auto_adjust=True,
        progress=False,
    )
    if history.empty:
        raise ValueError(f"No price data returned for {ticker} between {start} and {end}")
    closes = history["Close"].copy()
    closes.index = closes.index.tz_localize(None)
    return closes


def analyze_event(
    ticker: str,
    event_row: pd.Series,
    trough_window: int,
    rebound_window: int,
    prebuffer_days: int,
) -> Optional[EventAnalysis]:
    event_date: pd.Timestamp = event_row["earnings_date"]
    window_start = event_date - pd.Timedelta(days=prebuffer_days)
    window_end = event_date + pd.Timedelta(days=rebound_window)

    closes = download_price_window(ticker, window_start, window_end)

    pre_event_prices = closes[closes.index < event_date]
    if pre_event_prices.empty:
        return None
    pre_close = float(pre_event_prices.iloc[-1])

    event_day_prices = closes.loc[(closes.index >= event_date) & (closes.index <= event_date)]
    event_close = float(event_day_prices.iloc[-1]) if not event_day_prices.empty else None

    trough_prices = closes.loc[
        (closes.index > event_date)
        & (closes.index <= event_date + pd.Timedelta(days=trough_window))
    ]
    if trough_prices.empty:
        return None
    trough_idx = trough_prices.idxmin()
    trough_price = float(trough_prices.loc[trough_idx])

    rebound_prices = closes.loc[
        (closes.index >= trough_idx)
        & (closes.index <= event_date + pd.Timedelta(days=rebound_window))
    ]
    if rebound_prices.empty:
        return None
    rebound_idx = rebound_prices.idxmax()
    rebound_price = float(rebound_prices.loc[rebound_idx])

    drawdown_pct = (trough_price / pre_close - 1) * 100
    rebound_from_trough_pct = (rebound_price / trough_price - 1) * 100
    recovery_vs_pre_pct = (rebound_price / pre_close - 1) * 100
    days_to_trough = int((trough_idx - event_date).days)
    days_trough_to_rebound = int((rebound_idx - trough_idx).days)
    recovered_to_pre = rebound_price >= pre_close

    return EventAnalysis(
        ticker=ticker,
        earnings_date=event_date,
        eps_estimate=float(event_row.get("EPS Estimate")) if not pd.isna(event_row.get("EPS Estimate")) else None,
        reported_eps=float(event_row.get("Reported EPS")) if not pd.isna(event_row.get("Reported EPS")) else None,
        surprise_pct=float(event_row.get("surprise_pct")) if not pd.isna(event_row.get("surprise_pct")) else None,
        pre_close=pre_close,
        event_close=event_close,
        trough_date=trough_idx,
        trough_price=trough_price,
        rebound_date=rebound_idx,
        rebound_price=rebound_price,
        drawdown_pct=drawdown_pct,
        rebound_from_trough_pct=rebound_from_trough_pct,
        recovery_vs_pre_pct=recovery_vs_pre_pct,
        days_to_trough=days_to_trough,
        days_trough_to_rebound=days_trough_to_rebound,
        recovered_to_pre=recovered_to_pre,
    )


def analyze_ticker(
    ticker: str,
    limit: int,
    trough_window: int,
    rebound_window: int,
    prebuffer_days: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    events = fetch_earnings_events(ticker, limit=limit)
    miss_events = events[events["is_miss"]]
    analyses: List[EventAnalysis] = []

    for _, event_row in miss_events.iterrows():
        try:
            analysis = analyze_event(
                ticker,
                event_row,
                trough_window=trough_window,
                rebound_window=rebound_window,
                prebuffer_days=prebuffer_days,
            )
        except ValueError:
            continue
        if analysis is not None:
            analyses.append(analysis)

    per_event_df = pd.DataFrame([a.as_dict() for a in analyses])

    summary_rows: List[Dict[str, object]] = []
    if not per_event_df.empty:
        recovered_count = int(per_event_df["recovered_to_pre"].sum())
        total = len(per_event_df)
        ci_low, ci_high = wilson_interval(recovered_count, total)
        summary_rows.append(
            {
                "ticker": ticker,
                "events_analyzed": total,
                "recovery_rate": recovered_count / total,
                "recovery_rate_ci_low": ci_low,
                "recovery_rate_ci_high": ci_high,
                "median_drawdown_pct": per_event_df["drawdown_pct"].median(),
                "median_rebound_from_trough_pct": per_event_df["rebound_from_trough_pct"].median(),
                "median_recovery_vs_pre_pct": per_event_df["recovery_vs_pre_pct"].median(),
                "median_days_to_trough": per_event_df["days_to_trough"].median(),
                "median_days_trough_to_rebound": per_event_df["days_trough_to_rebound"].median(),
            }
        )

    summary_df = pd.DataFrame(summary_rows)
    return per_event_df, summary_df


def run_analysis(
    tickers: Sequence[str],
    limit: int,
    trough_window: int,
    rebound_window: int,
    prebuffer_days: int,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    per_event_frames: List[pd.DataFrame] = []
    summary_frames: List[pd.DataFrame] = []

    for ticker in tickers:
        per_event_df, summary_df = analyze_ticker(
            ticker,
            limit=limit,
            trough_window=trough_window,
            rebound_window=rebound_window,
            prebuffer_days=prebuffer_days,
        )
        if not per_event_df.empty:
            per_event_frames.append(per_event_df)
        if not summary_df.empty:
            summary_frames.append(summary_df)

    all_events = pd.concat(per_event_frames, ignore_index=True) if per_event_frames else pd.DataFrame()
    all_summary = pd.concat(summary_frames, ignore_index=True) if summary_frames else pd.DataFrame()
    return all_events, all_summary


def format_pct(value: float) -> str:
    return f"{value:.2f}%" if pd.notna(value) else "N/A"


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze post-earnings rebounds after misses.")
    parser.add_argument("--tickers", nargs="+", required=True, help="Ticker symbols to evaluate.")
    parser.add_argument("--limit", type=int, default=12, help="Number of earnings events to request per ticker.")
    parser.add_argument(
        "--trough-window",
        type=int,
        default=10,
        help="Days after earnings to search for the trough (trading days).",
    )
    parser.add_argument(
        "--rebound-window",
        type=int,
        default=30,
        help="Days after earnings to search for the rebound high.",
    )
    parser.add_argument(
        "--prebuffer-days",
        type=int,
        default=5,
        help="Days of history before the event to download for baseline prices.",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default=None,
        help="Optional path to write the per-event results as CSV.",
    )
    parser.add_argument(
        "--summary-csv",
        type=str,
        default=None,
        help="Optional path to write the per-ticker summary as CSV.",
    )

    args = parser.parse_args(argv)

    per_event_df, summary_df = run_analysis(
        args.tickers,
        limit=args.limit,
        trough_window=args.trough_window,
        rebound_window=args.rebound_window,
        prebuffer_days=args.prebuffer_days,
    )

    if per_event_df.empty:
        print("No qualifying earnings misses were found with sufficient price data.")
    else:
        print("Per-event results:")
        display_cols = [
            "ticker",
            "earnings_date",
            "eps_estimate",
            "reported_eps",
            "surprise_pct",
            "pre_close",
            "trough_date",
            "trough_price",
            "rebound_date",
            "rebound_price",
            "drawdown_pct",
            "rebound_from_trough_pct",
            "recovery_vs_pre_pct",
            "days_to_trough",
            "days_trough_to_rebound",
            "recovered_to_pre",
        ]
        print(per_event_df[display_cols].to_string(index=False))

    if not summary_df.empty:
        print("\nPer-ticker recovery probabilities (Wilson 95% CI):")
        formatted = summary_df.copy()
        formatted["recovery_rate"] = formatted["recovery_rate"].map(lambda x: format_pct(x * 100))
        formatted["recovery_rate_ci_low"] = formatted["recovery_rate_ci_low"].map(lambda x: format_pct(x * 100))
        formatted["recovery_rate_ci_high"] = formatted["recovery_rate_ci_high"].map(lambda x: format_pct(x * 100))
        formatted["median_drawdown_pct"] = formatted["median_drawdown_pct"].map(format_pct)
        formatted["median_rebound_from_trough_pct"] = formatted["median_rebound_from_trough_pct"].map(format_pct)
        formatted["median_recovery_vs_pre_pct"] = formatted["median_recovery_vs_pre_pct"].map(format_pct)
        print(formatted.to_string(index=False))

    if args.output_csv and not per_event_df.empty:
        per_event_df.to_csv(args.output_csv, index=False)
        print(f"\nPer-event results exported to {args.output_csv}")

    if args.summary_csv and not summary_df.empty:
        summary_df.to_csv(args.summary_csv, index=False)
        print(f"Summary exported to {args.summary_csv}")


if __name__ == "__main__":
    main()
