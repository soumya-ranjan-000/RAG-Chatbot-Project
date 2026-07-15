import os
import uuid
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger("pss-db-supabase")

# Load environment
parent_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(parent_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY or "your-service-role-key" in SUPABASE_KEY:
    raise ValueError(
        f"Missing or invalid Supabase PSS configuration.\n"
        f"Please configure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in 'pss_system/.env':\n"
        f"  - URL should be: https://mcrulyrkewmspkzawxcl.supabase.co\n"
        f"  - Key should be the service role key for project 'mcrulyrkewmspkzawxcl'.\n"
        f"Current URL: {SUPABASE_URL}\n"
        f"Current Key: {SUPABASE_KEY}"
    )

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def map_booking(row: dict) -> dict:
    if not row:
        return {}
    dep_date = row.get("departure_datetime", "")
    dep_datetime = dep_date
    if dep_date and len(dep_date) >= 10:
        dep_date = dep_date[:10]
        
    flight_id = None
    pnr_id = row.get("pnr_id")
    if pnr_id:
        try:
            res_seg = supabase.table("pss_pnr_segments").select("flight_id").eq("pnr_id", pnr_id).limit(1).execute()
            if res_seg.data:
                flight_id = res_seg.data[0]["flight_id"]
        except Exception as e:
            logger.warning(f"Failed to query flight_id from segments: {e}")
            
    return {
        "pnr": row.get("pnr_code"),
        "passenger_id": row.get("legacy_id") or str(row.get("passenger_id")),
        "passenger_name": row.get("passenger_name"),
        "flight_number": row.get("flight_number"),
        "flight_id": flight_id,
        "origin": row.get("from_airport"),
        "destination": row.get("to_airport"),
        "date": dep_date,
        "gate": row.get("gate"),
        "seat": row.get("seat_number"),
        "status": row.get("booking_status")
    }

def get_passenger_profile(passenger_id: str) -> dict:
    logger.info(f"DB Query: Fetching passenger profile for {passenger_id}")
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass

    query = supabase.table("pss_passengers").select("*")
    if is_uuid:
        res = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res = query.eq("legacy_id", passenger_id).execute()

    if not res.data:
        return None
        
    pax = res.data[0]
    
    # Query bookings
    query_b = supabase.table("vw_passenger_itinerary").select("*")
    if is_uuid:
        res_b = query_b.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_b = query_b.eq("legacy_id", passenger_id).execute()
        
    bookings = [map_booking(row) for row in res_b.data]
    
    return {
        "passenger_id": pax.get("legacy_id") or str(pax.get("passenger_id")),
        "name": f"{pax.get('first_name', '')} {pax.get('last_name', '')}".strip(),
        "email": pax.get("email"),
        "frequent_flyer_number": pax.get("frequent_flyer_number"),
        "bookings": bookings
    }

def get_booking(pnr: str) -> dict:
    pnr_upper = pnr.upper()
    logger.info(f"DB Query: Fetching booking {pnr_upper}")
    res = supabase.table("vw_passenger_itinerary").select("*").eq("pnr_code", pnr_upper).execute()
    if res.data:
        return map_booking(res.data[0])
    return None

def create_booking(passenger_id: str, origin: str, destination: str, date: str, status: str = "booked") -> dict:
    logger.info(f"DB Action: Creating booking for pax={passenger_id}, origin={origin}, dest={destination}")
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass

    query = supabase.table("pss_passengers").select("passenger_id, first_name, last_name")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()

    if not res_pax.data:
        raise ValueError("Passenger profile not found")
    pax_uuid = res_pax.data[0]["passenger_id"]
    pax_name = f"{res_pax.data[0]['first_name']} {res_pax.data[0]['last_name']}"

    # Find matching flight
    res_flights = supabase.table("vw_flight_availability").select("*")\
        .eq("origin", origin.upper())\
        .eq("destination", destination.upper())\
        .execute()
        
    if not res_flights.data:
        raise ValueError(f"No flights found from {origin} to {destination}")

    # Use first flight matching date, or just first available
    flight = res_flights.data[0]
    for f in res_flights.data:
        if f.get("departure_datetime", "").startswith(date):
            flight = f
            break

    flight_id = flight["flight_id"]
    fare_id = flight.get("fare_id")
    base_fare = float(flight.get("base_fare_usd") or 290.00)
    taxes = 65.00
    total_amount = base_fare + taxes
    booking_class = flight.get("booking_class") or 'Y'
    cabin_class = flight.get("cabin_class") or 'economy'

    # Find an available seat
    res_seats = supabase.table("pss_seat_map").select("seat_id, seat_number")\
        .eq("flight_id", flight_id)\
        .eq("is_occupied", False)\
        .eq("is_blocked", False)\
        .eq("cabin_class", cabin_class)\
        .limit(1)\
        .execute()
        
    seat_id = None
    seat_number = "12A"
    if res_seats.data:
        seat_id = res_seats.data[0]["seat_id"]
        seat_number = res_seats.data[0]["seat_number"]

    pnr_code = f"PNR{uuid.uuid4().hex[:3].upper()}"
    pnr_status = "confirmed"
    if status == "pending-payment":
        pnr_status = "held"
    elif status == "cancelled":
        pnr_status = "cancelled"

    # Insert PNR
    pnr_data = {
        "pnr_code": pnr_code,
        "primary_passenger_id": pax_uuid,
        "status": pnr_status,
        "channel": "web",
        "total_base_fare_usd": base_fare,
        "total_taxes_usd": taxes,
        "total_amount_usd": total_amount,
        "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
    }
    res_pnr = supabase.table("pss_pnrs").insert(pnr_data).execute()
    if not res_pnr.data:
        raise ValueError("Failed to create PNR record")
    pnr_id = res_pnr.data[0]["pnr_id"]

    # Insert Segment
    segment_data = {
        "pnr_id": pnr_id,
        "flight_id": flight_id,
        "fare_id": fare_id,
        "segment_number": 1,
        "booking_class": booking_class,
        "cabin_class": cabin_class,
        "seat_id": seat_id,
        "segment_status": "confirmed",
        "base_fare_usd": base_fare,
        "taxes_usd": taxes,
        "baggage_allowance_kg": 23
    }
    supabase.table("pss_pnr_segments").insert(segment_data).execute()

    # Assign seat
    if seat_id:
        supabase.table("pss_seat_map").update({
            "is_occupied": True,
            "passenger_id": pax_uuid,
            "pnr_id": pnr_id
        }).eq("seat_id", seat_id).execute()

    # Decrement inventory
    res_inv = supabase.table("pss_inventory").select("available_seats, sold_seats")\
        .eq("flight_id", flight_id)\
        .eq("booking_class", booking_class)\
        .execute()
    if res_inv.data:
        inv = res_inv.data[0]
        supabase.table("pss_inventory").update({
            "available_seats": max(0, inv["available_seats"] - 1),
            "sold_seats": inv["sold_seats"] + 1
        }).eq("flight_id", flight_id).eq("booking_class", booking_class).execute()

    return {
        "pnr": pnr_code,
        "passenger_id": passenger_id,
        "passenger_name": pax_name,
        "flight_number": flight["flight_number"],
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": date,
        "gate": flight.get("gate") or "B3",
        "seat": seat_number,
        "status": status
    }

def cancel_booking(pnr: str) -> bool:
    pnr_upper = pnr.upper()
    logger.info(f"DB Action: Cancelling booking {pnr_upper}")
    
    res_pnr = supabase.table("pss_pnrs").select("pnr_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        logger.warning(f"DB Action Fail: Booking {pnr_upper} not found")
        return False
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    supabase.table("pss_pnrs").update({"status": "cancelled"}).eq("pnr_id", pnr_id).execute()
    
    res_segs = supabase.table("pss_pnr_segments").select("flight_id, booking_class, seat_id")\
        .eq("pnr_id", pnr_id).execute()
        
    for seg in res_segs.data:
        flight_id = seg["flight_id"]
        booking_class = seg["booking_class"]
        seat_id = seg["seat_id"]
        
        if seat_id:
            supabase.table("pss_seat_map").update({
                "is_occupied": False,
                "passenger_id": None,
                "pnr_id": None
            }).eq("seat_id", seat_id).execute()
            
        res_inv = supabase.table("pss_inventory").select("available_seats, sold_seats")\
            .eq("flight_id", flight_id)\
            .eq("booking_class", booking_class)\
            .execute()
        if res_inv.data:
            inv = res_inv.data[0]
            supabase.table("pss_inventory").update({
                "available_seats": inv["available_seats"] + 1,
                "sold_seats": max(0, inv["sold_seats"] - 1)
            }).eq("flight_id", flight_id).eq("booking_class", booking_class).execute()
            
    supabase.table("pss_pnr_segments").update({"segment_status": "cancelled"}).eq("pnr_id", pnr_id).execute()
    return True

def reschedule_booking(pnr: str, new_date: str, new_flight: str) -> dict:
    pnr_upper = pnr.upper()
    logger.info(f"DB Action: Rescheduling booking {pnr_upper} to flight {new_flight} on {new_date}")
    
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    pax_uuid = res_pnr.data[0]["primary_passenger_id"]
    
    res_flight = supabase.table("pss_flights").select("flight_id, flight_number, gate")\
        .eq("flight_number", new_flight.upper()).limit(1).execute()
    if not res_flight.data:
        raise ValueError(f"Flight {new_flight} not found")
    new_flight_id = res_flight.data[0]["flight_id"]
    
    res_segs = supabase.table("pss_pnr_segments").select("segment_id, flight_id, seat_id, booking_class, cabin_class")\
        .eq("pnr_id", pnr_id).execute()
    
    if not res_segs.data:
        raise ValueError("No segments found for booking")
        
    old_seg = res_segs.data[0]
    old_flight_id = old_seg["flight_id"]
    old_seat_id = old_seg["seat_id"]
    booking_class = old_seg["booking_class"]
    cabin_class = old_seg["cabin_class"]
    
    if old_seat_id:
        supabase.table("pss_seat_map").update({
            "is_occupied": False,
            "passenger_id": None,
            "pnr_id": None
        }).eq("seat_id", old_seat_id).execute()
        
    res_new_seats = supabase.table("pss_seat_map").select("seat_id")\
        .eq("flight_id", new_flight_id)\
        .eq("is_occupied", False)\
        .eq("is_blocked", False)\
        .eq("cabin_class", cabin_class)\
        .limit(1).execute()
        
    new_seat_id = None
    if res_new_seats.data:
        new_seat_id = res_new_seats.data[0]["seat_id"]
        
    if new_seat_id:
        supabase.table("pss_seat_map").update({
            "is_occupied": True,
            "passenger_id": pax_uuid,
            "pnr_id": pnr_id
        }).eq("seat_id", new_seat_id).execute()
        
    supabase.table("pss_pnr_segments").update({
        "flight_id": new_flight_id,
        "seat_id": new_seat_id
    }).eq("segment_id", old_seg["segment_id"]).execute()
    
    res_inv_old = supabase.table("pss_inventory").select("available_seats, sold_seats")\
        .eq("flight_id", old_flight_id).eq("booking_class", booking_class).execute()
    if res_inv_old.data:
        inv = res_inv_old.data[0]
        supabase.table("pss_inventory").update({
            "available_seats": inv["available_seats"] + 1,
            "sold_seats": max(0, inv["sold_seats"] - 1)
        }).eq("flight_id", old_flight_id).eq("booking_class", booking_class).execute()
        
    res_inv_new = supabase.table("pss_inventory").select("available_seats, sold_seats")\
        .eq("flight_id", new_flight_id).eq("booking_class", booking_class).execute()
    if res_inv_new.data:
        inv = res_inv_new.data[0]
        supabase.table("pss_inventory").update({
            "available_seats": max(0, inv["available_seats"] - 1),
            "sold_seats": inv["sold_seats"] + 1
        }).eq("flight_id", new_flight_id).eq("booking_class", booking_class).execute()
        
    updated_b = get_booking(pnr_upper)
    if updated_b:
        if updated_b.get("date") != new_date:
            updated_b["date"] = new_date
        return updated_b
    raise ValueError("Booking not found")

def get_flights(origin: str = None, destination: str = None, date: str = None) -> list:
    logger.info(f"DB Query: Fetching flights origin={origin}, destination={destination}, date={date}")
    query = supabase.table("vw_flight_availability").select("*")
    if origin:
        query = query.eq("origin", origin.upper())
    if destination:
        query = query.eq("destination", destination.upper())
    if date:
        query = query.gte("departure_datetime", f"{date}T00:00:00").lte("departure_datetime", f"{date}T23:59:59")
        
    res = query.execute()
    flights = []
    seen = set()
    for row in res.data:
        f_num = row.get("flight_number")
        dep_dt = row.get("departure_datetime", "")
        f_date = dep_dt[:10] if dep_dt else ""
        dep_time = dep_dt.split("T")[1][:5] if dep_dt and "T" in dep_dt else ""
        
        seen_key = (f_num, f_date, dep_time)
        if seen_key in seen:
            continue
        seen.add(seen_key)
        
        flights.append({
            "flight_number": f_num,
            "origin": row.get("origin"),
            "destination": row.get("destination"),
            "departure_time": dep_time,
            "date": f_date,
            "price": float(row.get("base_fare_usd") or 300),
            "airline": row.get("airline_name")
        })
    return flights

def update_booking_status(pnr: str, status: str) -> dict:
    pnr_upper = pnr.upper()
    logger.info(f"DB Action: Updating status of {pnr_upper} to {status}")
    status_mapped = status.lower().replace("-", "_")
    if status_mapped == "booked":
        status_mapped = "confirmed"
    elif status_mapped == "pending_payment":
        status_mapped = "held"
        
    supabase.table("pss_pnrs").update({"status": status_mapped}).eq("pnr_code", pnr_upper).execute()
    b = get_booking(pnr_upper)
    if b:
        return b
    raise ValueError("Booking not found")

def get_all_bookings() -> list:
    logger.info("DB Query: Fetching all bookings")
    res = supabase.table("vw_passenger_itinerary").select("*").execute()
    bookings = {}
    for row in res.data:
        pnr = row.get("pnr_code")
        if pnr not in bookings:
            bookings[pnr] = map_booking(row)
    return list(bookings.values())

def select_seat(pnr: str, passenger_id: str, seat_number: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    res_seg = supabase.table("pss_pnr_segments").select("segment_id, flight_id, seat_id").eq("pnr_id", pnr_id).execute()
    if not res_seg.data:
        raise ValueError("Booking segment not found")
    seg = res_seg.data[0]
    flight_id = seg["flight_id"]
    old_seat_id = seg["seat_id"]
    
    res_seat = supabase.table("pss_seat_map").select("seat_id, is_occupied").eq("flight_id", flight_id).eq("seat_number", seat_number.upper()).execute()
    if not res_seat.data:
        generate_seats_for_flight(flight_id)
        res_seat = supabase.table("pss_seat_map").select("seat_id, is_occupied").eq("flight_id", flight_id).eq("seat_number", seat_number.upper()).execute()
        if not res_seat.data:
            raise ValueError(f"Seat {seat_number} not found for this flight")
    new_seat = res_seat.data[0]
    if new_seat["is_occupied"]:
        raise ValueError(f"Seat {seat_number} is already occupied")
        
    if old_seat_id:
        supabase.table("pss_seat_map").update({
            "is_occupied": False,
            "passenger_id": None,
            "pnr_id": None
        }).eq("seat_id", old_seat_id).execute()
        
    supabase.table("pss_seat_map").update({
        "is_occupied": True,
        "passenger_id": res_pnr.data[0]["primary_passenger_id"],
        "pnr_id": pnr_id
    }).eq("seat_id", new_seat["seat_id"]).execute()
    
    supabase.table("pss_pnr_segments").update({"seat_id": new_seat["seat_id"]}).eq("segment_id", seg["segment_id"]).execute()
    return {"status": "success", "message": f"Seat {seat_number} successfully selected for PNR {pnr}"}

def process_payment(pnr: str, amount: float, method: str, idempotency_key: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    payment_data = {
        "pnr_id": pnr_id,
        "amount_usd": amount,
        "payment_method": method,
        "idempotency_key": idempotency_key,
        "status": "captured",
        "three_ds_status": "authenticated",
        "card_last_four": "4242",
        "card_brand": "Visa",
        "captured_at": datetime.now().isoformat()
    }
    res_pay = supabase.table("pss_payments").insert(payment_data).execute()
    supabase.table("pss_pnrs").update({"status": "confirmed"}).eq("pnr_id", pnr_id).execute()
    
    return {
        "status": "success",
        "message": "Payment captured successfully",
        "payment": res_pay.data[0] if res_pay.data else {}
    }

def issue_ticket(pnr: str, passenger_id: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass
        
    query = supabase.table("pss_passengers").select("passenger_id")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()
        
    if not res_pax.data:
        raise ValueError("Passenger not found")
    pax_uuid = res_pax.data[0]["passenger_id"]
    
    res_pay = supabase.table("pss_payments").select("payment_id").eq("pnr_id", pnr_id).eq("status", "captured").execute()
    if not res_pay.data:
        raise ValueError("Cannot issue ticket. Payment has not been captured.")
        
    res_seg = supabase.table("pss_pnr_segments").select("segment_id, flight_id, booking_class, cabin_class, base_fare_usd, taxes_usd").eq("pnr_id", pnr_id).execute()
    if not res_seg.data:
        raise ValueError("Booking segments not found")
    seg = res_seg.data[0]
    
    tkt_num = f"016{uuid.uuid4().hex[:10].upper()}"
    res_airline = supabase.table("pss_airlines").select("airline_id").limit(1).execute()
    airline_id = res_airline.data[0]["airline_id"] if res_airline.data else None
    
    ticket_data = {
        "pnr_id": pnr_id,
        "passenger_id": pax_uuid,
        "ticket_number": tkt_num,
        "issuing_airline_id": airline_id,
        "ticket_status": "open",
        "fare_basis_code": f"TKT-{seg['booking_class']}",
        "total_fare_usd": seg["base_fare_usd"],
        "total_taxes_usd": seg["taxes_usd"]
    }
    res_tkt = supabase.table("pss_tickets").insert(ticket_data).execute()
    tkt_id = res_tkt.data[0]["ticket_id"]
    
    coupon_data = {
        "ticket_id": tkt_id,
        "segment_id": seg["segment_id"],
        "coupon_number": 1,
        "coupon_status": "open"
    }
    supabase.table("pss_coupons").insert(coupon_data).execute()
    supabase.table("pss_pnrs").update({"status": "ticketed"}).eq("pnr_id", pnr_id).execute()
    
    return {
        "status": "success",
        "message": f"Ticket {tkt_num} issued successfully",
        "ticket_number": tkt_num
    }

def check_in(pnr: str) -> dict:
    pnr_upper = pnr.upper()
    res = supabase.table("vw_passenger_itinerary").select("*").eq("pnr_code", pnr_upper).execute()
    if not res.data:
        raise ValueError("PNR not found")
    pnr_id = res.data[0]["pnr_id"]
    
    res_tkts = supabase.table("pss_tickets").select("ticket_id").eq("pnr_id", pnr_id).execute()
    for tkt in res_tkts.data:
        supabase.table("pss_coupons").update({"coupon_status": "used"}).eq("ticket_id", tkt["ticket_id"]).execute()
        
    supabase.table("pss_pnrs").update({"status": "checked_in"}).eq("pnr_id", pnr_id).execute()
    return {"status": "success", "message": f"Check-in complete for PNR {pnr}. Boarding pass issued."}

def board_passenger(pnr: str, gate: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    supabase.table("pss_pnrs").update({"status": "boarded"}).eq("pnr_id", pnr_id).execute()
    return {"status": "success", "message": f"Passenger boarded at gate {gate}."}

def generate_seats_for_flight(flight_id: str):
    logger.info(f"Generating seat map on-demand for flight {flight_id}")
    seats = []
    
    # Business class rows 1-5 (A-D)
    for row in range(1, 6):
        for letter in ['A', 'B', 'C', 'D']:
            seat_type = 'window' if letter in ['A', 'D'] else 'aisle'
            seats.append({
                "flight_id": flight_id,
                "seat_number": f"{row}{letter}",
                "row_number": row,
                "seat_letter": letter,
                "cabin_class": "business",
                "seat_type": seat_type,
                "seat_category": "preferred",
                "extra_charge_usd": 0.0,
                "is_occupied": False
            })
            
    # Economy rows 10-39 (A-F)
    for row in range(10, 40):
        for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
            seat_type = 'window' if letter in ['A', 'F'] else ('aisle' if letter in ['C', 'D'] else 'middle')
            is_exit = row in [20, 21]
            seat_cat = "exit_row" if is_exit else "standard"
            charge = 25.0 if is_exit else 0.0
            seats.append({
                "flight_id": flight_id,
                "seat_number": f"{row}{letter}",
                "row_number": row,
                "seat_letter": letter,
                "cabin_class": "economy",
                "seat_type": seat_type,
                "seat_category": seat_cat,
                "extra_charge_usd": charge,
                "is_occupied": False
            })
            
    # Batch insert to avoid rate limits
    chunk_size = 50
    for i in range(0, len(seats), chunk_size):
        chunk = seats[i:i+chunk_size]
        supabase.table("pss_seat_map").insert(chunk).execute()

def get_seat_map(flight_id: str) -> list:
    is_uuid = False
    try:
        uuid.UUID(flight_id)
        is_uuid = True
    except ValueError:
        pass
        
    if not is_uuid:
        res_flight = supabase.table("pss_flights").select("flight_id").eq("flight_number", flight_id.upper()).limit(1).execute()
        if not res_flight.data:
            return []
        f_id = res_flight.data[0]["flight_id"]
    else:
        f_id = flight_id
        
    res = supabase.table("vw_seat_availability").select("*").eq("flight_id", f_id).execute()
    if not res.data:
        # Check if flight exists
        check_flight = supabase.table("pss_flights").select("flight_id").eq("flight_id", f_id).execute()
        if check_flight.data:
            generate_seats_for_flight(f_id)
            res = supabase.table("vw_seat_availability").select("*").eq("flight_id", f_id).execute()
            
    return res.data

def add_ssr(pnr: str, passenger_id: str, ssr_code: str, remarks: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass
        
    query = supabase.table("pss_passengers").select("passenger_id")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()
        
    if not res_pax.data:
        raise ValueError("Passenger not found")
    pax_uuid = res_pax.data[0]["passenger_id"]
    
    ssr_data = {
        "pnr_id": pnr_id,
        "passenger_id": pax_uuid,
        "ssr_code": ssr_code.upper(),
        "status": "confirmed",
        "remarks": remarks
    }
    res = supabase.table("pss_ssrs").insert(ssr_data).execute()
    return {"status": "success", "message": f"Special service request {ssr_code} added successfully."}

def get_loyalty_info(passenger_id: str) -> dict:
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass
        
    query = supabase.table("pss_passengers").select("loyalty_tier, miles_balance")
    if is_uuid:
        res = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res = query.eq("legacy_id", passenger_id).execute()
        
    if not res.data:
        return {"loyalty_tier": "none", "miles_balance": 0}
    return res.data[0]

def add_ancillary(pnr: str, passenger_id: str, ancillary_type: str, amount: float) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass
        
    query = supabase.table("pss_passengers").select("passenger_id")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()
        
    if not res_pax.data:
        raise ValueError("Passenger not found")
    pax_uuid = res_pax.data[0]["passenger_id"]
    
    ancillary_data = {
        "pnr_id": pnr_id,
        "passenger_id": pax_uuid,
        "ancillary_type": ancillary_type,
        "amount_usd": amount,
        "status": "confirmed"
    }
    res = supabase.table("pss_ancillaries").insert(ancillary_data).execute()
    return {"status": "success", "message": f"Ancillary {ancillary_type} added successfully."}

def get_revenue_summary(flight_id: str) -> dict:
    is_uuid = False
    try:
        uuid.UUID(flight_id)
        is_uuid = True
    except ValueError:
        pass
        
    if not is_uuid:
        res_flight = supabase.table("pss_flights").select("flight_id").eq("flight_number", flight_id.upper()).limit(1).execute()
        if not res_flight.data:
            return {}
        f_id = res_flight.data[0]["flight_id"]
    else:
        f_id = flight_id
        
    res = supabase.table("vw_revenue_summary").select("*").eq("flight_id", f_id).execute()
    return res.data[0] if res.data else {}
