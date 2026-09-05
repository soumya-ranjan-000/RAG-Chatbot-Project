"""
DeepEval Conversational Simulator for Golden Scenarios
======================================================
Simulates multi-turn conversations against the chatbot backend using
DeepEval's `ConversationSimulator` and scenario rules defined in
`conversational_golden/rules`.

Exports generated multi-turn conversations as structured JSON datasets into
`conversational_golden/datasets/` preserving the golden hierarchy and
traceability links.
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import requests
from dotenv import load_dotenv

# 1. Robust sys.path bootstrap (ensures `import scripts...` works from any CWD)
_SCRIPT_DIR = Path(__file__).resolve().parent
_TEST_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _TEST_DIR.parent

for p in [str(_TEST_DIR), str(_PROJECT_ROOT), str(_SCRIPT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Load environment variables & API keys
load_dotenv()
parent_env = _TEST_DIR / ".env"
if parent_env.exists():
    load_dotenv(parent_env)

# Purge all empty-string environment variables so SDKs (OpenAI, Gemini, Confident) fall back to defaults
for k, v in list(os.environ.items()):
    if v == "":
        os.environ.pop(k, None)

from deepeval.dataset import ConversationalGolden, Persona
from deepeval.models import GeminiModel, OpenAIModel
from deepeval.simulator import ConversationSimulator
from deepeval.test_case import ConversationalTestCase, Turn

from scripts.golden_bridge import (
    build_conversational_goldens,
    discover_scenario_directories,
    export_scenario_summary,
    export_simulated_testcase,
    get_default_datasets_dir,
    get_default_rules_dir,
    load_scenario_bundle,
)
from scripts.testcase_store import save_simulator_case

DEFAULT_CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")


def get_simulator_model(model_name: Optional[str] = None):
    """
    Resolves and instantiates the LLM judge/simulator model.
    Prioritizes Gemini if GEMINI_API_KEY is available, else falls back to OpenAI GPT.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    chosen_model = model_name or os.getenv("SIMULATOR_MODEL") or os.getenv("GEMINI_MODEL_NAME")

    # if gemini_key and (not chosen_model or "gemini" in chosen_model.lower()):
    #     m = chosen_model or "gemini-3.6-flash"
    #     return GeminiModel(model=m, api_key=gemini_key)
    # elif openai_key:
    #     m = chosen_model or os.getenv("OPENAI_MODEL_NAME") or "gpt-4o-mini"
    #     return OpenAIModel(model=m, api_key=openai_key)
    # elif gemini_key:
    #     return GeminiModel(model="gemini-3.6-flash", api_key=gemini_key)
    # else:
    #     print("[Warning] No GEMINI_API_KEY or OPENAI_API_KEY found. Simulator will use default provider configuration.")
    #     return None

    return OpenAIModel(model="gpt-4o-mini", api_key=openai_key)

    


import re


def extract_ui_widgets(content: str) -> List[Dict[str, Any]]:
    """
    Extracts custom markdown code blocks (e.g. ```flights, ```tickets, ```seats)
    and validates their JSON schema syntax.
    """
    widgets = []
    pattern = r"```([a-zA-Z0-9_\-]+)\s*\n([\s\S]*?)\n```"
    for match in re.finditer(pattern, content):
        block_type = match.group(1).lower()
        block_body = match.group(2).strip()

        if block_type in ["flights", "tickets", "seats", "passenger", "booking", "fares"]:
            is_valid = False
            parsed_data = None
            try:
                parsed_data = json.loads(block_body)
                is_valid = True
            except Exception:
                is_valid = False

            widgets.append({
                "type": block_type,
                "is_valid_json": is_valid,
                "data": parsed_data if is_valid else block_body,
            })
    return widgets


def extract_citations(content: str) -> List[str]:
    """
    Extracts document and policy citations formatted like [document.pdf, Page 11].
    """
    citations = []
    pattern = r"\[([a-zA-Z0-9_\-\.]+\.(?:pdf|docx|txt|md|html)),\s*(?:Page|Section|Slide)?\s*([^\]]+)\]"
    for match in re.finditer(pattern, content, re.IGNORECASE):
        citations.append(match.group(0))
    return citations


class ChatApiCallbackHandler:
    """
    DeepEval Model Callback handler with thread_id, tool call, and UI widget tracking.
    Sends user queries to the Chat API and parses the streaming SSE response
    for tokens, tool invocations, results, and execution order.
    """

    def __init__(self, api_url: str = DEFAULT_CHAT_API_URL):
        self.api_url = api_url
        self.last_thread_id: Optional[str] = None
        self.last_run_id: Optional[str] = None

    def __call__(
        self,
        input: str,
        thread_id: str,
        turns: Optional[List[Turn]] = None,
    ) -> Turn:
        self.last_thread_id = thread_id
        history = []
        if turns:
            for turn in turns:
                history.append({"role": turn.role, "content": turn.content})

        payload = {
            "query": input,
            "thread_id": thread_id,
            "history": history,
            "passenger_profile": {
                "passenger_id": "usr_94f83b",
                "name": "Jane Smith",
                "email": "jane.smith@example.com",
                "frequent_flyer_number": "FF773910",
            },
        }

        try:
            response = requests.post(self.api_url, json=payload, stream=True, timeout=60)
            response.raise_for_status()

            assistant_content = ""
            turn_run_id: Optional[str] = None
            actual_tools_called: List[Dict[str, Any]] = []
            actual_tools_call_order: List[str] = []
            turn_metrics: Optional[Dict[str, Any]] = None

            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    raw_data = line[6:].strip()
                    if raw_data == "[DONE]":
                        break
                    try:
                        data = json.loads(raw_data)
                        event_type = data.get("type")

                        if event_type == "info":
                            server_thread_id = data.get("thread_id")
                            if server_thread_id:
                                self.last_thread_id = server_thread_id
                            turn_run_id = data.get("run_id")
                            self.last_run_id = turn_run_id

                        elif event_type == "token":
                            assistant_content += data.get("content", "")

                        elif event_type == "tool_call":
                            t_name = data.get("name")
                            t_args = data.get("args")
                            if t_name:
                                actual_tools_call_order.append(t_name)
                                actual_tools_called.append({
                                    "name": t_name,
                                    "args": t_args,
                                    "result": None,
                                })

                        elif event_type == "tool_result":
                            t_name = data.get("name")
                            t_args = data.get("args")
                            t_result = data.get("result")

                            # Match with corresponding pending tool call or append
                            matched = False
                            for call in reversed(actual_tools_called):
                                if call.get("name") == t_name and call.get("result") is None:
                                    call["result"] = t_result
                                    matched = True
                                    break
                            if not matched:
                                actual_tools_called.append({
                                    "name": t_name,
                                    "args": t_args,
                                    "result": t_result,
                                })

                        elif event_type == "metrics":
                            turn_metrics = data.get("metrics")

                        elif event_type == "error":
                            print(f"[Chat API Error] {data.get('message')}")

                    except json.JSONDecodeError:
                        continue

            content = assistant_content.strip() or "No response received from assistant."

            turn_metadata: Dict[str, Any] = {
                "thread_id": self.last_thread_id or thread_id,
                "run_id": turn_run_id,
                "actual_tools_called": actual_tools_called,
                "actual_tools_call_order": actual_tools_call_order,
            }
            if turn_metrics:
                turn_metadata["metrics"] = turn_metrics

            return Turn(
                role="assistant",
                content=content,
                metadata=turn_metadata,
            )

        except requests.exceptions.RequestException as e:
            print(f"[Warning] Could not reach Chat API at {self.api_url}: {e}")
            return Turn(
                role="assistant",
                content=f"Error connecting to backend chat API at {self.api_url}: {e}",
                metadata={
                    "thread_id": thread_id,
                    "actual_tools_called": [],
                    "actual_tools_call_order": [],
                },
            )


def create_chat_api_callback(api_url: str = DEFAULT_CHAT_API_URL) -> ChatApiCallbackHandler:
    return ChatApiCallbackHandler(api_url=api_url)


def run_simulations_for_scenario(
    scenario_dir: Path,
    simulator: Optional[ConversationSimulator] = None,
    datasets_dir: Optional[Path] = None,
    callback_handler: Optional[ChatApiCallbackHandler] = None,
    variation_filter: Optional[str] = None,
    max_turns: int = 4,
    dry_run: bool = False,
    target_mode: str = "dynamic_simulation",
    overwrite: bool = False,
) -> List[ConversationalTestCase]:
    """
    Executes simulations for all persona variations under a single scenario folder.
    Exports individual testcase JSON files into target_mode folder and updates scenario summaries.
    """
    bundle = load_scenario_bundle(scenario_dir)
    goldens = build_conversational_goldens(bundle, variation_id_filter=variation_filter)

    if not goldens:
        return []

    print(f"\n📂 Scenario: [{bundle['category']}] -> {bundle['scenario_name']}")
    print(f"   Config: {bundle['scenario_config_file']}")
    print(f"   Target Folder: {target_mode}")
    print(f"   Variations to simulate: {len(goldens)}")

    simulated_cases: List[ConversationalTestCase] = []

    for idx, golden in enumerate(goldens, start=1):
        g_meta = golden.additional_metadata or {}
        g_link = g_meta.get("golden_link", {})
        var_id = g_link.get("variation_id", golden.name)
        p_name = g_link.get("persona_name", "User")

        if dry_run:
            print(f"\n   [DRY-RUN] Case #{idx}: {var_id} ({p_name})")
            print(f"      • Scenario: {golden.scenario}")
            print(f"      • Expected Outcome: {golden.expected_outcome}")
            print(f"      • Context Chunks: {len(golden.context) if golden.context else 0}")
            print(f"      • Target Destination: {target_mode}")
            print(f"      • Variation File: {g_link.get('variation_file')}")
            continue

        print(f"\n   🤖 [{idx}/{len(goldens)}] Simulating: {var_id} ({p_name})...")

        # Run DeepEval simulation
        if simulator:
            test_cases = simulator.simulate(
                conversational_goldens=[golden],
                max_user_simulations=max_turns,
            )
            sim_tc = test_cases[0] if isinstance(test_cases, list) else test_cases
            simulated_cases.append(sim_tc)

            active_thread_id = callback_handler.last_thread_id if callback_handler else None

            # Export individual testcase to datasets hierarchy with target mode & safeguard
            export_result = export_simulated_testcase(
                test_case=sim_tc,
                datasets_dir=datasets_dir,
                thread_id=active_thread_id,
                target_mode=target_mode,
                overwrite=overwrite,
            )
            print(f"   ✅ Saved testcase: {export_result['json_path']}")

            # Also store in testcase store for legacy LangSmith compatibility if configured
            try:
                conversation_turns = [
                    {"role": turn.role, "content": turn.content}
                    for turn in getattr(sim_tc, "turns", [])
                ]
                save_simulator_case(
                    case_id=var_id,
                    case_type="multi_turn" if len(conversation_turns) > 1 else "single_turn",
                    thread_id=active_thread_id or sim_tc.metadata.get("thread_id"),
                    conversation=conversation_turns,
                    expected={
                        "scenario": getattr(sim_tc, "scenario", None),
                        "expected_outcome": getattr(sim_tc, "expected_outcome", None),
                    },
                    metadata=sim_tc.metadata or {},
                    project="airline-booking-chatbot",
                    base_dir="testdata",
                )
            except Exception:
                pass

    # Export scenario-level summary dataset & markdown
    if simulated_cases:
        summary_result = export_scenario_summary(
            scenario_rel_dir=bundle["scenario_rel_dir"],
            test_cases=simulated_cases,
            datasets_dir=datasets_dir,
        )
        print(f"   📊 Consolidated Dataset: {summary_result['dataset_json']}")
        print(f"   📝 Markdown Transcript:  {summary_result['report_md']}")

    return simulated_cases


def main():
    parser = argparse.ArgumentParser(
        description="DeepEval Multi-Turn Conversational Simulator for Golden Scenarios."
    )
    parser.add_argument(
        "--category",
        "-c",
        type=str,
        default=None,
        help="Filter by domain category (e.g. 'manage_my_booking', 'booking').",
    )
    parser.add_argument(
        "--scenario",
        "-s",
        type=str,
        default=None,
        help="Filter by scenario name or relative path (e.g. 'query_pnr', 'manage_my_booking/query_pnr').",
    )
    parser.add_argument(
        "--variation",
        "-v",
        type=str,
        default=None,
        help="Filter by specific variation ID (e.g. 'FRUST_01_INVALID_FORMAT').",
    )
    parser.add_argument(
        "--target",
        "--target-mode",
        type=str,
        default="dynamic",
        choices=["dynamic", "dynamic_simulation", "deterministic", "deterministic_replay", "deterministic_reply"],
        help="Target folder/mode for generated testcases: 'dynamic' (default) or 'deterministic' (for QA baseline creation).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing testcase JSON files instead of creating timestamped versions.",
    )
    parser.add_argument(
        "--max-turns",
        "-t",
        type=int,
        default=4,
        help="Maximum user conversation turns to simulate per scenario (default: 4).",
    )
    parser.add_argument(
        "--model",
        "-m",
        type=str,
        default=None,
        help="Simulator LLM model override (e.g. 'gemini-2.5-flash', 'gpt-4o-mini').",
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
        help="Validate and preview goldens without invoking the LLM simulator or chat API.",
    )
    parser.add_argument(
        "--rules-dir",
        type=str,
        default=None,
        help="Custom path to rules directory (default: 'conversational_golden/rules').",
    )
    parser.add_argument(
        "--datasets-dir",
        type=str,
        default=None,
        help="Custom path to datasets output directory (default: 'conversational_golden/datasets').",
    )

    args = parser.parse_args()

    rules_root = Path(args.rules_dir) if args.rules_dir else get_default_rules_dir()
    datasets_root = Path(args.datasets_dir) if args.datasets_dir else get_default_datasets_dir()

    print("=" * 70)
    print("🚀 DeepEval Conversational Golden Simulator")
    print("=" * 70)
    print(f"📁 Rules Directory:    {rules_root.resolve()}")
    print(f"📁 Datasets Directory: {datasets_root.resolve()}")
    print(f"🔗 Target Chat API:    {args.backend_url}")
    print(f"🎯 Filter Category:    {args.category or 'All'}")
    print(f"🎯 Filter Scenario:    {args.scenario or 'All'}")
    print(f"🎯 Filter Variation:   {args.variation or 'All'}")
    print(f"🔁 Max User Turns:     {args.max_turns}")
    print(f"⚙️  Dry-Run Mode:       {args.dry_run}")
    print("=" * 70)

    # 1. Discover all scenario directories
    all_scenario_dirs = discover_scenario_directories(rules_root)
    if not all_scenario_dirs:
        print(f"[Error] No scenario directories found in {rules_root}")
        sys.exit(1)

    # Filter scenario directories if category or scenario specified
    target_dirs: List[Path] = []
    for s_dir in all_scenario_dirs:
        bundle = load_scenario_bundle(s_dir, rules_root=rules_root)
        cat = bundle["category"]
        s_name = bundle["scenario_name"]
        s_rel = bundle["scenario_rel_dir"]

        if args.category and cat.lower() != args.category.lower():
            continue
        if args.scenario and s_name.lower() != args.scenario.lower() and s_rel.lower() != args.scenario.lower():
            continue

        target_dirs.append(s_dir)

    if not target_dirs:
        print(f"[Error] No scenarios matched filter (category='{args.category}', scenario='{args.scenario}')")
        sys.exit(1)

    print(f"✨ Found {len(target_dirs)} matching scenario(s) to process.")

    # 2. Setup Simulator & Callback if not dry run
    simulator = None
    callback = None
    if not args.dry_run:
        sim_model = get_simulator_model(args.model)
        callback = create_chat_api_callback(api_url=args.backend_url)

        simulator_kwargs: Dict[str, Any] = {
            "model_callback": callback,
            "max_concurrent": 1,
            "async_mode": False,
        }
        if sim_model:
            simulator_kwargs["simulator_model"] = sim_model

        simulator = ConversationSimulator(**simulator_kwargs)

    # 3. Run simulations across all target scenarios
    total_simulated = 0
    start_time = time.time()

    for s_dir in target_dirs:
        cases = run_simulations_for_scenario(
            scenario_dir=s_dir,
            simulator=simulator,
            datasets_dir=datasets_root,
            callback_handler=callback,
            variation_filter=args.variation,
            max_turns=args.max_turns,
            dry_run=args.dry_run,
            target_mode=args.target,
            overwrite=args.overwrite,
        )
        total_simulated += len(cases)

    duration = round(time.time() - start_time, 2)
    print("\n" + "=" * 70)
    if args.dry_run:
        print(f"🎉 Dry run complete in {duration}s. All goldens validated successfully.")
    else:
        print(f"🎉 Completed simulation of {total_simulated} conversation(s) in {duration}s.")
        print(f"📁 Datasets generated under: {datasets_root.resolve()}")
    print("=" * 70)


if __name__ == "__main__":
    main()

