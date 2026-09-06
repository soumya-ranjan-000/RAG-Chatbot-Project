#!/usr/bin/env python3
"""
DeepEval Deterministic Conversational Evaluator
===============================================
Evaluates executed deterministic test runs in `test/run/<timestamp>/`
(specifically runs under `deterministic_reply/` or `deterministic_replay/`).

Executes deterministic contract evaluations using `conv_metrics`:
1. Tool Correctness (names, arguments, responses)
2. Tool Call Order (sequence of execution)
3. UI Widgets (valid JSON syntax in markdown blocks)
4. Performance SLA (TTFT, latency, token budgets)
5. Negative Constraints (forbidden actions)
6. Custom domain-specific metrics registered in `conv_metrics`

Outputs a terminal scorecard and saves `evaluation_report.json` inside the targeted run directory.

Usage:
  # Evaluate latest deterministic run
  python scripts/deterministic_eval.py --run latest

  # Dry-run evaluation preview
  python scripts/deterministic_eval.py --dry-run

  # Evaluate specific scenario run
  python scripts/deterministic_eval.py --scenario query_pnr
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

# Sys.path bootstrap
_SCRIPT_DIR = Path(__file__).resolve().parent
_TEST_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _TEST_DIR.parent

for p in [str(_TEST_DIR), str(_PROJECT_ROOT), str(_SCRIPT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv(_TEST_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")

from scripts.conv_metrics import evaluate_deterministic_contracts
from scripts.golden_bridge import (
    get_default_runs_dir,
    get_latest_run_dir,
    get_run_timestamp_dir,
    load_dataset_for_evaluation,
    prune_old_runs,
)


def evaluate_deterministic_run(
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = "latest",
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates deterministic runs matching filters.
    """
    # 1. Resolve run directory
    if run_timestamp == "latest":
        target_run_dir = get_latest_run_dir(runs_root=runs_dir)
    else:
        target_run_dir = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)

    print(f"📁 Target Run Location: {target_run_dir.resolve() if target_run_dir else 'Not found'}")

    # 2. Load test cases from the run folder
    test_cases = load_dataset_for_evaluation(
        runs_dir=runs_dir,
        run_timestamp=run_timestamp,
        category_filter=category_filter,
        scenario_filter=scenario_filter,
        variation_filter=variation_filter,
    )

    # Filter to only deterministic testcases (target_mode in ['deterministic_reply', 'deterministic_replay'])
    deterministic_cases = []
    for tc in test_cases:
        meta = getattr(tc, "metadata", {}) or {}
        g_link = meta.get("golden_link") or {}
        t_mode = str(g_link.get("target_mode") or meta.get("target_mode") or "").lower()
        if "deterministic" in t_mode or "replay" in t_mode or "reply" in t_mode:
            deterministic_cases.append(tc)
        elif not t_mode:
            # If target_mode wasn't set, inspect directory parent path
            rep_from = meta.get("replayed_from_file", "")
            if "deterministic" in rep_from:
                deterministic_cases.append(tc)
            else:
                deterministic_cases.append(tc)

    target_cases = deterministic_cases if deterministic_cases else test_cases

    if not target_cases:
        print(f"[Warning] No deterministic test cases found to evaluate in {target_run_dir}")
        return {"total": 0, "passed": 0, "failed": 0, "cases": []}

    print(f"🎯 Evaluating {len(target_cases)} deterministic test case(s).")

    eval_results: List[Dict[str, Any]] = []

    print("\n" + "=" * 85)
    print(f"{'TestCase ID':<26} | {'Turns':<5} | {'Tools':<7} | {'Order':<7} | {'SLA':<7} | {'Widgets':<7} | {'Status':<6}")
    print("=" * 85)

    for tc in target_cases:
        var_id = getattr(tc, "name", "unknown")
        turns = getattr(tc, "turns", []) or []
        turn_count = len(turns) // 2 if len(turns) > 1 else len(turns)

        det_result = evaluate_deterministic_contracts(tc)
        case_passed = det_result["all_passed"]

        tools_status = "✅ PASS" if det_result["tool_correctness"]["passed"] else "❌ FAIL"
        order_status = "✅ PASS" if det_result["tool_order"]["passed"] else "❌ FAIL"
        sla_status = "✅ PASS" if det_result["performance_sla"]["passed"] else "❌ FAIL"
        widget_status = "✅ PASS" if det_result["ui_widgets"]["passed"] else "❌ FAIL"
        overall_status = "PASS" if case_passed else "FAIL"

        print(f"{var_id:<26} | {turn_count:<5} | {tools_status:<7} | {order_status:<7} | {sla_status:<7} | {widget_status:<7} | {overall_status:<6}")

        if not case_passed:
            for check_name, check_data in det_result.items():
                if isinstance(check_data, dict) and check_data.get("errors"):
                    for err in check_data["errors"]:
                        print(f"   ❌ [{check_name}] {err}")

        eval_results.append({
            "testcase_id": var_id,
            "scenario": getattr(tc, "scenario", ""),
            "expected_outcome": getattr(tc, "expected_outcome", ""),
            "passed": case_passed,
            "contract_evaluation": det_result,
            "turns_count": len(turns),
            "thread_id": (getattr(tc, "metadata", {}) or {}).get("thread_id"),
        })

    passed_total = sum(1 for r in eval_results if r["passed"])
    failed_total = len(eval_results) - passed_total

    print("=" * 85)
    print(f"🏁 Deterministic Evaluation Summary: {passed_total}/{len(eval_results)} PASSED | {failed_total} FAILED")
    print("=" * 85)

    report_data = {
        "evaluator": "deterministic_eval",
        "run_location": str(target_run_dir),
        "run_timestamp": run_timestamp,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_testcases": len(eval_results),
        "passed_testcases": passed_total,
        "failed_testcases": failed_total,
        "results": eval_results,
    }

    if target_run_dir and target_run_dir.exists() and not dry_run:
        report_file = target_run_dir / "deterministic_evaluation_report.json"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"📊 Saved Evaluation Report: {report_file}")
        except Exception as e:
            print(f"[Warning] Could not write report file: {e}")

    return report_data


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Deterministic Conversational Evaluator."
    )
    parser.add_argument(
        "--run",
        "--run-timestamp",
        dest="run_timestamp",
        type=str,
        default="latest",
        help="Run timestamp directory to evaluate under test/run/ or 'latest' (default: 'latest').",
    )
    parser.add_argument(
        "--run-dir",
        type=str,
        default=None,
        help="Root runs directory (default: 'test/run').",
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default=None,
        help="Filter by domain category (e.g. 'manage_my_booking').",
    )
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        default=None,
        help="Filter by scenario name (e.g. 'query_pnr').",
    )
    parser.add_argument(
        "--variation",
        "-v",
        type=str,
        default=None,
        help="Filter by variation ID (e.g. 'FRUST_01_INVALID_FORMAT').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview test cases and deterministic checks without writing report.",
    )
    parser.add_argument(
        "--prune-runs",
        type=int,
        default=None,
        metavar="N",
        help="Prune old test/run/ execution folders, keeping only the N most recent.",
    )

    args = parser.parse_args()

    print("=" * 85)
    print("⚖️  DeepEval Deterministic Conversational Evaluator")
    print("=" * 85)
    print(f"🎯 Target Run:       {args.run_timestamp}")
    print(f"🎯 Filter Category:  {args.category or 'All'}")
    print(f"🎯 Filter Scenario:  {args.scenario or 'All'}")
    print(f"🎯 Filter Variation: {args.variation or 'All'}")
    print(f"⚙️  Dry-Run:          {args.dry_run}")
    if args.prune_runs:
        print(f"🧹 Prune Runs:       Keep latest {args.prune_runs}")
    print("=" * 85)

    start_time = time.time()
    evaluate_deterministic_run(
        runs_dir=args.run_dir,
        run_timestamp=args.run_timestamp,
        category_filter=args.category,
        scenario_filter=args.scenario,
        variation_filter=args.variation,
        dry_run=args.dry_run,
    )
    duration = round(time.time() - start_time, 2)
    print(f"⏱️  Evaluation finished in {duration}s.\n")

    if args.prune_runs and args.prune_runs > 0:
        runs_root = Path(args.run_dir) if args.run_dir else get_default_runs_dir()
        prune_old_runs(runs_root=runs_root, keep_last=args.prune_runs)


if __name__ == "__main__":
    main()

