"""
Conversational Golden Bridge Module
====================================
Bridges hierarchical rule definitions and persona variations in
`conversational_golden/rules` with DeepEval's `ConversationSimulator`,
and manages exporting/loading generated multi-turn datasets in
`conversational_golden/datasets` while maintaining full traceability links.
"""

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

from deepeval.dataset import ConversationalGolden, Persona
from deepeval.test_case import ConversationalTestCase, Turn


def get_base_dir() -> Path:
    """Returns the base `test` directory."""
    return Path(__file__).resolve().parent.parent


def get_default_rules_dir() -> Path:
    """Returns default path to `test/conversational_golden/rules`."""
    return get_base_dir() / "conversational_golden" / "rules"


def get_default_datasets_dir() -> Path:
    """Returns default path to `test/conversational_golden/datasets`."""
    return get_base_dir() / "conversational_golden" / "datasets"


def get_default_personas_file() -> Path:
    """Returns default path to `test/conversational_golden/personas.json`."""
    return get_base_dir() / "conversational_golden" / "personas.json"


def load_personas_catalog(
    personas_file: Optional[Union[str, Path]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Loads the central personas catalog from `conversational_golden/personas.json`.
    Returns a dictionary mapping `persona_slug` -> persona metadata dictionary.
    """
    p_path = Path(personas_file) if personas_file else get_default_personas_file()
    data = load_json_file(p_path) or {}
    catalog: Dict[str, Dict[str, Any]] = {}
    for p in data.get("personas", []):
        slug = p.get("persona_slug")
        if slug:
            catalog[slug] = p
    return catalog


def get_default_runs_dir() -> Path:
    """Returns default path to `test/run`."""
    return get_base_dir() / "run"


def get_run_timestamp_dir(
    timestamp_str: Optional[str] = None,
    runs_root: Optional[Union[str, Path]] = None,
) -> Path:
    """
    Returns a specific or newly generated timestamped run directory under `test/run/<date_time>`.
    Creates the directory if it does not already exist.
    """
    root = Path(runs_root) if runs_root else get_default_runs_dir()
    ts = timestamp_str or datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = root / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def get_latest_run_dir(runs_root: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """Returns the most recent run directory found under `test/run/`."""
    root = Path(runs_root) if runs_root else get_default_runs_dir()
    if not root.exists():
        return None
    subdirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    if not subdirs:
        return None
    return sorted(subdirs, key=lambda d: d.name, reverse=True)[0]


def prune_old_runs(
    runs_root: Optional[Union[str, Path]] = None,
    keep_last: int = 20,
    max_age_days: Optional[int] = None,
) -> List[Path]:
    """
    Applies a retention policy to timestamped execution runs under `test/run/`.
    - `keep_last`: Retains the N most recent run folders, deleting older ones.
    - `max_age_days`: If provided, also deletes run folders older than N days.
    Returns the list of pruned directory paths.
    """
    root = Path(runs_root) if runs_root else get_default_runs_dir()
    if not root.exists():
        return []

    subdirs = [d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")]
    # Sort chronologically (oldest first, latest last)
    sorted_subdirs = sorted(subdirs, key=lambda d: d.name)

    pruned: List[Path] = []
    now = datetime.now(timezone.utc)

    # 1. Prune by max_age_days if specified
    if max_age_days is not None and max_age_days > 0:
        for d in list(sorted_subdirs):
            try:
                # Format: %Y-%m-%d_%H-%M-%S
                ts_part = d.name[:19]
                folder_dt = datetime.strptime(ts_part, "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)
                age_days = (now - folder_dt).total_seconds() / 86400.0
                if age_days > max_age_days:
                    shutil.rmtree(d)
                    pruned.append(d)
                    sorted_subdirs.remove(d)
            except Exception:
                pass

    # 2. Prune by keep_last limit
    if keep_last > 0 and len(sorted_subdirs) > keep_last:
        excess_count = len(sorted_subdirs) - keep_last
        to_delete = sorted_subdirs[:excess_count]
        for d in to_delete:
            try:
                shutil.rmtree(d)
                pruned.append(d)
            except Exception as e:
                print(f"[Notice] Failed to delete old run folder {d}: {e}")

    if pruned:
        print(f"🧹 Pruned {len(pruned)} old run directory(ies) according to retention policy (keep_last={keep_last}).")

    return pruned


def _fetch_langsmith_compact_trace(thread_id: str) -> Optional[Dict[str, Any]]:
    """Attempts to fetch compact turn export from LangSmith for the given thread_id."""
    if not thread_id or thread_id.startswith(("mock_", "test_", "case_")):
        return None
    try:
        from scripts.langsmith_client import build_compact_turn_export, export_traces_to_file
    except ImportError:
        try:
            from langsmith_client import build_compact_turn_export, export_traces_to_file
        except ImportError:
            return None
    try:
        try:
            export_traces_to_file(thread_id=thread_id)
        except Exception:
            pass
        return build_compact_turn_export(thread_id=thread_id)
    except Exception as e:
        print(f"[Notice] LangSmith trace extraction skipped for {thread_id}: {e}")
        return None


def load_json_file(file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Safely loads and parses a JSON file."""
    path = Path(file_path)
    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Warning] Failed to load JSON from {path}: {e}")
        return None


def discover_scenario_directories(
    rules_dir: Optional[Union[str, Path]] = None,
) -> List[Path]:
    """
    Recursively scans the rules directory for scenario folders.
    A valid scenario folder contains either a `scenario_config.json`
    or a `variations/` subfolder.
    """
    root = Path(rules_dir) if rules_dir else get_default_rules_dir()
    if not root.exists():
        return []

    scenario_dirs: List[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        # Check if current directory has scenario_config.json or variations/
        has_config = (current / "scenario_config.json").is_file()
        has_variations = (current / "variations").is_dir()
        if has_config or has_variations:
            scenario_dirs.append(current)

    return sorted(scenario_dirs)


def load_scenario_bundle(
    scenario_dir: Union[str, Path],
    rules_root: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Loads all configuration, shared context, expected metrics, and persona variations
    from a specific scenario folder.
    """
    s_dir = Path(scenario_dir).resolve()
    r_root = Path(rules_root).resolve() if rules_root else get_default_rules_dir().resolve()

    try:
        rel_path = s_dir.relative_to(r_root)
        parts = rel_path.parts
        category = parts[0] if len(parts) > 1 else "general"
        scenario_name = parts[-1]
        scenario_rel_dir = str(rel_path)
    except ValueError:
        category = "general"
        scenario_name = s_dir.name
        scenario_rel_dir = s_dir.name

    # 1. Load scenario config
    config_file = s_dir / "scenario_config.json"
    scenario_config = load_json_file(config_file) or {}

    # 2. Load shared context from text file if present
    txt_context_file = s_dir / "shared_context.txt"
    shared_context_text = ""
    if txt_context_file.exists() and txt_context_file.stat().st_size > 0:
        try:
            with open(txt_context_file, "r", encoding="utf-8") as f:
                shared_context_text = f.read().strip()
        except Exception as e:
            print(f"[Warning] Failed reading {txt_context_file}: {e}")

    # 3. Load expected metrics if present
    metrics_file = s_dir / "expected_metrics.json"
    expected_metrics = load_json_file(metrics_file) or {}

    # 4. Load variations files
    variations_dir = s_dir / "variations"
    personas: List[Dict[str, Any]] = []
    personas_catalog = load_personas_catalog()

    if variations_dir.is_dir():
        for var_file in sorted(variations_dir.glob("*.json")):
            var_data = load_json_file(var_file)
            if not var_data:
                continue

            persona_slug = var_file.stem
            catalog_entry = personas_catalog.get(persona_slug, {})
            persona_name = var_data.get("persona_name") or catalog_entry.get("persona_name") or persona_slug.replace("_", " ").title()
            persona_desc = var_data.get("persona_description") or catalog_entry.get("persona_description") or ""
            variations_list = var_data.get("variations") or []

            personas.append({
                "persona_file": str(var_file),
                "persona_filename": var_file.name,
                "persona_slug": persona_slug,
                "persona_name": persona_name,
                "persona_description": persona_desc,
                "variations": variations_list,
                "raw_data": var_data,
            })

    return {
        "category": category,
        "scenario_name": scenario_name,
        "scenario_rel_dir": scenario_rel_dir,
        "scenario_dir": str(s_dir),
        "scenario_config_file": str(config_file) if config_file.exists() else None,
        "scenario_config": scenario_config,
        "shared_context_text": shared_context_text,
        "expected_metrics": expected_metrics,
        "personas": personas,
    }


def build_conversational_goldens(
    scenario_bundle: Dict[str, Any],
    variation_id_filter: Optional[str] = None,
) -> List[ConversationalGolden]:
    """
    Transforms a loaded scenario bundle into DeepEval `ConversationalGolden` objects.
    Each Golden includes full traceability metadata linking back to the original rule files.
    """
    goldens: List[ConversationalGolden] = []

    scenario_config = scenario_bundle.get("scenario_config") or {}
    base_scenario = scenario_config.get("base_scenario", "").strip()
    scenario_id = scenario_config.get("scenario_id") or scenario_bundle.get("scenario_name")

    # Combine shared contexts
    shared_context_list: List[str] = []
    config_context = scenario_config.get("shared_context")
    if isinstance(config_context, list):
        shared_context_list.extend(str(item).strip() for item in config_context if str(item).strip())
    elif isinstance(config_context, str) and config_context.strip():
        shared_context_list.append(config_context.strip())

    txt_context = scenario_bundle.get("shared_context_text")
    if txt_context:
        shared_context_list.append(txt_context)

    for persona_info in scenario_bundle.get("personas", []):
        persona_name = persona_info["persona_name"]
        persona_desc = persona_info["persona_description"]
        persona_slug = persona_info["persona_slug"]
        persona_file = persona_info["persona_file"]

        persona_obj = Persona(
            name=persona_name,
            characteristics=persona_desc,
        )

        for var in persona_info.get("variations", []):
            var_id = var.get("variation_id") or f"{persona_slug}_{len(goldens)+1}"
            if variation_id_filter and var_id.lower() != variation_id_filter.lower():
                continue

            modifier = var.get("scenario_modifier", "").strip()
            expected_outcome = var.get("expected_outcome", "").strip()

            # Merge base scenario and modifier
            if base_scenario and modifier:
                full_scenario = f"{base_scenario} {modifier}"
            else:
                full_scenario = modifier or base_scenario or "Conversational test scenario"

            # Combine variation-specific context if any
            full_context = list(shared_context_list)
            var_context = var.get("context") or var.get("shared_context")
            if isinstance(var_context, list):
                full_context.extend(str(item).strip() for item in var_context if str(item).strip())
            elif isinstance(var_context, str) and var_context.strip():
                full_context.append(var_context.strip())

            additional_metadata = {
                "rule_category": scenario_bundle["category"],
                "scenario_name": scenario_bundle["scenario_name"],
                "scenario_rel_dir": scenario_bundle["scenario_rel_dir"],
                "scenario_id": scenario_id,
                "persona_slug": persona_slug,
                "persona_name": persona_name,
                "persona_description": persona_desc,
                "variation_id": var_id,
                "variation_file": persona_file,
                "scenario_config_file": str(scenario_bundle.get("scenario_config_file")),
                "expected_metrics": scenario_bundle.get("expected_metrics", {}),
                "expected_trajectory": var.get("expected_trajectory", {}),
                "expected_turns": var.get("expected_turns", []),
                "golden_link": {
                    "rule_category": scenario_bundle["category"],
                    "scenario_name": scenario_bundle["scenario_name"],
                    "scenario_rel_dir": scenario_bundle["scenario_rel_dir"],
                    "scenario_id": scenario_id,
                    "scenario_config_path": str(scenario_bundle.get("scenario_config_file")),
                    "variation_file": persona_file,
                    "persona_slug": persona_slug,
                    "persona_name": persona_name,
                    "persona_description": persona_desc,
                    "variation_id": var_id,
                },
            }

            golden = ConversationalGolden(
                name=var_id,
                scenario=full_scenario,
                expected_outcome=expected_outcome or "Satisfactory resolution by chatbot",
                persona=persona_obj,
                context=full_context or None,
                additional_metadata=additional_metadata,
            )
            goldens.append(golden)

    return goldens


def load_all_conversational_goldens(
    rules_dir: Optional[Union[str, Path]] = None,
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
) -> List[ConversationalGolden]:
    """
    Crawls the entire rules directory and builds all `ConversationalGolden` objects
    with optional filtering.
    """
    scenario_dirs = discover_scenario_directories(rules_dir)
    all_goldens: List[ConversationalGolden] = []

    for s_dir in scenario_dirs:
        bundle = load_scenario_bundle(s_dir, rules_root=rules_dir)
        cat = bundle["category"]
        s_name = bundle["scenario_name"]

        if category_filter and cat.lower() != category_filter.lower():
            continue
        if scenario_filter and s_name.lower() != scenario_filter.lower() and bundle["scenario_rel_dir"].lower() != scenario_filter.lower():
            continue

        goldens = build_conversational_goldens(bundle, variation_id_filter=variation_filter)
        all_goldens.extend(goldens)

    return all_goldens


def _extract_metadata(item: Any) -> Dict[str, Any]:
    """Helper to safely extract metadata or additional_metadata dictionary."""
    if hasattr(item, "metadata") and item.metadata:
        return dict(item.metadata)
    if hasattr(item, "additional_metadata") and item.additional_metadata:
        return dict(item.additional_metadata)
    return {}


def group_turns_into_conversations(
    turns: List[Any],
    expected_turns: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """
    Groups raw message turns into paired conversational interaction rounds:
    1 turn = user query + assistant response (or exchange).
    Enriches each assistant turn with QA expectations:
    - expected_content
    - expected_tools_call_order vs actual_tools_call_order
    - expected_args & expected_response vs actual_args & actual_response
    """
    conversations: Dict[str, List[Dict[str, Any]]] = {}
    current_turn_msgs: List[Dict[str, Any]] = []
    turn_num = 1

    def _get_turn_expectation(t_idx: int) -> Dict[str, Any]:
        if not expected_turns:
            return {}
        for exp in expected_turns:
            if exp.get("turn") == t_idx:
                return exp
        if 0 <= t_idx - 1 < len(expected_turns):
            return expected_turns[t_idx - 1]
        return {}

    def _finalize_turn(turn_idx: int, msgs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        exp_cfg = _get_turn_expectation(turn_idx)
        exp_content = exp_cfg.get("expected_content")
        exp_order = exp_cfg.get("expected_tools_call_order")
        exp_tools = exp_cfg.get("expected_tools") or []

        for msg in msgs:
            if msg.get("role") == "assistant":
                if exp_content and not msg.get("expected_content"):
                    msg["expected_content"] = exp_content
                if exp_order is not None and not msg.get("expected_tools_call_order"):
                    msg["expected_tools_call_order"] = exp_order
                elif "expected_tools_call_order" not in msg:
                    msg["expected_tools_call_order"] = []

                # Match tools in actual_tools_called with exp_tools
                actual_tools = msg.get("actual_tools_called") or []
                enriched_tools = []
                for tc_idx, tc_item in enumerate(actual_tools):
                    t_name = tc_item.get("name")
                    matched_exp_tool = None
                    for et in exp_tools:
                        if et.get("name") == t_name:
                            matched_exp_tool = et
                            break
                    if not matched_exp_tool and tc_idx < len(exp_tools):
                        matched_exp_tool = exp_tools[tc_idx]

                    args = tc_item.get("args") or tc_item.get("actual_args") or {}
                    resp = tc_item.get("response") or tc_item.get("result") or tc_item.get("actual_response")

                    exp_args = tc_item.get("expected_args") or (matched_exp_tool.get("expected_args") if matched_exp_tool else None)
                    exp_resp = tc_item.get("expected_response") or tc_item.get("expected_result") or (matched_exp_tool.get("expected_response") if matched_exp_tool else None)
                    enriched_tools.append({
                        "name": t_name,
                        "args": args,
                        "expected_args": exp_args,
                        "response": resp,
                        "expected_response": exp_resp,
                    })
                msg["actual_tools_called"] = enriched_tools
        return msgs

    for turn in turns:
        t_meta = getattr(turn, "metadata", None) or (turn.get("metadata") if isinstance(turn, dict) else {}) or {}
        role = getattr(turn, "role", turn.get("role") if isinstance(turn, dict) else "user")
        content = getattr(turn, "content", turn.get("content") if isinstance(turn, dict) else "")

        t_dict: Dict[str, Any] = {
            "role": role,
            "content": content,
        }

        if role == "assistant":
            if isinstance(t_meta, dict) and t_meta.get("expected_content"):
                t_dict["expected_content"] = t_meta["expected_content"]
            elif isinstance(turn, dict) and turn.get("expected_content"):
                t_dict["expected_content"] = turn["expected_content"]

            exp_order = t_meta.get("expected_tools_call_order") if isinstance(t_meta, dict) else None
            if exp_order is None and isinstance(turn, dict):
                exp_order = turn.get("expected_tools_call_order")
            if exp_order is not None:
                t_dict["expected_tools_call_order"] = exp_order

            tools_order = t_meta.get("actual_tools_call_order") if isinstance(t_meta, dict) else None
            if tools_order is None and isinstance(turn, dict):
                tools_order = turn.get("actual_tools_call_order")
            t_dict["actual_tools_call_order"] = tools_order or []

            tools_called = t_meta.get("actual_tools_called") if isinstance(t_meta, dict) else None
            if tools_called is None and isinstance(turn, dict):
                tools_called = turn.get("actual_tools_called")
            t_dict["actual_tools_called"] = tools_called or []

            ui_widgets = t_meta.get("actual_ui_widgets") if isinstance(t_meta, dict) else None
            if ui_widgets is None and isinstance(turn, dict):
                ui_widgets = turn.get("actual_ui_widgets")
            t_dict["actual_ui_widgets"] = ui_widgets or []

            citations = t_meta.get("actual_citations") if isinstance(t_meta, dict) else None
            if citations is None and isinstance(turn, dict):
                citations = turn.get("actual_citations")
            t_dict["actual_citations"] = citations or []

            if isinstance(t_meta, dict) and t_meta.get("metrics"):
                t_dict["metrics"] = t_meta["metrics"]

            run_id = t_meta.get("run_id") if isinstance(t_meta, dict) else None
            if run_id is None and isinstance(turn, dict):
                run_id = turn.get("run_id")
            if run_id:
                t_dict["run_id"] = run_id

        elif isinstance(t_meta, dict) and t_meta:
            for k in ["actual_tools_called", "actual_tools_call_order", "expected_tools_call_order", "expected_content", "actual_ui_widgets", "actual_citations", "metrics", "run_id"]:
                if k in t_meta:
                    t_dict[k] = t_meta[k]

        # If encountering a user message after assistant message(s), close previous turn
        if role == "user" and any(m.get("role") == "assistant" for m in current_turn_msgs):
            conversations[f"turn {turn_num}"] = _finalize_turn(turn_num, current_turn_msgs)
            turn_num += 1
            current_turn_msgs = []

        current_turn_msgs.append(t_dict)

    if current_turn_msgs:
        conversations[f"turn {turn_num}"] = _finalize_turn(turn_num, current_turn_msgs)

    total_turns = len(conversations)
    return conversations, total_turns


def is_deterministic_mode(target_mode: Optional[str]) -> bool:
    """Returns True if the target mode is a deterministic mode."""
    if not target_mode:
        return False
    norm_mode = str(target_mode).lower().strip()
    return norm_mode in [
        "deterministic",
        "deterministic_replay",
        "deterministic_reply",
        "replay",
        "reply",
    ]


def resolve_target_dir(
    dest_root: Path,
    rule_category: str,
    scenario_name: str,
    persona_slug: str,
    target_mode: str = "dynamic_simulation",
) -> Path:
    """
    Resolves the destination folder under dest_root for a specific persona variation.
    Maps:
    - 'deterministic', 'deterministic_replay', 'deterministic_reply' -> deterministic_reply/ or deterministic_replay/
    - 'dynamic', 'dynamic_simulation' -> dynamic_simulation/
    """
    persona_dir = dest_root / rule_category / scenario_name / persona_slug

    if is_deterministic_mode(target_mode):
        # If deterministic_reply exists on disk, respect user's folder name
        if (persona_dir / "deterministic_reply").exists():
            target_sub = "deterministic_reply"
        elif (persona_dir / "deterministic_replay").exists():
            target_sub = "deterministic_replay"
        else:
            target_sub = "deterministic_reply"
    else:
        target_sub = "dynamic_simulation"

    target_dir = persona_dir / target_sub
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def export_simulated_testcase(
    test_case: ConversationalTestCase,
    datasets_dir: Optional[Union[str, Path]] = None,
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = None,
    thread_id: Optional[str] = None,
    target_mode: str = "dynamic_simulation",
    overwrite: bool = False,
    enrich_with_langsmith: bool = True,
) -> Dict[str, Any]:
    """
    Exports a single simulated `ConversationalTestCase` into the hierarchy:
    - If `run_timestamp` or `runs_dir` is specified: saves under `test/run/<date_time>/<category>/<scenario>/<persona>/<target_mode>/<variation_id>.json`
    - Else if `datasets_dir`: saves under `datasets/<category>/<scenario>/<persona>/<target_mode>/<variation_id>.json`
    Merges expected golden targets with actual LangSmith runtime traces into a unified testcase JSON.
    - Else if `datasets_dir` and deterministic: saves under `datasets/<category>/<scenario>/<persona>/deterministic_reply/<variation_id>.json`
    - Dynamic simulation strictly saves to runs_dir (test/run/<date_time>/), never directly to datasets_dir.
    """
    is_det = is_deterministic_mode(target_mode)

    if run_timestamp:
        dest_root = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)
    elif runs_dir:
        dest_root = Path(runs_dir)
    elif is_det and datasets_dir:
        dest_root = Path(datasets_dir)
    elif datasets_dir and not is_det:
        # Dynamic simulation cannot go directly to datasets directory!
        # Route to runs_dir with timestamp
        dest_root = get_run_timestamp_dir(runs_root=runs_dir or get_default_runs_dir())
    else:
        dest_root = get_run_timestamp_dir(runs_root=get_default_runs_dir())

    meta = _extract_metadata(test_case)
    golden_link = meta.get("golden_link") or {}

    rule_category = golden_link.get("rule_category") or meta.get("rule_category") or "general"
    scenario_name = golden_link.get("scenario_name") or meta.get("scenario_name") or "default_scenario"
    persona_slug = golden_link.get("persona_slug") or meta.get("persona_slug") or "default_persona"
    variation_id = golden_link.get("variation_id") or meta.get("variation_id") or getattr(test_case, "name", None) or f"case_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    raw_turns = getattr(test_case, "turns", []) or []

    # Robust thread_id resolution
    active_thread_id = thread_id or meta.get("thread_id")
    if not active_thread_id:
        for t in raw_turns:
            t_meta = getattr(t, "metadata", {}) or {}
            if isinstance(t_meta, dict) and t_meta.get("thread_id"):
                active_thread_id = t_meta.get("thread_id")
                break

    if active_thread_id:
        meta["thread_id"] = active_thread_id
    if golden_link:
        meta["golden_link"] = golden_link

    # Segregated target folder: <dest_root>/<rule_category>/<scenario_name>/<persona_slug>/<target_sub>/
    scenario_out_dir = resolve_target_dir(
        dest_root=dest_root,
        rule_category=rule_category,
        scenario_name=scenario_name,
        persona_slug=persona_slug,
        target_mode=target_mode,
    )

    base_filename = f"{variation_id}.json"
    base_file_path = scenario_out_dir / base_filename

    # Non-destructive file safeguard: append timestamp if file already exists and overwrite is False
    if base_file_path.exists() and not overwrite:
        file_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file_path = scenario_out_dir / f"{variation_id}_{file_ts}.json"
        try:
            rel_loc = scenario_out_dir.relative_to(dest_root)
        except Exception:
            rel_loc = scenario_out_dir
        print(f"[Notice] File '{base_filename}' already exists in '{rel_loc}'. Created timestamped version: '{json_file_path.name}' to safeguard existing testcase.")
    else:
        json_file_path = base_file_path

    # Group turns into conversational pairs with expected turns if available
    expected_turns = meta.get("expected_turns") or (meta.get("expected_trajectory") or {}).get("expected_turns")
    grouped_conversations, total_turns_count = group_turns_into_conversations(raw_turns, expected_turns=expected_turns)

    # Fetch LangSmith trace for authoritative server-side execution if enabled
    compact_ls_export = None
    if enrich_with_langsmith and active_thread_id:
        compact_ls_export = _fetch_langsmith_compact_trace(active_thread_id)

    # For unit/mock testing: if thread_id is mock/test, synthesize mock LangSmith trace from testcase metadata
    if not compact_ls_export and active_thread_id and active_thread_id.startswith(("mock_", "test_", "case_")):
        mock_turns = []
        for t_idx, (t_lbl, t_msgs) in enumerate(grouped_conversations.items(), start=1):
            u_msg = next((m for m in t_msgs if m.get("role") == "user"), {})
            a_msg = next((m for m in t_msgs if m.get("role") == "assistant"), {})
            a_meta = a_msg.get("metadata") or {}
            mock_turns.append({
                "turn_index": t_idx,
                "run_id": a_msg.get("run_id") or a_meta.get("run_id") or f"mock_run_{t_idx}",
                "user_message": u_msg.get("content", ""),
                "llm_response": a_msg.get("content", ""),
                "tools_call": [
                    {
                        "tool_name": tc.get("name"),
                        "inputs": tc.get("args") or {},
                        "output": tc.get("response") or tc.get("result"),
                    }
                    for tc in (a_msg.get("actual_tools_called") or a_meta.get("actual_tools_called") or [])
                ],
                "tokens": a_msg.get("metrics") or a_meta.get("metrics") or {},
                "latency_ms": (a_msg.get("metrics") or a_meta.get("metrics") or {}).get("latency_ms"),
                "ttft_ms": (a_msg.get("metrics") or a_meta.get("metrics") or {}).get("ttft_ms"),
                "status": "success",
            })
        if any(t.get("tools_call") or t.get("latency_ms") for t in mock_turns):
            compact_ls_export = {
                "thread_id": active_thread_id,
                "project_name": "mock-test-project",
                "total_turns": len(mock_turns),
                "turns": mock_turns,
            }

    # Compute performance summary strictly from LangSmith trace data
    if compact_ls_export and compact_ls_export.get("turns"):
        ls_turns = compact_ls_export.get("turns", [])
        total_latency_ms = sum(t.get("latency_ms") or 0.0 for t in ls_turns)
        ttft_list = [t.get("ttft_ms") for t in ls_turns if t.get("ttft_ms") is not None]
        total_tokens = sum((t.get("tokens") or {}).get("total_tokens", 0) for t in ls_turns)
        total_cost_usd = sum((t.get("tokens") or {}).get("total_cost", 0.0) for t in ls_turns)

        performance_summary = {
            "total_turns": len(ls_turns),
            "total_latency_ms": round(total_latency_ms, 2),
            "avg_ttft_ms": round(sum(ttft_list) / len(ttft_list), 2) if ttft_list else 0.0,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
        }
        trace_status = "success"
    else:
        performance_summary = {
            "total_turns": 0,
            "total_latency_ms": 0.0,
            "avg_ttft_ms": 0.0,
            "total_tokens": 0,
            "total_cost_usd": 0.0,
        }
        trace_status = "missing_langsmith_trace"

    # Build Unified Turns (Expected + Actual from LangSmith)
    unified_turns: List[Dict[str, Any]] = []
    for turn_idx, (turn_label, turn_msgs) in enumerate(grouped_conversations.items(), start=1):
        user_msg = next((m for m in turn_msgs if m.get("role") == "user"), {})
        asst_msg = next((m for m in turn_msgs if m.get("role") == "assistant"), {})

        ls_turn = None
        if compact_ls_export and "turns" in compact_ls_export and turn_idx - 1 < len(compact_ls_export["turns"]):
            ls_turn = compact_ls_export["turns"][turn_idx - 1]

        expected_data = {
            "qa_note": asst_msg.get("qa_note"),
            "expected_content": asst_msg.get("expected_content"),
            "expected_tools_order": asst_msg.get("expected_tools_call_order") or [],
            "expected_tools": [
                {
                    "name": t.get("name"),
                    "expected_args": t.get("expected_args"),
                    "expected_response": t.get("expected_response"),
                }
                for t in asst_msg.get("actual_tools_called", [])
                if t.get("expected_args") or t.get("expected_response")
            ],
            "review_only": asst_msg.get("review_only", True),
        }

        if ls_turn:
            exp_tools = expected_data.get("expected_tools", [])
            actual_tools_called = []
            for tc in ls_turn.get("tools_call", []):
                t_name = tc.get("tool_name")
                matching_exp = next((et for et in exp_tools if et.get("name") == t_name), {})
                actual_tools_called.append({
                    "name": t_name,
                    "args": tc.get("inputs", {}),
                    "response": tc.get("output"),
                    "expected_args": matching_exp.get("expected_args"),
                    "expected_response": matching_exp.get("expected_response"),
                })
            actual_tools_order = [tc.get("tool_name") for tc in ls_turn.get("tools_call", []) if tc.get("tool_name")]
            actual_data = {
                "response": ls_turn.get("llm_response") or asst_msg.get("content"),
                "tools_called": actual_tools_called,
                "tools_order": actual_tools_order,
                "ui_widgets": asst_msg.get("actual_ui_widgets", []),
                "citations": asst_msg.get("actual_citations", []),
                "tokens": ls_turn.get("tokens") or {},
                "latency_ms": ls_turn.get("latency_ms"),
                "ttft_ms": ls_turn.get("ttft_ms"),
                "status": ls_turn.get("status", "success"),
                "reasoning": ls_turn.get("reasoning", []),
                "source": "langsmith",
            }
            run_id = ls_turn.get("run_id") or asst_msg.get("run_id")
            user_query = ls_turn.get("user_message") or user_msg.get("content", "")
            asst_response = ls_turn.get("llm_response") or asst_msg.get("content", "")
        else:
            # Strictly LangSmith: no trace found for this turn
            actual_data = {
                "response": asst_msg.get("content"),
                "tools_called": [],
                "tools_order": [],
                "ui_widgets": asst_msg.get("actual_ui_widgets", []),
                "citations": asst_msg.get("actual_citations", []),
                "tokens": {},
                "latency_ms": None,
                "ttft_ms": None,
                "status": "missing_langsmith_trace",
                "reasoning": [],
                "source": "langsmith",
                "warning": f"No LangSmith trace found for thread_id '{active_thread_id}' turn {turn_idx}.",
            }
            run_id = asst_msg.get("run_id")
            user_query = user_msg.get("content", "")
            asst_response = asst_msg.get("content", "")

        unified_turns.append({
        turn_entry = {
            "turn": turn_idx,
            "run_id": run_id,
            "user_query": user_query,
            "assistant_response": asst_response,
            "expected": expected_data,
            "actual": actual_data,
        })
        }
        if any(expected_data.get(k) for k in ["expected_content", "expected_tools_order", "expected_tools", "qa_note"]):
            turn_entry["expected"] = expected_data
        unified_turns.append(turn_entry)

    clean_meta = dict(meta)
    clean_meta.pop("expected_trajectory", None)
    clean_meta.pop("expected_turns", None)
    clean_meta.pop("thread_id", None)
    clean_meta.pop("Persona", None)

    export_payload = {
        "testcase_id": variation_id,
        "thread_id": active_thread_id,
        "target_mode": target_mode,
        "run_timestamp": run_timestamp,
        "scenario_description": getattr(test_case, "scenario", ""),
        "expected_outcome": getattr(test_case, "expected_outcome", ""),
        "expected": {
            "scenario_description": getattr(test_case, "scenario", ""),
            "expected_outcome": getattr(test_case, "expected_outcome", ""),
            "expected_trajectory": meta.get("expected_trajectory") or {},
            "expected_turns": expected_turns or [],
        },
        "actual": {
            "total_turns": len(compact_ls_export.get("turns", [])) if compact_ls_export else 0,
            "performance_summary": performance_summary,
            "trace_source": "langsmith",
            "status": trace_status,
            "langsmith_project": (compact_ls_export or {}).get("project_name") or os.getenv("LANGCHAIN_PROJECT", "airline-booking-chatbot"),
        },
        "unified_turns": unified_turns,
        "persona": {
            "name": golden_link.get("persona_name"),
            "characteristics": meta.get("Persona") or golden_link.get("persona_description"),
        },
        "context": getattr(test_case, "context", []) or [],
        "simulated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": clean_meta,
    }

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    # If saving into run_timestamp/runs_dir, ONLY mirror to datasets_dir if deterministic!
    # Dynamic simulation changes each run and belongs strictly in test/run/<timestamp>/.
    if is_det and (run_timestamp or runs_dir):
        effective_datasets_dir = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
        datasets_out_dir = resolve_target_dir(
            dest_root=effective_datasets_dir,
            rule_category=rule_category,
            scenario_name=scenario_name,
            persona_slug=persona_slug,
            target_mode="deterministic_reply",
        )
        canonical_file_path = datasets_out_dir / f"{variation_id}.json"
        truth_payload = {
            "testcase_id": variation_id,
            "target_mode": "deterministic_reply",
            "scenario_description": getattr(test_case, "scenario", ""),
            "expected_outcome": getattr(test_case, "expected_outcome", ""),
            "expected": {
                "scenario_description": getattr(test_case, "scenario", ""),
                "expected_outcome": getattr(test_case, "expected_outcome", ""),
                "expected_trajectory": meta.get("expected_trajectory") or {},
                "expected_turns": expected_turns or [],
            },
            "persona": {
                "name": golden_link.get("persona_name"),
                "characteristics": meta.get("Persona") or golden_link.get("persona_description"),
            },
            "context": getattr(test_case, "context", []) or [],
            "conversations": grouped_conversations,
            "total_turns": total_turns_count,
            "metadata": clean_meta,
        }
        try:
            with open(canonical_file_path, "w", encoding="utf-8") as f:
                json.dump(truth_payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Notice] Could not mirror testcase to datasets: {e}")

    return {
        "testcase_id": variation_id,
        "json_path": str(json_file_path),
        "payload": export_payload,
    }


def export_scenario_summary(
    scenario_rel_dir: str,
    test_cases: List[ConversationalTestCase],
    datasets_dir: Optional[Union[str, Path]] = None,
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = None,
    target_mode: str = "dynamic_simulation",
) -> Dict[str, str]:
    """
    Exports a consolidated `dataset.json` and a markdown transcript report
    at the scenario level under `<dest_root>/<scenario_rel_dir>/`.
    Supports exporting to runs_dir/<run_timestamp> or datasets_dir.
    Only mirrors to datasets_dir if target_mode is deterministic.
    """
    is_det = is_deterministic_mode(target_mode)

    if run_timestamp:
        dest_root = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)
    elif runs_dir:
        dest_root = Path(runs_dir)
    elif is_det and datasets_dir:
        dest_root = Path(datasets_dir)
    else:
        dest_root = get_run_timestamp_dir(runs_root=get_default_runs_dir())

    scenario_base_dir = dest_root / scenario_rel_dir
    scenario_base_dir.mkdir(parents=True, exist_ok=True)

    json_path = scenario_base_dir / "dataset.json"
    md_path = scenario_base_dir / "simulation_report.md"

    serialized_cases = []
    for tc in test_cases:
        meta = _extract_metadata(tc)
        g_link = meta.get("golden_link") or {}
        var_id = g_link.get("variation_id") or tc.name

        raw_turns = getattr(tc, "turns", []) or []
        grouped_convs, total_turns_count = group_turns_into_conversations(raw_turns)

        serialized_cases.append({
            "testcase_id": var_id,
            "scenario_description": tc.scenario,
            "expected_outcome": tc.expected_outcome,
            "persona": meta.get("Persona") or g_link.get("persona_name"),
            "conversations": grouped_convs,
            "total_turns": total_turns_count,
            "metadata": meta,
        })

    consolidated_payload = {
        "scenario_rel_dir": scenario_rel_dir,
        "run_timestamp": run_timestamp,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "total_conversations": len(test_cases),
        "conversations": serialized_cases,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(consolidated_payload, f, indent=2, ensure_ascii=False)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🤖 Multi-Turn Conversational Dataset Report\n\n")
        f.write(f"- **Scenario**: `{scenario_rel_dir}`\n")
        f.write(f"- **Exported at**: `{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}`\n")
        if run_timestamp:
            f.write(f"- **Run Timestamp**: `{run_timestamp}`\n")
        f.write(f"- **Total Variations**: `{len(test_cases)}`\n\n")
        f.write("---\n\n")

        for idx, tc in enumerate(test_cases, start=1):
            meta = _extract_metadata(tc)
            g_link = meta.get("golden_link") or {}
            var_id = g_link.get("variation_id") or tc.name

            f.write(f"## 💬 Case #{idx}: `{var_id}`\n\n")
            f.write(f"- **Persona**: {g_link.get('persona_name', 'Unknown')}\n")
            f.write(f"- **Scenario**: {tc.scenario}\n")
            f.write(f"- **Expected Outcome**: {tc.expected_outcome}\n")
            f.write(f"- **Variation File**: `{g_link.get('variation_file', '')}`\n\n")
            f.write("### Transcript\n\n")

            raw_turns = getattr(tc, "turns", []) or []
            grouped_convs, _ = group_turns_into_conversations(raw_turns)

            for turn_label, turn_msgs in grouped_convs.items():
                f.write(f"#### 🔄 {turn_label.title()}\n\n")
                for msg in turn_msgs:
                    icon = "👤 **User**" if msg.get("role") == "user" else "🤖 **Assistant**"
                    f.write(f"{icon}:\n{msg.get('content', '')}\n\n")
                    if msg.get("actual_tools_called"):
                        f.write("  - 🛠️ **Tools Called**:\n")
                        for tc_item in msg["actual_tools_called"]:
                            args_str = json.dumps(tc_item.get("args", {}), ensure_ascii=False)
                            resp_str = json.dumps(tc_item.get("response", {}), ensure_ascii=False)
                            f.write(f"    - `{tc_item.get('name')}` with params `{args_str}` -> response `{resp_str}`\n")
                        f.write("\n")
                    if msg.get("actual_ui_widgets"):
                        f.write("  - 📱 **UI Widgets Emitted**:\n")
                        for widget in msg["actual_ui_widgets"]:
                            f.write(f"    - `{widget.get('type')}` (Valid JSON: `{widget.get('is_valid_json')}`)\n")
                        f.write("\n")

            f.write("---\n\n")

    # If saving into run_timestamp/runs_dir, ONLY mirror summary to datasets_dir if deterministic
    if is_det and (run_timestamp or runs_dir or datasets_dir):
        effective_datasets_dir = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
        datasets_base_dir = effective_datasets_dir / scenario_rel_dir
        datasets_base_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(datasets_base_dir / "dataset.json", "w", encoding="utf-8") as f:
                json.dump(consolidated_payload, f, indent=2, ensure_ascii=False)
            with open(datasets_base_dir / "simulation_report.md", "w", encoding="utf-8") as f:
                with open(md_path, "r", encoding="utf-8") as src_f:
                    f.write(src_f.read())
        except Exception as e:
            print(f"[Notice] Could not mirror scenario summary to datasets: {e}")

    return {
        "dataset_json": str(json_path),
        "report_md": str(md_path),
    }


def promote_run_to_deterministic(
    run_file_path: Union[str, Path],
    datasets_dir: Optional[Union[str, Path]] = None,
    overwrite: bool = True,
) -> Path:
    """
    Promotes an executed run JSON (e.g. from dynamic simulation in test/run/) into a curated
    deterministic ground-truth testcase under datasets/<category>/<scenario>/<persona>/deterministic_reply/<variation_id>.json.
    Freezes user queries and expected outputs into a clean turn-by-turn format for QA editing.
    """
    run_path = Path(run_file_path)
    if not run_path.exists():
        raise FileNotFoundError(f"Run file not found: {run_path}")

    with open(run_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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
    if dest_file.exists() and not overwrite:
        raise FileExistsError(f"Target file already exists: {dest_file}")

    # Build turn-by-turn conversations structure for QA editing
    # Baseline expected values are derived from actual execution (user comment: "use expected from the actual execution")
    conversations = {}
    unified_turns = data.get("unified_turns") or []
    for ut in unified_turns:
        t_num = ut.get("turn", len(conversations) + 1)
        exp = ut.get("expected") or {}
        act = ut.get("actual") or {}

        exp_content = exp.get("expected_content") or ut.get("assistant_response") or act.get("response")
        exp_tools_order = exp.get("expected_tools_order") or act.get("tools_order") or []
        exp_tools = exp.get("expected_tools")
        if not exp_tools:
            exp_tools = [
                {
                    "name": tc.get("name"),
                    "expected_args": tc.get("args") or tc.get("inputs") or {},
                    "expected_response": tc.get("response") or tc.get("output"),
                }
                for tc in act.get("tools_called", [])
                if tc.get("name")
            ]

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
                "expected_content": exp_content,
                "expected_tools_call_order": exp_tools_order,
                "expected_tools": exp_tools,
                "qa_note": exp.get("qa_note") or f"Promoted from dynamic run {var_id} turn {t_num}",
            },
        ]

    promoted_expected = dict(data.get("expected") or {})
    promoted_expected.pop("expected_turns", None)

    promoted_payload = {
        "testcase_id": var_id,
        "target_mode": "deterministic_reply",
        "scenario_description": data.get("scenario_description") or "",
        "expected_outcome": data.get("expected_outcome") or "",
        "expected": data.get("expected") or {},
        "expected": promoted_expected,
        "persona": data.get("persona") or {},
        "context": data.get("context") or [],
        "conversations": conversations,
        "total_turns": len(conversations),
        "promoted_from_run": str(run_path),
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "metadata": meta,
    }

    with open(dest_file, "w", encoding="utf-8") as f:
        json.dump(promoted_payload, f, indent=2, ensure_ascii=False)

    return dest_file


def load_dataset_for_evaluation(
    datasets_dir: Optional[Union[str, Path]] = None,
    runs_dir: Optional[Union[str, Path]] = None,
    run_timestamp: Optional[str] = None,
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
    variation_filter: Optional[str] = None,
) -> List[ConversationalTestCase]:
    """
    Loads simulated conversation JSONs from `test/run/<run_timestamp>/` or `conversational_golden/datasets/`
    into DeepEval `ConversationalTestCase` instances ready for evaluation.
    Supports both unified turns format (`unified_turns`) and grouped turn format (`conversations`).
    Unpacks tools, responses, UI widgets, citations, LangSmith execution traces, and performance metrics.
    """
    if run_timestamp:
        if run_timestamp.lower() == "latest":
            root = get_latest_run_dir(runs_root=runs_dir)
            if not root:
                # Fallback to datasets_dir if no runs exist yet
                root = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
        else:
            root = get_run_timestamp_dir(timestamp_str=run_timestamp, runs_root=runs_dir)
    elif runs_dir:
        root = Path(runs_dir)
    elif datasets_dir:
        root = Path(datasets_dir)
    else:
        # Default: try latest run first, fallback to datasets
        latest_run = get_latest_run_dir()
        root = latest_run if latest_run and latest_run.exists() else get_default_datasets_dir()

    if not root or not root.exists():
        return []

    test_cases: List[ConversationalTestCase] = []

    # Find all variation testcase files (exclude dataset.json consolidated files and evaluation_report.json)
    for json_path in sorted(root.rglob("*.json")):
        if json_path.name in ("dataset.json", "evaluation_report.json", "personas.json"):
            continue

        data = load_json_file(json_path)
        if not data:
            continue

        case_name = data.get("testcase_id") or data.get("case_id") or json_path.stem
        if variation_filter and case_name.lower() != variation_filter.lower():
            continue

        metadata = dict(data.get("metadata") or {})
        g_link = metadata.get("golden_link") or data.get("golden_link") or {}
        cat = g_link.get("rule_category") or ""
        s_name = g_link.get("scenario_name") or ""
        s_rel = g_link.get("scenario_rel_dir") or ""

        if category_filter and cat.lower() != category_filter.lower():
            continue
        if scenario_filter and s_name.lower() != scenario_filter.lower() and s_rel.lower() != scenario_filter.lower():
            continue

        turns: List[Turn] = []

        # Check if unified_turns format is present (enriched with LangSmith actuals)
        if data.get("unified_turns"):
            for ut in data["unified_turns"]:
                # User turn
                u_content = ut.get("user_query") or ""
                turns.append(Turn(role="user", content=u_content))

                # Assistant turn
                asst_content = ut.get("assistant_response") or ""
                actual_info = ut.get("actual") or {}
                expected_info = ut.get("expected") or {}

                asst_meta: Dict[str, Any] = {
                    "turn": ut.get("turn"),
                    "run_id": ut.get("run_id"),
                    "actual": actual_info,
                    "expected": expected_info,
                    "actual_tools_called": actual_info.get("tools_called") or [],
                    "actual_tools_call_order": actual_info.get("tools_order") or [],
                    "expected_tools_call_order": expected_info.get("expected_tools_order") or [],
                    "expected_content": expected_info.get("expected_content"),
                    "actual_ui_widgets": actual_info.get("ui_widgets") or [],
                    "actual_citations": actual_info.get("citations") or [],
                    "metrics": {
                        "tokens": actual_info.get("tokens"),
                        "latency_ms": actual_info.get("latency_ms"),
                        "ttft_ms": actual_info.get("ttft_ms"),
                    },
                }
                turns.append(Turn(role="assistant", content=asst_content, metadata=asst_meta))
        else:
            # Fallback for older dataset files with conversations or turns
            raw_conversations = data.get("conversations") or data.get("turns")
            if not raw_conversations:
                continue

            messages = []
            if isinstance(raw_conversations, dict):
                for turn_key, turn_msgs in raw_conversations.items():
                    if isinstance(turn_msgs, list):
                        messages.extend(turn_msgs)
            elif isinstance(raw_conversations, list):
                messages = raw_conversations

            for t in messages:
                turn_meta = {}
                for k in [
                    "actual_tools_called",
                    "actual_tools_call_order",
                    "expected_tools_call_order",
                    "expected_content",
                    "actual_ui_widgets",
                    "actual_citations",
                    "metrics",
                    "run_id",
                ]:
                    if t.get(k) is not None:
                        turn_meta[k] = t[k]
                if isinstance(t.get("metadata"), dict):
                    turn_meta.update(t["metadata"])

                turns.append(
                    Turn(
                        role=t.get("role", "user"),
                        content=t.get("content", ""),
                        metadata=turn_meta if turn_meta else None,
                    )
                )

        if not turns:
            continue

        metadata["golden_link"] = g_link
        metadata["thread_id"] = data.get("thread_id") or metadata.get("thread_id")
        metadata["expected_metrics"] = metadata.get("expected_metrics") or (data.get("expected") or {}).get("expected_metrics") or data.get("expected_metrics") or {}
        metadata["expected_trajectory"] = (data.get("expected") or {}).get("expected_trajectory") or data.get("expected_trajectory") or metadata.get("expected_trajectory") or {}
        metadata["expected"] = data.get("expected") or {}
        metadata["actual"] = data.get("actual") or {}
        metadata["unified_turns"] = data.get("unified_turns") or []
        metadata["performance_summary"] = (data.get("actual") or {}).get("performance_summary") or data.get("performance_summary") or {}
        metadata["json_path"] = str(json_path)

        scenario_text = data.get("scenario_description") or data.get("scenario") or "Conversational test"

        tc = ConversationalTestCase(
            turns=turns,
            scenario=scenario_text,
            expected_outcome=data.get("expected_outcome") or "",
            context=data.get("context") or None,
            name=case_name,
            metadata=metadata,
        )
        test_cases.append(tc)

    return test_cases
