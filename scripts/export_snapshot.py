#!/usr/bin/env python3
"""Export only the public MOON view from the existing dashboard implementation."""
import argparse
import asyncio
import datetime
import importlib
import json
from pathlib import Path
import sys

PERIODS = ("10y", "5y", "3y", "1y", "ytd", "since_launch")
VIEWS = ("all-pro", "atlas")
SOURCE_VIEWS = ("all-pro", "all", "mas", "dzi", "atlas")
LAUNCH_DATES = {"all-pro": "20261126", "atlas": "20260927"}
BEIJING = datetime.timezone(datetime.timedelta(hours=8))


def public_payload(payload, risk_metrics):
    strategies = []
    for strategy in payload["strategies"]:
        if strategy["view"] not in VIEWS:
            continue
        curve = [
            {field: point[field] for field in ("date", "net_value", "drawdown")}
            for point in strategy["equity_curve"]
        ]
        if not curve and payload["period"] != "since_launch":
            raise ValueError("Missing performance curve; keeping the previous snapshot")
        trades = []
        if strategy["view"] == "atlas":
            trades = [
                {field: trade.get(field) for field in
                 ("ts", "symbol", "direction", "offset", "trade_price", "traded", "close_pnl")}
                for trade in strategy["recent_trades"]
            ]
        strategies.append({
            "view": strategy["view"],
            "title": strategy["title"],
            "launch_date": LAUNCH_DATES[strategy["view"]],
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
            "risk_metrics": {"sharpe": risk_metrics(strategy["equity_curve"])["sharpe"] if curve else None},
        })
    if tuple(strategy["view"] for strategy in strategies) != VIEWS:
        raise ValueError("Unexpected strategy list; keeping the previous snapshot")
    return {"period": payload["period"], "updated_at": payload["updated_at"],
            "strategies": strategies}


def launch_payload(payloads, moon, today):
    payload = moon.build_moon_payload(payloads, "10y", today=today)
    sources = dict(zip(SOURCE_VIEWS, payloads))
    strategies = []
    for strategy in payload["strategies"]:
        view = strategy["view"]
        if view not in VIEWS:
            continue
        source = sources[view]
        brief = source.get("all_weather") or next(iter(source.get("brief", [])), {})
        full = brief.get("history_curve") or brief.get("equity_curve", [])
        chart, monthly, annual = moon.performance_series(
            full, LAUNCH_DATES[view], today.strftime("%Y%m%d"))
        strategies.append(dict(
            strategy, start_date=chart[0]["date"] if chart else None,
            end_date=chart[-1]["date"] if chart else None,
            equity_curve=chart, monthly_returns=monthly, annual_returns=annual))
    return dict(payload, period="since_launch", strategies=strategies)


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
            for view in SOURCE_VIEWS
        ))
        if any(payload.get("error") for payload in payloads):
            raise RuntimeError("Dashboard data export failed")
        today = datetime.datetime.now(BEIJING).date()
        periods = {}
        for period in PERIODS:
            payload = (launch_payload(payloads, moon, today) if period == "since_launch"
                       else moon.build_moon_payload(payloads, period, today=today))
            periods[period] = public_payload(payload, dashboard.build_all_weather_risk_metrics)
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
