import logging

try:
    from .db_supabase import (
        get_passenger_profile,
        get_booking,
        create_booking,
        cancel_booking,
        reschedule_booking,
        get_flights,
        update_booking_status,
        get_all_bookings,
        select_seat,
        process_payment,
        issue_ticket,
        check_in,
        board_passenger,
        get_seat_map,
        add_ssr,
        get_loyalty_info,
        add_ancillary,
        get_revenue_summary
    )
except ImportError:
    from db_supabase import (
        get_passenger_profile,
        get_booking,
        create_booking,
        cancel_booking,
        reschedule_booking,
        get_flights,
        update_booking_status,
        get_all_bookings,
        select_seat,
        process_payment,
        issue_ticket,
        check_in,
        board_passenger,
        get_seat_map,
        add_ssr,
        get_loyalty_info,
        add_ancillary,
        get_revenue_summary
    )

logger = logging.getLogger("pss-db-shim")
logger.info("Initializing db.py shim pointing to db_supabase.py")
