"""Dependency-free demo for post-earnings trough/rebound analysis.

This script is intentionally simple and uses built-in synthetic 2024 data so
you can run it immediately without pandas, yfinance, or network access.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from statistics import mean
from typing import Dict, List


@dataclass
class DemoEvent:
    ticker: str
    earnings_date: str
    pre_close: float
    closes_after_event: List[float]


DEMO_EVENTS: List[DemoEvent] = [
    DemoEvent("PYPL", "2024-02-08", 63.0, [56.5, 55.2, 56.8, 58.9, 61.4, 62.0, 64.1, 65.0]),
    DemoEvent("SQ", "2024-05-03", 77.0, [72.1, 70.5, 69.8, 70.2, 71.7, 73.4, 75.6, 76.2]),
    DemoEvent("SHOP", "2024-08-07", 69.0, [61.2, 59.9, 60.3, 62.1, 63.8, 66.2, 68.7, 70.4]),
]


def analyze(events: List[DemoEvent], trough_window: int, rebound_window: int) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for event in events:
        prices = event.closes_after_event
        trough_slice = prices[: max(trough_window, 1)]
        trough_price = min(trough_slice)
        trough_idx = trough_slice.index(trough_price)

        rebound_slice = prices[trough_idx : trough_idx + max(rebound_window, 1)]
        rebound_price = max(rebound_slice)
        rebound_idx = trough_idx + rebound_slice.index(rebound_price)

        rows.append(
            {
                "ticker": event.ticker,
                "earnings_date": event.earnings_date,
                "pre_close": event.pre_close,
                "trough_price": trough_price,
                "rebound_price": rebound_price,
                "drawdown_pct": (trough_price / event.pre_close - 1) * 100,
                "rebound_from_trough_pct": (rebound_price / trough_price - 1) * 100,
                "recovery_vs_pre_pct": (rebound_price / event.pre_close - 1) * 100,
                "days_to_trough": trough_idx + 1,
                "days_to_rebound": rebound_idx + 1,
                "recovered_to_pre": rebound_price >= event.pre_close,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a local rebound-analysis demo with synthetic 2024 events.")
    parser.add_argument("--trough-window", type=int, default=3)
    parser.add_argument("--rebound-window", type=int, default=8)
    args = parser.parse_args()

    rows = analyze(DEMO_EVENTS, args.trough_window, args.rebound_window)
    for row in rows:
        print(
            f"{row['ticker']} {row['earnings_date']} | drawdown={row['drawdown_pct']:.2f}% "
            f"| rebound={row['rebound_from_trough_pct']:.2f}% "
            f"| recovered={row['recovered_to_pre']}"
        )

    recovery_rate = mean(1.0 if row["recovered_to_pre"] else 0.0 for row in rows)
    print(f"\nDemo recovery rate: {recovery_rate * 100:.1f}%")


if __name__ == "__main__":
    main()
