import os
import httpx
from langchain_core.tools import tool

PSS_API_URL = os.environ.get("PSS_API_URL", "http://localhost:8000/api/pss")
if PSS_API_URL and not PSS_API_URL.endswith("/api/pss"):
    PSS_API_URL = PSS_API_URL.rstrip("/") + "/api/pss"


@tool
def check_passenger_profile(passenger_id: str) -> dict:
    """
    Retrieves the passenger's details, frequent flyer tier, and contact information.
    Use this to identify the passenger's details.
    """
    try:
        response = httpx.get(f"{PSS_API_URL}/passengers/{passenger_id}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Passenger {passenger_id} not found."}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def check_booking_status(pnr: str) -> dict:
    """
    Retrieves the details of a booking (origin, destination, date, flight number, seat, gate, status) using the PNR code.
    """
    try:
        response = httpx.get(f"{PSS_API_URL}/bookings/{pnr}")
        if response.status_code == 200:
            return response.json()
        return {"error": f"Booking with PNR '{pnr}' not found."}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def book_flight(passenger_id: str, origin: str, destination: str, date: str, booking_class: str = "Y") -> dict:
    """
    Creates a new flight booking for the given passenger from origin to destination on the specified date (YYYY-MM-DD).
    Input parameters:
      - passenger_id: Unique passenger identifier or legacy ID.
      - origin: Three-letter departure airport code (e.g. BLR, JFK).
      - destination: Three-letter arrival airport code (e.g. JFK, LAX).
      - date: Departure date (YYYY-MM-DD).
      - booking_class: Booking class letter (e.g., 'B' for Economy Light, 'Y' for Economy Flex, 'J' for Business Flex). Defaults to 'Y'.
    Returns the booking confirmation including the generated PNR code.
    """
    try:
        payload = {
            "passenger_id": passenger_id,
            "origin": origin,
            "destination": destination,
            "date": date,
            "status": "pending-payment",
            "booking_class": booking_class
        }
        response = httpx.post(f"{PSS_API_URL}/bookings", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to book flight.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def cancel_flight(pnr: str) -> dict:
    """
    Cancels an active booking using its PNR code. Returns success or failure status.
    """
    try:
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/cancel")
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to cancel booking.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def reschedule_flight(pnr: str, new_date: str, new_flight: str) -> dict:
    """
    Reschedules an active flight booking. Updates the flight date and flight number.
    Input parameters:
      - pnr: Booking reservation code.
      - new_date: New date of departure (YYYY-MM-DD).
      - new_flight: New flight number (e.g., AA102).
    """
    try:
        payload = {
            "new_date": new_date,
            "new_flight": new_flight
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/reschedule", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to reschedule booking.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def search_flights(origin: str = None, destination: str = None, date: str = None) -> list:
    """
    Searches and lists scheduled flights matching the given origin, destination airport codes (e.g. BLR, JFK, LAX), and optional date (e.g. 2026-08-15).
    Use this to find available flight numbers, departure dates/times, and prices before booking.
    """
    try:
        params = {}
        if origin:
            params["origin"] = origin
        if destination:
            params["destination"] = destination
        if date:
            params["date"] = date
        response = httpx.get(f"{PSS_API_URL}/flights", params=params)
        if response.status_code == 200:
            return response.json()
        return {"error": "Failed to retrieve flights."}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def check_in_passenger(pnr: str) -> dict:
    """
    Performs online check-in for a passenger using their booking PNR.
    This updates the booking status to 'checked-in' and automatically issues/generates their boarding pass.
    """
    try:
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/checkin")
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", f"Failed to perform check-in for PNR {pnr}.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def list_passenger_bookings(passenger_id: str) -> list:
    """
    Retrieves the list of active/past flight bookings (including PNR numbers, dates, origin/destination, and status) for a specific passenger ID.
    Use this to look up a passenger's PNR numbers or booking history.
    """
    try:
        response = httpx.get(f"{PSS_API_URL}/passengers/{passenger_id}")
        if response.status_code == 200:
            return response.json().get("bookings", [])
        return {"error": f"Passenger {passenger_id} not found."}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def select_seat_tool(pnr: str, passenger_id: str, seat_number: str) -> dict:
    """
    Selects a specific seat (e.g. 14A, 12B) for a passenger on their flight using their PNR and passenger ID.
    """
    try:
        payload = {
            "passenger_id": passenger_id,
            "seat_number": seat_number
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/seat", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to select seat.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def process_payment_tool(pnr: str, amount: float, payment_method: str, idempotency_key: str) -> dict:
    """
    Processes mock payment for a flight booking (PNR) to transition status from pending-payment to confirmed/paid.
    """
    try:
        payload = {
            "amount": amount,
            "payment_method": payment_method,
            "idempotency_key": idempotency_key
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/payment", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to process payment.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def add_ssr_tool(pnr: str, passenger_id: str, ssr_code: str, remarks: str = "") -> dict:
    """
    Adds a Special Service Request (SSR) like wheelchair (WCHR), vegetarian meal (VGML), etc., to a booking.
    """
    try:
        payload = {
            "passenger_id": passenger_id,
            "ssr_code": ssr_code,
            "remarks": remarks
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/ssr", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to add SSR.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def get_loyalty_info_tool(passenger_id: str) -> dict:
    """
    Retrieves the loyalty tier and miles balance for a passenger.
    """
    try:
        response = httpx.get(f"{PSS_API_URL}/passengers/{passenger_id}/loyalty")
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to retrieve loyalty info.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def issue_ticket_tool(pnr: str, passenger_id: str) -> dict:
    """
    Issues e-tickets and coupons for a paid booking (PNR). E-tickets are required for check-in.
    """
    try:
        payload = {
            "passenger_id": passenger_id
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/ticket", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to issue ticket.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def board_passenger_tool(pnr: str, gate: str) -> dict:
    """
    Boards a checked-in passenger at the gate.
    """
    try:
        payload = {
            "gate": gate
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/board", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to board passenger.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def get_seat_map_tool(flight_id: str) -> dict:
    """
    Retrieves the seat map showing availability, row numbers, and charges for a flight.
    """
    try:
        response = httpx.get(f"{PSS_API_URL}/flights/{flight_id}/seats")
        if response.status_code == 200:
            seats = response.json()
            total_seats = len(seats)
            available = [s for s in seats if s.get("is_available", True) and not s.get("is_occupied", False)]
            business_avail = [s for s in available if s.get("cabin_class") == "business"]
            economy_avail = [s for s in available if s.get("cabin_class") == "economy"]
            
            sample_seats = [s.get("seat_number") for s in available[:10]]
            
            return {
                "status": "success",
                "flight_id": flight_id,
                "total_seats": total_seats,
                "available_seats_count": len(available),
                "business_available_count": len(business_avail),
                "economy_available_count": len(economy_avail),
                "sample_available_seats": sample_seats,
                "message": "Seat map retrieved successfully. You MUST show the visual seat map using the seats-options code block so the user can select their seat."
            }
        return {"error": "Failed to retrieve seat map."}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def add_ancillary_tool(pnr: str, passenger_id: str, ancillary_type: str, amount: float) -> dict:
    """
    Adds an ancillary service (like baggage, meals, lounge access, Wi-Fi, etc.) to a passenger's booking.
    Parameters:
      - pnr: The reservation code.
      - passenger_id: The passenger's ID.
      - ancillary_type: The type of ancillary service (e.g. 'extra_baggage', 'in_flight_meal', 'lounge_access', 'wifi').
      - amount: The price/cost of the ancillary in USD.
    """
    try:
        payload = {
            "passenger_id": passenger_id,
            "ancillary_type": ancillary_type,
            "amount": amount
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/ancillary", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to add ancillary.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def upgrade_with_miles_tool(pnr: str, passenger_id: str, required_miles: int) -> dict:
    """
    Upgrades a booking segment (PNR) to Business Class using the passenger's accumulated loyalty miles.
    Parameters:
      - pnr: The reservation code.
      - passenger_id: The passenger's ID.
      - required_miles: The number of loyalty miles required for the upgrade.
    """
    try:
        payload = {
            "passenger_id": passenger_id,
            "required_miles": required_miles
        }
        response = httpx.post(f"{PSS_API_URL}/bookings/{pnr}/upgrade", json=payload)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to upgrade flight with miles.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

@tool
def check_flight_status_tool(flight_number: str, date: str = None) -> dict:
    """
    Checks the real-time flight status (e.g. gates, delays, status like Scheduled, Delayed, Boarding, Departed) 
    for a flight number (e.g. EK511).
    Parameters:
      - flight_number: The flight code/number (e.g. EK511).
      - date: Optional departure date (YYYY-MM-DD). If omitted, retrieves the most recent or scheduled flight.
    """
    try:
        params = {}
        if date:
            params["date"] = date
        response = httpx.get(f"{PSS_API_URL}/flights/{flight_number}/status", params=params)
        if response.status_code == 200:
            return response.json()
        return {"error": response.json().get("detail", "Failed to retrieve flight status.")}
    except Exception as e:
        return {"error": f"Failed to connect to PSS: {e}"}

