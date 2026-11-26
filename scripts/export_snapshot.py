#!/usr/bin/env python3
"""Export only the public MOON view from the existing dashboard implementation."""
import argparse
import asyncio
import datetime
import importlib
import json
from pathlib import Path
import sys

PERIODS = ("10y", "5y", "3y", "1y", "ytd")
VIEWS = ("all-pro", "all", "dzi", "atlas")
BEIJING = datetime.timezone(datetime.timedelta(hours=8))


def public_payload(payload, risk_metrics):
    strategies = []
    for strategy in payload["strategies"]:
        curve = [
            {field: point[field] for field in ("date", "net_value", "drawdown")}
            for point in strategy["equity_curve"]
        ]
        if not curve:
            raise ValueError("Missing performance curve; keeping the previous snapshot")
        trades = []
        if strategy["view"] in ("dzi", "atlas"):
            trades = [
                {field: trade.get(field) for field in
                 ("ts", "symbol", "direction", "offset", "trade_price", "traded", "close_pnl")}
                for trade in strategy["recent_trades"]
            ]
        strategies.append({
            "view": strategy["view"],
            "title": strategy["title"],
            "start_date": strategy["start_date"],
            "end_date": strategy["end_date"],
            "equity_curve": curve,
            "monthly_returns": [
                {field: row[field] for field in ("year", "month", "return_pct", "end_date")}
                for row in strategy["monthly_returns"]
            ],
            "annual_returns": [
                {field: row[field] for field in ("year", "return_pct", "end_date")}
                for row in strategy["annual_returns"]
            ],
            "recent_trades": trades,
            "risk_metrics": {"sharpe": risk_metrics(strategy["equity_curve"])["sharpe"]},
        })
    if tuple(strategy["view"] for strategy in strategies) != VIEWS:
        raise ValueError("Unexpected strategy list; keeping the previous snapshot")
    return {"period": payload["period"], "updated_at": payload["updated_at"],
            "strategies": strategies}


async def build_snapshot(dashboard, moon):
    redis = await dashboard.get_redis()
    try:
        credential = await redis.get(dashboard.AUTH_TOKEN_KEY)
        if not credential:
            raise RuntimeError("Dashboard data source is unavailable")
        payloads = await asyncio.gather(*(
            dashboard.get_all_dashboards(
                token=credential, view=view,
                period_years=dashboard.AllWeatherPeriodYears.RECENT_10)
            for view in ("all-pro", "all", "mas", "dzi", "atlas")
        ))
        if any(payload.get("error") for payload in payloads):
            raise RuntimeError("Dashboard data export failed")
        today = datetime.datetime.now(BEIJING).date()
        periods = {
            period: public_payload(
                moon.build_moon_payload(payloads, period, today=today),
                dashboard.build_all_weather_risk_metrics)
            for period in PERIODS
        }
        return {"schema_version": 1,
                "generated_at": datetime.datetime.now(BEIJING).isoformat(timespec="seconds"),
                "periods": periods}
    finally:
        await redis.aclose()
        await dashboard.pool.disconnect()


def write_snapshot(snapshot, output_dir):
    content = json.dumps(snapshot, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "moon.json"
    temporary = output_dir / "moon.json.tmp"
    temporary.write_text(content + "\n", encoding="utf-8")
    temporary.replace(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dashboard-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.dashboard_dir.resolve()))
    dashboard = importlib.import_module("dashboard_server")
    moon = importlib.import_module("moon_dashboard")
    snapshot = asyncio.run(build_snapshot(dashboard, moon))
    output = write_snapshot(snapshot, args.output_dir)
    print(f"Exported {len(PERIODS)} periods, {len(VIEWS)} strategies; {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
