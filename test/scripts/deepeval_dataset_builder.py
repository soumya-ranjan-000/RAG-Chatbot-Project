import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from deepeval.test_case import ConversationalTestCase, Turn


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _iter_testcase_files(testdata_root: str = "testdata") -> List[Path]:
    root = _project_root() / testdata_root
    if not root.exists():
        return []

    files: List[Path] = []
    for folder in [root / "simulate_conversations", root / "direct_api"]:
        if folder.exists():
            files.extend(sorted(folder.rglob("*.json")))
    return files


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _find_trace_file(thread_id: Optional[str], exports_root: str = "exports/langsmith_traces") -> Optional[Path]:
    if not thread_id:
        return None
    trace_root = _project_root() / exports_root
    if not trace_root.exists():
        return None

    matches = sorted(trace_root.rglob(f"{thread_id}.json"))
    if matches:
        return matches[0]
    return None


def _extract_expected_outcome(case_record: Dict[str, Any]) -> Optional[str]:
    expected = case_record.get("expected") or {}
    return (
        expected.get("expected_outcome")
        or expected.get("final_answer")
        or expected.get("ground_truth")
        or expected.get("expected")
    )


def _extract_final_llm_response(trace_record: Optional[Dict[str, Any]]) -> Optional[str]:
    if not trace_record:
        return None

    turns = trace_record.get("turns") or []
    if not turns:
        return None

    final_turn = turns[-1]
    if isinstance(final_turn, dict):
        llm_response = final_turn.get("llm_response")
        if llm_response:
            return str(llm_response)
    return None


def _build_turns(conversation: Iterable[Dict[str, Any]], trace_record: Optional[Dict[str, Any]]) -> List[Turn]:
    turns: List[Turn] = []
    for idx, msg in enumerate(conversation or []):
        role = str(msg.get("role", "user")).strip().lower()
        content = str(msg.get("content") or "")
        if role not in {"user", "assistant"}:
            role = "user"

        turn_metadata: Dict[str, Any] = {
            "turn_index": idx,
        }
        if trace_record:
            trace_turns = trace_record.get("turns") or []
            if idx < len(trace_turns):
                trace_turn = trace_turns[idx]
                if isinstance(trace_turn, dict):
                    turn_metadata["trace_turn"] = {
                        "run_id": trace_turn.get("run_id"),
                        "latency_ms": trace_turn.get("latency_ms"),
                        "ttft_ms": trace_turn.get("ttft_ms"),
                        "status": trace_turn.get("status"),
                    }

        turns.append(
            Turn(
                role=role,
                content=content,
                metadata=turn_metadata,
            )
        )
    return turns


def build_deepeval_dataset(
    testdata_root: str = "testdata",
    exports_root: str = "exports/langsmith_traces",
) -> List[ConversationalTestCase]:
    dataset: List[ConversationalTestCase] = []

    for testcase_file in _iter_testcase_files(testdata_root):
        case_record = _load_json(testcase_file)
        if not case_record:
            continue

        thread_id = case_record.get("thread_id")
        trace_file = _find_trace_file(thread_id, exports_root)
        trace_record = _load_json(trace_file) if trace_file else None

        conversation = case_record.get("conversation") or []
        expected = case_record.get("expected") or {}
        metadata = dict(case_record.get("metadata") or {})
        metadata.update({
            "case_id": case_record.get("case_id"),
            "source": case_record.get("source"),
            "type": case_record.get("type"),
            "thread_id": thread_id,
            "trace_file": str(trace_file) if trace_file else None,
        })

        turns = _build_turns(conversation, trace_record)

        scenario = (
            expected.get("scenario")
            or metadata.get("scenario")
            or "Conversation evaluation"
        )

        context = []
        if isinstance(expected.get("retrieved_context"), list):
            context.extend(str(item) for item in expected["retrieved_context"])

        expected_outcome = _extract_expected_outcome(case_record)
        if isinstance(expected_outcome, dict):
            expected_outcome = json.dumps(expected_outcome, ensure_ascii=False)

        if not expected_outcome:
            expected_outcome = _extract_final_llm_response(trace_record) or "No expected outcome provided."

        dataset.append(
            ConversationalTestCase(
                turns=turns,
                scenario=scenario,
                context=context or None,
                expected_outcome=str(expected_outcome),
                metadata=metadata,
            )
        )

    return dataset


def export_deepeval_dataset(
    output_path: str = "testdata/deepeval_dataset.json",
    testdata_root: str = "testdata",
    exports_root: str = "exports/langsmith_traces",
) -> str:
    dataset = build_deepeval_dataset(testdata_root=testdata_root, exports_root=exports_root)
    output_file = _project_root() / output_path
    output_file.parent.mkdir(parents=True, exist_ok=True)

    serialized = []
    for idx, case in enumerate(dataset, start=1):
        serialized.append({
            "index": idx,
            "scenario": case.scenario,
            "expected_outcome": case.expected_outcome,
            "metadata": case.metadata,
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "metadata": turn.metadata,
                }
                for turn in case.turns
            ],
        })

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2, ensure_ascii=False)

    return str(output_file)


if __name__ == "__main__":
    dataset = build_deepeval_dataset()
    print(f"Built {len(dataset)} DeepEval conversational cases.")
    for case in dataset:
        print(case.metadata.get("case_id"), case.metadata.get("thread_id"), case.expected_outcome)

    export_path = export_deepeval_dataset()
    print(f"Dataset export saved to: {export_path}")
