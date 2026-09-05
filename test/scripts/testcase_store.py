import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_case_dirs(base_dir: str = "testdata") -> Dict[str, str]:
    root = os.path.abspath(base_dir)
    dirs = {
        "root": root,
        "simulate_single": os.path.join(root, "simulate_conversations", "single_turn"),
        "simulate_multi": os.path.join(root, "simulate_conversations", "multi_turn"),
        "api_single": os.path.join(root, "direct_api", "single_turn"),
        "api_multi": os.path.join(root, "direct_api", "multi_turn"),
    }
    for path in dirs.values():
        os.makedirs(path, exist_ok=True)
    return dirs


def build_testcase_record(
    *,
    case_id: Optional[str] = None,
    source: str,
    case_type: str,
    thread_id: Optional[str] = None,
    conversation: Optional[List[Dict[str, Any]]] = None,
    expected: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project: Optional[str] = None,
) -> Dict[str, Any]:
    if not case_id:
        case_id = f"{source}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    if not thread_id:
        thread_id = str(uuid.uuid4())

    record = {
        "case_id": case_id,
        "source": source,
        "type": case_type,
        "thread_id": thread_id,
        "project": project,
        "created_at": _now_iso(),
        "conversation": conversation or [],
        "expected": expected or {},
        "metadata": metadata or {},
    }
    return record


def save_testcase_record(record: Dict[str, Any], base_dir: str = "testdata") -> str:
    dirs = ensure_case_dirs(base_dir)
    case_type = record.get("type", "single_turn")
    source = record.get("source", "direct_api")

    if source == "simulator":
        folder = dirs["simulate_multi"] if case_type == "multi_turn" else dirs["simulate_single"]
    else:
        folder = dirs["api_multi"] if case_type == "multi_turn" else dirs["api_single"]

    path = os.path.join(folder, f"{record['case_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2, ensure_ascii=False)
    return os.path.abspath(path)


def save_simulator_case(
    *,
    case_id: Optional[str] = None,
    case_type: str,
    thread_id: Optional[str] = None,
    conversation: Optional[List[Dict[str, Any]]] = None,
    expected: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project: Optional[str] = None,
    base_dir: str = "testdata",
) -> Dict[str, Any]:
    record = build_testcase_record(
        case_id=case_id,
        source="simulator",
        case_type=case_type,
        thread_id=thread_id,
        conversation=conversation,
        expected=expected,
        metadata=metadata,
        project=project,
    )
    record["trace_file"] = ""  # will be set later when LangSmith trace is exported
    record["path"] = save_testcase_record(record, base_dir=base_dir)
    return record


def save_direct_api_case(
    *,
    case_id: Optional[str] = None,
    case_type: str,
    thread_id: Optional[str] = None,
    conversation: Optional[List[Dict[str, Any]]] = None,
    expected: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project: Optional[str] = None,
    base_dir: str = "testdata",
) -> Dict[str, Any]:
    record = build_testcase_record(
        case_id=case_id,
        source="direct_api",
        case_type=case_type,
        thread_id=thread_id,
        conversation=conversation,
        expected=expected,
        metadata=metadata,
        project=project,
    )
    record["trace_file"] = ""  # will be set later when LangSmith trace is exported
    record["path"] = save_testcase_record(record, base_dir=base_dir)
    return record
