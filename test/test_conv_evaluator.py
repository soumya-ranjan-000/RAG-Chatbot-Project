import os
import sys
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone

_TEST_DIR = Path(__file__).resolve().parent
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

from deepeval.test_case import ConversationalTestCase, Turn
from scripts.golden_bridge import (
    export_simulated_testcase,
    export_scenario_summary,
    get_run_timestamp_dir,
    load_dataset_for_evaluation,
    prune_old_runs,
)
from scripts.conv_metrics import (
    evaluate_deterministic_contracts,
    register_custom_metric,
)
from scripts.deterministic_eval import evaluate_deterministic_run
from scripts.dynamic_eval import evaluate_dynamic_run
from scripts.conv_evaluator import run_evaluation_suite


def test_runs_dir_and_unified_schema_export_and_load():
    with tempfile.TemporaryDirectory() as tmp_dir:
        runs_root = Path(tmp_dir) / "test_runs"
        run_ts = "2026-09-06_15-30-00"

        g_link = {
            "rule_category": "manage_my_booking",
            "scenario_name": "query_pnr",
            "scenario_rel_dir": "manage_my_booking/query_pnr",
            "persona_slug": "frustrated_traveler",
            "persona_name": "Frustrated Traveler",
            "variation_id": "FRUST_01_INVALID_FORMAT",
            "target_mode": "dynamic_simulation",
        }

        mock_test_case = ConversationalTestCase(
            turns=[
                Turn(role="user", content="I need flight status for AB123!"),
                Turn(
                    role="assistant",
                    content="A valid PNR must be 6 characters. Would you like me to connect you to an agent?",
                    metadata={
                        "actual_tools_called": [
                            {
                                "name": "check_booking_status",
                                "args": {"pnr": "AB123"},
                                "response": {"error": "Invalid format"},
                            }
                        ],
                        "actual_tools_call_order": ["check_booking_status"],
                        "actual_ui_widgets": [{"type": "flights", "is_valid_json": True}],
                        "actual_citations": [],
                        "metrics": {
                            "ttft_ms": 300.0,
                            "latency_ms": 1000.0,
                            "total_tokens": 450,
                        },
                        "run_id": "mock_run_123",
                    },
                ),
            ],
            scenario="User wants to check flight status with invalid 5-character PNR.",
            expected_outcome="Explain 6-character requirement.",
            context=["PNR must be 6 characters."],
            name="FRUST_01_INVALID_FORMAT",
            metadata={
                "golden_link": g_link,
                "thread_id": "mock_thread_test",
                "Persona": "Highly impatient",
                "expected_trajectory": {
                    "expected_tools": [{"name": "check_booking_status", "expected_args": {"pnr": "AB123"}}],
                    "expected_tools_order": ["check_booking_status"],
                    "forbidden_actions": ["Do not invent fake flight details"],
                    "performance_sla": {"max_ttft_ms": 2000, "max_total_tokens": 4000, "max_latency_ms": 5000},
                },
                "expected_turns": [
                    {
                        "turn": 1,
                        "expected_content": "Inform user that PNR AB123 is invalid.",
                        "expected_tools_call_order": ["check_booking_status"],
                        "expected_tools": [{"name": "check_booking_status", "expected_args": {"pnr": "AB123"}}],
                    }
                ],
                "expected_metrics": {
                    "metrics": [{"name": "RoleAdherenceMetric", "threshold": 0.8}]
                },
            },
        )

        # 1. Export using runs_dir and run_timestamp
        result = export_simulated_testcase(
            mock_test_case,
            runs_dir=runs_root,
            run_timestamp=run_ts,
            target_mode="dynamic_simulation",
            enrich_with_langsmith=False,
        )
        json_path = Path(result["json_path"])
        assert json_path.exists()

        # 2. Verify exact directory hierarchy: test/run/<date_time>/<category>/<scenario>/<persona>/<target_mode>/<variation_id>.json
        expected_rel_path = Path(run_ts) / "manage_my_booking" / "query_pnr" / "frustrated_traveler" / "dynamic_simulation" / "FRUST_01_INVALID_FORMAT.json"
        assert json_path.resolve() == (runs_root / expected_rel_path).resolve()

        # 3. Verify unified JSON schema
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        assert "expected" in payload
        assert "actual" in payload
        assert "unified_turns" in payload
        assert payload["thread_id"] == "mock_thread_test"
        assert payload["run_timestamp"] == run_ts
        assert len(payload["unified_turns"]) == 1

        u_turn = payload["unified_turns"][0]
        assert u_turn["turn"] == 1
        assert u_turn["user_query"] == "I need flight status for AB123!"
        assert "A valid PNR must be 6 characters" in u_turn["assistant_response"]
        assert u_turn["expected"]["expected_tools_order"] == ["check_booking_status"]
        assert u_turn["actual"]["tools_order"] == ["check_booking_status"]

        # 4. Load dataset for evaluation from runs_root
        loaded_cases = load_dataset_for_evaluation(
            runs_dir=runs_root,
            run_timestamp=run_ts,
            category_filter="manage_my_booking",
            scenario_filter="query_pnr",
        )
        assert len(loaded_cases) == 1
        loaded_tc = loaded_cases[0]
        assert loaded_tc.name == "FRUST_01_INVALID_FORMAT"
        assert len(loaded_tc.turns) == 2
        assert loaded_tc.turns[0].role == "user"
        assert loaded_tc.turns[1].role == "assistant"
        assert loaded_tc.turns[1].metadata["actual_tools_call_order"] == ["check_booking_status"]

        # 5. Evaluate deterministic contracts
        det_eval = evaluate_deterministic_contracts(loaded_tc)
        assert det_eval["all_passed"] is True
        assert det_eval["tool_correctness"]["passed"] is True
        assert det_eval["tool_order"]["passed"] is True
        assert det_eval["ui_widgets"]["passed"] is True
        assert det_eval["performance_sla"]["passed"] is True
        assert det_eval["negative_constraints"]["passed"] is True

        # 6. Execute evaluate_dynamic_run and verify dynamic_evaluation_report.json
        dyn_report = evaluate_dynamic_run(
            runs_dir=runs_root,
            run_timestamp=run_ts,
            skip_llm=True,
            dry_run=False,
        )
        assert dyn_report["total_testcases"] == 1
        assert dyn_report["passed_testcases"] == 1
        assert dyn_report["failed_testcases"] == 0

        dyn_report_path = runs_root / run_ts / "dynamic_evaluation_report.json"
        assert dyn_report_path.exists()
        with open(dyn_report_path, "r", encoding="utf-8") as f:
            saved_dyn = json.load(f)
        assert saved_dyn["total_testcases"] == 1
        assert saved_dyn["passed_testcases"] == 1

        # 7. Execute legacy run_evaluation_suite wrapper
        legacy_report = run_evaluation_suite(
            runs_dir=runs_root,
            run_timestamp=run_ts,
            skip_llm=True,
            dry_run=True,
        )
        assert legacy_report["total_testcases"] == 1
        assert legacy_report["passed_testcases"] == 1


def test_prune_old_runs():
    with tempfile.TemporaryDirectory() as tmp_dir:
        runs_root = Path(tmp_dir)

        # Create dummy .gitkeep file (must be preserved)
        gitkeep = runs_root / ".gitkeep"
        gitkeep.touch()

        # Create 5 chronological run directories
        run_dates = [
            "2026-09-01_10-00-00",
            "2026-09-02_10-00-00",
            "2026-09-03_10-00-00",
            "2026-09-04_10-00-00",
            "2026-09-05_10-00-00",
        ]
        for rd in run_dates:
            d = runs_root / rd
            d.mkdir(parents=True, exist_ok=True)
            (d / "dummy_report.json").write_text("{}", encoding="utf-8")

        assert len([d for d in runs_root.iterdir() if d.is_dir()]) == 5

        # Retention limit of 2: keep 09-04 and 09-05, prune 09-01, 09-02, 09-03
        pruned = prune_old_runs(runs_root=runs_root, keep_last=2)

        assert len(pruned) == 3
        pruned_names = [p.name for p in pruned]
        assert pruned_names == [
            "2026-09-01_10-00-00",
            "2026-09-02_10-00-00",
            "2026-09-03_10-00-00",
        ]

        remaining_dirs = sorted([d.name for d in runs_root.iterdir() if d.is_dir()])
        assert remaining_dirs == [
            "2026-09-04_10-00-00",
            "2026-09-05_10-00-00",
        ]
        # Ensure .gitkeep is never deleted
        assert gitkeep.exists()

