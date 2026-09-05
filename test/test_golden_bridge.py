import json
import tempfile
from pathlib import Path
from deepeval.dataset import ConversationalGolden, Persona
from deepeval.test_case import ConversationalTestCase, Turn

from scripts.golden_bridge import (
    build_conversational_goldens,
    discover_scenario_directories,
    export_scenario_summary,
    export_simulated_testcase,
    get_default_rules_dir,
    load_all_conversational_goldens,
    load_dataset_for_evaluation,
    load_scenario_bundle,
)


def test_discover_scenario_directories():
    rules_dir = get_default_rules_dir()
    discovered = discover_scenario_directories(rules_dir)
    assert len(discovered) >= 1
    paths_str = [str(p) for p in discovered]
    assert any("manage_my_booking/query_pnr" in p for p in paths_str)


def test_load_scenario_bundle():
    rules_dir = get_default_rules_dir()
    scenario_dir = rules_dir / "manage_my_booking" / "query_pnr"
    bundle = load_scenario_bundle(scenario_dir, rules_root=rules_dir)

    assert bundle["category"] == "manage_my_booking"
    assert bundle["scenario_name"] == "query_pnr"
    assert bundle["scenario_config"]["scenario_id"] == "SCENARIO_PNR_01"
    assert len(bundle["personas"]) >= 2
    assert "metrics" in bundle["expected_metrics"]
    assert "Airline Policy for PNR Query" in bundle["shared_context_text"]


def test_build_conversational_goldens():
    rules_dir = get_default_rules_dir()
    scenario_dir = rules_dir / "manage_my_booking" / "query_pnr"
    bundle = load_scenario_bundle(scenario_dir, rules_root=rules_dir)

    goldens = build_conversational_goldens(bundle)
    assert len(goldens) == 4

    # Check variation IDs
    var_ids = [g.name for g in goldens]
    assert "FRUST_01_INVALID_FORMAT" in var_ids
    assert "FRUST_02_DEMANDS_AGENT" in var_ids
    assert "NORM_01_VALID_PNR_DIRECT" in var_ids
    assert "NORM_02_PNR_ON_REQUEST" in var_ids

    # Check golden link metadata
    g1 = next(g for g in goldens if g.name == "FRUST_01_INVALID_FORMAT")
    g_link = g1.additional_metadata["golden_link"]
    assert g_link["scenario_id"] == "SCENARIO_PNR_01"
    assert g_link["rule_category"] == "manage_my_booking"
    assert g_link["scenario_name"] == "query_pnr"
    assert g_link["persona_slug"] == "frustrated_traveler"
    assert g_link["persona_name"] == "Frustrated Traveler"
    assert "AB123" in g1.scenario
    assert g1.expected_outcome.startswith("The chatbot politely explains")
    assert len(g1.context) >= 3
    # Check expected_trajectory in golden metadata
    traj = g1.additional_metadata.get("expected_trajectory", {})
    assert "expected_tools" in traj
    assert "forbidden_actions" in traj
    assert traj["expected_tools"][0]["name"] == "check_booking_status"


def test_ui_widgets_and_citations_extraction():
    from scripts.conv_simulator import extract_ui_widgets, extract_citations

    sample_content = (
        "Here are your flight details as per [airline_policy.pdf, Page 4]:\n\n"
        "```tickets\n"
        "[\n"
        "  {\"pnr\": \"AB1234\", \"flight\": \"AI-101\", \"status\": \"Confirmed\"}\n"
        "]\n"
        "```\n"
        "Let me know if you need anything else."
    )

    widgets = extract_ui_widgets(sample_content)
    assert len(widgets) == 1
    assert widgets[0]["type"] == "tickets"
    assert widgets[0]["is_valid_json"] is True
    assert widgets[0]["data"][0]["pnr"] == "AB1234"

    citations = extract_citations(sample_content)
    assert len(citations) == 1
    assert "airline_policy.pdf" in citations[0]


def test_export_and_load_simulated_dataset():
    with tempfile.TemporaryDirectory() as tmp_dir:
        datasets_dir = Path(tmp_dir)

        # Create a mock ConversationalTestCase with 7-dimension attributes
        g_link = {
            "rule_category": "manage_my_booking",
            "scenario_name": "query_pnr",
            "scenario_rel_dir": "manage_my_booking/query_pnr",
            "scenario_id": "SCENARIO_PNR_01",
            "scenario_config_path": "/fake/scenario_config.json",
            "variation_file": "/fake/frustrated_traveler.json",
            "persona_slug": "frustrated_traveler",
            "persona_name": "Frustrated Traveler",
            "persona_description": "Highly impatient",
            "variation_id": "FRUST_01_INVALID_FORMAT",
        }

        mock_test_case = ConversationalTestCase(
            turns=[
                Turn(role="user", content="Check my flight status for PNR AB123!"),
                Turn(
                    role="assistant",
                    content="A valid PNR must be exactly 6 characters. Would you like me to connect you to a human agent?",
                    metadata={
                        "actual_tools_called": [
                            {
                                "name": "check_booking_status",
                                "args": {"pnr": "AB123"},
                                "response": {"error": "Invalid format"},
                                "result": {"error": "Invalid format"},
                            }
                        ],
                        "actual_tools_call_order": ["check_booking_status"],
                        "actual_ui_widgets": [],
                        "actual_citations": [],
                        "metrics": {
                            "ttft_ms": 350.0,
                            "latency_ms": 1100.0,
                            "total_tokens": 480,
                            "cost_usd": 0.00012,
                        },
                        "run_id": "mock_run_999",
                    },
                ),
            ],
            scenario="User wants to check flight status. User provides 5-character PNR.",
            expected_outcome="The chatbot explains 6-character requirement and offers handoff.",
            context=["A valid PNR must be exactly 6 characters."],
            name="FRUST_01_INVALID_FORMAT",
            metadata={
                "golden_link": g_link,
                "thread_id": "test_thread_12345",
                "Persona": "Highly impatient",
                "expected_trajectory": {
                    "expected_tools": [{"name": "check_booking_status", "expected_args": {"pnr": "AB123"}}],
                    "expected_tools_order": ["check_booking_status"],
                    "forbidden_actions": ["Do not invent fake flight details"],
                    "performance_sla": {"max_ttft_ms": 2000, "max_total_tokens": 4000},
                },
                "expected_turns": [
                    {
                        "turn": 1,
                        "expected_content": "Inform user that PNR AB123 is invalid and explain 6-character rule.",
                        "expected_tools_call_order": ["check_booking_status"],
                        "expected_tools": [
                            {
                                "name": "check_booking_status",
                                "expected_args": {"pnr": "AB123"},
                                "expected_response": {"error": "Invalid format"},
                            }
                        ],
                    }
                ],
                "expected_metrics": {
                    "metrics": [{"name": "ConversationalRelevancyMetric", "threshold": 0.7}]
                },
            },
        )

        # Export single test case
        result = export_simulated_testcase(mock_test_case, datasets_dir=datasets_dir)
        exported_path = Path(result["json_path"])
        assert exported_path.exists()
        assert "manage_my_booking/query_pnr/frustrated_traveler/dynamic_simulation/FRUST_01_INVALID_FORMAT.json" in str(exported_path)

        # Verify JSON payload
        with open(exported_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["testcase_id"] == "FRUST_01_INVALID_FORMAT"
        assert data["thread_id"] == "test_thread_12345"
        assert "User wants to check flight status" in data["scenario_description"]
        assert data["metadata"]["golden_link"]["scenario_id"] == "SCENARIO_PNR_01"
        assert "turn 1" in data["conversations"]
        turn_1 = data["conversations"]["turn 1"]
        assert len(turn_1) == 2
        assert turn_1[0]["role"] == "user"
        assert turn_1[1]["role"] == "assistant"
        assert turn_1[1]["expected_content"] == "Inform user that PNR AB123 is invalid and explain 6-character rule."
        assert turn_1[1]["expected_tools_call_order"] == ["check_booking_status"]
        assert turn_1[1]["actual_tools_call_order"] == ["check_booking_status"]
        assert turn_1[1]["actual_tools_called"][0]["name"] == "check_booking_status"
        assert turn_1[1]["actual_tools_called"][0]["args"] == {"pnr": "AB123"}
        assert turn_1[1]["actual_tools_called"][0]["expected_args"] == {"pnr": "AB123"}
        assert turn_1[1]["actual_tools_called"][0]["response"] == {"error": "Invalid format"}
        assert turn_1[1]["actual_tools_called"][0]["expected_response"] == {"error": "Invalid format"}
        assert turn_1[1]["metrics"]["ttft_ms"] == 350.0
        assert turn_1[1]["run_id"] == "mock_run_999"
        assert data["total_turns"] == 1
        assert data["performance_summary"]["total_tokens"] == 480
        assert data["performance_summary"]["avg_ttft_ms"] == 350.0

        # Export scenario summary
        summary = export_scenario_summary(
            scenario_rel_dir="manage_my_booking/query_pnr",
            test_cases=[mock_test_case],
            datasets_dir=datasets_dir,
        )
        assert Path(summary["dataset_json"]).exists()
        assert Path(summary["report_md"]).exists()

        # Load back dataset for evaluation
        loaded_cases = load_dataset_for_evaluation(
            datasets_dir=datasets_dir,
            category_filter="manage_my_booking",
            scenario_filter="query_pnr",
        )
        assert len(loaded_cases) == 1
        loaded = loaded_cases[0]
        assert loaded.name == "FRUST_01_INVALID_FORMAT"
        assert len(loaded.turns) == 2
        assert loaded.metadata["golden_link"]["scenario_id"] == "SCENARIO_PNR_01"
        assert loaded.metadata["thread_id"] == "test_thread_12345"
        assert "expected_tools" in loaded.metadata["expected_trajectory"]

        # Verify turn metadata is preserved
        assistant_turn = loaded.turns[1]
        assert assistant_turn.metadata["expected_content"] == "Inform user that PNR AB123 is invalid and explain 6-character rule."
        assert assistant_turn.metadata["expected_tools_call_order"] == ["check_booking_status"]
        assert assistant_turn.metadata["actual_tools_call_order"] == ["check_booking_status"]
        assert assistant_turn.metadata["actual_tools_called"][0]["name"] == "check_booking_status"
        assert assistant_turn.metadata["actual_tools_called"][0]["args"] == {"pnr": "AB123"}
        assert assistant_turn.metadata["actual_tools_called"][0]["expected_args"] == {"pnr": "AB123"}
        assert assistant_turn.metadata["actual_tools_called"][0]["response"] == {"error": "Invalid format"}
        assert assistant_turn.metadata["actual_tools_called"][0]["expected_response"] == {"error": "Invalid format"}
        assert assistant_turn.metadata["run_id"] == "mock_run_999"
        assert assistant_turn.metadata["metrics"]["ttft_ms"] == 350.0


def test_non_destructive_export_safeguard():
    with tempfile.TemporaryDirectory() as tmp_dir:
        datasets_dir = Path(tmp_dir)

        mock_tc = ConversationalTestCase(
            turns=[Turn(role="user", content="Hello"), Turn(role="assistant", content="Hi")],
            scenario="Test safeguard",
            expected_outcome="Success",
            name="TEST_SAFEGUARD_01",
            metadata={
                "golden_link": {
                    "rule_category": "test_cat",
                    "scenario_name": "test_scen",
                    "persona_slug": "test_persona",
                    "variation_id": "TEST_SAFEGUARD_01",
                }
            },
        )

        # First export creates base TEST_SAFEGUARD_01.json
        res1 = export_simulated_testcase(mock_tc, datasets_dir=datasets_dir, target_mode="dynamic", overwrite=False)
        path1 = Path(res1["json_path"])
        assert path1.name == "TEST_SAFEGUARD_01.json"
        assert path1.exists()

        # Second export without overwrite creates timestamped version to safeguard original
        res2 = export_simulated_testcase(mock_tc, datasets_dir=datasets_dir, target_mode="dynamic", overwrite=False)
        path2 = Path(res2["json_path"])
        assert path2.exists()
        assert path2.name != "TEST_SAFEGUARD_01.json"
        assert path2.name.startswith("TEST_SAFEGUARD_01_")
        assert path1.exists()  # Original file is preserved untouched
