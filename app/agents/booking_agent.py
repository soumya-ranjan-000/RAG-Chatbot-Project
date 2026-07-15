import os
import json
import logging
from typing import AsyncGenerator, List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from .tools import (
    check_passenger_profile,
    check_booking_status,
    book_flight,
    cancel_flight,
    reschedule_flight,
    search_flights,
    check_in_passenger,
    list_passenger_bookings,
    select_seat_tool,
    process_payment_tool,
    add_ssr_tool,
    get_loyalty_info_tool,
    issue_ticket_tool,
    board_passenger_tool,
    get_seat_map_tool,
    add_ancillary_tool
)

logger = logging.getLogger("booking-agent")

# Map tool names to actual functions
tools_map = {
    "check_passenger_profile": check_passenger_profile,
    "check_booking_status": check_booking_status,
    "book_flight": book_flight,
    "cancel_flight": cancel_flight,
    "reschedule_flight": reschedule_flight,
    "search_flights": search_flights,
    "check_in_passenger": check_in_passenger,
    "list_passenger_bookings": list_passenger_bookings,
    "select_seat_tool": select_seat_tool,
    "process_payment_tool": process_payment_tool,
    "add_ssr_tool": add_ssr_tool,
    "get_loyalty_info_tool": get_loyalty_info_tool,
    "issue_ticket_tool": issue_ticket_tool,
    "board_passenger_tool": board_passenger_tool,
    "get_seat_map_tool": get_seat_map_tool,
    "add_ancillary_tool": add_ancillary_tool
}

SYSTEM_PROMPT = """You are the Airline Booking Agent. You help passengers manage their bookings, check flight statuses, search flights, perform online check-in, select seats, make payments, request special services (SSR), check loyalty profiles, issue e-tickets, select ancillary options (such as baggage, meals, lounge access, or Wi-Fi), and board flights.
You have access to the Passenger Service System (PSS) database via tools.

When assisting a passenger:
1. Identify the passenger's details using their profile (injected below).
2. If they ask to search flights, check booking status, book, check in, cancel, reschedule a flight, select seats, request special services (SSR), add ancillaries (baggage/meals/etc.), make payments, issue e-tickets, or board flights, call the appropriate tool.
3. Formatting flight search results:
   When showing available flights, you MUST format the flight list using a JSON array inside a ```flights code block.
   Example:
   ```flights
   [
     {
       "flight_number": "AA100",
       "airline": "American Airlines",
       "origin": "JFK",
       "destination": "LAX",
       "departure_time": "10:30 AM",
       "price": 150,
       "date": "2026-07-22"
     }
   ]
   ```
4. Formatting passenger bookings/tickets/PNR details:
   When listing the passenger's bookings or details about tickets/PNRs, you MUST format them using a JSON array inside a ```tickets code block.
   Example:
   ```tickets
   [
     {
       "pnr": "PNRXYZ",
       "passenger_name": "Alex Mercer",
       "flight_number": "AA100",
       "origin": "JFK",
       "destination": "LAX",
       "date": "2026-07-22",
       "gate": "B3",
       "seat": "12A",
       "status": "pending-payment"
     }
   ]
   ```
5. Formatting new bookings (mock payments):
   When a user requests to book a flight and the booking is created (it starts in "pending-payment" status), you MUST output a ```payment code block containing the booking details so the user can pay.
   Example:
   ```payment
   {
     "pnr": "PNRXYZ",
     "price": 150,
     "flight_number": "AA100",
     "origin": "JFK",
     "destination": "LAX",
     "date": "2026-07-22",
     "passenger_id": "usr_94f83b"
   }
   ```
   Under the payment block, explain clearly that the passenger needs to click the payment link to pay and confirm their ticket in the new tab.
6. When they check in for a booking, call the `check_in_passenger` tool which will update the status to checked-in and boarding-pass-generated.
7. Be professional, direct, and confirm details before booking, cancelling, selecting seats, processing payments, or adding extra services.
8. Interactive Passenger Details Review:
   Before calling `book_flight` to create a booking, you MUST ask the passenger to review their details (Name, Email, Frequent Flyer No). Always format these details using a ```passenger-review code block containing a JSON object.
   Example:
   ```passenger-review
   {
     "name": "Jane Doe",
     "email": "jane@example.com",
     "frequent_flyer": "FF-9382"
   }
   ```
9. Interactive Seat Selection Options:
   When prompting the user to select their seat from available seats, you MUST retrieve the seat map using `get_seat_map_tool` for the flight. Then, you MUST output a ```seats-options code block containing a JSON object with keys "pnr", "flight_id", and "passenger_id".
   CRITICAL: Do NOT output the JSON object as plain text or within standard ```json code blocks. It MUST start exactly with ```seats-options on a new line, followed by the JSON, and end with ```. If you do not format it this way, the frontend visual seat selector will fail to render.
   IMPORTANT: If you do not have the flight_id or passenger_id in the conversation history/context, you MUST call the `check_booking_status` tool first with the PNR code (e.g. PNRC6E) to retrieve the flight number/ID and passenger details. Do NOT ask the user for flight details or seat numbers; retrieve them using the tools, and output the interactive `seats-options` code block.
   Example:
   ```seats-options
   {
     "pnr": "PNRXYZ",
     "flight_id": "EK565",
     "passenger_id": "usr_938b8"
   }
   ```
10. Interactive Meal Options Selection:
    When asking the passenger about their meal preference, you MUST output the options using a ```meal-options code block containing a JSON array.
    Example:
    ```meal-options
    [
      {"code": "VGML", "label": "Vegetarian Meal"},
      {"code": "GFML", "label": "Gluten-Free Meal"},
      {"code": "KSML", "label": "Kosher Meal"},
      {"code": "STD", "label": "Standard Meal"}
    ]
    ```
11. General Options Block:
    At the beginning of a conversation (e.g. if the user greets you or says hello) or whenever the user asks for help or is unsure what to do, you MUST present them with a list of available actions. You MUST format these options using a ```options code block containing a JSON array.
    Example:
    ```options
    [
      {"label": "🔍 Search Flights", "text": "Search flights"},
      {"label": "✈️ View My Bookings", "text": "Show my active bookings"},
      {"label": "💺 Choose Seat", "text": "Select seat for my booking"},
      {"label": "🍱 Meal Options", "text": "Choose meal option"},
      {"label": "💼 Add Baggage", "text": "Add baggage or service"},
      {"label": "👤 Passenger Info", "text": "Show passenger info"}
    ]
    ```
12. Confirmation Block:
    Whenever you ask the passenger for a yes/no confirmation (such as "Would you like to book this flight?", "Are you sure you want to cancel this booking?", or "Would you like to proceed with rescheduling?"), you MUST present them with selectable options by outputting a ```confirm code block containing a JSON object.
    Example:
    ```confirm
    {
      "question": "Would you like to proceed with booking flight SQ511 to SIN?",
      "yes_text": "yes",
      "yes_label": "Yes, book now",
      "no_text": "no",
      "no_label": "No, cancel"
    }
    ```
"""

async def run_booking_agent(
    query: str,
    history: List[Dict[str, str]],
    passenger_profile: Dict[str, Any]
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stateful agent execution loop. Streams text tokens and tool invocation events.
    """
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY_TEMP")
    
    # Initialize the LLM with bound tools
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.1,
        openai_api_key=key,
        streaming=True,
        stream_options={"include_usage": True}
    )
    llm_with_tools = llm.bind_tools(list(tools_map.values()))

    # Build prompt messages
    passenger_context = f"""
Current Logged-in Passenger:
- ID: {passenger_profile.get('passenger_id', 'unknown')}
- Name: {passenger_profile.get('name', 'Unknown')}
- Email: {passenger_profile.get('email', 'Unknown')}
- Frequent Flyer Number: {passenger_profile.get('frequent_flyer_number', 'None')}

Always use this ID and details when interacting with tools on behalf of this passenger.
"""
    messages = [
        SystemMessage(content=SYSTEM_PROMPT + passenger_context)
    ]

    # Add chat history
    for msg in history[-10:]:
        role = msg.get("role")
        content = msg.get("content")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # Add latest query
    messages.append(HumanMessage(content=query))

    # Stateful loop: max 5 turns to prevent infinite agent execution loops
    for turn in range(5):
        logger.info(f"Agent executing turn {turn + 1}...")
        
        full_chunk = None
        async for chunk in llm_with_tools.astream(messages):
            if full_chunk is None:
                full_chunk = chunk
            else:
                full_chunk += chunk

            # Stream text content if generated
            if chunk.content:
                has_content = True
                yield {"type": "token", "content": chunk.content}

        if full_chunk:
            if full_chunk.usage_metadata:
                usage_metadata = full_chunk.usage_metadata
            if full_chunk.tool_calls:
                tool_calls = full_chunk.tool_calls
            else:
                tool_calls = []
        else:
            tool_calls = []
            usage_metadata = None

        if tool_calls:
            # Execute each tool call sequentially
            for tool_call in tool_calls:
                name = tool_call["name"]
                args = tool_call["args"]
                call_id = tool_call["id"]

                logger.info(f"Agent calling tool '{name}' with args {args}")
                yield {"type": "tool_call", "name": name, "args": args}

                tool_func = tools_map.get(name)
                if tool_func:
                    try:
                        result = tool_func.invoke(args)
                    except Exception as e:
                        logger.error(f"Error executing tool '{name}': {e}")
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Tool '{name}' not found."}

                logger.info(f"Tool '{name}' returned: {result}")
                yield {"type": "tool_result", "name": name, "args": args, "result": result}

                # Construct and append messages to feed back into the model in the next turn
                assistant_msg = AIMessage(content="", tool_calls=tool_calls)
                messages.append(assistant_msg)

                tool_msg = ToolMessage(content=json.dumps(result), tool_call_id=call_id)
                messages.append(tool_msg)
            
            # Continue the loop for the model to generate the response based on tool results
            continue
        else:
            # Yield final usage/metrics if present
            if usage_metadata:
                yield {"type": "metrics", "usage": usage_metadata}
            # Finished execution (no tool calls made)
            break
