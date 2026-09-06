#!/usr/bin/env python3
"""
DeepEval Multi-Turn Conversational Evaluator Runner (Legacy Wrapper)
===================================================================
Provides backward compatibility for existing scripts, test suites, and CI.
Delegates to:
- `deterministic_eval.py` for deterministic test cases / replay runs
- `dynamic_eval.py` for dynamic simulation runs
- `conv_metrics.py` for centralized metrics & contract checks
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

_SCRIPT_DIR = Path(__file__).resolve().parent
_TEST_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _TEST_DIR.parent

for p in [str(_TEST_DIR), str(_PROJECT_ROOT), str(_SCRIPT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

load_dotenv(_TEST_DIR / ".env")
load_dotenv(_PROJECT_ROOT / ".env")

# Re-export centralized metrics for backward compatibility
from scripts.conv_metrics import (
    evaluate_deterministic_contracts,
    evaluate_llm_metrics,
    evaluate_negative_constraints,
    evaluate_performance_sla,
    evaluate_tool_correctness,
    evaluate_tool_order,
    evaluate_ui_widgets,
    get_default_deepeval_metrics,
    register_custom_metric,
    resolve_judge_model,
)
from scripts.deterministic_eval import evaluate_deterministic_run
from scripts.dynamic_eval import evaluate_dynamic_run
from scripts.golden_bridge import (
    get_default_datasets_dir,
    get_default_runs_dir,
    get_latest_run_dir,
    get_run_timestamp_dir,
    load_dataset_for_evaluation,
    prune_old_runs,
)


def run_evaluation_suite(
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
    Backward-compatible evaluation suite runner.
    Loads unified testcases from target run directory and executes contract checks and metrics.
    """
    return evaluate_dynamic_run(
        runs_dir=runs_dir,
        run_timestamp=run_timestamp,
        category_filter=category_filter,
        scenario_filter=scenario_filter,
        variation_filter=variation_filter,
        model_name=model_name,
        skip_llm=skip_llm,
        dry_run=dry_run,
    )


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Multi-Turn Conversational Evaluator Runner (Legacy Wrapper)."
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

    print("=" * 80)
    print("⚖️  DeepEval Multi-Turn Conversational Evaluator (Legacy Wrapper)")
    print("=" * 80)
    print(f"🎯 Target Run:       {args.run_timestamp}")
    print(f"🎯 Filter Category:  {args.category or 'All'}")
    print(f"🎯 Filter Scenario:  {args.scenario or 'All'}")
    print(f"🎯 Filter Variation: {args.variation or 'All'}")
    print(f"🤖 Judge Model:      {args.model or 'Auto-detect'}")
    print(f"⚙️  Skip LLM:         {args.skip_llm}")
    print(f"⚙️  Dry-Run:          {args.dry_run}")
    if args.prune_runs:
        print(f"🧹 Prune Runs:       Keep latest {args.prune_runs}")
    print("=" * 80)

    start_time = time.time()
    run_evaluation_suite(
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
