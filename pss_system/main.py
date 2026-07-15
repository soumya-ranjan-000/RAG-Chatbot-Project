import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pss-api")

app = FastAPI(title="Passenger Service System (PSS) Supabase API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BookRequest(BaseModel):
    passenger_id: str
    origin: str
    destination: str
    date: str
    status: str = "booked"
    booking_class: str = "Y"

class RescheduleRequest(BaseModel):
    new_date: str
    new_flight: str

class StatusRequest(BaseModel):
    status: str

class SeatSelectRequest(BaseModel):
    passenger_id: str
    seat_number: str

class PaymentRequest(BaseModel):
    amount: float
    payment_method: str
    idempotency_key: str

class TicketRequest(BaseModel):
    passenger_id: str

class BoardRequest(BaseModel):
    gate: str

class SSRRequest(BaseModel):
    passenger_id: str
    ssr_code: str
    remarks: str = ""

class AncillaryRequest(BaseModel):
    passenger_id: str
    ancillary_type: str
    amount: float

class UpgradeRequest(BaseModel):
    passenger_id: str
    required_miles: int

# --- Existing Endpoints ---

@app.get("/api/pss/passengers/{passenger_id}")
def read_passenger(passenger_id: str):
    profile = db.get_passenger_profile(passenger_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return profile

@app.get("/api/pss/bookings/{pnr}")
def read_booking(pnr: str):
    booking = db.get_booking(pnr)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking

@app.post("/api/pss/bookings")
def make_booking(req: BookRequest):
    try:
        return db.create_booking(req.passenger_id, req.origin, req.destination, req.date, req.status, req.booking_class)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/cancel")
def remove_booking(pnr: str):
    if db.cancel_booking(pnr):
        return {"status": "success", "message": f"Booking {pnr} successfully cancelled"}
    raise HTTPException(status_code=404, detail="Booking not found")

@app.post("/api/pss/bookings/{pnr}/reschedule")
def update_booking(pnr: str, req: RescheduleRequest):
    try:
        return db.reschedule_booking(pnr, req.new_date, req.new_flight)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/pss/flights")
def list_flights(origin: str = None, destination: str = None, date: str = None):
    return db.get_flights(origin, destination, date)

@app.post("/api/pss/bookings/{pnr}/status")
def update_booking_status(pnr: str, req: StatusRequest):
    try:
        return db.update_booking_status(pnr, req.status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/pss/bookings")
def list_bookings():
    return db.get_all_bookings()

# --- New Airline Lifecycle Endpoints ---

@app.get("/api/pss/flights/{flight_id}/seats")
def get_flight_seats(flight_id: str):
    return db.get_seat_map(flight_id)

@app.post("/api/pss/bookings/{pnr}/seat")
def select_booking_seat(pnr: str, req: SeatSelectRequest):
    try:
        return db.select_seat(pnr, req.passenger_id, req.seat_number)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/payment")
def pay_for_booking(pnr: str, req: PaymentRequest):
    try:
        return db.process_payment(pnr, req.amount, req.payment_method, req.idempotency_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/ticket")
def issue_booking_ticket(pnr: str, req: TicketRequest):
    try:
        return db.issue_ticket(pnr, req.passenger_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/checkin")
def check_in_booking(pnr: str):
    try:
        return db.check_in(pnr)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/board")
def board_booking_passenger(pnr: str, req: BoardRequest):
    try:
        return db.board_passenger(pnr, req.gate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/pss/passengers/{passenger_id}/loyalty")
def get_passenger_loyalty(passenger_id: str):
    return db.get_loyalty_info(passenger_id)

@app.post("/api/pss/bookings/{pnr}/ssr")
def add_booking_ssr(pnr: str, req: SSRRequest):
    try:
        return db.add_ssr(pnr, req.passenger_id, req.ssr_code, req.remarks)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/ancillary")
def add_booking_ancillary(pnr: str, req: AncillaryRequest):
    try:
        return db.add_ancillary(pnr, req.passenger_id, req.ancillary_type, req.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/pss/bookings/{pnr}/upgrade")
def upgrade_booking_with_miles(pnr: str, req: UpgradeRequest):
    try:
        return db.upgrade_with_miles(pnr, req.passenger_id, req.required_miles)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/pss/flights/{flight_id}/revenue")
def get_flight_revenue(flight_id: str):
    return db.get_revenue_summary(flight_id)

@app.get("/api/pss/flights/{flight_number}/status")
def get_flight_status_endpoint(flight_number: str, date: str = None):
    try:
        return db.get_flight_status(flight_number, date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
