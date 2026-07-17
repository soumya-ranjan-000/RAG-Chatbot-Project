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

def get_bookings_batch(pnr_codes: list) -> list:
    if not pnr_codes:
        return []
        
    pnr_codes_upper = list(set(p.upper() for p in pnr_codes if p))
    if not pnr_codes_upper:
        return []
        
    logger.info(f"DB Query: Fetching bookings batch for {pnr_codes_upper}")
    
    # 1. PNR rows
    res_pnrs = supabase.table("pss_pnrs").select("*").in_("pnr_code", pnr_codes_upper).execute()
    if not res_pnrs.data:
        return []
        
    pnrs_by_code = {p["pnr_code"].upper(): p for p in res_pnrs.data}
    pnr_ids = [p["pnr_id"] for p in res_pnrs.data]
    
    # 2. PNR Passengers
    res_pax = supabase.table("pss_pnr_passengers")\
        .select("pnr_id, passenger_id, passenger_type, is_primary")\
        .in_("pnr_id", pnr_ids)\
        .execute()
        
    pax_by_pnr = {}
    for p in res_pax.data:
        pnr_id_str = str(p["pnr_id"])
        pax_by_pnr.setdefault(pnr_id_str, []).append(p)
        
    # 3. Passenger Profiles
    passenger_ids = list(set(str(p["passenger_id"]) for p in res_pax.data))
    profiles_by_uuid = {}
    if passenger_ids:
        res_profiles = supabase.table("pss_passengers")\
            .select("passenger_id, legacy_id, first_name, last_name, email, frequent_flyer_number")\
            .in_("passenger_id", passenger_ids)\
            .execute()
        profiles_by_uuid = {str(p_row["passenger_id"]): p_row for p_row in res_profiles.data}
        
    # 4. Segments
    res_segs = supabase.table("pss_pnr_segments")\
        .select("*")\
        .in_("pnr_id", pnr_ids)\
        .order("segment_number")\
        .execute()
        
    segs_by_pnr = {}
    for s in res_segs.data:
        pnr_id_str = str(s["pnr_id"])
        segs_by_pnr.setdefault(pnr_id_str, []).append(s)
        
    # 5. Flight Details
    flight_ids = list(set(str(s["flight_id"]) for s in res_segs.data if s.get("flight_id")))
    flights_by_id = {}
    if flight_ids:
        res_flights = supabase.table("vw_flight_availability")\
            .select("*")\
            .in_("flight_id", flight_ids)\
            .execute()
        for f_row in res_flights.data:
            flights_by_id[str(f_row["flight_id"])] = f_row
            
    # 6. Seat Details
    seat_ids = [str(s["seat_id"]) for s in res_segs.data if s.get("seat_id")]
    seats_by_id = {}
    if seat_ids:
        res_seats = supabase.table("pss_seat_map")\
            .select("seat_id, seat_number, passenger_id")\
            .in_("seat_id", seat_ids)\
            .execute()
        seats_by_id = {str(st["seat_id"]): st for st in res_seats.data}
        
    # Now construct the bookings
    bookings_list = []
    
    # We want to return them in the order of requested pnr_codes (if found)
    for pnr in pnr_codes_upper:
        pnr_row = pnrs_by_code.get(pnr)
        if not pnr_row:
            continue
            
        pnr_id = pnr_row["pnr_id"]
        pnr_id_str = str(pnr_id)
        primary_passenger_id = pnr_row["primary_passenger_id"]
        
        # Build pax list for this PNR
        pax_list = []
        primary_pax = None
        pax_rows = pax_by_pnr.get(pnr_id_str, [])
        
        for p in pax_rows:
            p_uuid_str = str(p["passenger_id"])
            profile = profiles_by_uuid.get(p_uuid_str)
            if profile:
                name = f"{profile['first_name']} {profile['last_name']}"
                pax_info = {
                    "passenger_id": profile["legacy_id"] or str(profile["passenger_id"]),
                    "uuid": p_uuid_str,
                    "name": name,
                    "first_name": profile["first_name"],
                    "last_name": profile["last_name"],
                    "email": profile["email"],
                    "frequent_flyer": profile["frequent_flyer_number"],
                    "passenger_type": p["passenger_type"],
                    "is_primary": p["is_primary"]
                }
                pax_list.append(pax_info)
                if p["is_primary"] or p["passenger_id"] == primary_passenger_id:
                    primary_pax = pax_info
                    
        if not primary_pax and pax_list:
            primary_pax = pax_list[0]
            
        # Build segments list for this PNR
        segs_list = []
        seg_rows = segs_by_pnr.get(pnr_id_str, [])
        
        for s in seg_rows:
            flight_id_str = str(s["flight_id"])
            f = flights_by_id.get(flight_id_str, {})
            
            flight_num = f.get("flight_number") or "N/A"
            origin = f.get("origin") or "N/A"
            destination = f.get("destination") or "N/A"
            dep_datetime = f.get("departure_datetime", "") or "N/A"
            dep_time = dep_datetime.split("T")[1][:5] if dep_datetime and "T" in dep_datetime else ""
            airline = f.get("airline_name") or "Apex Air"
            gate = f.get("gate") or "B3"
            flight_status = f.get("flight_status")
            
            seat_num = None
            assigned_pax_id = None
            if s.get("seat_id"):
                seat_info = seats_by_id.get(str(s["seat_id"]), {})
                seat_num = seat_info.get("seat_number")
                pax_uuid_seat = seat_info.get("passenger_id")
                if pax_uuid_seat:
                    for p in pax_list:
                        if p["uuid"] == str(pax_uuid_seat):
                            assigned_pax_id = p["passenger_id"]
                            break
                            
            segs_list.append({
                "segment_id": s["segment_id"],
                "flight_id": flight_id_str,
                "flight_number": flight_num,
                "origin": origin,
                "destination": destination,
                "departure_datetime": dep_datetime,
                "departure_time": dep_time,
                "date": dep_datetime[:10] if dep_datetime and dep_datetime != "N/A" else "N/A",
                "gate": gate,
                "seat": seat_num,
                "status": s["segment_status"],
                "airline": airline,
                "booking_class": s["booking_class"],
                "cabin_class": s["cabin_class"],
                "passenger_id": assigned_pax_id,
                "flight_status": flight_status
            })
            
        first_seg = segs_list[0] if segs_list else {}
        pnr_status = pnr_row["status"]
        flight_id = first_seg.get("flight_id")
        flight_status = first_seg.get("flight_status") if first_seg else None
        
        # Fallback for flight status if needed
        if flight_id and not flight_status:
            try:
                res_f = supabase.table("pss_flights").select("status").eq("flight_id", flight_id).execute()
                if res_f.data:
                    flight_status = res_f.data[0].get("status")
            except Exception as e:
                logger.error(f"Failed to query flight status for PNR mapping: {e}")
                
        if pnr_status == "checked_in":
            pnr_status = "checked-in"
        elif pnr_status == "boarded":
            pnr_status = "boarding-pass-generated"
        elif pnr_status == "flown":
            if flight_status == "departed":
                pnr_status = "departed"
            elif flight_status == "arrived":
                pnr_status = "completed"
            else:
                pnr_status = "completed"
                
        booking_dict = {
            "pnr": pnr,
            "pnr_id": str(pnr_id),
            "status": pnr_status,
            "total_amount": float(pnr_row["total_amount_usd"] or 0.0),
            "passenger_id": primary_pax["passenger_id"] if primary_pax else None,
            "passenger_name": primary_pax["name"] if primary_pax else None,
            "flight_number": first_seg.get("flight_number"),
            "flight_id": first_seg.get("flight_id"),
            "origin": first_seg.get("origin"),
            "destination": first_seg.get("destination"),
            "date": first_seg.get("date"),
            "gate": first_seg.get("gate"),
            "seat": first_seg.get("seat"),
            "airline": first_seg.get("airline"),
            "booking_class": first_seg.get("booking_class"),
            "cabin_class": first_seg.get("cabin_class"),
            "passengers": pax_list,
            "segments": segs_list
        }
        bookings_list.append(booking_dict)
        
    return bookings_list

def get_booking(pnr: str) -> dict:
    bookings = get_bookings_batch([pnr])
    return bookings[0] if bookings else None

def map_booking(row: dict) -> dict:
    if not row:
        return {}
    pnr_code = row.get("pnr_code")
    if pnr_code:
        return get_booking(pnr_code)
    return {}

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
        if passenger_id == "admin":
            logger.info("Admin passenger profile not found, dynamically creating it...")
            admin_row = {
                "legacy_id": "admin",
                "first_name": "System",
                "last_name": "Administrator",
                "email": "admin",
                "frequent_flyer_number": "FF_ADMIN"
            }
            res_ins = supabase.table("pss_passengers").insert(admin_row).execute()
            if res_ins.data:
                res.data = res_ins.data
            else:
                return None
        else:
            return None
        
    pax = res.data[0]
    
    # Query bookings
    query_b = supabase.table("vw_passenger_itinerary").select("*")
    if is_uuid:
        res_b = query_b.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_b = query_b.eq("legacy_id", passenger_id).execute()
        
    # Deduplicate PNRs to prevent querying the same PNR multiple times for multi-segment itineraries
    pnr_codes = []
    seen_pnrs = set()
    for row in res_b.data:
        pnr = row.get("pnr_code")
        if pnr and pnr not in seen_pnrs:
            seen_pnrs.add(pnr)
            pnr_codes.append(pnr)

    bookings = get_bookings_batch(pnr_codes)
    
    return {
        "passenger_id": pax.get("legacy_id") or str(pax.get("passenger_id")),
        "name": f"{pax.get('first_name', '')} {pax.get('last_name', '')}".strip(),
        "email": pax.get("email"),
        "frequent_flyer_number": pax.get("frequent_flyer_number"),
        "bookings": bookings
    }

def create_booking(passenger_id: str, origin: str, destination: str, date: str, status: str = "booked", booking_class: str = "Y", passengers: list = None, return_date: str = None, return_booking_class: str = None) -> dict:
    logger.info(f"DB Action: Creating booking for pax={passenger_id}, origin={origin}, dest={destination}, class={booking_class}")
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass

    query = supabase.table("pss_passengers").select("passenger_id, first_name, last_name, email")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()

    if not res_pax.data:
        raise ValueError("Passenger profile not found")
    primary_pax = res_pax.data[0]
    pax_uuid = primary_pax["passenger_id"]
    pax_name = f"{primary_pax['first_name']} {primary_pax['last_name']}"

    passenger_ids = []
    if passengers:
        for idx, p in enumerate(passengers):
            first_name = p.get("first_name", "").strip()
            last_name = p.get("last_name", "").strip()
            email = p.get("email", "").strip()
            p_type = p.get("passenger_type", "ADT").upper()
            if not email:
                email = f"{first_name.lower()}.{last_name.lower()}@example.com"
                
            res_p_check = supabase.table("pss_passengers").select("passenger_id").eq("email", email).execute()
            if res_p_check.data:
                p_uuid = res_p_check.data[0]["passenger_id"]
            else:
                title_val = p.get("title", "MR").upper() if p.get("title") else "MR"
                if title_val not in ['MR', 'MRS', 'MS', 'DR', 'PROF']:
                    title_val = 'MR'
                new_pax = {
                    "first_name": first_name or "Passenger",
                    "last_name": last_name or "Guest",
                    "email": email,
                    "title": title_val
                }
                res_p_ins = supabase.table("pss_passengers").insert(new_pax).execute()
                if not res_p_ins.data:
                    raise ValueError(f"Failed to create profile for passenger {first_name} {last_name}")
                p_uuid = res_p_ins.data[0]["passenger_id"]
                
            passenger_ids.append((p_uuid, p_type, f"{first_name} {last_name}"))
    else:
        passenger_ids.append((pax_uuid, "ADT", pax_name))

    # Find matching flight
    res_flights = supabase.table("vw_flight_availability").select("*")\
        .eq("origin", origin.upper())\
        .eq("destination", destination.upper())\
        .execute()
        
    if not res_flights.data:
        raise ValueError(f"No flights found from {origin} to {destination}")

    # Use first flight matching date and booking_class, fallback to matching date, fallback to first available
    outbound_flight = None
    for f in res_flights.data:
        if f.get("departure_datetime", "").startswith(date) and f.get("booking_class") == booking_class.upper():
            outbound_flight = f
            break
            
    if not outbound_flight:
        for f in res_flights.data:
            if f.get("departure_datetime", "").startswith(date):
                outbound_flight = f
                break
                
    if not outbound_flight:
        outbound_flight = res_flights.data[0]

    outbound_flight_id = outbound_flight["flight_id"]
    outbound_fare_id = outbound_flight.get("fare_id")
    outbound_base_fare = float(outbound_flight.get("base_fare_usd") or 290.00)
    outbound_taxes = 65.00
    outbound_booking_class = outbound_flight.get("booking_class") or booking_class or 'Y'
    outbound_cabin_class = outbound_flight.get("cabin_class") or 'economy'

    return_flight = None
    return_base_fare = 0.0
    return_taxes = 0.0
    if return_date:
        res_ret_flights = supabase.table("vw_flight_availability").select("*")\
            .eq("origin", destination.upper())\
            .eq("destination", origin.upper())\
            .execute()
            
        if not res_ret_flights.data:
            raise ValueError(f"No return flights found from {destination} to {origin}")

        ret_class = (return_booking_class or booking_class or "Y").upper()
        for f in res_ret_flights.data:
            if f.get("departure_datetime", "").startswith(return_date) and f.get("booking_class") == ret_class:
                return_flight = f
                break
        if not return_flight:
            for f in res_ret_flights.data:
                if f.get("departure_datetime", "").startswith(return_date):
                    return_flight = f
                    break
        if not return_flight:
            return_flight = res_ret_flights.data[0]

        return_flight_id = return_flight["flight_id"]
        return_fare_id = return_flight.get("fare_id")
        return_base_fare = float(return_flight.get("base_fare_usd") or 290.00)
        return_taxes = 65.00
        return_booking_class = return_flight.get("booking_class") or ret_class or 'Y'
        return_cabin_class = return_flight.get("cabin_class") or 'economy'

    num_pax = len(passenger_ids)
    total_base_fare = (outbound_base_fare + return_base_fare) * num_pax
    total_taxes = (outbound_taxes + return_taxes) * num_pax
    total_amount = total_base_fare + total_taxes

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
        "total_base_fare_usd": total_base_fare,
        "total_taxes_usd": total_taxes,
        "total_amount_usd": total_amount,
        "expires_at": (datetime.now() + timedelta(days=1)).isoformat()
    }
    res_pnr = supabase.table("pss_pnrs").insert(pnr_data).execute()
    if not res_pnr.data:
        raise ValueError("Failed to create PNR record")
    pnr_id = res_pnr.data[0]["pnr_id"]

    # Insert PNR Passengers
    for idx, (p_uuid, p_type, name) in enumerate(passenger_ids):
        pnr_pax_data = {
            "pnr_id": pnr_id,
            "passenger_id": p_uuid,
            "is_primary": (idx == 0),
            "passenger_type": p_type
        }
        supabase.table("pss_pnr_passengers").insert(pnr_pax_data).execute()

    # Assign seats and segments
    outbound_seat_number = "12A"
    
    for idx, (p_uuid, p_type, name) in enumerate(passenger_ids):
        # 1. Outbound segment
        res_seats = supabase.table("pss_seat_map").select("seat_id, seat_number")\
            .eq("flight_id", outbound_flight_id)\
            .eq("is_occupied", False)\
            .eq("is_blocked", False)\
            .eq("cabin_class", outbound_cabin_class)\
            .limit(1)\
            .execute()
            
        outbound_seat_id = None
        if res_seats.data:
            outbound_seat_id = res_seats.data[0]["seat_id"]
            if idx == 0:
                outbound_seat_number = res_seats.data[0]["seat_number"]

        outbound_seg_data = {
            "pnr_id": pnr_id,
            "flight_id": outbound_flight_id,
            "fare_id": outbound_fare_id,
            "segment_number": 1,
            "booking_class": outbound_booking_class,
            "cabin_class": outbound_cabin_class,
            "seat_id": outbound_seat_id,
            "segment_status": "confirmed",
            "base_fare_usd": outbound_base_fare,
            "taxes_usd": outbound_taxes,
            "baggage_allowance_kg": 23
        }
        supabase.table("pss_pnr_segments").insert(outbound_seg_data).execute()

        if outbound_seat_id:
            supabase.table("pss_seat_map").update({
                "is_occupied": True,
                "passenger_id": p_uuid,
                "pnr_id": pnr_id
            }).eq("seat_id", outbound_seat_id).execute()

        # Decrement inventory outbound
        res_inv = supabase.table("pss_inventory").select("available_seats, sold_seats")\
            .eq("flight_id", outbound_flight_id)\
            .eq("booking_class", outbound_booking_class)\
            .execute()
        if res_inv.data:
            inv = res_inv.data[0]
            supabase.table("pss_inventory").update({
                "available_seats": max(0, inv["available_seats"] - 1),
                "sold_seats": inv["sold_seats"] + 1
            }).eq("flight_id", outbound_flight_id).eq("booking_class", outbound_booking_class).execute()

        # 2. Return segment
        if return_flight:
            res_ret_seats = supabase.table("pss_seat_map").select("seat_id, seat_number")\
                .eq("flight_id", return_flight_id)\
                .eq("is_occupied", False)\
                .eq("is_blocked", False)\
                .eq("cabin_class", return_cabin_class)\
                .limit(1)\
                .execute()
                
            return_seat_id = None
            if res_ret_seats.data:
                return_seat_id = res_ret_seats.data[0]["seat_id"]

            return_seg_data = {
                "pnr_id": pnr_id,
                "flight_id": return_flight_id,
                "fare_id": return_fare_id,
                "segment_number": 2,
                "booking_class": return_booking_class,
                "cabin_class": return_cabin_class,
                "seat_id": return_seat_id,
                "segment_status": "confirmed",
                "base_fare_usd": return_base_fare,
                "taxes_usd": return_taxes,
                "baggage_allowance_kg": 23
            }
            supabase.table("pss_pnr_segments").insert(return_seg_data).execute()

            if return_seat_id:
                supabase.table("pss_seat_map").update({
                    "is_occupied": True,
                    "passenger_id": p_uuid,
                    "pnr_id": pnr_id
                }).eq("seat_id", return_seat_id).execute()

            # Decrement inventory return
            res_inv_ret = supabase.table("pss_inventory").select("available_seats, sold_seats")\
                .eq("flight_id", return_flight_id)\
                .eq("booking_class", return_booking_class)\
                .execute()
            if res_inv_ret.data:
                inv_ret = res_inv_ret.data[0]
                supabase.table("pss_inventory").update({
                    "available_seats": max(0, inv_ret["available_seats"] - 1),
                    "sold_seats": inv_ret["sold_seats"] + 1
                }).eq("flight_id", return_flight_id).eq("booking_class", return_booking_class).execute()

    return {
        "pnr": pnr_code,
        "passenger_id": passenger_id,
        "passenger_name": pax_name,
        "flight_number": outbound_flight["flight_number"],
        "origin": origin.upper(),
        "destination": destination.upper(),
        "date": date,
        "gate": outbound_flight.get("gate") or "B3",
        "seat": outbound_seat_number,
        "status": status,
        "airline": outbound_flight.get("airline_name") or "Apex Air",
        "booking_class": outbound_booking_class,
        "cabin_class": outbound_cabin_class,
        "price": total_amount,
        "passengers": [{"passenger_id": pid, "name": name, "type": ptype} for pid, ptype, name in passenger_ids],
        "is_round_trip": bool(return_flight),
        "return_flight_number": return_flight["flight_number"] if return_flight else None,
        "return_date": return_date if return_flight else None
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
    
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id, status").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    
    pnr_data = res_pnr.data[0]
    pnr_status = pnr_data.get("status")
    if pnr_status in ("checked_in", "checked-in", "boarded"):
        raise ValueError("Cannot reschedule booking after check-in.")
        
    pnr_id = pnr_data["pnr_id"]
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

def get_flights(origin: str = None, destination: str = None, date: str = None, time_range: str = None) -> list:
    logger.info(f"DB Query: Fetching flights origin={origin}, destination={destination}, date={date}, time_range={time_range}")
    query = supabase.table("vw_flight_availability").select("*")
    if origin:
        query = query.eq("origin", origin.upper())
    if destination:
        query = query.eq("destination", destination.upper())
        
    start_time = "00:00:00"
    end_time = "23:59:59"
    if time_range:
        tr = time_range.strip().lower()
        if tr == "morning":
            start_time = "06:00:00"
            end_time = "12:00:00"
        elif tr == "afternoon":
            start_time = "12:00:00"
            end_time = "17:00:00"
        elif tr == "evening":
            start_time = "17:00:00"
            end_time = "21:00:00"
        elif tr == "night":
            start_time = "21:00:00"
            end_time = "23:59:59"
        elif "-" in tr:
            parts = tr.split("-")
            if len(parts) == 2:
                def parse_time_part(t_str: str) -> str:
                    t_str = t_str.strip()
                    if t_str.isdigit():
                        return f"{int(t_str):02d}:00:00"
                    if ":" in t_str:
                        sub_parts = t_str.split(":")
                        if len(sub_parts) >= 2:
                            try:
                                h = int(sub_parts[0])
                                m = int(sub_parts[1])
                                s = int(sub_parts[2]) if len(sub_parts) > 2 and sub_parts[2].isdigit() else 0
                                return f"{h:02d}:{m:02d}:{s:02d}"
                            except ValueError:
                                pass
                    return t_str
                
                start_time = parse_time_part(parts[0])
                end_time = parse_time_part(parts[1])
                
    if date:
        query = query.gte("departure_datetime", f"{date}T{start_time}").lte("departure_datetime", f"{date}T{end_time}")
        
    res = query.execute()
    
    flights_dict = {}
    for row in res.data:
        f_num = row.get("flight_number")
        dep_dt = row.get("departure_datetime", "")
        f_date = dep_dt[:10] if dep_dt else ""
        dep_time = dep_dt.split("T")[1][:5] if dep_dt and "T" in dep_dt else ""
        
        if not f_num or not f_date:
            continue
            
        key = (f_num, f_date, dep_time)
        
        benefits = []
        if row.get("refundable"):
            benefits.append("Refundable")
        else:
            benefits.append("Non-refundable")
        if row.get("changeable"):
            benefits.append("Changeable")
        else:
            benefits.append("No changes")
        if row.get("extra_baggage_kg"):
            benefits.append(f"+{row.get('extra_baggage_kg')}kg bag")
        if row.get("seat_selection"):
            benefits.append("Free seat selection")
        if row.get("lounge_access"):
            benefits.append("Lounge access")
            
        fare_option = {
            "class": row.get("fare_family") or "Standard Class",
            "booking_class": row.get("booking_class") or "Y",
            "cabin": row.get("cabin_class") or "economy",
            "price": float(row.get("base_fare_usd") or 300.0),
            "benefits": ", ".join(benefits)
        }
        
        if key not in flights_dict:
            flights_dict[key] = {
                "flight_number": f_num,
                "origin": row.get("origin"),
                "destination": row.get("destination"),
                "departure_time": dep_time,
                "date": f_date,
                "airline": row.get("airline_name") or "Apex Air",
                "fares": [fare_option]
            }
        else:
            if not any(f["booking_class"] == fare_option["booking_class"] for f in flights_dict[key]["fares"]):
                flights_dict[key]["fares"].append(fare_option)

    flights_list = []
    for f_data in flights_dict.values():
        f_data["fares"] = sorted(f_data["fares"], key=lambda x: x["price"])
        f_data["price"] = f_data["fares"][0]["price"] if f_data["fares"] else 300.0
        flights_list.append(f_data)
        
    return flights_list

def update_booking_status(pnr: str, status: str) -> dict:
    pnr_upper = pnr.upper()
    logger.info(f"DB Action: Updating status of {pnr_upper} to {status}")
    status_mapped = status.lower().replace("-", "_")
    if status_mapped == "booked":
        status_mapped = "confirmed"
    elif status_mapped == "pending_payment":
        status_mapped = "held"
    elif status_mapped in ("boarding_pass_generated", "boarding_pass"):
        status_mapped = "boarded"
    elif status_mapped in ("departed", "completed", "landed"):
        status_mapped = "flown"
        
    supabase.table("pss_pnrs").update({"status": status_mapped}).eq("pnr_code", pnr_upper).execute()
    
    # If simulation updates status to departed or completed, also update the flight status in pss_flights
    if status.lower() in ("departed", "completed", "landed"):
        try:
            b = get_booking(pnr_upper)
            if b and b.get("segments"):
                for seg in b["segments"]:
                    flight_id = seg.get("flight_id")
                    if flight_id:
                        f_status = "departed" if status.lower() == "departed" else "arrived"
                        supabase.table("pss_flights").update({"status": f_status}).eq("flight_id", flight_id).execute()
        except Exception as e:
            logger.error(f"Failed to update flight status during booking status simulation: {e}")

    b = get_booking(pnr_upper)
    if b:
        return b
    raise ValueError("Booking not found")

def get_all_bookings() -> list:
    logger.info("DB Query: Fetching all bookings")
    res = supabase.table("pss_pnrs").select("pnr_code").execute()
    pnr_codes = [row["pnr_code"] for row in res.data if row.get("pnr_code")]
    return get_bookings_batch(pnr_codes)

def select_seat(pnr: str, passenger_id: str, seat_number: str, flight_id: str = None) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id, status").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    
    pnr_data = res_pnr.data[0]
    pnr_status = pnr_data.get("status")
    if pnr_status in ("checked_in", "checked-in", "boarded"):
        raise ValueError("Cannot select or change seat after check-in.")
        
    pnr_id = pnr_data["pnr_id"]
    
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
        raise ValueError("Passenger profile not found")
    pax_uuid = res_pax.data[0]["passenger_id"]

    flight_uuid = None
    if flight_id:
        try:
            uuid.UUID(flight_id)
            flight_uuid = flight_id
        except ValueError:
            res_fl = supabase.table("pss_flights").select("flight_id").eq("flight_number", flight_id.upper()).limit(1).execute()
            if res_fl.data:
                flight_uuid = res_fl.data[0]["flight_id"]

    res_seg = supabase.table("pss_pnr_segments").select("segment_id, flight_id, seat_id, cabin_class").eq("pnr_id", pnr_id).execute()
    if not res_seg.data:
        raise ValueError("Booking segment not found")

    seg_to_update = None
    matching_segs = res_seg.data
    if flight_uuid:
        matching_segs = [s for s in matching_segs if s["flight_id"] == flight_uuid]

    for s in matching_segs:
        s_id = s.get("seat_id")
        if s_id:
            res_seat = supabase.table("pss_seat_map").select("passenger_id").eq("seat_id", s_id).execute()
            if res_seat.data and res_seat.data[0].get("passenger_id") == pax_uuid:
                seg_to_update = s
                break

    if not seg_to_update and matching_segs:
        seg_to_update = matching_segs[0]

    if not seg_to_update:
        raise ValueError("Booking segment not found for this passenger and flight")

    flight_id_to_use = seg_to_update["flight_id"]
    old_seat_id = seg_to_update["seat_id"]
    cabin_class = seg_to_update.get("cabin_class") or "economy"

    if seat_number.lower() in ("system-assigned", "auto", "any", "system_assigned"):
        res_avail = supabase.table("pss_seat_map").select("seat_id, seat_number, is_occupied")\
            .eq("flight_id", flight_id_to_use)\
            .eq("is_occupied", False)\
            .eq("cabin_class", cabin_class)\
            .order("seat_number").execute()
            
        if not res_avail.data:
            res_avail = supabase.table("pss_seat_map").select("seat_id, seat_number, is_occupied")\
                .eq("flight_id", flight_id_to_use)\
                .eq("is_occupied", False)\
                .order("seat_number").execute()
                
        if not res_avail.data:
            generate_seats_for_flight(flight_id_to_use)
            res_avail = supabase.table("pss_seat_map").select("seat_id, seat_number, is_occupied")\
                .eq("flight_id", flight_id_to_use)\
                .eq("is_occupied", False)\
                .eq("cabin_class", cabin_class)\
                .order("seat_number").execute()
                
            if not res_avail.data:
                res_avail = supabase.table("pss_seat_map").select("seat_id, seat_number, is_occupied")\
                    .eq("flight_id", flight_id_to_use)\
                    .eq("is_occupied", False)\
                    .order("seat_number").execute()
                    
            if not res_avail.data:
                raise ValueError("No available seats on this flight")
        new_seat = res_avail.data[0]
        seat_number = new_seat["seat_number"]
    else:
        res_seat = supabase.table("pss_seat_map").select("seat_id, is_occupied").eq("flight_id", flight_id_to_use).eq("seat_number", seat_number.upper()).execute()
        if not res_seat.data:
            generate_seats_for_flight(flight_id_to_use)
            res_seat = supabase.table("pss_seat_map").select("seat_id, is_occupied").eq("flight_id", flight_id_to_use).eq("seat_number", seat_number.upper()).execute()
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
        "passenger_id": pax_uuid,
        "pnr_id": pnr_id
    }).eq("seat_id", new_seat["seat_id"]).execute()
    
    supabase.table("pss_pnr_segments").update({"seat_id": new_seat["seat_id"]}).eq("segment_id", seg_to_update["segment_id"]).execute()
    return {"status": "success", "message": f"Seat {seat_number} successfully selected for PNR {pnr}", "seat_number": seat_number}

def process_payment(pnr: str, amount: float, method: str, idempotency_key: str) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    method_val = (method or "card").lower()
    if method_val in ('credit_card', 'cc', 'debit_card', 'card'):
        method_val = 'card'
    elif method_val not in ('card','wallet','bank_transfer','voucher','miles'):
        method_val = 'card'
        
    payment_data = {
        "pnr_id": pnr_id,
        "amount_usd": amount,
        "payment_method": method_val,
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
    
    # Check payment
    res_pay = supabase.table("pss_payments").select("payment_id").eq("pnr_id", pnr_id).eq("status", "captured").execute()
    if not res_pay.data:
        raise ValueError("Cannot issue ticket. Payment has not been captured.")

    # Get all passengers in this PNR
    res_pax = supabase.table("pss_pnr_passengers").select("passenger_id").eq("pnr_id", pnr_id).execute()
    pax_uuids = [p["passenger_id"] for p in res_pax.data]
    
    # If a specific passenger_id is requested (and it's not 'all'), filter to that one
    if passenger_id and passenger_id != "all":
        is_uuid = False
        try:
            uuid.UUID(passenger_id)
            is_uuid = True
        except ValueError:
            pass
            
        query = supabase.table("pss_passengers").select("passenger_id")
        if is_uuid:
            res_target_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
        else:
            res_target_pax = query.eq("legacy_id", passenger_id).execute()
            
        if res_target_pax.data:
            pax_uuids = [res_target_pax.data[0]["passenger_id"]]

    res_seg = supabase.table("pss_pnr_segments").select("segment_id, flight_id, booking_class, cabin_class, base_fare_usd, taxes_usd, seat_id").eq("pnr_id", pnr_id).execute()
    if not res_seg.data:
        raise ValueError("Booking segments not found")

    res_airline = supabase.table("pss_airlines").select("airline_id").limit(1).execute()
    airline_id = res_airline.data[0]["airline_id"] if res_airline.data else None

    issued_ticket_numbers = []

    for pax_uuid in pax_uuids:
        # Find segments for this passenger (via seat_map)
        pax_segs = []
        for s in res_seg.data:
            seat_id = s.get("seat_id")
            if seat_id:
                res_seat = supabase.table("pss_seat_map").select("passenger_id").eq("seat_id", seat_id).execute()
                if res_seat.data and res_seat.data[0].get("passenger_id") == pax_uuid:
                    pax_segs.append(s)
        
        # Fallback to all segments if no specific seat mapping is found
        if not pax_segs:
            pax_segs = res_seg.data

        # Check if ticket already exists
        res_tkt_exist = supabase.table("pss_tickets").select("ticket_id, ticket_number").eq("pnr_id", pnr_id).eq("passenger_id", pax_uuid).execute()
        if res_tkt_exist.data:
            tkt_num = res_tkt_exist.data[0]["ticket_number"]
            tkt_id = res_tkt_exist.data[0]["ticket_id"]
        else:
            tkt_num = f"016{uuid.uuid4().hex[:10].upper()}"
            pax_base_fare = sum(float(s["base_fare_usd"]) for s in pax_segs)
            pax_taxes = sum(float(s["taxes_usd"]) for s in pax_segs)
            
            ticket_data = {
                "pnr_id": pnr_id,
                "passenger_id": pax_uuid,
                "ticket_number": tkt_num,
                "issuing_airline_id": airline_id,
                "ticket_status": "open",
                "fare_basis_code": f"TKT-{pax_segs[0]['booking_class']}" if pax_segs else "TKT-Y",
                "total_fare_usd": pax_base_fare,
                "total_taxes_usd": pax_taxes
            }
            res_tkt = supabase.table("pss_tickets").insert(ticket_data).execute()
            tkt_id = res_tkt.data[0]["ticket_id"]

        # Ensure coupons exist
        for idx, s in enumerate(pax_segs):
            res_cp_exist = supabase.table("pss_coupons").select("coupon_id").eq("ticket_id", tkt_id).eq("segment_id", s["segment_id"]).execute()
            if not res_cp_exist.data:
                coupon_data = {
                    "ticket_id": tkt_id,
                    "segment_id": s["segment_id"],
                    "coupon_number": idx + 1,
                    "coupon_status": "open"
                }
                supabase.table("pss_coupons").insert(coupon_data).execute()

            issued_ticket_numbers.append(tkt_num)

    supabase.table("pss_pnrs").update({"status": "ticketed"}).eq("pnr_id", pnr_id).execute()

    return {
        "status": "success",
        "message": f"Tickets issued successfully for passengers: {', '.join(issued_ticket_numbers)}",
        "ticket_number": issued_ticket_numbers[0] if issued_ticket_numbers else "N/A"
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
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id, status").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    
    pnr_data = res_pnr.data[0]
    pnr_status = pnr_data.get("status")
    if pnr_status in ("checked_in", "checked-in", "boarded"):
        raise ValueError("Cannot request special service/meal after check-in.")
        
    pnr_id = pnr_data["pnr_id"]
    
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
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id, status").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("PNR not found")
    
    pnr_data = res_pnr.data[0]
    pnr_status = pnr_data.get("status")
    if pnr_status in ("checked_in", "checked-in", "boarded"):
        raise ValueError("Cannot add baggage or ancillary services after check-in.")
        
    pnr_id = pnr_data["pnr_id"]
    
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

def upgrade_with_miles(pnr: str, passenger_id: str, required_miles: int) -> dict:
    pnr_upper = pnr.upper()
    res_pnr = supabase.table("pss_pnrs").select("pnr_id, primary_passenger_id").eq("pnr_code", pnr_upper).execute()
    if not res_pnr.data:
        raise ValueError("Booking not found")
    pnr_id = res_pnr.data[0]["pnr_id"]
    
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass
        
    query = supabase.table("pss_passengers").select("passenger_id, miles_balance")
    if is_uuid:
        res_pax = query.or_(f"passenger_id.eq.{passenger_id},legacy_id.eq.{passenger_id}").execute()
    else:
        res_pax = query.eq("legacy_id", passenger_id).execute()
        
    if not res_pax.data:
        raise ValueError("Passenger not found")
        
    db_pax_id = res_pax.data[0]["passenger_id"]
    miles_balance = res_pax.data[0]["miles_balance"] or 0
    
    if miles_balance < required_miles:
        raise ValueError(f"Insufficient miles. Required: {required_miles}, Available: {miles_balance}")
        
    res_seg = supabase.table("pss_pnr_segments").select("segment_id, cabin_class, booking_class").eq("pnr_id", pnr_id).execute()
    if not res_seg.data:
        raise ValueError("No segment found for this PNR")
        
    seg = res_seg.data[0]
    if seg["cabin_class"] == "business":
        raise ValueError("Ticket is already in Business Class")
        
    new_miles = miles_balance - required_miles
    supabase.table("pss_passengers").update({"miles_balance": new_miles}).eq("passenger_id", db_pax_id).execute()
    
    supabase.table("pss_pnr_segments").update({
        "cabin_class": "business",
        "booking_class": "J"
    }).eq("segment_id", seg["segment_id"]).execute()
    
    return {
        "status": "success",
        "message": f"Successfully upgraded PNR {pnr} to Business Class. Deducted {required_miles} miles.",
        "remaining_miles": new_miles
    }

def get_flight_status(flight_number: str, date: str = None) -> dict:
    f_num = flight_number.upper().strip()
    logger.info(f"DB Query: Fetching flight status for {f_num} on date={date}")
    
    query = supabase.table("pss_flights").select("*").eq("flight_number", f_num)
    if date:
        query = query.gte("departure_datetime", f"{date}T00:00:00").lte("departure_datetime", f"{date}T23:59:59")
        
    query = query.order("departure_datetime", desc=True).limit(1)
    res = query.execute()
    
    if not res.data:
        return {}
        
    flight = res.data[0]
    
    airports_res = supabase.table("pss_airports").select("airport_id, iata_code, city, name").execute()
    airports_map = {row["airport_id"]: row for row in airports_res.data}
    
    airlines_res = supabase.table("pss_airlines").select("airline_id, iata_code, name").execute()
    airlines_map = {row["airline_id"]: row for row in airlines_res.data}
    
    orig = airports_map.get(flight.get("origin_airport_id"), {})
    dest = airports_map.get(flight.get("destination_airport_id"), {})
    airline = airlines_map.get(flight.get("airline_id"), {})
    
    return {
        "flight_id": flight.get("flight_id"),
        "flight_number": flight.get("flight_number"),
        "airline_name": airline.get("name", "Airline"),
        "airline_code": airline.get("iata_code", ""),
        "origin_iata": orig.get("iata_code", ""),
        "origin_city": orig.get("city", ""),
        "origin_name": orig.get("name", ""),
        "destination_iata": dest.get("iata_code", ""),
        "destination_city": dest.get("city", ""),
        "destination_name": dest.get("name", ""),
        "departure_datetime": flight.get("departure_datetime"),
        "arrival_datetime": flight.get("arrival_datetime"),
        "actual_departure": flight.get("actual_departure"),
        "actual_arrival": flight.get("actual_arrival"),
        "status": flight.get("status"),
        "gate": flight.get("gate") or "N/A",
        "terminal": flight.get("terminal") or "N/A",
        "delay_minutes": flight.get("delay_minutes") or 0
    }

def get_all_passengers() -> list:
    res = supabase.table("pss_passengers").select("*").execute()
    return res.data

def create_passenger_profile(data: dict) -> dict:
    # default legacy_id to something
    legacy_id = f"usr_{uuid.uuid4().hex[:6]}"
    row = {
        "legacy_id": legacy_id,
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "frequent_flyer_number": data.get("frequent_flyer_number", "")
    }
    res = supabase.table("pss_passengers").insert(row).execute()
    return res.data[0] if res.data else None

def update_passenger_profile(passenger_id: str, data: dict) -> dict:
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass

    row = {
        "first_name": data.get("first_name", ""),
        "last_name": data.get("last_name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "frequent_flyer_number": data.get("frequent_flyer_number", "")
    }
    
    query = supabase.table("pss_passengers").update(row)
    if is_uuid:
        res = query.eq("passenger_id", passenger_id).execute()
    else:
        res = query.eq("legacy_id", passenger_id).execute()
        
    return res.data[0] if res.data else None

def delete_passenger_profile(passenger_id: str) -> bool:
    is_uuid = False
    try:
        uuid.UUID(passenger_id)
        is_uuid = True
    except ValueError:
        pass

    # First, get the passenger's UUID
    query = supabase.table("pss_passengers").select("passenger_id")
    if is_uuid:
        res = query.eq("passenger_id", passenger_id).execute()
    else:
        res = query.eq("legacy_id", passenger_id).execute()
        
    if not res.data:
        return False
        
    pax_uuid = res.data[0]["passenger_id"]
    
    # Supabase foreign keys usually have ON DELETE CASCADE.
    # However, for bookings where this is primary passenger, they might not cascade depending on schema.
    # Let's manually delete PNRs where this passenger is the primary.
    res_pnrs = supabase.table("pss_pnrs").select("pnr_code").eq("primary_passenger_id", pax_uuid).execute()
    for pnr in res_pnrs.data:
        cancel_booking(pnr["pnr_code"])
        
    # Now delete the passenger profile itself
    res_del = supabase.table("pss_passengers").delete().eq("passenger_id", pax_uuid).execute()
    return True

def clear_booking_data() -> dict:
    logger.info("DB Action: Clearing all booking-related data from database.")
    
    results = {}
    
    # 1. Delete coupons
    try:
        res = supabase.table("pss_coupons").delete().neq("coupon_id", "00000000-0000-0000-0000-000000000000").execute()
        results["coupons_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting coupons: {e}")
        results["coupons_error"] = str(e)
        
    # 2. Delete tickets
    try:
        res = supabase.table("pss_tickets").delete().neq("ticket_id", "00000000-0000-0000-0000-000000000000").execute()
        results["tickets_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting tickets: {e}")
        results["tickets_error"] = str(e)
        
    # 3. Delete payments
    try:
        res = supabase.table("pss_payments").delete().neq("payment_id", "00000000-0000-0000-0000-000000000000").execute()
        results["payments_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting payments: {e}")
        results["payments_error"] = str(e)
        
    # 4. Delete ancillaries
    try:
        res = supabase.table("pss_ancillaries").delete().neq("ancillary_id", "00000000-0000-0000-0000-000000000000").execute()
        results["ancillaries_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting ancillaries: {e}")
        results["ancillaries_error"] = str(e)
        
    # 5. Delete SSRs
    try:
        res = supabase.table("pss_ssrs").delete().neq("ssr_id", "00000000-0000-0000-0000-000000000000").execute()
        results["ssrs_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting SSRs: {e}")
        results["ssrs_error"] = str(e)
        
    # 6. Delete PNR segments
    try:
        res = supabase.table("pss_pnr_segments").delete().neq("segment_id", "00000000-0000-0000-0000-000000000000").execute()
        results["segments_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting segments: {e}")
        results["segments_error"] = str(e)
        
    # 7. Delete PNR passengers
    try:
        res = supabase.table("pss_pnr_passengers").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        results["pnr_passengers_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting PNR passengers: {e}")
        results["pnr_passengers_error"] = str(e)
        
    # 8. Reset Seat Map bookings (Must be done before deleting PNRs to satisfy foreign key constraints)
    try:
        res_seats = supabase.table("pss_seat_map").select("seat_id").or_("is_occupied.eq.true,pnr_id.not.is.null").execute()
        if res_seats.data:
            seat_ids = [s["seat_id"] for s in res_seats.data]
            results["seats_reset"] = len(seat_ids)
            for i in range(0, len(seat_ids), 100):
                batch = seat_ids[i:i+100]
                supabase.table("pss_seat_map").update({
                    "is_occupied": False,
                    "passenger_id": None,
                    "pnr_id": None
                }).in_("seat_id", batch).execute()
        else:
            results["seats_reset"] = 0
    except Exception as e:
        logger.error(f"Error resetting seat map: {e}")
        results["seats_error"] = str(e)
        
    # 9. Delete PNRs
    try:
        res = supabase.table("pss_pnrs").delete().neq("pnr_id", "00000000-0000-0000-0000-000000000000").execute()
        results["pnrs_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting PNRs: {e}")
        results["pnrs_error"] = str(e)
        
    # 10. Reset flight inventory sold/blocked seats
    try:
        res_inv = supabase.table("pss_inventory").select("inventory_id, total_seats").or_("sold_seats.gt.0,blocked_seats.gt.0,waitlisted_seats.gt.0").execute()
        if res_inv.data:
            results["inventory_items_reset"] = len(res_inv.data)
            for item in res_inv.data:
                supabase.table("pss_inventory").update({
                    "available_seats": item["total_seats"],
                    "sold_seats": 0,
                    "blocked_seats": 0,
                    "waitlisted_seats": 0
                }).eq("inventory_id", item["inventory_id"]).execute()
        else:
            results["inventory_items_reset"] = 0
    except Exception as e:
        logger.error(f"Error resetting inventory: {e}")
        results["inventory_error"] = str(e)
        
    # 11. Delete Audit Log
    try:
        res = supabase.table("pss_audit_log").delete().neq("log_id", "00000000-0000-0000-0000-000000000000").execute()
        results["audit_logs_deleted"] = len(res.data) if res.data else 0
    except Exception as e:
        logger.error(f"Error deleting audit logs: {e}")
        results["audit_logs_error"] = str(e)
        
    return {"status": "success", "message": "Database booking data cleared.", "details": results}
