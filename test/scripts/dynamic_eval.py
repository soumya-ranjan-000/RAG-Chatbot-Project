#!/usr/bin/env python3
"""
DeepEval Dynamic Conversational Evaluator
=========================================
Evaluates executed dynamic test runs in `test/run/<timestamp>/`
(specifically runs under `dynamic_simulation/`).

Executes both:
1. Deterministic Contract Evaluations (via centralized `conv_metrics`):
   - Tool Correctness
   - Tool Call Order
   - UI Widget Validation
   - Performance SLA
   - Negative Constraints
2. DeepEval LLM-as-a-Judge Conversational Metrics:
   - RoleAdherenceMetric
   - ConversationCompletenessMetric
   - TurnRelevancyMetric / Conversational Relevancy
   - FaithfulnessMetric

Outputs a terminal scorecard and saves `evaluation_report.json` inside the targeted run directory.

Usage:
  # Evaluate latest dynamic run with contract checks only (no LLM judge API needed)
  python scripts/dynamic_eval.py --skip-llm

  # Evaluate latest dynamic run with LLM judge metrics
  python scripts/dynamic_eval.py --run latest

  # Dry-run evaluation preview
  python scripts/dynamic_eval.py --dry-run
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

from scripts.conv_metrics import (
    evaluate_deterministic_contracts,
    evaluate_llm_metrics,
    resolve_judge_model,
)
from scripts.golden_bridge import (
    get_default_runs_dir,
    get_latest_run_dir,
    get_run_timestamp_dir,
    load_dataset_for_evaluation,
    prune_old_runs,
)


def evaluate_dynamic_run(
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = "latest",
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
    model_name: Optional[str] = None,
    skip_llm: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates dynamic runs matching filters.
    """
    # 1. Resolve run directory
    if run_timestamp == "latest":
        target_run_dir = get_latest_run_dir(runs_root=runs_dir)
    else:
        target_run_dir = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)

    print(f"📁 Target Run Location: {target_run_dir.resolve() if target_run_dir else 'Not found'}")

    # 2. Load test cases from run folder
    test_cases = load_dataset_for_evaluation(
        runs_dir=runs_dir,
        run_timestamp=run_timestamp,
        category_filter=category_filter,
        scenario_filter=scenario_filter,
        variation_filter=variation_filter,
    )

    # Filter to dynamic_simulation cases
    dynamic_cases = []
    for tc in test_cases:
        meta = getattr(tc, "metadata", {}) or {}
        g_link = meta.get("golden_link") or {}
        t_mode = str(g_link.get("target_mode") or meta.get("target_mode") or "").lower()
        if "dynamic" in t_mode or not t_mode:
            dynamic_cases.append(tc)

    target_cases = dynamic_cases if dynamic_cases else test_cases

    if not target_cases:
        print(f"[Warning] No dynamic test cases found to evaluate in {target_run_dir}")
        return {"total": 0, "passed": 0, "failed": 0, "cases": []}

    print(f"🎯 Evaluating {len(target_cases)} dynamic test case(s).")

    # 3. Setup LLM judge
    judge_model = None
    if not skip_llm and not dry_run:
        judge_model = resolve_judge_model(model_name=model_name)
        if not judge_model:
            print("[Notice] No LLM API key detected for judge model. Skipping LLM metrics and running contract checks only.")
            skip_llm = True

    eval_results: List[Dict[str, Any]] = []

    print("\n" + "=" * 85)
    print(f"{'TestCase ID':<26} | {'Turns':<5} | {'Contracts':<12} | {'LLM Metrics':<15} | {'Status':<6}")
    print("=" * 85)

    for tc in target_cases:
        var_id = getattr(tc, "name", "unknown")
        turns = getattr(tc, "turns", []) or []
        turn_count = len(turns) // 2 if len(turns) > 1 else len(turns)

        # 4. Deterministic Contracts Check
        det_result = evaluate_deterministic_contracts(tc)
        det_status = "✅ PASS" if det_result["all_passed"] else "❌ FAIL"

        # 5. DeepEval LLM Judge Metrics
        llm_status = "⏭️ SKIPPED"
        llm_metrics_dict: Dict[str, Any] = {}

        if not skip_llm and not dry_run and judge_model:
            llm_pass, llm_metrics_dict, llm_status = evaluate_llm_metrics(
                test_case=tc,
                judge_model=judge_model,
            )

        case_passed = det_result["all_passed"] and (skip_llm or dry_run or "PASS" in llm_status)
        status_label = "PASS" if case_passed else "FAIL"

        print(f"{var_id:<26} | {turn_count:<5} | {det_status:<12} | {llm_status:<15} | {status_label:<6}")

        if not det_result["all_passed"]:
            for check_name, check_data in det_result.items():
                if isinstance(check_data, dict) and check_data.get("errors"):
                    for err in check_data["errors"]:
                        print(f"   ❌ [{check_name}] {err}")

        eval_results.append({
            "testcase_id": var_id,
            "scenario": getattr(tc, "scenario", ""),
            "expected_outcome": getattr(tc, "expected_outcome", ""),
            "passed": case_passed,
            "deterministic_checks": det_result,
            "llm_metrics": llm_metrics_dict,
            "turns_count": len(turns),
            "thread_id": (getattr(tc, "metadata", {}) or {}).get("thread_id"),
        })

    passed_total = sum(1 for r in eval_results if r["passed"])
    failed_total = len(eval_results) - passed_total

    print("=" * 85)
    print(f"🏁 Dynamic Evaluation Summary: {passed_total}/{len(eval_results)} PASSED | {failed_total} FAILED")
    print("=" * 85)

    report_data = {
        "evaluator": "dynamic_eval",
        "run_location": str(target_run_dir),
        "run_timestamp": run_timestamp,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_testcases": len(eval_results),
        "passed_testcases": passed_total,
        "failed_testcases": failed_total,
        "results": eval_results,
    }

    if target_run_dir and target_run_dir.exists() and not dry_run:
        report_file = target_run_dir / "dynamic_evaluation_report.json"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"📊 Saved Evaluation Report: {report_file}")
        except Exception as e:
            print(f"[Warning] Could not write report file: {e}")

    return report_data


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Dynamic Multi-Turn Conversational Evaluator."
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
        "--model",
        "-m",
        type=str,
        default=None,
        help="LLM judge model override (e.g. 'gemini-2.5-flash', 'gpt-4o-mini').",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM-as-a-judge evaluation and only run deterministic contract checks.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview test cases and deterministic checks without calling judges or writing reports.",
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
    print("⚖️  DeepEval Dynamic Conversational Evaluator")
    print("=" * 85)
    print(f"🎯 Target Run:       {args.run_timestamp}")
    print(f"🎯 Filter Category:  {args.category or 'All'}")
    print(f"🎯 Filter Scenario:  {args.scenario or 'All'}")
    print(f"🎯 Filter Variation: {args.variation or 'All'}")
    print(f"🤖 Judge Model:      {args.model or 'Auto-detect'}")
    print(f"⚙️  Skip LLM:         {args.skip_llm}")
    print(f"⚙️  Dry-Run:          {args.dry_run}")
    if args.prune_runs:
        print(f"🧹 Prune Runs:       Keep latest {args.prune_runs}")
    print("=" * 85)

    start_time = time.time()
    evaluate_dynamic_run(
        runs_dir=args.run_dir,
        run_timestamp=args.run_timestamp,
        category_filter=args.category,
        scenario_filter=args.scenario,
        variation_filter=args.variation,
        model_name=args.model,
        skip_llm=args.skip_llm,
        dry_run=args.dry_run,
    )
    duration = round(time.time() - start_time, 2)
    print(f"⏱️  Evaluation finished in {duration}s.\n")

    if args.prune_runs and args.prune_runs > 0:
        runs_root = Path(args.run_dir) if args.run_dir else get_default_runs_dir()
        prune_old_runs(runs_root=runs_root, keep_last=args.prune_runs)


if __name__ == "__main__":
    main()

