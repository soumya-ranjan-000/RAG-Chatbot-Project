from typing import Any, Dict, List, Optional

from scripts.testcase_store import save_direct_api_case


def create_direct_api_case(
    *,
    user_message: str,
    expected: Dict[str, Any],
    thread_id: Optional[str] = None,
    case_id: Optional[str] = None,
    case_type: str = "single_turn",
    metadata: Optional[Dict[str, Any]] = None,
    project: str = "airline-booking-chatbot",
    base_dir: str = "testdata",
) -> Dict[str, Any]:
    conversation = [{"role": "user", "content": user_message}]
    case = save_direct_api_case(
        case_id=case_id,
        case_type=case_type,
        thread_id=thread_id,
        conversation=conversation,
        expected=expected,
        metadata=metadata or {},
        project=project,
        base_dir=base_dir,
    )
    return case


def create_direct_api_multiturn_case(
    *,
    conversation: List[Dict[str, Any]],
    expected: Dict[str, Any],
    thread_id: Optional[str] = None,
    case_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    project: str = "airline-booking-chatbot",
    base_dir: str = "testdata",
) -> Dict[str, Any]:
    case = save_direct_api_case(
        case_id=case_id,
        case_type="multi_turn",
        thread_id=thread_id,
        conversation=conversation,
        expected=expected,
        metadata=metadata or {},
        project=project,
        base_dir=base_dir,
    )
    return case
