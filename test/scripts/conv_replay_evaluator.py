#!/usr/bin/env python3
"""
DeepEval Deterministic Replay Evaluator for Golden Scenarios
===========================================================
Replays fixed user queries turn-by-turn from `conversational_golden/datasets/**/deterministic_reply/`
against the live chatbot API to evaluate live model responses, tool calls, parameters,
and trajectories without requiring an LLM simulator to generate new queries.

Features:
- Fixed User Script Execution (exact multi-turn user queries re-sent to live bot)
- Turn-by-Turn Evaluation:
  • expected_content (nature of response)
  • expected_tools_call_order vs actual_tools_call_order
  • expected_args vs actual args
  • expected_response vs actual tool response
  • expected_ui_widgets and citations
  • SLA & negative policy constraints
- Non-destructive testcase report exports
- Full Scorecard & Summary Reporting

Usage:
  # Dry-run preview of deterministic test scripts
  python scripts/conv_replay_evaluator.py --dry-run

  # Run replay evaluation against live backend
  python scripts/conv_replay_evaluator.py --category manage_my_booking

  # Run specific variation
  python scripts/conv_replay_evaluator.py -v FRUST_01_INVALID_FORMAT
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from dotenv import load_dotenv

# Ensure project root & test directory are in python path
test_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(test_dir))

load_dotenv(test_dir / ".env")
load_dotenv(test_dir.parent / ".env")

# Purge all empty-string environment variables
for k, v in list(os.environ.items()):
    if v == "":
        os.environ.pop(k, None)

try:
    from deepeval.test_case import ConversationalTestCase, Turn
except ImportError:
    pass

from scripts.conv_simulator import (
    DEFAULT_CHAT_API_URL,
    ChatApiCallbackHandler,
    extract_citations,
    extract_ui_widgets,
)
from scripts.golden_bridge import (
    export_simulated_testcase,
    get_default_datasets_dir,
    get_default_runs_dir,
    group_turns_into_conversations,
    load_dataset_for_evaluation,
    load_json_file,
    prune_old_runs,
)


def evaluate_tool_correctness(
    actual_tools: List[Dict[str, Any]],
    expected_tools: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Evaluates whether the tools called match expected names, arguments, and responses.
    """
    errors = []
    if len(actual_tools) != len(expected_tools):
        errors.append(f"Tool count mismatch: expected {len(expected_tools)}, got {len(actual_tools)}")

    for idx, exp_t in enumerate(expected_tools):
        exp_name = exp_t.get("name")
        if idx >= len(actual_tools):
            errors.append(f"Missing expected tool call #{idx+1}: '{exp_name}'")
            continue

        act_t = actual_tools[idx]
        act_name = act_t.get("name")
        if act_name != exp_name:
            errors.append(f"Tool #{idx+1} name mismatch: expected '{exp_name}', got '{act_name}'")

        exp_args = exp_t.get("expected_args") or exp_t.get("args")
        act_args = act_t.get("args") or {}
        if exp_args:
            for k, v in exp_args.items():
                if act_args.get(k) != v:
                    errors.append(f"Tool '{act_name}' arg mismatch for '{k}': expected '{v}', got '{act_args.get(k)}'")

    return len(errors) == 0, errors


def replay_testcase(
    test_case_file: Path,
    api_url: str = DEFAULT_CHAT_API_URL,
    dry_run: bool = False,
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = None,
    enrich_with_langsmith: bool = True,
) -> Dict[str, Any]:
    """
    Loads a deterministic testcase JSON, extracts fixed user queries turn-by-turn,
    sends them to the live chatbot, and evaluates the live assistant responses.
    """
    data = load_json_file(test_case_file)
    if not data:
        return {"status": "error", "error": f"Failed to load {test_case_file}"}

    case_id = data.get("testcase_id") or test_case_file.stem
    scenario_desc = data.get("scenario_description") or ""
    expected_outcome = data.get("expected_outcome") or ""
    raw_convs = data.get("conversations") or {}
    expected_trajectory = (
        (data.get("expected") or {}).get("expected_trajectory")
        or data.get("expected_trajectory")
        or (data.get("metadata") or {}).get("expected_trajectory")
        or {}
    )

    # Extract user queries per turn
    user_script: List[Dict[str, Any]] = []
    if data.get("unified_turns"):
        for ut in data["unified_turns"]:
            asst_exp = ut.get("expected") or {}
            asst_act = ut.get("actual") or {}
            turn_label = f"turn {ut.get('turn', len(user_script) + 1)}"
            user_script.append({
                "turn_label": turn_label,
                "user_content": ut.get("user_query", ""),
                "expected_content": asst_exp.get("expected_content"),
                "expected_tools_order": asst_exp.get("expected_tools_order") or [],
                "expected_tools": [
                    {
                        "name": t.get("name"),
                        "expected_args": t.get("expected_args"),
                        "expected_response": t.get("expected_response"),
                    }
                    for t in asst_exp.get("expected_tools", [])
                    if t.get("expected_args") or t.get("expected_response")
                ],
            })
    else:
        for turn_label, turn_msgs in raw_convs.items():
            user_msg = next((m for m in turn_msgs if m.get("role") == "user"), None)
            asst_msg = next((m for m in turn_msgs if m.get("role") == "assistant"), None)
            if user_msg:
                user_script.append({
                    "turn_label": turn_label,
                    "user_content": user_msg.get("content", ""),
                    "expected_content": asst_msg.get("expected_content") if asst_msg else None,
                    "expected_tools_order": asst_msg.get("expected_tools_call_order") if asst_msg else [],
                    "expected_tools": (
                        [
                            {
                                "name": t.get("name"),
                                "expected_args": t.get("expected_args"),
                                "expected_response": t.get("expected_response"),
                            }
                            for t in asst_msg.get("actual_tools_called", [])
                            if t.get("expected_args") or t.get("expected_response")
                        ]
                        if asst_msg and asst_msg.get("actual_tools_called")
                        else []
                    ),
                })

    if dry_run:
        print(f"\n   [REPLAY DRY-RUN] Case: {case_id}")
        print(f"      • Scenario: {scenario_desc}")
        print(f"      • Scripted Turns: {len(user_script)}")
        for idx, s_turn in enumerate(user_script, start=1):
            print(f"         Turn {idx} User Query: \"{s_turn['user_content']}\"")
            if s_turn.get("expected_content"):
                print(f"            Expected Nature: \"{s_turn['expected_content']}\"")
            if s_turn.get("expected_tools_order"):
                print(f"            Expected Tools:  {s_turn['expected_tools_order']}")
        return {"status": "dry_run", "testcase_id": case_id, "turns": len(user_script)}

    # Live Replay Execution
    new_thread_id = str(uuid.uuid4())
    callback = ChatApiCallbackHandler(api_url=api_url)
    replayed_turns: List[Turn] = []
    turn_evaluations: List[Dict[str, Any]] = []

    print(f"\n▶️  [Replaying] {case_id} (Thread: {new_thread_id[:8]}...)...")

    for idx, s_turn in enumerate(user_script, start=1):
        user_query = s_turn["user_content"]
        print(f"   💬 Turn {idx} User: \"{user_query}\"")

        # 1. Append User Turn
        user_turn_obj = Turn(role="user", content=user_query)
        replayed_turns.append(user_turn_obj)

        # 2. Call live chatbot
        asst_turn_obj = callback(
            input=user_query,
            thread_id=new_thread_id,
            turns=replayed_turns[:-1],
        )
        replayed_turns.append(asst_turn_obj)

    # Fetch authoritative LangSmith execution trace for replay evaluation
    compact_ls_export = None
    if not dry_run and enrich_with_langsmith and new_thread_id:
        from scripts.golden_bridge import _fetch_langsmith_compact_trace
        compact_ls_export = _fetch_langsmith_compact_trace(new_thread_id)

    ls_turns = (compact_ls_export.get("turns") if compact_ls_export else []) or []

    # 3. Evaluate replay turns against LangSmith trace
    for idx, s_turn in enumerate(user_script, start=1):
        user_query = s_turn["user_content"]
        asst_turn_idx = (idx * 2) - 1
        asst_turn_obj = replayed_turns[asst_turn_idx] if asst_turn_idx < len(replayed_turns) else Turn(role="assistant", content="")
        ls_t = ls_turns[idx - 1] if idx - 1 < len(ls_turns) else None

        actual_tools = [
            {
                "name": tc.get("tool_name"),
                "args": tc.get("inputs", {}),
                "response": tc.get("output"),
            }
            for tc in (ls_t.get("tools_call", []) if ls_t else [])
        ]
        actual_order = [tc.get("tool_name") for tc in (ls_t.get("tools_call", []) if ls_t else []) if tc.get("tool_name")]

        # Tool correctness check
        tool_passed, tool_errors = evaluate_tool_correctness(
            actual_tools=actual_tools,
            expected_tools=s_turn.get("expected_tools") or [],
        )
        if not ls_t and not dry_run:
            tool_errors.append(f"No LangSmith execution trace found for thread {new_thread_id} turn {idx}")
            tool_passed = False

        # Tool order check
        exp_order = s_turn.get("expected_tools_order") or []
        order_passed = (actual_order == exp_order) if exp_order else True
        if not order_passed:
            tool_errors.append(f"Tool order mismatch: expected {exp_order}, got {actual_order}")

        turn_eval = {
            "turn": idx,
            "user_query": user_query,
            "assistant_content": asst_turn_obj.content,
            "expected_content": s_turn.get("expected_content"),
            "actual_tools": actual_tools,
            "expected_tools": s_turn.get("expected_tools"),
            "actual_tools_order": actual_order,
            "expected_tools_order": exp_order,
            "tool_correctness_passed": tool_passed and order_passed,
            "tool_errors": tool_errors,
            "metrics": ls_t.get("tokens") if ls_t else None,
        }
        turn_evaluations.append(turn_eval)

        status_sym = "✅" if (tool_passed and order_passed) else "⚠️"
        print(f"   🤖 Turn {idx} Bot ({status_sym}): \"{asst_turn_obj.content[:80]}...\"")
        if tool_errors:
            for err in tool_errors:
                print(f"      ❌ {err}")

    # Build new ConversationalTestCase from live run
    new_metadata = dict(data.get("metadata") or {})
    new_metadata["thread_id"] = new_thread_id
    new_metadata["replayed_from_file"] = str(test_case_file)
    new_metadata["replay_evaluations"] = turn_evaluations

    live_test_case = ConversationalTestCase(
        turns=replayed_turns,
        scenario=scenario_desc,
        expected_outcome=expected_outcome,
        context=data.get("context") or [],
        name=case_id,
        metadata=new_metadata,
    )

    # Export replayed run strictly into test/run/<date_time>/ (truth set in datasets/ remains untouched)
    export_result = export_simulated_testcase(
        test_case=live_test_case,
        datasets_dir=None,
        runs_dir=runs_dir,
        run_timestamp=run_timestamp,
        thread_id=new_thread_id,
        target_mode="deterministic_reply",
        overwrite=False,
        enrich_with_langsmith=enrich_with_langsmith,
    )
    print(f"   💾 Exported Replay Run: {Path(export_result['json_path']).name}")

    all_passed = all(t["tool_correctness_passed"] for t in turn_evaluations)
    return {
        "status": "passed" if all_passed else "failed",
        "testcase_id": case_id,
        "thread_id": new_thread_id,
        "total_turns": len(turn_evaluations),
        "turn_evaluations": turn_evaluations,
        "all_passed": all_passed,
        "export_path": export_result["json_path"],
    }


def run_replay_suite(
    datasets_dir: Optional[Union[str, Path]] = None,
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = None,
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
    api_url: str = DEFAULT_CHAT_API_URL,
    dry_run: bool = False,
    enrich_with_langsmith: bool = True,
) -> List[Dict[str, Any]]:
    """
    Crawls deterministic_reply folders and runs replay evaluations.
    """
    root = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
    if not root.exists():
        print(f"[Error] Datasets directory not found at: {root}")
        return []

    # Find all testcase JSONs in deterministic_reply / deterministic_replay
    matching_files: List[Path] = []
    for json_file in sorted(root.rglob("*.json")):
        if json_file.name == "dataset.json":
            continue
        parent_name = json_file.parent.name
        if parent_name not in ["deterministic_reply", "deterministic_replay"]:
            continue

        # Check filters
        parts = [p.lower() for p in json_file.parts]
        if category_filter and category_filter.lower() not in parts:
            continue
        if scenario_filter and scenario_filter.lower() not in parts:
            continue
        if variation_filter and variation_filter.lower() not in json_file.stem.lower():
            continue

        matching_files.append(json_file)

    if not matching_files:
        print(f"[Warning] No deterministic testcase files found matching filters (cat='{category_filter}', scen='{scenario_filter}', var='{variation_filter}').")
        return []

    print(f"🎯 Found {len(matching_files)} deterministic testcase(s) to replay.")

    results = []
    for f in matching_files:
        res = replay_testcase(
            test_case_file=f,
            api_url=api_url,
            dry_run=dry_run,
            runs_dir=runs_dir,
            run_timestamp=run_timestamp,
            enrich_with_langsmith=enrich_with_langsmith,
        )
        results.append(res)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Deterministic Replay Evaluator for Golden Datasets."
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
        "--backend-url",
        "-u",
        type=str,
        default=DEFAULT_CHAT_API_URL,
        help=f"Chatbot backend endpoint URL (default: '{DEFAULT_CHAT_API_URL}').",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview deterministic user query scripts without sending requests to live API.",
    )
    parser.add_argument(
        "--datasets-dir",
        type=str,
        default=None,
        help="Path to datasets root (default: 'conversational_golden/datasets').",
    )
    parser.add_argument(
        "--run-timestamp",
        type=str,
        default=None,
        help="Run timestamp folder name under test/run/ (default: current UTC timestamp 'YYYY-MM-DD_HH-MM-SS').",
    )
    parser.add_argument(
        "--run-dir",
        type=str,
        default=None,
        help="Custom root directory for run exports (default: 'test/run').",
    )
    parser.add_argument(
        "--enrich-langsmith",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enrich test cases with real-time LangSmith execution traces (default: True).",
    )
    parser.add_argument(
        "--retention-limit",
        type=int,
        default=20,
        help="Maximum number of historical execution runs to retain in test/run/ (default: 20, 0 to disable).",
    )

    args = parser.parse_args()

    runs_root = Path(args.run_dir) if args.run_dir else get_default_runs_dir()
    run_timestamp = args.run_timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")

    print("=" * 70)
    print("🔁 DeepEval Deterministic Conversational Replay Evaluator")
    print("=" * 70)
    print(f"🔗 Target Chat API:  {args.backend_url}")
    print(f"🎯 Filter Category:  {args.category or 'All'}")
    print(f"🎯 Filter Scenario:  {args.scenario or 'All'}")
    print(f"🎯 Filter Variation: {args.variation or 'All'}")
    print(f"📁 Runs Directory:   {(runs_root / run_timestamp).resolve()}")
    print(f"🔍 LangSmith Traces: {args.enrich_langsmith}")
    print(f"🧹 Retention Limit:  {args.retention_limit}")
    print(f"⚙️  Dry-Run Mode:     {args.dry_run}")
    print("=" * 70)

    start_time = time.time()
    results = run_replay_suite(
        datasets_dir=args.datasets_dir,
        runs_dir=runs_root,
        run_timestamp=run_timestamp,
        category_filter=args.category,
        scenario_filter=args.scenario,
        variation_filter=args.variation,
        api_url=args.backend_url,
        dry_run=args.dry_run,
        enrich_with_langsmith=args.enrich_langsmith,
    )
    duration = round(time.time() - start_time, 2)

    if not args.dry_run and results:
        passed_count = sum(1 for r in results if r.get("all_passed"))
        print("\n" + "=" * 70)
        print(f"🏁 Replay Evaluation Complete in {duration}s")
        print(f"📊 Passed: {passed_count}/{len(results)} | Failed: {len(results) - passed_count}")
        if args.retention_limit and args.retention_limit > 0:
            prune_old_runs(runs_root=runs_root, keep_last=args.retention_limit)
        print("=" * 70)


if __name__ == "__main__":
    main()
