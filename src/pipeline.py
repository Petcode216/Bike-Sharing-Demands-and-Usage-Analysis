"""End-to-end pipeline: ingest -> validate -> clean -> analyse -> figures -> report.

Run from the project root:  python -m src.pipeline
"""
import sys

from src.analysis.results import compute_all, export_tables
from src.data.clean import run_pipeline
from src.data.ingest import extract_raw
from src.data.validate import run_all_checks, write_report
from src.visualization.figures import save_all


def main() -> int:
    print("1/6 Ingest:", extract_raw())
    checks = run_all_checks()
    blocking = [c for c in checks if not c.passed and c.blocking]
    print(f"2/6 Validate: {len(checks)} checks, {len(blocking)} blocking failures ->", write_report(checks))
    if blocking:
        for c in blocking:
            print("   FAIL:", c.table, c.check, c.detail)
        return 1
    print("3/6 Clean:", run_pipeline())
    res = compute_all()
    print(f"4/6 Analyse: {len(export_tables(res))} tables exported")
    print(f"5/6 Figures: {len(save_all(res.day, res.hour, res.correlations, res.regression))} saved")
    from src.reporting.build_report import build_report
    print("6/6 Report:", build_report(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
