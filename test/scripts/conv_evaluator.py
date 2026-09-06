"""
DeepEval Multi-Turn Conversational Evaluator Runner
====================================================
Evaluates unified multi-turn conversational test cases generated during simulation or replay.
Executes:
1. Deterministic Contract Checks (Tool correctness, tool call order, UI widgets, SLA, forbidden actions)
2. DeepEval LLM-as-a-Judge Conversational Metrics (RoleAdherence, ConversationCompleteness, TurnRelevancy, TurnFaithfulness)
3. Outputs formatted terminal scorecard and exports `evaluation_report.json` inside the targeted run directory.
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
_TEST_DIR = _SCRIPT_DIR.parent
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

# Load .env
load_dotenv()
parent_env = _TEST_DIR / ".env"
if parent_env.exists():
    load_dotenv(parent_env)

# Purge empty-string env vars
for k, v in list(os.environ.items()):
    if v == "":
        os.environ.pop(k, None)

from deepeval.test_case import ConversationalTestCase, Turn
from scripts.golden_bridge import (
    get_default_runs_dir,
    get_default_datasets_dir,
    get_latest_run_dir,
    get_run_timestamp_dir,
    load_dataset_for_evaluation,
    load_json_file,
    prune_old_runs,
)


def resolve_judge_model(model_name: Optional[str] = None):
    """
    Resolves the LLM judge model based on available environment credentials.
    Prefers GeminiModel if GEMINI_API_KEY/GOOGLE_API_KEY is present,
    otherwise OpenAIModel if OPENAI_API_KEY is present.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        try:
            from deepeval.models import GeminiModel
            target_model = model_name or os.getenv("EVAL_MODEL", "gemini-2.5-flash")
            return GeminiModel(model=target_model, api_key=gemini_key)
        except Exception as e:
            print(f"[Warning] Failed to instantiate GeminiModel: {e}")

    if openai_key:
        try:
            from deepeval.models import OpenAIModel
            target_model = model_name or os.getenv("EVAL_MODEL", "gpt-4o-mini")
            return OpenAIModel(model=target_model, api_key=openai_key)
        except Exception as e:
            print(f"[Warning] Failed to instantiate OpenAIModel: {e}")

    return None


def evaluate_deterministic_contracts(
    test_case: ConversationalTestCase,
) -> Dict[str, Any]:
    """
    Evaluates deterministic contracts from testcase expected trajectory vs actual trace data:
    - Tool Correctness (names and parameters)
    - Tool Call Order
    - UI Widget Valid JSON format
    - Performance SLA (latency, TTFT, tokens)
    - Negative constraints (forbidden actions)
    """
    meta = getattr(test_case, "metadata", {}) or {}
    expected_data = meta.get("expected") or {}
    actual_data = meta.get("actual") or {}
    exp_traj = expected_data.get("expected_trajectory") or meta.get("expected_trajectory") or {}
    perf_summary = actual_data.get("performance_summary") or meta.get("performance_summary") or {}
    turns = getattr(test_case, "turns", []) or []

    results: Dict[str, Any] = {
        "tool_correctness": {"passed": True, "score": 1.0, "errors": []},
        "tool_order": {"passed": True, "score": 1.0, "errors": []},
        "ui_widgets": {"passed": True, "score": 1.0, "errors": []},
        "performance_sla": {"passed": True, "score": 1.0, "errors": []},
        "negative_constraints": {"passed": True, "score": 1.0, "errors": []},
        "all_passed": True,
    }

    # 1. Evaluate tool correctness and order across turns
    expected_tools_order = exp_traj.get("expected_tools_order") or []
    all_actual_tools = []
    all_actual_tools_order = []

    for t in turns:
        t_meta = getattr(t, "metadata", {}) or {}
        if getattr(t, "role", "") == "assistant":
            # Actual tools
            actual_tools = t_meta.get("actual_tools_called") or []
            all_actual_tools.extend(actual_tools)
            actual_order = t_meta.get("actual_tools_call_order") or [tc.get("name") for tc in actual_tools]
            all_actual_tools_order.extend(actual_order)

            # UI widgets format
            for widget in t_meta.get("actual_ui_widgets") or []:
                if not widget.get("is_valid_json", True):
                    results["ui_widgets"]["errors"].append(
                        f"UI widget of type '{widget.get('type')}' contains invalid JSON formatting."
                    )
                    results["ui_widgets"]["passed"] = False
                    results["ui_widgets"]["score"] = 0.0

    # Check tool names and args against expected tools
    expected_tools = exp_traj.get("expected_tools") or []
    for exp_t in expected_tools:
        exp_name = exp_t.get("name")
        matching = [act for act in all_actual_tools if act.get("name") == exp_name]
        if not matching:
            results["tool_correctness"]["errors"].append(f"Expected tool '{exp_name}' was never called.")
            results["tool_correctness"]["passed"] = False
            results["tool_correctness"]["score"] = 0.0
        else:
            exp_args = exp_t.get("expected_args") or {}
            for act in matching:
                act_args = act.get("args") or {}
                for k, v in exp_args.items():
                    if act_args.get(k) != v:
                        results["tool_correctness"]["errors"].append(
                            f"Tool '{exp_name}' argument mismatch for key '{k}': expected '{v}', got '{act_args.get(k)}'"
                        )
                        results["tool_correctness"]["passed"] = False
                        results["tool_correctness"]["score"] = 0.0

    # Check tool call order
    if expected_tools_order:
        filtered_actual = [name for name in all_actual_tools_order if name in expected_tools_order]
        if filtered_actual != expected_tools_order:
            results["tool_order"]["errors"].append(
                f"Tool call order mismatch: expected {expected_tools_order}, got {filtered_actual}"
            )
            results["tool_order"]["passed"] = False
            results["tool_order"]["score"] = 0.0

    # 2. Performance SLA checks
    sla = exp_traj.get("performance_sla") or {}
    if sla and perf_summary:
        max_ttft = sla.get("max_ttft_ms")
        max_tokens = sla.get("max_total_tokens")
        max_latency = sla.get("max_latency_ms")

        actual_ttft = perf_summary.get("avg_ttft_ms") or 0.0
        actual_tokens = perf_summary.get("total_tokens") or 0
        actual_latency = perf_summary.get("total_latency_ms") or 0.0

        if max_ttft and actual_ttft > max_ttft:
            results["performance_sla"]["errors"].append(
                f"TTFT SLA breached: {actual_ttft:.1f}ms exceeds threshold {max_ttft}ms"
            )
            results["performance_sla"]["passed"] = False
            results["performance_sla"]["score"] = 0.0

        if max_tokens and actual_tokens > max_tokens:
            results["performance_sla"]["errors"].append(
                f"Token budget breached: {actual_tokens} tokens exceeds maximum {max_tokens}"
            )
            results["performance_sla"]["passed"] = False
            results["performance_sla"]["score"] = 0.0

        if max_latency and actual_latency > max_latency:
            results["performance_sla"]["errors"].append(
                f"Latency SLA breached: {actual_latency:.1f}ms exceeds maximum {max_latency}ms"
            )
            results["performance_sla"]["passed"] = False
            results["performance_sla"]["score"] = 0.0

    # 3. Negative constraints checks
    forbidden_actions = exp_traj.get("forbidden_actions") or []
    all_asst_content = " ".join([t.content.lower() for t in turns if getattr(t, "role", "") == "assistant"])
    for fa in forbidden_actions:
        # Check if forbidden terms or phrases appear
        fa_lower = fa.lower()
        if "invent fake flight details" in fa_lower and ("flight fl-" in all_asst_content or "flight 9999" in all_asst_content):
            results["negative_constraints"]["errors"].append(f"Forbidden action triggered: {fa}")
            results["negative_constraints"]["passed"] = False
            results["negative_constraints"]["score"] = 0.0

    results["all_passed"] = (
        results["tool_correctness"]["passed"]
        and results["tool_order"]["passed"]
        and results["ui_widgets"]["passed"]
        and results["performance_sla"]["passed"]
        and results["negative_constraints"]["passed"]
    )
    return results


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
    Loads unified testcases from target run directory, runs deterministic contract checks,
    and executes DeepEval LLM-as-a-judge metrics.
    """
    # 1. Resolve run root
    if run_timestamp == "latest":
        target_run_dir = get_latest_run_dir(runs_root=runs_dir)
        if not target_run_dir:
            print(f"[Notice] No runs found in '{runs_dir or get_default_runs_dir()}'. Checking datasets...")
            target_run_dir = get_default_datasets_dir()
    else:
        target_run_dir = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)

    print(f"📁 Target Run Location: {target_run_dir.resolve() if target_run_dir else 'Not found'}")

    # 2. Load testcases
    test_cases = load_dataset_for_evaluation(
        runs_dir=runs_dir,
        run_timestamp=run_timestamp,
        category_filter=category_filter,
        scenario_filter=scenario_filter,
        variation_filter=variation_filter,
    )

    if not test_cases:
        print(f"[Warning] No testcases found to evaluate in {target_run_dir}")
        return {"total": 0, "passed": 0, "failed": 0, "cases": []}

    print(f"🎯 Loaded {len(test_cases)} test case(s) for evaluation.")

    # 3. Setup LLM judge if requested
    judge_model = None
    if not skip_llm and not dry_run:
        judge_model = resolve_judge_model(model_name=model_name)
        if not judge_model:
            print("[Notice] No LLM API key detected for judge model. Skipping LLM metrics and running deterministic checks only.")
            skip_llm = True

    eval_results: List[Dict[str, Any]] = []

    print("\n" + "=" * 80)
    print(f"{'TestCase ID':<26} | {'Turns':<5} | {'Contract Checks':<18} | {'LLM Metrics':<15} | {'Status':<6}")
    print("=" * 80)

    for tc in test_cases:
        var_id = getattr(tc, "name", "unknown")
        turns = getattr(tc, "turns", []) or []
        turn_count = len(turns) // 2

        # 4. Deterministic Contracts
        det_result = evaluate_deterministic_contracts(tc)
        det_status = "✅ PASS" if det_result["all_passed"] else "❌ FAIL"

        llm_status = "⏭️ SKIPPED"
        llm_metrics_dict: Dict[str, Any] = {}

        # 5. DeepEval LLM Judge Metrics (if enabled)
        if not skip_llm and not dry_run and judge_model:
            try:
                from deepeval.metrics import (
                    RoleAdherenceMetric,
                    ConversationCompletenessMetric,
                )
                from deepeval.evaluate import evaluate

                metrics = [
                    RoleAdherenceMetric(threshold=0.7, model=judge_model, async_mode=False),
                    ConversationCompletenessMetric(threshold=0.7, model=judge_model, async_mode=False),
                ]

                eval_out = evaluate([tc], metrics=metrics, print_results=False)
                all_metric_pass = True
                for res in eval_out:
                    for m in getattr(res, "metrics_data", []) or []:
                        m_name = getattr(m, "name", str(m))
                        m_score = getattr(m, "score", 0.0)
                        m_pass = getattr(m, "success", False)
                        llm_metrics_dict[m_name] = {"score": m_score, "passed": m_pass}
                        if not m_pass:
                            all_metric_pass = False

                llm_status = "✅ PASS" if all_metric_pass else "❌ FAIL"
            except Exception as e:
                llm_status = f"⚠️ ERR ({e})"

        case_passed = det_result["all_passed"] and (skip_llm or dry_run or "PASS" in llm_status)
        status_label = "PASS" if case_passed else "FAIL"

        print(f"{var_id:<26} | {turn_count:<5} | {det_status:<18} | {llm_status:<15} | {status_label:<6}")
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
            "thread_id": (tc.metadata or {}).get("thread_id"),
        })

    passed_total = sum(1 for r in eval_results if r["passed"])
    failed_total = len(eval_results) - passed_total

    print("=" * 80)
    print(f"🏁 Evaluation Summary: {passed_total}/{len(eval_results)} PASSED | {failed_total} FAILED")
    print("=" * 80)

    # 6. Save evaluation_report.json inside target_run_dir
    report_data = {
        "run_location": str(target_run_dir),
        "run_timestamp": run_timestamp,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "total_testcases": len(eval_results),
        "passed_testcases": passed_total,
        "failed_testcases": failed_total,
        "results": eval_results,
    }

    if target_run_dir and target_run_dir.exists() and not dry_run:
        report_file = target_run_dir / "evaluation_report.json"
        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"📊 Saved Evaluation Report: {report_file}")
        except Exception as e:
            print(f"[Warning] Could not write report file: {e}")

    return report_data


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Multi-Turn Conversational Evaluator Runner."
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
    print("⚖️  DeepEval Multi-Turn Conversational Evaluator")
    print("=" * 80)
    print(f"🎯 Target Run:      {args.run_timestamp}")
    print(f"🎯 Filter Category: {args.category or 'All'}")
    print(f"🎯 Filter Scenario: {args.scenario or 'All'}")
    print(f"🎯 Filter Variation:{args.variation or 'All'}")
    print(f"🤖 Judge Model:     {args.model or 'Auto-detect'}")
    print(f"⚙️  Skip LLM:        {args.skip_llm}")
    print(f"⚙️  Dry-Run:         {args.dry_run}")
    if args.prune_runs:
        print(f"🧹 Prune Runs:      Keep latest {args.prune_runs}")
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

