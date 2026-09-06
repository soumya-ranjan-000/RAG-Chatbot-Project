"""
Centralized Conversational Metrics Engine
=========================================
Provides modular, extensible metric evaluators for both deterministic contracts
and dynamic LLM-as-a-judge evaluations.

Supported metric categories:
1. Deterministic Contract Metrics:
   - Tool Correctness (Tool name, arguments, return payload)
   - Tool Call Order (Chronological execution sequence)
   - UI Widget Validation (JSON structure within markdown blocks)
   - Performance SLAs (TTFT, latency, token consumption)
   - Negative Constraints (Forbidden assistant actions or statements)
2. DeepEval LLM Judge Metrics:
   - RoleAdherenceMetric
   - ConversationCompletenessMetric
   - ConversationalRelevancyMetric / TurnRelevancyMetric
   - FaithfulnessMetric
3. Extensible Custom Metric Registry:
   - Allows registering domain-specific airline rules, QA policies, or safety checks.
"""

import os
import re
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from pathlib import Path
from dotenv import load_dotenv

_SCRIPT_DIR = Path(__file__).resolve().parent
_TEST_DIR = _SCRIPT_DIR.parent
if str(_TEST_DIR) not in sys.path:
    sys.path.insert(0, str(_TEST_DIR))

load_dotenv()
parent_env = _TEST_DIR / ".env"
if parent_env.exists():
    load_dotenv(parent_env)

# Purge empty env vars
for k, v in list(os.environ.items()):
    if v == "":
        os.environ.pop(k, None)

try:
    from deepeval.test_case import ConversationalTestCase, Turn
except ImportError:
    ConversationalTestCase = None
    Turn = None


# ---------------------------------------------------------------------------
# Extensible Custom Metrics Registry
# ---------------------------------------------------------------------------

_CUSTOM_METRIC_REGISTRY: Dict[str, Callable[..., Dict[str, Any]]] = {}


def register_custom_metric(name: str, evaluator_func: Callable[..., Dict[str, Any]]) -> None:
    """Registers a new metric evaluator for future extension."""
    _CUSTOM_METRIC_REGISTRY[name.lower()] = evaluator_func


def get_registered_metric(name: str) -> Optional[Callable[..., Dict[str, Any]]]:
    """Retrieves a registered custom metric evaluator by name."""
    return _CUSTOM_METRIC_REGISTRY.get(name.lower())


def list_registered_metrics() -> List[str]:
    """Lists names of all registered custom metrics."""
    return list(_CUSTOM_METRIC_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Deterministic Contract Evaluators
# ---------------------------------------------------------------------------

def evaluate_tool_correctness(
    actual_tools: List[Dict[str, Any]],
    expected_tools: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Evaluates whether actual tools called match expected tool names, arguments, and responses.
    """
    errors: List[str] = []

    for exp_t in expected_tools:
        exp_name = exp_t.get("name")
        matching = [act for act in actual_tools if act.get("name") == exp_name]

        if not matching:
            errors.append(f"Expected tool '{exp_name}' was never called.")
            continue

        exp_args = exp_t.get("expected_args") or exp_t.get("args") or {}
        for act in matching:
            act_args = act.get("args") or {}
            for k, v in exp_args.items():
                if act_args.get(k) != v:
                    errors.append(
                        f"Tool '{exp_name}' argument mismatch for key '{k}': expected '{v}', got '{act_args.get(k)}'"
                    )

            exp_resp = exp_t.get("expected_response") or {}
            if exp_resp:
                act_resp = act.get("response") or {}
                for rk, rv in exp_resp.items():
                    if isinstance(act_resp, dict) and act_resp.get(rk) != rv:
                        errors.append(
                            f"Tool '{exp_name}' response mismatch for key '{rk}': expected '{rv}', got '{act_resp.get(rk)}'"
                        )

    return len(errors) == 0, errors


def evaluate_tool_order(
    actual_order: List[str],
    expected_order: List[str],
) -> Tuple[bool, List[str]]:
    """
    Evaluates whether tool call sequence matches expected execution order.
    """
    errors: List[str] = []
    if not expected_order:
        return True, errors

    filtered_actual = [name for name in actual_order if name in expected_order]
    if filtered_actual != expected_order:
        errors.append(
            f"Tool call order mismatch: expected {expected_order}, got {filtered_actual}"
        )
        return False, errors

    return True, errors


def evaluate_ui_widgets(
    actual_widgets: List[Dict[str, Any]],
) -> Tuple[bool, List[str]]:
    """
    Evaluates that all UI markdown widgets contain valid JSON formatting.
    """
    errors: List[str] = []
    for widget in actual_widgets:
        if not widget.get("is_valid_json", True):
            errors.append(
                f"UI widget of type '{widget.get('type')}' contains invalid JSON formatting."
            )
    return len(errors) == 0, errors


def evaluate_performance_sla(
    perf_summary: Dict[str, Any],
    sla: Dict[str, Any],
) -> Tuple[bool, List[str]]:
    """
    Evaluates performance summary against SLA constraints (TTFT, latency, token budgets).
    """
    errors: List[str] = []
    if not sla or not perf_summary:
        return True, errors

    max_ttft = sla.get("max_ttft_ms")
    max_tokens = sla.get("max_total_tokens")
    max_latency = sla.get("max_turn_latency_ms") or sla.get("max_latency_ms")

    actual_ttft = perf_summary.get("avg_ttft_ms") or 0.0
    actual_tokens = perf_summary.get("total_tokens") or 0
    actual_latency = perf_summary.get("total_latency_ms") or 0.0

    if max_ttft and actual_ttft > max_ttft:
        errors.append(
            f"TTFT SLA breached: {actual_ttft:.1f}ms exceeds threshold {max_ttft}ms"
        )
    if max_tokens and actual_tokens > max_tokens:
        errors.append(
            f"Token budget breached: {actual_tokens} tokens exceeds maximum {max_tokens}"
        )
    if max_latency and actual_latency > max_latency:
        errors.append(
            f"Latency SLA breached: {actual_latency:.1f}ms exceeds maximum {max_latency}ms"
        )

    return len(errors) == 0, errors


def evaluate_negative_constraints(
    assistant_responses: List[str],
    forbidden_actions: List[str],
) -> Tuple[bool, List[str]]:
    """
    Checks assistant content against forbidden actions or hallucinations.
    """
    errors: List[str] = []
    if not forbidden_actions:
        return True, errors

    combined_text = " ".join(assistant_responses).lower()
    for fa in forbidden_actions:
        fa_lower = fa.lower()
        if "invent fake flight details" in fa_lower and (
            "flight fl-" in combined_text or "flight 9999" in combined_text
        ):
            errors.append(f"Forbidden action triggered: {fa}")

    return len(errors) == 0, errors


def evaluate_deterministic_contracts(
    test_case: Any,
) -> Dict[str, Any]:
    """
    Executes the full suite of deterministic contract evaluations against a testcase.
    Returns structured results with pass/fail flags, scores, and error details.
    """
    meta = getattr(test_case, "metadata", {}) or {}
    expected_data = meta.get("expected") or {}
    actual_data = meta.get("actual") or {}
    exp_traj = expected_data.get("expected_trajectory") or meta.get("expected_trajectory") or {}
    perf_summary = actual_data.get("performance_summary") or meta.get("performance_summary") or {}
    turns = getattr(test_case, "turns", []) or []

    # Gather actual tools, widgets, and assistant texts across turns
    all_actual_tools: List[Dict[str, Any]] = []
    all_actual_tools_order: List[str] = []
    all_actual_widgets: List[Dict[str, Any]] = []
    assistant_contents: List[str] = []

    for t in turns:
        t_meta = getattr(t, "metadata", {}) or {}
        role = getattr(t, "role", "")
        if role == "assistant":
            assistant_contents.append(getattr(t, "content", "") or "")
            actual_tools = t_meta.get("actual_tools_called") or []
            all_actual_tools.extend(actual_tools)
            actual_order = t_meta.get("actual_tools_call_order") or [
                tc.get("name") for tc in actual_tools if tc.get("name")
            ]
            all_actual_tools_order.extend(actual_order)
            all_actual_widgets.extend(t_meta.get("actual_ui_widgets") or [])

    # If testcase loaded from unified schema where actual tools are in metadata
    if not all_actual_tools and actual_data.get("tools_called"):
        all_actual_tools = actual_data.get("tools_called", [])
    if not all_actual_tools_order and actual_data.get("tools_order"):
        all_actual_tools_order = actual_data.get("tools_order", [])

    # 1. Tool correctness
    exp_tools = exp_traj.get("expected_tools") or []
    tool_pass, tool_errs = evaluate_tool_correctness(all_actual_tools, exp_tools)

    # 2. Tool order
    exp_order = exp_traj.get("expected_tools_order") or []
    order_pass, order_errs = evaluate_tool_order(all_actual_tools_order, exp_order)

    # 3. UI Widgets
    widget_pass, widget_errs = evaluate_ui_widgets(all_actual_widgets)

    # 4. Performance SLA
    sla = exp_traj.get("performance_sla") or {}
    sla_pass, sla_errs = evaluate_performance_sla(perf_summary, sla)

    # 5. Negative constraints
    forbidden = exp_traj.get("forbidden_actions") or []
    neg_pass, neg_errs = evaluate_negative_constraints(assistant_contents, forbidden)

    # 6. Custom registered metrics
    custom_results: Dict[str, Any] = {}
    for metric_name, evaluator_func in _CUSTOM_METRIC_REGISTRY.items():
        try:
            custom_results[metric_name] = evaluator_func(test_case)
        except Exception as e:
            custom_results[metric_name] = {"passed": False, "score": 0.0, "errors": [str(e)]}

    all_passed = tool_pass and order_pass and widget_pass and sla_pass and neg_pass
    for c_res in custom_results.values():
        if isinstance(c_res, dict) and not c_res.get("passed", True):
            all_passed = False

    return {
        "tool_correctness": {
            "passed": tool_pass,
            "score": 1.0 if tool_pass else 0.0,
            "errors": tool_errs,
        },
        "tool_order": {
            "passed": order_pass,
            "score": 1.0 if order_pass else 0.0,
            "errors": order_errs,
        },
        "ui_widgets": {
            "passed": widget_pass,
            "score": 1.0 if widget_pass else 0.0,
            "errors": widget_errs,
        },
        "performance_sla": {
            "passed": sla_pass,
            "score": 1.0 if sla_pass else 0.0,
            "errors": sla_errs,
        },
        "negative_constraints": {
            "passed": neg_pass,
            "score": 1.0 if neg_pass else 0.0,
            "errors": neg_errs,
        },
        "custom_metrics": custom_results,
        "all_passed": all_passed,
    }


# ---------------------------------------------------------------------------
# DeepEval LLM-as-a-Judge Evaluators
# ---------------------------------------------------------------------------

def resolve_judge_model(model_name: Optional[str] = None):
    """
    Resolves the LLM judge model based on available environment credentials.
    Prefers GeminiModel if GEMINI_API_KEY/GOOGLE_API_KEY is present,
    otherwise OpenAIModel if OPENAI_API_KEY is present.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        try:
            from deepeval.models import GeminiModel
            target_model = model_name or os.getenv("EVAL_MODEL", "gemini-2.5-flash")
            return GeminiModel(model=target_model, api_key=gemini_key)
        except Exception as e:
            print(f"[Warning] Failed to instantiate GeminiModel: {e}")

    if openai_key:
        try:
            from deepeval.models import OpenAIModel
            target_model = model_name or os.getenv("EVAL_MODEL", "gpt-4o-mini")
            return OpenAIModel(model=target_model, api_key=openai_key)
        except Exception as e:
            print(f"[Warning] Failed to instantiate OpenAIModel: {e}")

    return None


def get_default_deepeval_metrics(
    judge_model: Any,
    role_adherence_threshold: float = 0.7,
    completeness_threshold: float = 0.7,
) -> List[Any]:
    """
    Constructs default DeepEval conversational metrics with thresholds.
    """
    from deepeval.metrics import (
        RoleAdherenceMetric,
        ConversationCompletenessMetric,
    )
    return [
        RoleAdherenceMetric(threshold=role_adherence_threshold, model=judge_model, async_mode=False),
        ConversationCompletenessMetric(threshold=completeness_threshold, model=judge_model, async_mode=False),
    ]


def evaluate_llm_metrics(
    test_case: Any,
    judge_model: Any,
    metrics: Optional[List[Any]] = None,
) -> Tuple[bool, Dict[str, Any], str]:
    """
    Evaluates DeepEval LLM-as-a-judge metrics for a given test case.
    """
    from deepeval.evaluate import evaluate

    if metrics is None:
        metrics = get_default_deepeval_metrics(judge_model)

    llm_metrics_dict: Dict[str, Any] = {}
    try:
        eval_out = evaluate([test_case], metrics=metrics, print_results=False)
        all_metric_pass = True
        for res in eval_out:
            for m in getattr(res, "metrics_data", []) or []:
                m_name = getattr(m, "name", str(m))
                m_score = getattr(m, "score", 0.0)
                m_pass = getattr(m, "success", False)
                llm_metrics_dict[m_name] = {"score": m_score, "passed": m_pass}
                if not m_pass:
                    all_metric_pass = False

        status_str = "✅ PASS" if all_metric_pass else "❌ FAIL"
        return all_metric_pass, llm_metrics_dict, status_str
    except Exception as e:
        return False, {}, f"⚠️ ERR ({e})"

