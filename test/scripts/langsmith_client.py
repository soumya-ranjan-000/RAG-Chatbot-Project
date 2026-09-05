"""
LangSmith Trace Extractor & Observability Client
=================================================
Extracts complete trace information, agent trajectories, spans, and metrics
from LangSmith for a given thread_id.
"""

import os
import sys
import json
import logging
import warnings
from datetime import datetime, timezone
from uuid import UUID
from typing import Any, Dict, List, Optional, Tuple, Union
from dotenv import load_dotenv

# Suppress deprecation warnings from LangSmith internal client if any
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 1. Load environment variables (.env in test/ or parent project root)
load_dotenv()
parent_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(parent_env):
    load_dotenv(parent_env)

from decimal import Decimal
from langsmith import Client
from langsmith.schemas import Run

logger = logging.getLogger("langsmith-client")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely converts any value (including Decimal, string, float) to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_int(val: Any, default: int = 0) -> int:
    """Safely converts any value to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_default_project_name() -> Optional[str]:
    """Returns the default project name from environment or fallback candidate list."""
    return os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT") or None


def get_langsmith_client(api_key: Optional[str] = None, endpoint: Optional[str] = None) -> Client:
    """
    Initializes and returns a LangSmith Client instance.
    """
    key = api_key or os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    api_url = endpoint or os.getenv("LANGCHAIN_ENDPOINT") or os.getenv("LANGSMITH_ENDPOINT")

    client_kwargs = {}
    if key:
        client_kwargs["api_key"] = key
    if api_url:
        client_kwargs["api_url"] = api_url

    try:
        return Client(**client_kwargs)
    except Exception as e:
        logger.warning(f"Failed to initialize LangSmith Client: {e}")
        return Client()


# Global default client instance
client = get_langsmith_client()


def _json_serializable(obj: Any) -> Any:
    """Recursively converts objects (datetime, UUID, Decimal, pydantic, etc.) to JSON-serializable types."""
    if obj is None:
        return None
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {str(k): _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_json_serializable(item) for item in obj]
    if hasattr(obj, "model_dump"):
        return _json_serializable(obj.model_dump())
    if hasattr(obj, "dict"):
        return _json_serializable(obj.dict())
    if hasattr(obj, "__dict__"):
        return _json_serializable(obj.__dict__)
    return str(obj) if not isinstance(obj, (int, float, bool, str)) else obj


def _calculate_latency_ms(start_time: Any, end_time: Any) -> Optional[float]:
    """Calculates latency in milliseconds from start and end time objects or ISO strings."""
    if not start_time or not end_time:
        return None
    try:
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        return round((end_time - start_time).total_seconds() * 1000, 2)
    except Exception:
        return None


def _extract_ttft_ms(raw: Dict[str, Any]) -> Optional[float]:
    """Attempts to recover TTFT from LangSmith payloads using first_token_time or event timestamps."""
    def _to_utc(dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    candidates: List[datetime] = []

    first_token_time = raw.get("first_token_time")
    if first_token_time:
        try:
            if isinstance(first_token_time, str):
                candidates.append(_to_utc(datetime.fromisoformat(first_token_time.replace("Z", "+00:00"))))
            else:
                candidates.append(_to_utc(first_token_time))
        except Exception:
            pass

    for event in raw.get("events") or []:
        if not isinstance(event, dict):
            continue
        ts = event.get("timestamp") or event.get("time") or event.get("created_at")
        if not ts:
            continue
        try:
            if isinstance(ts, str):
                candidates.append(_to_utc(datetime.fromisoformat(ts.replace("Z", "+00:00"))))
            else:
                candidates.append(_to_utc(ts))
        except Exception:
            continue

    start_time = raw.get("start_time")
    if start_time:
        try:
            if isinstance(start_time, str):
                start_time_dt = _to_utc(datetime.fromisoformat(start_time.replace("Z", "+00:00")))
            else:
                start_time_dt = _to_utc(start_time)
        except Exception:
            start_time_dt = None
    else:
        start_time_dt = None

    if not candidates or start_time_dt is None:
        return None

    first_event_time = min(candidates)
    return round((first_event_time - start_time_dt).total_seconds() * 1000, 2)


def serialize_run(run: Union[Run, Dict[str, Any]], load_children: bool = True) -> Dict[str, Any]:
    """
    Transforms a LangSmith Run schema or dictionary into a comprehensive,
    JSON-serializable trace object containing complete metadata, inputs,
    outputs, latency, token usage, tool calls, and nested child spans.
    """
    if isinstance(run, dict):
        raw = run
    elif hasattr(run, "model_dump"):
        raw = run.model_dump()
    elif hasattr(run, "dict"):
        raw = run.dict()
    else:
        raw = getattr(run, "__dict__", {})

    run_id = str(raw.get("id", ""))
    trace_id = str(raw.get("trace_id", run_id))
    parent_run_id = str(raw.get("parent_run_id")) if raw.get("parent_run_id") else None
    name = raw.get("name", "")
    run_type = raw.get("run_type", "")
    status = raw.get("status", "success" if not raw.get("error") else "error")
    error = raw.get("error")

    start_time = raw.get("start_time")
    end_time = raw.get("end_time")
    latency_ms = _calculate_latency_ms(start_time, end_time)
    ttft_ms = _extract_ttft_ms(raw)

    inputs = raw.get("inputs") or {}
    outputs = raw.get("outputs") or {}
    extra = raw.get("extra") or {}
    metadata = extra.get("metadata") or {}
    tags = raw.get("tags") or []
    events = raw.get("events") or []

    # Token usage & Cost (safely cast to int and float)
    prompt_tokens = _safe_int(raw.get("prompt_tokens"))
    completion_tokens = _safe_int(raw.get("completion_tokens"))
    total_tokens = _safe_int(raw.get("total_tokens")) or (prompt_tokens + completion_tokens)
    total_cost = _safe_float(raw.get("total_cost"))
    prompt_cost = _safe_float(raw.get("prompt_cost"))
    completion_cost = _safe_float(raw.get("completion_cost"))

    # Extract parsed reasoning, plans, tool calls, and retrieval contexts
    extracted_info = _extract_span_highlights(run_type, name, inputs, outputs, extra, metadata)

    # Process child runs recursively
    child_runs_processed = []
    raw_children = raw.get("child_runs") or []
    if load_children and raw_children:
        for child in raw_children:
            child_runs_processed.append(serialize_run(child, load_children=True))

    trace_data = {
        "run_id": run_id,
        "trace_id": trace_id,
        "parent_run_id": parent_run_id,
        "name": name,
        "run_type": run_type,
        "status": status,
        "error": error,
        "start_time": _json_serializable(start_time),
        "end_time": _json_serializable(end_time),
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "tokens": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "total_cost": total_cost,
        },
        "tags": tags,
        "metadata": _json_serializable(metadata),
        "extra": _json_serializable(extra),
        "inputs": _json_serializable(inputs),
        "outputs": _json_serializable(outputs),
        "events": _json_serializable(events),
        "extracted": extracted_info,
        "child_runs_count": len(child_runs_processed),
        "child_runs": child_runs_processed,
    }

    return trace_data


def _flatten_output_text(value: Any) -> Optional[str]:
    """Convert LangSmith output payloads into a plain-text LLM response while preserving token spacing."""
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            text = _flatten_output_text(item)
            if text:
                parts.append(text)
        return "".join(parts) if parts else None
    if isinstance(value, dict):
        if "content" in value and isinstance(value["content"], str):
            return value["content"]
        if "text" in value and isinstance(value["text"], str):
            return value["text"]
        for key in ["output", "message", "answer", "response"]:
            if key in value:
                text = _flatten_output_text(value[key])
                if text:
                    return text
        if "messages" in value and isinstance(value["messages"], list):
            for msg in value["messages"]:
                if isinstance(msg, dict):
                    content = msg.get("content")
                    if isinstance(content, str) and content.strip():
                        return content.strip()
                    if isinstance(content, list):
                        text = _flatten_output_text(content)
                        if text:
                            return text
        if "generations" in value and isinstance(value["generations"], list):
            texts: List[str] = []
            for generation in value["generations"]:
                text = _flatten_output_text(generation)
                if text:
                    texts.append(text)
            if texts:
                return "\n".join(texts)
        if "tool_calls" in value:
            tool_calls = value["tool_calls"]
            if isinstance(tool_calls, list) and tool_calls:
                return json.dumps(_json_serializable(tool_calls), ensure_ascii=False)
        return None
    if isinstance(value, tuple):
        return _flatten_output_text(list(value))
    if hasattr(value, "content"):
        return _flatten_output_text(getattr(value, "content"))
    return None


def _extract_span_highlights(
    run_type: str,
    name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    extra: Dict[str, Any],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    """Helper to extract structured highlights (tool calls, reasoning, RAG context) from run payloads."""
    highlights: Dict[str, Any] = {
        "thoughts": [],
        "plans": [],
        "tool_calls": [],
        "tool_results": [],
        "retrieval_context": [],
        "messages": [],
        "response_text": None,
    }

    response_text = _flatten_output_text(outputs)
    if response_text:
        highlights["response_text"] = response_text

    # 1. Extract thought / plan from outputs or metadata
    if isinstance(outputs, dict):
        for key in ["thought", "thoughts", "reasoning", "reasoning_content", "agent_thought"]:
            if key in outputs and outputs[key]:
                highlights["thoughts"].append(outputs[key])
        for key in ["plan", "plans", "agent_plan", "steps"]:
            if key in outputs and outputs[key]:
                highlights["plans"].append(outputs[key])

    # 2. Tool calls and Tool results
    if run_type == "tool" or "tool" in name.lower():
        highlights["tool_calls"].append({
            "tool_name": name,
            "inputs": inputs,
            "output": outputs,
        })

    # Tool calls inside LLM outputs (LangChain / OpenAI function calls)
    if isinstance(outputs, dict) and "generations" in outputs:
        for gen_list in outputs.get("generations", []):
            items = gen_list if isinstance(gen_list, list) else [gen_list]
            for item in items:
                msg = item.get("message", {}) if isinstance(item, dict) else getattr(item, "message", None)
                if msg:
                    msg_kwargs = msg.get("additional_kwargs", {}) if isinstance(msg, dict) else getattr(msg, "additional_kwargs", {})
                    tool_calls = msg_kwargs.get("tool_calls") or (msg.get("tool_calls") if isinstance(msg, dict) else getattr(msg, "tool_calls", []))
                    if tool_calls:
                        for tc in tool_calls:
                            highlights["tool_calls"].append(_json_serializable(tc))

    # 3. Retrieval context (RAG vector searches, documents)
    if run_type == "retriever" or "retrieval" in name.lower() or "search" in name.lower():
        docs = outputs.get("documents") or outputs.get("chunks") or outputs.get("output") or outputs.get("results") if isinstance(outputs, dict) else None
        if docs:
            if isinstance(docs, list):
                for doc in docs:
                    if isinstance(doc, dict):
                        highlights["retrieval_context"].append(doc)
                    elif hasattr(doc, "page_content"):
                        highlights["retrieval_context"].append({
                            "content": doc.page_content,
                            "metadata": getattr(doc, "metadata", {})
                        })
                    else:
                        highlights["retrieval_context"].append(str(doc))
            elif isinstance(docs, str):
                highlights["retrieval_context"].append({"content": docs})

    # 4. Extract Chat Messages from inputs
    if isinstance(inputs, dict):
        if "messages" in inputs:
            highlights["messages"] = _json_serializable(inputs["messages"])
        elif "history" in inputs:
            highlights["messages"] = _json_serializable(inputs["history"])
        if "query" in inputs and isinstance(inputs["query"], str):
            highlights["query"] = inputs["query"]
        elif "question" in inputs and isinstance(inputs["question"], str):
            highlights["query"] = inputs["question"]
        elif "input" in inputs and isinstance(inputs["input"], str):
            highlights["query"] = inputs["input"]

    return highlights


def _discover_candidate_projects(target_client: Client, user_project: Optional[str] = None) -> List[Optional[str]]:
    """
    Builds an ordered list of project candidates to search.

    We intentionally avoid listing projects through the legacy LangSmith API. Instead,
    we prefer explicitly configured and known project names and fall back to a global
    project-agnostic search.
    """
    candidates: List[Optional[str]] = []

    if user_project:
        candidates.append(user_project)

    env_proj = get_default_project_name()
    if env_proj and env_proj not in candidates:
        candidates.append(env_proj)

    known_projects = ["airline-booking-chatbot", "airline-chatbot", "rag-chatbot-eval"]
    for p in known_projects:
        if p not in candidates:
            candidates.append(p)

    if None not in candidates:
        candidates.append(None)

    return candidates


def get_traces_by_thread_id(
    thread_id: str,
    project_name: Optional[str] = None,
    ls_client: Optional[Client] = None,
    load_child_runs: bool = True,
) -> List[Dict[str, Any]]:
    """
    Fetches and extracts all traces associated with a specific thread_id from LangSmith.
    Automatically searches across candidate projects and uses native thread APIs.

    Parameters:
    -----------
    thread_id : str
        The unique thread ID or conversation ID.
    project_name : Optional[str]
        The LangSmith project name (auto-discovered if not specified or not found).
    ls_client : Optional[Client]
        Custom LangSmith Client instance (defaults to global client).
    load_child_runs : bool
        Whether to recursively fetch the full run tree of child spans.

    Returns:
    --------
    List[Dict[str, Any]]
        List of complete, fully populated trace dictionaries sorted chronologically.
    """
    target_client = ls_client or client
    candidate_projects = _discover_candidate_projects(target_client, user_project=project_name)

    runs_to_process: List[Run] = []
    seen_run_ids = set()
    resolved_project = None

    # Step 1: Query runs by thread_id with the supported list_runs API and project filters.
    for proj in candidate_projects:
        try:
            kwargs: Dict[str, Any] = {
                "filter": f'eq(thread_id, "{thread_id}")',
                "is_root": False,
                "order": "asc",
            }
            if proj:
                kwargs["project_name"] = proj
            thread_runs = list(target_client.list_runs(**kwargs))
            if thread_runs:
                for r in thread_runs:
                    r_id = str(r.id)
                    if r_id not in seen_run_ids:
                        seen_run_ids.add(r_id)
                        runs_to_process.append(r)
                resolved_project = proj
                logger.info(f"Found {len(thread_runs)} run(s) using list_runs(thread_id filter) in project='{proj or 'Global'}'.")
                break
        except Exception as e:
            logger.debug(f"list_runs(thread_id filter) failed for project='{proj}': {e}")

    # Step 2: Try filter queries if read_thread didn't return runs
    if not runs_to_process:
        filter_queries = [
            f'eq(metadata.thread_id, "{thread_id}")',
            f'eq(metadata.configurable.thread_id, "{thread_id}")',
            f'eq(metadata.session_id, "{thread_id}")',
            f'eq(metadata.conversation_id, "{thread_id}")',
            f'eq(session_name, "{thread_id}")',
        ]

        for proj in candidate_projects:
            for filter_expr in filter_queries:
                try:
                    query_kwargs: Dict[str, Any] = {"filter": filter_expr}
                    if proj:
                        query_kwargs["project_name"] = proj

                    found_runs = list(target_client.list_runs(**query_kwargs))
                    if found_runs:
                        for r in found_runs:
                            r_id = str(r.id)
                            if r_id not in seen_run_ids:
                                seen_run_ids.add(r_id)
                                runs_to_process.append(r)
                        if not resolved_project:
                            resolved_project = proj
                except Exception as e:
                    logger.debug(f"Filter query '{filter_expr}' on '{proj}' error: {e}")
            if runs_to_process:
                break

    # Step 3: Check if thread_id is actually a trace_id or run_id
    if not runs_to_process:
        try:
            trace_runs = list(target_client.list_runs(trace_id=thread_id))
            if trace_runs:
                for r in trace_runs:
                    r_id = str(r.id)
                    if r_id not in seen_run_ids:
                        seen_run_ids.add(r_id)
                        runs_to_process.append(r)
                logger.info(f"Found {len(trace_runs)} runs treating thread_id as trace_id.")
        except Exception:
            pass

    if not runs_to_process:
        try:
            single_run = target_client.read_run(thread_id, load_child_runs=load_child_runs)
            if single_run:
                runs_to_process.append(single_run)
                logger.info(f"Found root run matching ID directly.")
        except Exception:
            pass

    logger.info(f"Resolved {len(runs_to_process)} total run(s) for thread_id='{thread_id}' (Project: '{resolved_project}').")

    # Step 4: Group runs into root traces
    root_runs: List[Run] = []
    child_spans: List[Run] = []

    for r in runs_to_process:
        if r.parent_run_id is None:
            root_runs.append(r)
        else:
            child_spans.append(r)

    # If only child spans found, load their root traces
    if not root_runs and child_spans:
        trace_ids = {str(r.trace_id) for r in child_spans if r.trace_id}
        for t_id in trace_ids:
            try:
                root = target_client.read_run(t_id, load_child_runs=load_child_runs)
                root_runs.append(root)
            except Exception as e:
                logger.debug(f"Could not load root run for trace_id {t_id}: {e}")

    # Step 5: Build detailed trace structures with child hierarchies
    detailed_traces: List[Dict[str, Any]] = []

    if root_runs:
        for root in root_runs:
            if load_child_runs:
                try:
                    full_root = target_client.read_run(root.id, load_child_runs=True)
                    detailed_traces.append(serialize_run(full_root, load_children=True))
                except Exception:
                    detailed_traces.append(serialize_run(root, load_children=True))
            else:
                detailed_traces.append(serialize_run(root, load_children=False))
    else:
        for r in runs_to_process:
            detailed_traces.append(serialize_run(r, load_children=False))

    # Sort traces chronologically
    def _sort_key(t: Dict[str, Any]) -> str:
        return t.get("start_time") or ""

    detailed_traces.sort(key=_sort_key)
    return detailed_traces


def get_agent_trajectory(
    thread_id: str,
    project_name: Optional[str] = None,
    ls_client: Optional[Client] = None,
) -> Tuple[List[Any], List[str]]:
    """
    Extracts reasoning thoughts, plans, and actions from LangSmith spans.
    Maintains full backward compatibility returning (plans, actions_taken).

    Parameters:
    -----------
    thread_id : str
        The thread_id to look up.
    project_name : Optional[str]
        LangSmith project name.
    ls_client : Optional[Client]
        Custom client instance.

    Returns:
    --------
    Tuple[List[Any], List[str]]
        (plans, actions_taken)
    """
    traces = get_traces_by_thread_id(
        thread_id=thread_id,
        project_name=project_name,
        ls_client=ls_client,
        load_child_runs=True,
    )

    plans: List[Any] = []
    actions_taken: List[str] = []

    def _collect_spans_recursive(node: Dict[str, Any]):
        run_type = node.get("run_type")
        name = node.get("name", "")
        inputs = node.get("inputs") or {}
        outputs = node.get("outputs") or {}
        extracted = node.get("extracted") or {}

        # Plans and thoughts
        if extracted.get("plans"):
            plans.extend(extracted["plans"])
        if extracted.get("thoughts"):
            plans.extend(extracted["thoughts"])

        if run_type == "llm":
            if isinstance(outputs, dict):
                if "plan" in outputs:
                    plans.append(outputs.get("plan"))
                elif "thought" in outputs:
                    plans.append(outputs.get("thought"))
                elif "reasoning" in outputs:
                    plans.append(outputs.get("reasoning"))

        # Actions and tool calls
        if run_type == "tool" or "tool" in name.lower():
            actions_taken.append(f"Tool: {name}, Input: {inputs}")

        if extracted.get("tool_calls"):
            for tc in extracted["tool_calls"]:
                if isinstance(tc, dict) and "function" in tc:
                    func = tc.get("function", {})
                    actions_taken.append(f"Tool: {func.get('name')}, Input: {func.get('arguments')}")
                elif isinstance(tc, dict) and "name" in tc:
                    actions_taken.append(f"Tool: {tc.get('name')}, Input: {tc.get('args') or tc.get('inputs')}")

        for child in node.get("child_runs", []):
            _collect_spans_recursive(child)

    for trace in traces:
        _collect_spans_recursive(trace)

    return plans, actions_taken


def get_thread_summary(
    thread_id: str,
    project_name: Optional[str] = None,
    ls_client: Optional[Client] = None,
) -> Dict[str, Any]:
    """
    Generates a high-level summary of the entire thread including total turns,
    latency, token counts, tools called, and conversation turns.
    """
    traces = get_traces_by_thread_id(
        thread_id=thread_id,
        project_name=project_name,
        ls_client=ls_client,
        load_child_runs=True,
    )

    total_prompt_tokens = 0
    total_completion_tokens = 0
    total_tokens = 0
    total_cost = 0.0
    total_latency_ms = 0.0
    tools_used = []
    conversation_turns = []

    def _aggregate(node: Dict[str, Any]):
        nonlocal total_prompt_tokens, total_completion_tokens, total_tokens, total_cost, total_latency_ms
        tok = node.get("tokens", {})
        total_prompt_tokens += tok.get("prompt_tokens", 0)
        total_completion_tokens += tok.get("completion_tokens", 0)
        total_tokens += tok.get("total_tokens", 0)
        total_cost += _safe_float(tok.get("total_cost", 0.0))

        lat = node.get("latency_ms")
        if lat and node.get("parent_run_id") is None:
            total_latency_ms += lat

        if node.get("run_type") == "tool":
            tools_used.append({
                "tool": node.get("name"),
                "latency_ms": node.get("latency_ms"),
                "status": node.get("status"),
            })

        for child in node.get("child_runs", []):
            _aggregate(child)

    for trace in traces:
        _aggregate(trace)
        extracted = trace.get("extracted", {})
        conversation_turns.append({
            "run_id": trace.get("run_id"),
            "name": trace.get("name"),
            "start_time": trace.get("start_time"),
            "user_query": extracted.get("query"),
            "assistant_response": extracted.get("response_text"),
            "latency_ms": trace.get("latency_ms"),
            "status": trace.get("status"),
        })

    return {
        "thread_id": thread_id,
        "project_name": project_name or get_default_project_name() or "Auto-Resolved",
        "total_traces": len(traces),
        "total_latency_ms": round(total_latency_ms, 2),
        "tokens": {
            "prompt_tokens": total_prompt_tokens,
            "completion_tokens": total_completion_tokens,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
        },
        "tools_called_count": len(tools_used),
        "tools_used": tools_used,
        "turns": conversation_turns,
        "traces": traces,
    }


def build_compact_turn_export(
    thread_id: str,
    project_name: Optional[str] = None,
    ls_client: Optional[Client] = None,
) -> Dict[str, Any]:
    """Build a turn-by-turn export containing only the fields needed for analysis."""
    traces = get_traces_by_thread_id(
        thread_id=thread_id,
        project_name=project_name,
        ls_client=ls_client,
        load_child_runs=True,
    )

    turns: List[Dict[str, Any]] = []
    for idx, trace in enumerate(traces, start=1):
        extracted = trace.get("extracted") or {}
        inputs = trace.get("inputs") or {}
        outputs = trace.get("outputs") or {}
        tokens = trace.get("tokens") or {}
        tool_calls = extracted.get("tool_calls") or []
        reasoning = []
        if extracted.get("thoughts"):
            reasoning.extend(extracted.get("thoughts", []))
        if extracted.get("plans"):
            reasoning.extend(extracted.get("plans", []))

        for child in trace.get("child_runs", []):
            child_extracted = child.get("extracted") or {}
            if child_extracted.get("tool_calls"):
                tool_calls.extend(child_extracted.get("tool_calls", []))
            if child_extracted.get("thoughts"):
                reasoning.extend(child_extracted.get("thoughts", []))
            if child_extracted.get("plans"):
                reasoning.extend(child_extracted.get("plans", []))

        user_message = (
            extracted.get("query")
            or inputs.get("query")
            or inputs.get("question")
            or inputs.get("input")
            or None
        )
        llm_response = (
            extracted.get("response_text")
            or _flatten_output_text(outputs)
            or None
        )

        turns.append({
            "turn_index": idx,
            "run_id": trace.get("run_id"),
            "user_message": user_message,
            "tools_call": tool_calls,
            "reasoning": reasoning,
            "llm_response": llm_response,
            "tokens": {
                "prompt_tokens": tokens.get("prompt_tokens", 0),
                "completion_tokens": tokens.get("completion_tokens", 0),
                "total_tokens": tokens.get("total_tokens", 0),
                "total_cost": _safe_float(tokens.get("total_cost", 0.0)),
            },
            "latency_ms": trace.get("latency_ms"),
            "ttft_ms": trace.get("ttft_ms"),
            "status": trace.get("status"),
        })

    return {
        "thread_id": thread_id,
        "project_name": project_name or get_default_project_name() or "Auto-Resolved",
        "total_turns": len(turns),
        "turns": turns,
    }


def export_traces_to_file(
    thread_id: str,
    output_path: Optional[str] = None,
    project_name: Optional[str] = None,
    indent: int = 2,
) -> str:
    """
    Exports only the compact turn-by-turn data needed for analysis and observability.
    """
    export_data = build_compact_turn_export(thread_id, project_name=project_name)

    if not output_path:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        date_dir = datetime.now().strftime("%Y-%m-%d")
        exports_dir = os.path.join(project_root, "exports", "langsmith_traces", date_dir)
        os.makedirs(exports_dir, exist_ok=True)
        output_path = os.path.join(exports_dir, f"{thread_id}.json")
    else:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=indent, ensure_ascii=False)

    logger.info(f"✅ Successfully exported compact turn data to {os.path.abspath(output_path)}")
    return os.path.abspath(output_path)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LangSmith Trace Extractor by Thread ID")
    parser.add_argument("thread_id", nargs="?", help="The thread_id to fetch traces for")
    parser.add_argument("--thread-id", dest="opt_thread_id", help="Thread ID")
    parser.add_argument("--project", "-p", default=None, help="LangSmith Project Name (e.g. airline-booking-chatbot)")
    parser.add_argument("--export", "-e", nargs="?", const="", default=None, help="Path to export traces JSON (or default dir)")
    parser.add_argument("--summary", "-s", action="store_true", help="Print thread summary table")

    args = parser.parse_args()
    target_thread = args.thread_id or args.opt_thread_id

    if not target_thread:
        print("❌ Error: Please provide a thread_id.")
        print("Usage: python langsmith_client.py <thread_id> [--project <name>] [--export [path]]")
        sys.exit(1)

    print(f"\n🔍 Querying LangSmith traces for Thread ID: {target_thread}...")
    
    summary_data = get_thread_summary(target_thread, project_name=args.project)
    print(f"\n📊 Thread Observability Summary:")
    print(f"  • Total Traces:   {summary_data['total_traces']}")
    print(f"  • Total Latency:  {summary_data['total_latency_ms']} ms")
    print(f"  • Total Tokens:   {summary_data['tokens']['total_tokens']}")
    print(f"  • Tools Executed: {summary_data['tools_called_count']}")
    print(f"  • Turns Recorded: {len(summary_data['turns'])}\n")

    for idx, turn in enumerate(summary_data['turns'], 1):
        print(f"  Turn {idx} [{turn.get('name')}]:")
        if turn.get('user_query'):
            print(f"    • User: {turn.get('user_query')}")
        if turn.get('assistant_response'):
            print(f"    • AI: {turn.get('assistant_response')[:120]}...")

    plans, actions = get_agent_trajectory(target_thread, project_name=args.project)
    print(f"\n🧠 Agent Reasoning & Plans ({len(plans)}):")
    for idx, plan in enumerate(plans, 1):
        print(f"  [{idx}] {plan}")

    print(f"\n🛠️ Actions & Tools Taken ({len(actions)}):")
    for idx, action in enumerate(actions, 1):
        print(f"  [{idx}] {action}")

    if args.export is not None:
        path = args.export if args.export != "" else None
        saved_file = export_traces_to_file(target_thread, output_path=path, project_name=args.project)
        print(f"\n📁 Complete Traces JSON saved to: {saved_file}")