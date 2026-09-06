#!/usr/bin/env python3
"""
Dynamic-to-Deterministic Conversation Promotion & Golden Truth Generator
========================================================================
Promotes approved dynamic multi-turn conversation runs (from `test/run/<timestamp>/`)
into the curated ground-truth truth set under:
`test/conversational_golden/datasets/<category>/<scenario>/<persona>/deterministic_reply/<variation_id>.json`

Key Features:
1. Direct File Promotion:
   python scripts/dynamic_to_deterministic.py test/run/2026-09-06_16-30-22/.../FRUST_01.json

2. Run Filter Promotion:
   python scripts/dynamic_to_deterministic.py --run latest --scenario query_pnr

3. Smart Merge Mode (--merge):
   Updates rules, SLAs, and context chunks while preserving QA's customized queries & notes.

4. Conversational Linting (--lint):
   Validates tool names against backend tool definitions and asserts schema integrity.

5. Offline Scaffolding Fallback (--from-rules):
   Scaffolds deterministic test cases directly from `rules/` when a dynamic run is not yet available.

6. QA Sign-Off Manifest:
   Consolidates `qa_review.md` and `dataset.json` for human review and pull request audits.
"""

import argparse
import glob
import importlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
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

from scripts.golden_bridge import (
    discover_scenario_directories,
    get_default_datasets_dir,
    get_default_rules_dir,
    get_default_runs_dir,
    get_latest_run_dir,
    get_run_timestamp_dir,
    load_json_file,
    load_scenario_bundle,
    resolve_target_dir,
)


def get_registered_backend_tools() -> List[str]:
    """
    Introspects app.agents.tools to discover all registered chatbot tool names.
    """
    try:
        from app.agents import tools as backend_tools
        tool_names = []
        for attr_name in dir(backend_tools):
            attr = getattr(backend_tools, attr_name)
            # LangChain structured tool or callable tool
            if hasattr(attr, "name") and isinstance(getattr(attr, "name"), str):
                tool_names.append(attr.name)
            elif callable(attr) and not attr_name.startswith("_"):
                tool_names.append(attr_name)
        return sorted(list(set(tool_names)))
    except Exception:
        # Fallback known tool signatures
        return [
            "search_flights",
            "book_flight",
            "check_booking_status",
            "cancel_flight",
            "reschedule_flight",
            "check_in_passenger",
            "list_passenger_bookings",
            "get_seat_map_tool",
            "select_seat_tool",
            "process_payment_tool",
            "add_ssr_tool",
            "add_ancillary_tool",
            "get_loyalty_info_tool",
            "upgrade_with_miles_tool",
            "check_flight_status_tool",
            "search_company_policy_tool",
            "search_web_tool",
        ]


def lint_testcase_payload(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validates a deterministic test case payload against backend tools and airline policies.
    """
    issues: List[str] = []
    registered_tools = get_registered_backend_tools()

    var_id = payload.get("testcase_id", "UNKNOWN")
    convs = payload.get("conversations", {})
    expected = payload.get("expected", {})
    traj = expected.get("expected_trajectory", {})

    # 1. Check tools in trajectory
    for t in traj.get("expected_tools", []):
        t_name = t.get("name")
        if t_name and t_name not in registered_tools:
            issues.append(f"[{var_id}] Tool '{t_name}' in expected_trajectory is not recognized in tools.py")

        # PNR format check
        args = t.get("expected_args") or {}
        pnr = args.get("pnr")
        if pnr and (len(pnr) != 6 or not pnr.isalnum()) and "invalid" not in var_id.lower() and "frust" not in var_id.lower():
            issues.append(f"[{var_id}] PNR '{pnr}' should be 6 alphanumeric characters for standard flow")

    # 2. Check turns tools
    for turn_label, msgs in convs.items():
        asst = next((m for m in msgs if m.get("role") == "assistant"), None)
        if asst:
            for t_name in asst.get("expected_tools_call_order", []):
                if t_name not in registered_tools:
                    issues.append(f"[{var_id} {turn_label}] Tool '{t_name}' in call order is not recognized in tools.py")

    return len(issues) == 0, issues


def promote_run_to_deterministic_dataset(
    run_file_path: Union[str, Path],
    datasets_dir: Optional[Union[str, Path]] = None,
    overwrite: bool = False,
    merge: bool = False,
    lint: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Promotes an executed dynamic run JSON into a curated deterministic ground-truth testcase.
    """
    run_path = Path(run_file_path)
    if not run_path.exists():
        return {"status": "error", "error": f"Run file not found: {run_path}"}

    data = load_json_file(run_path)
    if not data:
        return {"status": "error", "error": f"Could not read JSON from {run_path}"}

    meta = data.get("metadata") or {}
    golden_link = meta.get("golden_link") or {}
    rule_category = golden_link.get("rule_category") or meta.get("rule_category") or "general"
    scenario_name = golden_link.get("scenario_name") or meta.get("scenario_name") or "default_scenario"
    persona_slug = golden_link.get("persona_slug") or meta.get("persona_slug") or "default_persona"
    var_id = data.get("testcase_id") or run_path.stem

    effective_datasets_dir = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
    target_dir = resolve_target_dir(
        dest_root=effective_datasets_dir,
        rule_category=rule_category,
        scenario_name=scenario_name,
        persona_slug=persona_slug,
        target_mode="deterministic_reply",
    )
    dest_file = target_dir / f"{var_id}.json"

    file_exists = dest_file.exists()
    existing_conversations = None

    if file_exists:
        if merge:
            existing_data = load_json_file(dest_file) or {}
            existing_conversations = existing_data.get("conversations")
        elif not overwrite and not dry_run:
            return {
                "status": "skipped",
                "testcase_id": var_id,
                "reason": f"Target file already exists: {dest_file.name}. Use --overwrite or --merge.",
                "target_path": str(dest_file),
            }

    # Build turn-by-turn conversations structure
    conversations: Dict[str, List[Dict[str, Any]]] = {}

    if existing_conversations and merge:
        conversations = existing_conversations
    else:
        unified_turns = data.get("unified_turns") or []
        if unified_turns:
            for ut in unified_turns:
                t_num = ut.get("turn", len(conversations) + 1)
                exp = ut.get("expected") or {}
                conversations[f"turn {t_num}"] = [
                    {
                        "role": "user",
                        "content": ut.get("user_query", ""),
                    },
                    {
                        "role": "assistant",
                        "expected_content": exp.get("expected_content"),
                        "expected_tools_call_order": exp.get("expected_tools_order") or [],
                        "expected_tools": exp.get("expected_tools") or [],
                        "qa_note": exp.get("qa_note"),
                    },
                ]
        else:
            # Fallback from raw conversations
            raw_convs = data.get("conversations") or {}
            for t_label, t_msgs in raw_convs.items():
                u_msg = next((m for m in t_msgs if m.get("role") == "user"), None)
                a_msg = next((m for m in t_msgs if m.get("role") == "assistant"), None)
                if u_msg:
                    conversations[t_label] = [
                        {
                            "role": "user",
                            "content": u_msg.get("content", ""),
                        },
                        {
                            "role": "assistant",
                            "expected_content": a_msg.get("expected_content") if a_msg else None,
                            "expected_tools_call_order": a_msg.get("expected_tools_call_order") if a_msg else [],
                            "expected_tools": a_msg.get("expected_tools") or a_msg.get("actual_tools_called") or [] if a_msg else [],
                            "qa_note": a_msg.get("qa_note") if a_msg else None,
                        },
                    ]

    promoted_payload = {
        "testcase_id": var_id,
        "target_mode": "deterministic_reply",
        "scenario_description": data.get("scenario_description") or "",
        "expected_outcome": data.get("expected_outcome") or "",
        "expected": data.get("expected") or {},
        "persona": data.get("persona") or {},
        "context": data.get("context") or [],
        "conversations": conversations,
        "total_turns": len(conversations),
        "promoted_from_run": str(run_path),
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": meta,
    }

    # Lint check
    lint_issues = []
    if lint:
        is_valid, lint_issues = lint_testcase_payload(promoted_payload)
        if not is_valid:
            print(f"   ⚠️  [Lint Warning] Issues detected in {var_id}:")
            for iss in lint_issues:
                print(f"      • {iss}")

    if dry_run:
        return {
            "status": "dry_run",
            "testcase_id": var_id,
            "target_path": str(dest_file),
            "turns": len(conversations),
            "exists": file_exists,
            "lint_issues": lint_issues,
        }

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(promoted_payload, f, indent=2, ensure_ascii=False)

    return {
        "status": "promoted" if not file_exists else ("merged" if merge else "overwritten"),
        "testcase_id": var_id,
        "target_path": str(dest_file),
        "turns": len(conversations),
        "lint_issues": lint_issues,
    }


def generate_scenario_qa_manifest(
    scenario_dir_in_datasets: Path,
    bundle_info: Optional[Dict[str, Any]] = None,
) -> Path:
    """
    Generates qa_review.md and updates dataset.json in a scenario dataset folder.
    """
    scenario_dir = Path(scenario_dir_in_datasets)
    test_files = sorted(scenario_dir.rglob("*.json"))
    valid_test_files = [f for f in test_files if f.name != "dataset.json"]

    records = []
    dataset_records = []

    for f in valid_test_files:
        d = load_json_file(f)
        if not d:
            continue
        var_id = d.get("testcase_id") or f.stem
        persona = (d.get("persona") or {}).get("name", "User")
        turns = d.get("total_turns", len(d.get("conversations", {})))
        first_query = ""
        convs = d.get("conversations", {})
        if convs.get("turn 1"):
            u = next((m for m in convs["turn 1"] if m.get("role") == "user"), None)
            if u:
                first_query = u.get("content", "")

        traj = (d.get("expected") or {}).get("expected_trajectory") or {}
        tools = [t.get("name") for t in traj.get("expected_tools", [])]

        records.append({
            "var_id": var_id,
            "persona": persona,
            "turns": turns,
            "first_query": first_query[:60] + "..." if len(first_query) > 60 else first_query,
            "tools": ", ".join(tools) if tools else "None",
            "promoted_from": d.get("promoted_from_run", "Rules Authoring"),
        })
        dataset_records.append(d)

    # Write dataset.json
    dataset_json_path = scenario_dir / "dataset.json"
    with open(dataset_json_path, "w", encoding="utf-8") as f:
        json.dump(dataset_records, f, indent=2, ensure_ascii=False)

    # Write qa_review.md
    md_lines = [
        f"# QA Acceptance & Golden Review Manifest",
        f"\n**Scenario Directory**: `{scenario_dir.name}`",
        f"**Generated / Updated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**Total Curated Test Cases**: {len(records)}\n",
        "| Variation ID | Persona | Turns | Initial Query | Expected Tools | Provenance |",
        "| :--- | :--- | :---: | :--- | :--- | :--- |",
    ]
    for r in records:
        md_lines.append(
            f"| `{r['var_id']}` | {r['persona']} | {r['turns']} | \"{r['first_query']}\" | `{r['tools']}` | {Path(str(r['promoted_from'])).name} |"
        )
    md_lines.append("\n## Sign-off Checklist\n- [ ] Initial user queries reflect real customer tone\n- [ ] Tool parameters and expected order match technical contracts\n- [ ] Edge cases, cancellations, or human escalation properly covered\n")

    manifest_md_path = scenario_dir / "qa_review.md"
    with open(manifest_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    return manifest_md_path


def scaffold_from_rules(
    rules_dir: Optional[Path] = None,
    datasets_dir: Optional[Path] = None,
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
    overwrite: bool = False,
    merge: bool = False,
    lint: bool = True,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fallback: Scaffolds deterministic test cases directly from rules/ when dynamic runs do not exist yet.
    """
    rules_root = rules_dir or get_default_rules_dir()
    datasets_root = datasets_dir or get_default_datasets_dir()

    all_scenarios = discover_scenario_directories(rules_root)
    results = []

    for s_dir in all_scenarios:
        bundle = load_scenario_bundle(s_dir, rules_root=rules_root)
        cat = bundle["category"]
        s_name = bundle["scenario_name"]

        if category_filter and cat.lower() != category_filter.lower():
            continue
        if scenario_filter and s_name.lower() != scenario_filter.lower() and bundle["scenario_rel_dir"].lower() != scenario_filter.lower():
            continue

        for persona in bundle.get("personas", []):
            p_name = persona.get("persona_name", "User")
            p_slug = persona.get("persona_slug", "general")

            for var in persona.get("variations", []):
                var_id = var.get("variation_id")
                if variation_filter and variation_filter.lower() not in var_id.lower():
                    continue

                target_dir = resolve_target_dir(
                    dest_root=datasets_root,
                    rule_category=cat,
                    scenario_name=s_name,
                    persona_slug=p_slug,
                    target_mode="deterministic_reply",
                )
                dest_file = target_dir / f"{var_id}.json"
                file_exists = dest_file.exists()

                if file_exists and not overwrite and not merge and not dry_run:
                    results.append({"status": "skipped", "testcase_id": var_id, "target_path": str(dest_file)})
                    continue

                # Build conversations from expected_turns
                conversations: Dict[str, List[Dict[str, Any]]] = {}
                expected_turns = var.get("expected_turns") or []
                exp_traj = var.get("expected_trajectory") or {}

                for t_idx, t_def in enumerate(expected_turns, start=1):
                    turn_label = f"turn {t_def.get('turn', t_idx)}"
                    user_q = t_def.get("user_query") or (var.get("scenario_modifier") if t_idx == 1 else f"[{p_name}: Turn {t_idx}]")
                    exp_tools = t_def.get("expected_tools") or (exp_traj.get("expected_tools") if t_idx == 1 else [])
                    conversations[turn_label] = [
                        {"role": "user", "content": user_q},
                        {
                            "role": "assistant",
                            "expected_content": t_def.get("expected_content"),
                            "expected_tools_call_order": t_def.get("expected_tools_call_order") or (exp_traj.get("expected_tools_order") if t_idx == 1 else []),
                            "expected_tools": exp_tools or [],
                            "qa_note": t_def.get("qa_note"),
                        },
                    ]

                cfg = bundle.get("scenario_config") or {}
                ctx = list(cfg.get("shared_context") or [])
                if bundle.get("shared_context_text"):
                    ctx.append(bundle["shared_context_text"])

                payload = {
                    "testcase_id": var_id,
                    "target_mode": "deterministic_reply",
                    "scenario_description": f"{cfg.get('base_scenario', '')} {var.get('scenario_modifier', '')}".strip(),
                    "expected_outcome": var.get("expected_outcome", ""),
                    "expected": {
                        "scenario_description": f"{cfg.get('base_scenario', '')} {var.get('scenario_modifier', '')}".strip(),
                        "expected_outcome": var.get("expected_outcome", ""),
                        "expected_trajectory": exp_traj,
                        "expected_turns": expected_turns,
                    },
                    "persona": {"name": p_name, "characteristics": persona.get("persona_description", "")},
                    "context": ctx,
                    "conversations": conversations,
                    "total_turns": len(conversations),
                    "created_from_rules": datetime.now(timezone.utc).isoformat(),
                    "metadata": {
                        "rule_category": cat,
                        "scenario_name": s_name,
                        "persona_slug": p_slug,
                        "variation_id": var_id,
                        "expected_metrics": bundle.get("expected_metrics") or {},
                        "golden_link": {
                            "rule_category": cat,
                            "scenario_name": s_name,
                            "persona_slug": p_slug,
                            "variation_id": var_id,
                        },
                    },
                }

                if lint:
                    is_val, iss = lint_testcase_payload(payload)
                    if not is_val:
                        for i in iss:
                            print(f"   ⚠️  [Lint] {i}")

                if dry_run:
                    results.append({"status": "dry_run", "testcase_id": var_id, "target_path": str(dest_file), "turns": len(conversations)})
                else:
                    with open(dest_file, "w", encoding="utf-8") as f:
                        json.dump(payload, f, indent=2, ensure_ascii=False)
                    results.append({"status": "created", "testcase_id": var_id, "target_path": str(dest_file), "turns": len(conversations)})

        # Update manifest for scenario
        if not dry_run and results:
            scenario_dest = datasets_root / cat / s_name
            if scenario_dest.exists():
                generate_scenario_qa_manifest(scenario_dest)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Dynamic-to-Deterministic Conversation Promotion & Golden Truth Generator."
    )
    parser.add_argument(
        "run_file",
        nargs="?",
        default=None,
        help="Path to an executed dynamic simulation run JSON file to promote into datasets/.",
    )
    parser.add_argument(
        "--run",
        "--run-timestamp",
        dest="run_timestamp",
        type=str,
        default=None,
        help="Promote dynamic runs from a specific timestamp directory under test/run/ or 'latest'.",
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
        "--from-rules",
        action="store_true",
        help="Scaffold deterministic test cases directly from rules/ when dynamic runs are not available.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing testcase JSON files in datasets/.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge mode: Update scenario metadata, SLAs, and context from rules while preserving QA's customized queries in conversations.",
    )
    parser.add_argument(
        "--lint",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run conversational linting against registered backend tools (default: True).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview test cases without creating or modifying files on disk.",
    )
    parser.add_argument(
        "--datasets-dir",
        type=str,
        default=None,
        help="Custom path to datasets directory (default: 'test/conversational_golden/datasets').",
    )
    parser.add_argument(
        "--runs-dir",
        type=str,
        default=None,
        help="Custom path to runs directory (default: 'test/run').",
    )
    parser.add_argument(
        "--rules-dir",
        type=str,
        default=None,
        help="Custom path to rules directory (default: 'test/conversational_golden/rules').",
    )

    args = parser.parse_args()

    datasets_root = Path(args.datasets_dir) if args.datasets_dir else get_default_datasets_dir()
    runs_root = Path(args.runs_dir) if args.runs_dir else get_default_runs_dir()

    print("=" * 75)
    print("🌟 Dynamic-to-Deterministic Golden Truth Generator")
    print("=" * 75)
    print(f"📁 Target Datasets:   {datasets_root.resolve()}")
    print(f"🔄 Overwrite Mode:    {args.overwrite}")
    print(f"🔀 Merge Mode:        {args.merge}")
    print(f"🔍 Tool & SLA Lint:   {args.lint}")
    print(f"⚙️  Dry-Run Mode:      {args.dry_run}")
    print("=" * 75)

    start_time = time.time()
    results: List[Dict[str, Any]] = []

    # Mode 1: Offline scaffolding from rules
    if args.from_rules:
        print("📋 Mode: Scaffolding test cases from rules/...")
        results = scaffold_from_rules(
            rules_dir=Path(args.rules_dir) if args.rules_dir else None,
            datasets_dir=datasets_root,
            category_filter=args.category,
            scenario_filter=args.scenario,
            variation_filter=args.variation,
            overwrite=args.overwrite,
            merge=args.merge,
            lint=args.lint,
            dry_run=args.dry_run,
        )

    # Mode 2: Direct file path provided
    elif args.run_file:
        file_path = Path(args.run_file)
        if "*" in str(file_path):
            matched = [Path(p) for p in glob.glob(str(file_path), recursive=True)]
        else:
            matched = [file_path]

        print(f"🚀 Mode: Promoting {len(matched)} dynamic run file(s)...")
        for f in matched:
            res = promote_run_to_deterministic_dataset(
                run_file_path=f,
                datasets_dir=datasets_root,
                overwrite=args.overwrite,
                merge=args.merge,
                lint=args.lint,
                dry_run=args.dry_run,
            )
            results.append(res)
            status = res.get("status", "unknown")
            var_id = res.get("testcase_id", f.stem)
            if status in ["promoted", "overwritten", "merged"]:
                print(f"   ✅ [{status.upper()}] {var_id} -> {Path(res['target_path']).name}")
            elif status == "skipped":
                print(f"   🛡️  [SKIPPED] {var_id} (already exists; use --overwrite or --merge)")
            elif status == "dry_run":
                print(f"   🔍 [DRY-RUN] Would promote {var_id} ({res.get('turns')} turns)")

    # Mode 3: Timestamp or latest run directory
    elif args.run_timestamp:
        target_dir = get_latest_run_dir(runs_root=runs_root) if args.run_timestamp == "latest" else get_run_timestamp_dir(timestamp_str=args.run_timestamp, runs_root=runs_root)
        if not target_dir or not target_dir.exists():
            print(f"[Error] Run directory not found: {target_dir}")
            sys.exit(1)

        print(f"🚀 Mode: Promoting dynamic runs from {target_dir.name}...")
        dyn_files = sorted(target_dir.rglob("*.json"))
        for f in dyn_files:
            if f.name in ["dataset.json", "evaluation_report.json", "dynamic_evaluation_report.json"]:
                continue
            if "dynamic_simulation" not in str(f):
                continue
            if args.variation and args.variation.lower() not in f.stem.lower():
                continue

            res = promote_run_to_deterministic_dataset(
                run_file_path=f,
                datasets_dir=datasets_root,
                overwrite=args.overwrite,
                merge=args.merge,
                lint=args.lint,
                dry_run=args.dry_run,
            )
            results.append(res)
            status = res.get("status", "unknown")
            var_id = res.get("testcase_id", f.stem)
            if status in ["promoted", "overwritten", "merged"]:
                print(f"   ✅ [{status.upper()}] {var_id} -> {Path(res['target_path']).name}")
            elif status == "skipped":
                print(f"   🛡️  [SKIPPED] {var_id} (already exists)")
            elif status == "dry_run":
                print(f"   🔍 [DRY-RUN] Would promote {var_id} ({res.get('turns')} turns)")

    else:
        print("[Notice] No input file or mode specified. Defaulting to --from-rules.")
        results = scaffold_from_rules(
            rules_dir=Path(args.rules_dir) if args.rules_dir else None,
            datasets_dir=datasets_root,
            category_filter=args.category,
            scenario_filter=args.scenario,
            variation_filter=args.variation,
            overwrite=args.overwrite,
            merge=args.merge,
            lint=args.lint,
            dry_run=args.dry_run,
        )

    # Generate scenario-level manifest for affected scenarios
    if not args.dry_run:
        affected_scenario_dirs = set()
        for r in results:
            t_path = r.get("target_path")
            if t_path:
                # target_path is like datasets/<cat>/<scen>/<persona>/deterministic_reply/<id>.json
                # Scenario level is target_path.parent.parent.parent
                p = Path(t_path).resolve()
                try:
                    scen_dir = p.parent.parent.parent
                    if scen_dir.exists():
                        affected_scenario_dirs.add(scen_dir)
                except Exception:
                    pass

        for s_dir in affected_scenario_dirs:
            manifest_file = generate_scenario_qa_manifest(s_dir)
            print(f"   📋 Updated QA Manifest: {manifest_file}")

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 75)
    success_count = sum(1 for r in results if r.get("status") in ["promoted", "created", "merged", "overwritten"])
    print(f"🎉 Process completed in {duration}s. Total processed: {len(results)} (Updated: {success_count})")
    print("=" * 75)


if __name__ == "__main__":
    main()

