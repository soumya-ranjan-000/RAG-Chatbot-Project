-- ============================================================
-- PSS SUPABASE SCHEMA — PART 2: VIEWS
-- Run AFTER Part 1 (tables) in the Supabase SQL Editor
-- ============================================================

-- Drop existing views (safe re-run)
DROP VIEW IF EXISTS vw_revenue_summary      CASCADE;
DROP VIEW IF EXISTS vw_seat_availability    CASCADE;
DROP VIEW IF EXISTS vw_passenger_itinerary  CASCADE;
DROP VIEW IF EXISTS vw_pnr_detail           CASCADE;
DROP VIEW IF EXISTS vw_flight_availability  CASCADE;

-- ============================================================
-- VIEW 1: vw_flight_availability
-- Used for flight search — joins flights, inventory, fares
-- ============================================================
CREATE OR REPLACE VIEW vw_flight_availability AS
SELECT
    f.flight_id,
    f.flight_number,
    al.iata_code                    AS airline_code,
    al.name                         AS airline_name,
    orig.iata_code                  AS origin,
    orig.city                       AS origin_city,
    orig.country                    AS origin_country,
    dest.iata_code                  AS destination,
    dest.city                       AS destination_city,
    dest.country                    AS destination_country,
    f.departure_datetime,
    f.arrival_datetime,
    EXTRACT(EPOCH FROM (f.arrival_datetime - f.departure_datetime))/60
                                    AS duration_minutes,
    f.status                        AS flight_status,
    f.gate,
    f.terminal,
    f.delay_minutes,
    at2.name                        AS aircraft_type,
    at2.iata_code                   AS aircraft_iata,
    i.booking_class,
    i.cabin_class,
    i.available_seats,
    i.total_seats,
    i.sold_seats,
    i.oversell_limit,
    (i.available_seats + i.oversell_limit)
                                    AS sellable_seats,
    fa.fare_id,
    fa.base_fare_usd,
    fa.fare_basis_code,
    fa.currency,
    ff.name                         AS fare_family,
    ff.refundable,
    ff.changeable,
    ff.extra_baggage_kg,
    ff.seat_selection,
    ff.lounge_access
FROM pss_flights f
JOIN pss_airlines      al   ON f.airline_id             = al.airline_id
JOIN pss_airports      orig ON f.origin_airport_id      = orig.airport_id
JOIN pss_airports      dest ON f.destination_airport_id = dest.airport_id
LEFT JOIN pss_aircraft_types at2 ON f.aircraft_type_id  = at2.aircraft_type_id
LEFT JOIN pss_inventory      i   ON f.flight_id          = i.flight_id
LEFT JOIN pss_fares          fa  ON (
    fa.origin_airport_id      = f.origin_airport_id      AND
    fa.destination_airport_id = f.destination_airport_id AND
    fa.booking_class          = i.booking_class           AND
    fa.airline_id             = f.airline_id
)
LEFT JOIN pss_fare_families  ff  ON fa.fare_family_id   = ff.fare_family_id
WHERE f.status NOT IN ('cancelled');

-- ============================================================
-- VIEW 2: vw_pnr_detail
-- Full PNR view — used by booking agent and API
-- ============================================================
CREATE OR REPLACE VIEW vw_pnr_detail AS
SELECT
    -- PNR
    p.pnr_id,
    p.pnr_code,
    p.status                        AS pnr_status,
    p.channel,
    p.total_base_fare_usd,
    p.total_taxes_usd,
    p.total_amount_usd,
    p.currency,
    p.gds_pnr_ref,
    p.airline_pnr_ref,
    p.remarks,
    p.expires_at,
    p.created_at                    AS pnr_created_at,
    -- Primary passenger
    pas.passenger_id,
    pas.legacy_id,
    pas.first_name,
    pas.last_name,
    pas.email,
    pas.phone,
    pas.frequent_flyer_number,
    pas.loyalty_tier,
    pas.miles_balance,
    pas.passport_number,
    pas.passport_expiry,
    -- Segment
    seg.segment_id,
    seg.segment_number,
    seg.booking_class,
    seg.cabin_class,
    seg.segment_status,
    seg.base_fare_usd               AS seg_base_fare,
    seg.taxes_usd                   AS seg_taxes,
    seg.baggage_allowance_kg,
    seg.is_married,
    seg.married_group_id,
    -- Flight
    f.flight_id,
    f.flight_number,
    al.iata_code                    AS airline_code,
    al.name                         AS airline_name,
    orig.iata_code                  AS origin,
    orig.city                       AS origin_city,
    dest.iata_code                  AS destination,
    dest.city                       AS destination_city,
    f.departure_datetime,
    f.arrival_datetime,
    f.gate,
    f.terminal,
    f.status                        AS flight_status,
    f.delay_minutes,
    -- Seat
    sm.seat_id,
    sm.seat_number,
    sm.seat_type,
    sm.seat_category,
    sm.extra_charge_usd             AS seat_charge,
    -- Payment
    pay.payment_id,
    pay.status                      AS payment_status,
    pay.amount_usd                  AS paid_amount,
    pay.payment_method,
    pay.captured_at,
    -- Ticket
    t.ticket_id,
    t.ticket_number,
    t.ticket_status,
    t.issue_date                    AS ticket_issue_date
FROM pss_pnrs p
JOIN pss_passengers    pas  ON p.primary_passenger_id   = pas.passenger_id
LEFT JOIN pss_pnr_segments seg  ON p.pnr_id             = seg.pnr_id
LEFT JOIN pss_flights       f   ON seg.flight_id         = f.flight_id
LEFT JOIN pss_airlines      al  ON f.airline_id          = al.airline_id
LEFT JOIN pss_airports      orig ON f.origin_airport_id  = orig.airport_id
LEFT JOIN pss_airports      dest ON f.destination_airport_id = dest.airport_id
LEFT JOIN pss_seat_map      sm  ON seg.seat_id           = sm.seat_id
LEFT JOIN pss_payments      pay ON p.pnr_id              = pay.pnr_id
                                AND pay.status            = 'captured'
LEFT JOIN pss_tickets       t   ON p.pnr_id              = t.pnr_id
                                AND pas.passenger_id      = t.passenger_id;

-- ============================================================
-- VIEW 3: vw_passenger_itinerary
-- Passenger-facing itinerary summary (clean, minimal)
-- ============================================================
CREATE OR REPLACE VIEW vw_passenger_itinerary AS
SELECT
    pas.passenger_id,
    pas.legacy_id,
    pas.first_name || ' ' || pas.last_name   AS passenger_name,
    pas.email,
    pas.frequent_flyer_number,
    pas.loyalty_tier,
    p.pnr_code,
    p.pnr_id,
    p.status                                 AS booking_status,
    p.total_amount_usd,
    p.created_at                             AS booked_at,
    f.flight_number,
    al.name                                  AS airline,
    orig.iata_code                           AS from_airport,
    orig.city                                AS from_city,
    dest.iata_code                           AS to_airport,
    dest.city                                AS to_city,
    f.departure_datetime,
    f.arrival_datetime,
    seg.cabin_class,
    seg.booking_class,
    seg.baggage_allowance_kg,
    sm.seat_number,
    f.gate,
    f.terminal,
    f.status                                 AS flight_status,
    t.ticket_number,
    t.ticket_status,
    pay.status                               AS payment_status,
    pay.amount_usd                           AS amount_paid
FROM pss_passengers     pas
JOIN pss_pnrs           p   ON pas.passenger_id          = p.primary_passenger_id
LEFT JOIN pss_pnr_segments seg ON p.pnr_id               = seg.pnr_id
LEFT JOIN pss_flights    f   ON seg.flight_id             = f.flight_id
LEFT JOIN pss_airlines   al  ON f.airline_id              = al.airline_id
LEFT JOIN pss_airports   orig ON f.origin_airport_id     = orig.airport_id
LEFT JOIN pss_airports   dest ON f.destination_airport_id= dest.airport_id
LEFT JOIN pss_seat_map   sm  ON seg.seat_id               = sm.seat_id
LEFT JOIN pss_tickets    t   ON p.pnr_id                  = t.pnr_id
                             AND pas.passenger_id         = t.passenger_id
LEFT JOIN pss_payments   pay ON p.pnr_id                  = pay.pnr_id
                             AND pay.status                = 'captured'
ORDER BY p.created_at DESC;

-- ============================================================
-- VIEW 4: vw_seat_availability
-- Seat map with availability, charges, occupancy
-- ============================================================
CREATE OR REPLACE VIEW vw_seat_availability AS
SELECT
    sm.seat_id,
    sm.flight_id,
    f.flight_number,
    orig.iata_code                           AS origin,
    dest.iata_code                           AS destination,
    f.departure_datetime,
    sm.seat_number,
    sm.row_number,
    sm.seat_letter,
    sm.cabin_class,
    sm.seat_type,
    sm.seat_category,
    sm.is_occupied,
    sm.is_blocked,
    sm.extra_charge_usd,
    CASE
        WHEN sm.is_occupied OR sm.is_blocked THEN FALSE
        ELSE TRUE
    END                                      AS is_available,
    CASE
        WHEN sm.seat_category = 'exit_row'   THEN 'Exit Row — must be able-bodied'
        WHEN sm.seat_category = 'bassinet'   THEN 'Bassinet — for infants only'
        WHEN sm.seat_category = 'bulkhead'   THEN 'Bulkhead — extra legroom'
        WHEN sm.seat_category = 'preferred'  THEN 'Preferred — extra legroom'
        ELSE NULL
    END                                      AS restriction_note
FROM pss_seat_map sm
JOIN pss_flights  f    ON sm.flight_id             = f.flight_id
JOIN pss_airports orig ON f.origin_airport_id      = orig.airport_id
JOIN pss_airports dest ON f.destination_airport_id = dest.airport_id;

-- ============================================================
-- VIEW 5: vw_revenue_summary
-- Flight-level revenue and yield metrics for accounting
-- ============================================================
CREATE OR REPLACE VIEW vw_revenue_summary AS
SELECT
    f.flight_id,
    f.flight_number,
    f.departure_datetime,
    al.name                                            AS airline,
    orig.iata_code                                     AS origin,
    dest.iata_code                                     AS destination,
    at2.total_seats                                    AS aircraft_capacity,
    COUNT(DISTINCT seg.segment_id)                     AS booked_segments,
    COALESCE(SUM(seg.base_fare_usd), 0)               AS total_base_revenue,
    COALESCE(SUM(seg.taxes_usd), 0)                   AS total_tax_revenue,
    COALESCE(SUM(seg.base_fare_usd + seg.taxes_usd), 0) AS total_revenue,
    CASE WHEN at2.total_seats > 0
         THEN ROUND(COUNT(DISTINCT seg.segment_id) * 100.0 / at2.total_seats, 2)
         ELSE 0
    END                                                AS load_factor_pct,
    CASE WHEN COUNT(DISTINCT seg.segment_id) > 0
         THEN ROUND(SUM(seg.base_fare_usd) / COUNT(DISTINCT seg.segment_id), 2)
         ELSE 0
    END                                                AS avg_fare_usd,
    COUNT(DISTINCT pay.payment_id)                     AS payments_captured,
    COALESCE(SUM(pay.amount_usd), 0)                  AS total_collected_usd,
    COUNT(DISTINCT anc.ancillary_id)                   AS ancillary_count,
    COALESCE(SUM(anc.amount_usd), 0)                  AS ancillary_revenue
FROM pss_flights         f
JOIN pss_airlines        al   ON f.airline_id             = al.airline_id
JOIN pss_airports        orig ON f.origin_airport_id      = orig.airport_id
JOIN pss_airports        dest ON f.destination_airport_id = dest.airport_id
LEFT JOIN pss_aircraft_types at2 ON f.aircraft_type_id    = at2.aircraft_type_id
LEFT JOIN pss_pnr_segments   seg ON f.flight_id           = seg.flight_id
                                 AND seg.segment_status NOT IN ('cancelled','no_show')
LEFT JOIN pss_pnrs           pnr ON seg.pnr_id            = pnr.pnr_id
LEFT JOIN pss_payments       pay ON pnr.pnr_id            = pay.pnr_id
                                 AND pay.status           = 'captured'
LEFT JOIN pss_ancillaries    anc ON pnr.pnr_id            = anc.pnr_id
                                 AND anc.status           = 'confirmed'
GROUP BY
    f.flight_id, f.flight_number, f.departure_datetime,
    al.name, orig.iata_code, dest.iata_code, at2.total_seats;

-- ============================================================
-- PART 2 COMPLETE — Run Part 3 (seed data) next
-- ============================================================
