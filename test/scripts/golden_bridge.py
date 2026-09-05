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

    if variations_dir.is_dir():
        for var_file in sorted(variations_dir.glob("*.json")):
            var_data = load_json_file(var_file)
            if not var_data:
                continue

            persona_name = var_data.get("persona_name") or var_file.stem.replace("_", " ").title()
            persona_desc = var_data.get("persona_description") or ""
            variations_list = var_data.get("variations") or []

            personas.append({
                "persona_file": str(var_file),
                "persona_filename": var_file.name,
                "persona_slug": var_file.stem,
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


def resolve_target_dir(
    dest_root: Path,
    rule_category: str,
    scenario_name: str,
    persona_slug: str,
    target_mode: str = "dynamic_simulation",
) -> Path:
    """
    Resolves the destination folder under datasets for a specific persona variation.
    Maps:
    - 'deterministic', 'deterministic_replay', 'deterministic_reply' -> deterministic_reply/ or deterministic_replay/
    - 'dynamic', 'dynamic_simulation' -> dynamic_simulation/
    """
    persona_dir = dest_root / rule_category / scenario_name / persona_slug

    norm_mode = (target_mode or "dynamic_simulation").lower().strip()
    if norm_mode in ["deterministic", "deterministic_replay", "deterministic_reply", "replay", "reply"]:
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
    thread_id: Optional[str] = None,
    target_mode: str = "dynamic_simulation",
    overwrite: bool = False,
) -> Dict[str, Any]:
    """
    Exports a single simulated `ConversationalTestCase` into the datasets hierarchy,
    matching the exact directory layout of `conversational_golden/rules`.
    Supports segregated target_mode folders ('dynamic_simulation' vs 'deterministic_replay')
    and applies a non-destructive timestamped naming safeguard if the file already exists.
    """
    dest_root = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
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

    # Segregated target folder: datasets/<rule_category>/<scenario_name>/<persona_slug>/<target_sub>/
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
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file_path = scenario_out_dir / f"{variation_id}_{timestamp_str}.json"
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

    # Compute performance summary across turns
    total_latency_ms = 0.0
    ttft_list = []
    total_tokens = 0
    total_cost_usd = 0.0

    for turn_label, turn_msgs in grouped_conversations.items():
        for msg in turn_msgs:
            m = msg.get("metrics") or {}
            if m:
                total_latency_ms += m.get("latency_ms", 0.0)
                if m.get("ttft_ms") is not None:
                    ttft_list.append(m["ttft_ms"])
                total_tokens += m.get("total_tokens", 0)
                total_cost_usd += m.get("cost_usd", 0.0)

    performance_summary = {
        "total_turns": total_turns_count,
        "total_latency_ms": round(total_latency_ms, 2),
        "avg_ttft_ms": round(sum(ttft_list) / len(ttft_list), 2) if ttft_list else 0.0,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost_usd, 6),
    }

    clean_meta = dict(meta)
    clean_meta.pop("expected_trajectory", None)
    clean_meta.pop("expected_turns", None)
    clean_meta.pop("thread_id", None)
    clean_meta.pop("Persona", None)

    export_payload = {
        "testcase_id": variation_id,
        "thread_id": active_thread_id,
        "scenario_description": getattr(test_case, "scenario", ""),
        "expected_outcome": getattr(test_case, "expected_outcome", ""),
        "expected_trajectory": meta.get("expected_trajectory") or {},
        "persona": {
            "name": golden_link.get("persona_name"),
            "characteristics": meta.get("Persona") or golden_link.get("persona_description"),
        },
        "context": getattr(test_case, "context", []) or [],
        "conversations": grouped_conversations,
        "performance_summary": performance_summary,
        "simulated_at": datetime.now(timezone.utc).isoformat(),
        "total_turns": total_turns_count,
        "metadata": clean_meta,
    }

    with open(json_file_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    return {
        "testcase_id": variation_id,
        "json_path": str(json_file_path),
        "payload": export_payload,
    }


def export_scenario_summary(
    scenario_rel_dir: str,
    test_cases: List[ConversationalTestCase],
    datasets_dir: Optional[Union[str, Path]] = None,
) -> Dict[str, str]:
    """
    Exports a consolidated `dataset.json` and a markdown transcript report
    at the scenario level under `datasets/<scenario_rel_dir>/`.
    """
    dest_root = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
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

    return {
        "dataset_json": str(json_path),
        "report_md": str(md_path),
    }


def load_dataset_for_evaluation(
    datasets_dir: Optional[Union[str, Path]] = None,
    category_filter: Optional[str] = None,
    scenario_filter: Optional[str] = None,
) -> List[ConversationalTestCase]:
    """
    Loads simulated conversation JSONs from `conversational_golden/datasets/`
    into DeepEval `ConversationalTestCase` instances ready for evaluation.
    Supports both grouped turn format ({"turn 1": [...]}) and flat list format.
    Unpacks tools, responses, UI widgets, citations, and performance metrics.
    """
    root = Path(datasets_dir) if datasets_dir else get_default_datasets_dir()
    if not root.exists():
        return []

    test_cases: List[ConversationalTestCase] = []

    # Find all variation testcase files (exclude dataset.json consolidated files)
    for json_path in sorted(root.rglob("*.json")):
        if json_path.name == "dataset.json":
            continue

        data = load_json_file(json_path)
        if not data:
            continue

        raw_conversations = data.get("conversations") or data.get("turns")
        if not raw_conversations:
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

        messages = []
        if isinstance(raw_conversations, dict):
            for turn_key, turn_msgs in raw_conversations.items():
                if isinstance(turn_msgs, list):
                    messages.extend(turn_msgs)
        elif isinstance(raw_conversations, list):
            messages = raw_conversations

        turns = []
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

        metadata["golden_link"] = g_link
        metadata["thread_id"] = data.get("thread_id") or metadata.get("thread_id")
        metadata["expected_metrics"] = metadata.get("expected_metrics") or data.get("expected_metrics")
        metadata["expected_trajectory"] = data.get("expected_trajectory") or metadata.get("expected_trajectory") or {}
        metadata["performance_summary"] = data.get("performance_summary") or {}

        case_name = data.get("testcase_id") or data.get("case_id")
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
