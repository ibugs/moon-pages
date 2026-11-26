import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "export_snapshot", Path(__file__).parents[1] / "scripts/export_snapshot.py")
export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export)


def source_payload():
    strategy = {
        "title": "示例", "start_date": "20260101", "end_date": "20261126",
        "equity_curve": [
            {"date": "20260101", "net_value": 1.0, "drawdown": 0.0},
            {"date": "20261126", "net_value": 0.75, "drawdown": -0.25},
        ],
        "monthly_returns": [{"year": 2026, "month": 11, "return_pct": -25.0,
                             "end_date": "20261126"}],
        "annual_returns": [{"year": 2026, "return_pct": -25.0, "end_date": "20261126"}],
        "recent_trades": [{"ts": "2026-11-26T09:00:00+08:00", "symbol": "TEST.demo",
                           "direction": "BUY", "offset": "CLOSE", "trade_price": 10.5,
                           "traded": 2, "close_pnl": -3.5, "order_id": "DEMO_INTERNAL_ID"}],
    }
    return {"period": "ytd", "updated_at": "2026-11-26 09:00:00",
            "access": {"credential": "DEMO_PRIVATE_VALUE"},
            "strategies": [dict(copy.deepcopy(strategy), view=view) for view in export.VIEWS]}


class SnapshotTests(unittest.TestCase):
    def test_public_export_excludes_internal_fields(self):
        payload = source_payload()
        for strategy in payload["strategies"]:
            strategy["account_id"] = "DEMO_PRIVATE_VALUE"
            strategy["equity_curve"][0]["private"] = "DEMO_PRIVATE_VALUE"
            strategy["monthly_returns"][0]["private"] = "DEMO_PRIVATE_VALUE"
        result = export.public_payload(payload, lambda curve: {"sharpe": 1.25,
                                                              "private": "DEMO_PRIVATE_VALUE"})
        serialized = json.dumps(result)
        self.assertNotIn("DEMO_PRIVATE_VALUE", serialized)
        self.assertNotIn("DEMO_INTERNAL_ID", serialized)
        self.assertNotIn("account_id", serialized)
        self.assertEqual(result["strategies"][0]["recent_trades"], [])
        self.assertEqual(result["strategies"][1]["recent_trades"], [])

    def test_preserves_performance_and_trade_values(self):
        payload = source_payload()
        result = export.public_payload(payload, lambda curve: {"sharpe": 1.25})
        for original, public in zip(payload["strategies"], result["strategies"]):
            self.assertEqual(original["equity_curve"], public["equity_curve"])
            self.assertEqual(original["monthly_returns"], public["monthly_returns"])
            self.assertEqual(original["annual_returns"], public["annual_returns"])
            self.assertEqual(public["risk_metrics"]["sharpe"], 1.25)
        trade = result["strategies"][2]["recent_trades"][0]
        self.assertEqual(trade["trade_price"], 10.5)
        self.assertEqual(trade["close_pnl"], -3.5)

    def test_rejects_incomplete_source(self):
        payload = source_payload()
        payload["strategies"][0]["equity_curve"] = []
        with self.assertRaises(ValueError):
            export.public_payload(payload, lambda curve: {"sharpe": None})

    def test_dzi_is_excluded_and_launch_dates_are_public(self):
        payload = source_payload()
        hidden = dict(copy.deepcopy(payload["strategies"][0]), view="dzi", title="DZI")
        payload["strategies"].insert(2, hidden)
        result = export.public_payload(payload, lambda curve: {"sharpe": 1.25})
        self.assertEqual([s["view"] for s in result["strategies"]], ["all-pro", "all", "atlas"])
        self.assertEqual([s["launch_date"] for s in result["strategies"]],
                         ["20261126", "20250101", "20260927"])
        self.assertNotIn('"dzi"', json.dumps(result))

    def test_launch_period_can_wait_for_first_available_record(self):
        payload = source_payload()
        payload["period"] = "since_launch"
        payload["strategies"][0].update(
            equity_curve=[], monthly_returns=[], annual_returns=[], start_date=None, end_date=None)
        result = export.public_payload(payload, lambda curve: {"sharpe": 1.25})
        self.assertEqual(result["strategies"][0]["equity_curve"], [])
        self.assertIsNone(result["strategies"][0]["risk_metrics"]["sharpe"])

    def test_invalid_numeric_export_keeps_previous_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            destination = export.write_snapshot({"valid": True}, output_dir)
            previous = destination.read_bytes()
            with self.assertRaises(ValueError):
                export.write_snapshot({"net_value": float("nan")}, output_dir)
            self.assertEqual(destination.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
