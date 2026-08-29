import os
import json
import requests
from datetime import datetime
from typing import List, Optional
from dotenv import load_dotenv

# 1. Load environment variables & API keys
load_dotenv()
if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY_TEMP"):
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_TEMP")
if not os.getenv("OPENAI_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "../app/.env"))
    if not os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY_TEMP"):
        os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY_TEMP")

# Clean empty string environment variables that can corrupt SDK base URLs
for k in ["OPENAI_BASE_URL", "LOCAL_MODEL_BASE_URL", "CONFIDENT_API_KEY"]:
    if os.environ.get(k) == "":
        os.environ.pop(k, None)

from deepeval.dataset import ConversationalGolden, Persona
from deepeval.simulator import ConversationSimulator
from deepeval.test_case import ConversationalTestCase, Turn

# Backend /chat endpoint URL (Default to local running server)
CHAT_API_URL = os.getenv("CHAT_API_URL", "http://localhost:8000/chat")


# 2. Callback with thread_id for stateful multi-turn simulation
def chat_api_callback(input: str, thread_id: str, turns: Optional[List[Turn]] = None) -> Turn:
    """
    DeepEval Model Callback with thread_id and turns.
    Sends user queries to the Chat API and parses the streaming SSE response.
    """
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
        response = requests.post(CHAT_API_URL, json=payload, stream=True, timeout=60)
        response.raise_for_status()

        assistant_content = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                raw_data = line[6:].strip()
                if raw_data == "[DONE]":
                    break
                try:
                    data = json.loads(raw_data)
                    if data.get("type") == "token":
                        assistant_content += data.get("content", "")
                    elif data.get("type") == "error":
                        print(f"Chat API Error: {data.get('message')}")
                except json.JSONDecodeError:
                    continue

        return Turn(
            role="assistant",
            content=assistant_content.strip() or "No response received from assistant.",
        )

    except requests.exceptions.RequestException as e:
        print(f"[Warning] Could not reach Chat API at {CHAT_API_URL}: {e}")
        return Turn(
            role="assistant",
            content=f"Error connecting to backend chat API: {e}",
        )


# 3. Export Utilities for DeepEval Conversations
def export_simulations(
    test_cases: List[ConversationalTestCase],
    output_dir: str = "exports",
    base_filename: Optional[str] = None,
) -> dict:
    """
    Exports simulated conversations to JSON, JSONL, and Markdown files.
    """
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = base_filename or f"simulation_{timestamp}"

    json_path = os.path.join(output_dir, f"{prefix}.json")
    jsonl_path = os.path.join(output_dir, f"{prefix}.jsonl")
    md_path = os.path.join(output_dir, f"{prefix}.md")

    # 3a. Export structured JSON
    serialized_cases = []
    for tc in test_cases:
        dump = tc.model_dump() if hasattr(tc, "model_dump") else tc.dict()
        serialized_cases.append(dump)

    export_payload = {
        "exported_at": datetime.now().isoformat(),
        "total_conversations": len(test_cases),
        "conversations": serialized_cases,
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    # 3b. Export JSONL (one conversation per line)
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for item in serialized_cases:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 3c. Export human-readable Markdown transcript
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# 🤖 Multi-Turn Conversation Simulation Report\n\n")
        f.write(f"- **Exported at**: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n")
        f.write(f"- **Total Conversations**: `{len(test_cases)}`\n\n")
        f.write("---\n\n")

        for idx, tc in enumerate(test_cases, 1):
            f.write(f"## 💬 Conversation #{idx}\n\n")
            f.write(f"- **Scenario**: {tc.scenario}\n")
            f.write(f"- **Expected Outcome**: {tc.expected_outcome}\n")
            if tc.additional_metadata:
                persona_info = tc.additional_metadata.get("persona") or tc.additional_metadata.get("Persona")
                if persona_info:
                    f.write(f"- **Persona**: {persona_info}\n")
            f.write("\n### Transcript\n\n")

            for turn_idx, turn in enumerate(tc.turns, 1):
                icon = "👤 **User**" if turn.role == "user" else "🤖 **Assistant**"
                f.write(f"#### Turn {turn_idx} — {icon}\n\n")
                f.write(f"{turn.content}\n\n")

            f.write("---\n\n")

    print(f"\n📁 Exported {len(test_cases)} simulated conversation(s) successfully:")
    print(f"  • JSON:     {os.path.abspath(json_path)}")
    print(f"  • JSONL:    {os.path.abspath(jsonl_path)}")
    print(f"  • Markdown: {os.path.abspath(md_path)}\n")

    return {
        "json": json_path,
        "jsonl": jsonl_path,
        "markdown": md_path,
    }


# 4. Define Golden Persona & Scenario
golden = ConversationalGolden(
    scenario="Single passenger booking a flight from Bangalore to Delhi in the near future",
    expected_outcome="Passenger receives confirmation of a successful Bangalore-to-Delhi flight booking",
    persona=Persona(characteristics="Single passenger planning a near-future trip from Bangalore to Delhi"),
)

# 5. Instantiate Simulator with the callback
simulator = ConversationSimulator(
    model_callback=chat_api_callback,
    max_concurrent=1,
)


if __name__ == "__main__":
    print(f"🚀 Starting Multi-turn Conversation Simulation...")
    print(f"🔗 Target Chat API: {CHAT_API_URL}")
    print(f"🎭 Scenario: {golden.scenario}\n")

    test_cases = simulator.simulate(
        conversational_goldens=[golden],
        max_user_simulations=10,
    )

    # 6. Export conversations to files
    export_simulations(
        test_cases=test_cases,
        output_dir=os.path.join(os.path.dirname(__file__), "exports"),
    )