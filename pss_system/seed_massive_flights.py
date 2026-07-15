import os
import sys
import uuid
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed-massive-flights")

# Load environment
parent_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(parent_dir, '.env')
if os.path.exists(env_path):
    load_dotenv(env_path, override=True)
else:
    load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY.")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def seed_airports():
    airports = [
        {"iata_code": "DEL", "icao_code": "VIDP", "name": "Indira Gandhi International", "city": "Delhi", "country": "India", "timezone": "Asia/Kolkata"},
        {"iata_code": "BOM", "icao_code": "VABB", "name": "Chhatrapati Shivaji Maharaj International", "city": "Mumbai", "country": "India", "timezone": "Asia/Kolkata"},
        {"iata_code": "BLR", "icao_code": "VOBL", "name": "Kempegowda International", "city": "Bangalore", "country": "India", "timezone": "Asia/Kolkata"},
        {"iata_code": "MAA", "icao_code": "VOMM", "name": "Chennai International", "city": "Chennai", "country": "India", "timezone": "Asia/Kolkata"},
        {"iata_code": "CCU", "icao_code": "VECC", "name": "Netaji Subhash Chandra Bose International", "city": "Kolkata", "country": "India", "timezone": "Asia/Kolkata"},
        {"iata_code": "DXB", "icao_code": "OMDB", "name": "Dubai International", "city": "Dubai", "country": "UAE", "timezone": "Asia/Dubai"},
        {"iata_code": "AUH", "icao_code": "OMAA", "name": "Abu Dhabi International", "city": "Abu Dhabi", "country": "UAE", "timezone": "Asia/Abu Dhabi"},
        {"iata_code": "LHR", "icao_code": "EGLL", "name": "London Heathrow", "city": "London", "country": "United Kingdom", "timezone": "Europe/London"},
        {"iata_code": "SIN", "icao_code": "WSSS", "name": "Singapore Changi", "city": "Singapore", "country": "Singapore", "timezone": "Asia/Singapore"},
        {"iata_code": "JFK", "icao_code": "KJFK", "name": "John F. Kennedy International", "city": "New York", "country": "United States", "timezone": "America/New_York"}
    ]
    
    mapping = {}
    for ap in airports:
        res = supabase.table("pss_airports").select("airport_id").eq("iata_code", ap["iata_code"]).execute()
        if res.data:
            mapping[ap["iata_code"]] = res.data[0]["airport_id"]
        else:
            insert_res = supabase.table("pss_airports").insert(ap).execute()
            if insert_res.data:
                mapping[ap["iata_code"]] = insert_res.data[0]["airport_id"]
                logger.info(f"Inserted airport {ap['iata_code']}")
    return mapping

def seed_airlines():
    airlines = [
        {"iata_code": "AI", "icao_code": "AIC", "name": "Air India", "country": "India", "hub_airport": "DEL"},
        {"iata_code": "6E", "icao_code": "IGO", "name": "IndiGo", "country": "India", "hub_airport": "DEL"},
        {"iata_code": "UK", "icao_code": "VTI", "name": "Vistara", "country": "India", "hub_airport": "DEL"},
        {"iata_code": "EK", "icao_code": "UAE", "name": "Emirates", "country": "UAE", "hub_airport": "DXB"},
        {"iata_code": "EY", "icao_code": "ETD", "name": "Etihad Airways", "country": "UAE", "hub_airport": "AUH"},
        {"iata_code": "SQ", "icao_code": "SIA", "name": "Singapore Airlines", "country": "Singapore", "hub_airport": "SIN"},
        {"iata_code": "BA", "icao_code": "BAW", "name": "British Airways", "country": "United Kingdom", "hub_airport": "LHR"},
        {"iata_code": "VS", "icao_code": "VIR", "name": "Virgin Atlantic", "country": "United Kingdom", "hub_airport": "LHR"}
    ]
    
    mapping = {}
    for al in airlines:
        res = supabase.table("pss_airlines").select("airline_id").eq("iata_code", al["iata_code"]).execute()
        if res.data:
            mapping[al["iata_code"]] = res.data[0]["airline_id"]
        else:
            insert_res = supabase.table("pss_airlines").insert(al).execute()
            if insert_res.data:
                mapping[al["iata_code"]] = insert_res.data[0]["airline_id"]
                logger.info(f"Inserted airline {al['iata_code']}")
    return mapping

def seed_flights(airports, airlines):
    # Get Boeing 787-9 aircraft type ID
    res_ac = supabase.table("pss_aircraft_types").select("aircraft_type_id").eq("iata_code", "789").execute()
    acft_id = res_ac.data[0]["aircraft_type_id"] if res_ac.data else None
    
    # 12 Bidirectional Routes with 5 flights per day each
    routes = [
        # Domestic India
        {"orig": "DEL", "dest": "BOM", "flights": [
            {"al": "AI", "num": "AI805", "time": "07:00", "price": 90},
            {"al": "6E", "num": "6E2015", "time": "10:30", "price": 75},
            {"al": "AI", "num": "AI807", "time": "13:00", "price": 85},
            {"al": "6E", "num": "6E2021", "time": "16:45", "price": 80},
            {"al": "UK", "num": "UK953", "time": "19:30", "price": 95}
        ]},
        {"orig": "BOM", "dest": "DEL", "flights": [
            {"al": "AI", "num": "AI806", "time": "08:15", "price": 90},
            {"al": "6E", "num": "6E2016", "time": "11:45", "price": 75},
            {"al": "AI", "num": "AI808", "time": "14:15", "price": 85},
            {"al": "6E", "num": "6E2022", "time": "18:00", "price": 80},
            {"al": "UK", "num": "UK954", "time": "20:45", "price": 95}
        ]},
        {"orig": "DEL", "dest": "BLR", "flights": [
            {"al": "6E", "num": "6E5031", "time": "06:15", "price": 110},
            {"al": "AI", "num": "AI505", "time": "09:30", "price": 120},
            {"al": "6E", "num": "6E5035", "time": "12:15", "price": 105},
            {"al": "UK", "num": "UK815", "time": "15:45", "price": 130},
            {"al": "AI", "num": "AI507", "time": "18:30", "price": 125}
        ]},
        {"orig": "BLR", "dest": "DEL", "flights": [
            {"al": "6E", "num": "6E5032", "time": "07:30", "price": 110},
            {"al": "AI", "num": "AI506", "time": "10:45", "price": 120},
            {"al": "6E", "num": "6E5036", "time": "13:30", "price": 105},
            {"al": "UK", "num": "UK816", "time": "17:00", "price": 130},
            {"al": "AI", "num": "AI508", "time": "19:45", "price": 125}
        ]},
        {"orig": "BOM", "dest": "BLR", "flights": [
            {"al": "6E", "num": "6E3401", "time": "07:45", "price": 65},
            {"al": "AI", "num": "AI609", "time": "11:00", "price": 70},
            {"al": "UK", "num": "UK851", "time": "14:30", "price": 80},
            {"al": "6E", "num": "6E3405", "time": "17:15", "price": 60},
            {"al": "AI", "num": "AI611", "time": "20:30", "price": 75}
        ]},
        {"orig": "BLR", "dest": "BOM", "flights": [
            {"al": "6E", "num": "6E3402", "time": "09:00", "price": 65},
            {"al": "AI", "num": "AI610", "time": "12:15", "price": 70},
            {"al": "UK", "num": "UK852", "time": "15:45", "price": 80},
            {"al": "6E", "num": "6E3406", "time": "18:30", "price": 60},
            {"al": "AI", "num": "AI612", "time": "21:45", "price": 75}
        ]},
        
        # India to Dubai (UAE)
        {"orig": "DEL", "dest": "DXB", "flights": [
            {"al": "EK", "num": "EK511", "time": "10:30", "price": 280},
            {"al": "6E", "num": "6E23", "time": "07:15", "price": 190},
            {"al": "AI", "num": "AI991", "time": "14:45", "price": 230},
            {"al": "EK", "num": "EK513", "time": "18:20", "price": 290},
            {"al": "6E", "num": "6E25", "time": "21:55", "price": 180}
        ]},
        {"orig": "DXB", "dest": "DEL", "flights": [
            {"al": "EK", "num": "EK512", "time": "04:55", "price": 290},
            {"al": "6E", "num": "6E24", "time": "11:45", "price": 200},
            {"al": "AI", "num": "AI992", "time": "18:15", "price": 240},
            {"al": "EK", "num": "EK514", "time": "22:00", "price": 310},
            {"al": "6E", "num": "6E26", "time": "01:30", "price": 190}
        ]},
        {"orig": "BOM", "dest": "DXB", "flights": [
            {"al": "EK", "num": "EK501", "time": "04:30", "price": 270},
            {"al": "EK", "num": "EK503", "time": "10:20", "price": 280},
            {"al": "6E", "num": "6E95", "time": "16:15", "price": 185},
            {"al": "AI", "num": "AI909", "time": "18:40", "price": 220},
            {"al": "EK", "num": "EK505", "time": "22:25", "price": 290}
        ]},
        {"orig": "DXB", "dest": "BOM", "flights": [
            {"al": "EK", "num": "EK502", "time": "09:15", "price": 280},
            {"al": "EK", "num": "EK504", "time": "15:00", "price": 290},
            {"al": "6E", "num": "6E96", "time": "21:10", "price": 195},
            {"al": "AI", "num": "AI910", "time": "23:45", "price": 230},
            {"al": "EK", "num": "EK506", "time": "03:10", "price": 300}
        ]},
        {"orig": "BLR", "dest": "DXB", "flights": [
            {"al": "EK", "num": "EK565", "time": "10:25", "price": 310},
            {"al": "6E", "num": "6E97", "time": "07:00", "price": 210},
            {"al": "AI", "num": "AI951", "time": "14:15", "price": 250},
            {"al": "EK", "num": "EK567", "time": "20:30", "price": 320},
            {"al": "6E", "num": "6E99", "time": "23:45", "price": 195}
        ]},
        {"orig": "DXB", "dest": "BLR", "flights": [
            {"al": "EK", "num": "EK564", "time": "03:15", "price": 320},
            {"al": "6E", "num": "6E98", "time": "11:30", "price": 220},
            {"al": "AI", "num": "AI952", "time": "18:45", "price": 260},
            {"al": "EK", "num": "EK566", "time": "21:00", "price": 330},
            {"al": "6E", "num": "6E100", "time": "02:15", "price": 205}
        ]}
    ]
    
    # Range of 30 days starting from today
    start_date = datetime.now()
    total_inserted = 0
    
    for day_offset in range(0, 31):
        target_date = start_date + timedelta(days=day_offset)
        date_str = target_date.strftime("%Y-%m-%d")
        logger.info(f"Seeding flights for date: {date_str}")
        
        for route in routes:
            o_id = airports[route["orig"]]
            d_id = airports[route["dest"]]
            
            for f in route["flights"]:
                airline_id = airlines[f["al"]]
                dep_datetime = f"{date_str}T{f['time']}:00+00:00"
                
                try:
                    # Check if flight already exists
                    check_f = supabase.table("pss_flights")\
                        .select("flight_id")\
                        .eq("flight_number", f["num"])\
                        .eq("departure_datetime", dep_datetime)\
                        .execute()
                    
                    if check_f.data:
                        f_id = check_f.data[0]["flight_id"]
                    else:
                        # Insert concrete flight
                        ins_f = supabase.table("pss_flights").insert({
                            "airline_id": airline_id,
                            "flight_number": f["num"],
                            "origin_airport_id": o_id,
                            "destination_airport_id": d_id,
                            "aircraft_type_id": acft_id,
                            "departure_datetime": dep_datetime,
                            "arrival_datetime": f"{date_str}T{(datetime.strptime(f['time'], '%H:%M') + timedelta(hours=3)).strftime('%H:%M')}:00+00:00",
                            "status": "scheduled"
                        }).execute()
                        
                        if ins_f.data:
                            f_id = ins_f.data[0]["flight_id"]
                            total_inserted += 1
                        else:
                            continue
                    
                    # Seed Inventories (Y, B, J)
                    for b_class, cab_class, seats in [('Y', 'economy', 140), ('B', 'economy', 60), ('J', 'business', 28)]:
                        try:
                            supabase.table("pss_inventory").insert({
                                "flight_id": f_id,
                                "booking_class": b_class,
                                "cabin_class": cab_class,
                                "total_seats": seats,
                                "available_seats": seats,
                                "oversell_limit": 5 if b_class == 'Y' else 2,
                                "sold_seats": 0
                            }).execute()
                        except Exception as e:
                            # Ignore duplicate inventory
                            pass
                    
                    # Seed Fares
                    for b_class, cab_class, multiplier in [('Y', 'economy', 1.0), ('B', 'economy', 0.8), ('J', 'business', 3.5)]:
                        try:
                            supabase.table("pss_fares").insert({
                                "fare_basis_code": f"{f['num']}{b_class}",
                                "airline_id": airline_id,
                                "origin_airport_id": o_id,
                                "destination_airport_id": d_id,
                                "cabin_class": cab_class,
                                "booking_class": b_class,
                                "base_fare_usd": f["price"] * multiplier,
                                "valid_from": date_str
                            }).execute()
                        except Exception as e:
                            # Ignore duplicate fares
                            pass
                except Exception as e:
                    logger.warning(f"Error seeding flight {f['num']} on {date_str}: {e}")
                    continue
                    
    logger.info(f"Successfully seeded {total_inserted} flight records across 30 days!")

def main():
    logger.info("Starting massive flight seeding...")
    airports = seed_airports()
    airlines = seed_airlines()
    seed_flights(airports, airlines)
    logger.info("Done!")

if __name__ == "__main__":
    main()
