-- PSS SCHEMA — PART 3: SEED DATA
-- Run AFTER Part 1 & Part 2

-- ============================================================
-- AIRLINES
-- ============================================================
INSERT INTO pss_airlines (iata_code, icao_code, name, country, hub_airport) VALUES
('AI', 'AIC', 'Air India',            'India',          'BLR'),
('BA', 'BAW', 'British Airways',       'United Kingdom', 'LHR'),
('EK', 'UAE', 'Emirates',             'UAE',            'DXB'),
('SQ', 'SIA', 'Singapore Airlines',   'Singapore',      'SIN'),
('AF', 'AFR', 'Air France',           'France',         'CDG'),
('AA', 'AAL', 'American Airlines',    'USA',            'JFK'),
('UA', 'UAL', 'United Airlines',      'USA',            'SFO'),
('DL', 'DAL', 'Delta Air Lines',      'USA',            'JFK'),
('VS', 'VIR', 'Virgin Atlantic',      'United Kingdom', 'LHR'),
('WN', 'SWA', 'Southwest Airlines',   'USA',            'LAX');

-- ============================================================
-- AIRPORTS
-- ============================================================
INSERT INTO pss_airports (iata_code, icao_code, name, city, country, timezone) VALUES
('BLR','VOBL','Kempegowda International',      'Bangalore',      'India',          'Asia/Kolkata'),
('JFK','KJFK','John F. Kennedy International', 'New York',       'USA',            'America/New_York'),
('LAX','KLAX','Los Angeles International',     'Los Angeles',    'USA',            'America/Los_Angeles'),
('SFO','KSFO','San Francisco International',   'San Francisco',  'USA',            'America/Los_Angeles'),
('LHR','EGLL','Heathrow Airport',              'London',         'United Kingdom', 'Europe/London'),
('CDG','LFPG','Charles de Gaulle Airport',     'Paris',          'France',         'Europe/Paris'),
('DXB','OMDB','Dubai International Airport',   'Dubai',          'UAE',            'Asia/Dubai'),
('SIN','WSSS','Changi Airport',                'Singapore',      'Singapore',      'Asia/Singapore');

-- ============================================================
-- AIRCRAFT TYPES
-- ============================================================
INSERT INTO pss_aircraft_types (iata_code, name, manufacturer, total_seats, first_class_seats, business_seats, premium_econ_seats, economy_seats) VALUES
('789','Boeing 787-9 Dreamliner','Boeing',  296, 0, 28, 21, 247),
('77W','Boeing 777-300ER',       'Boeing',  396, 8, 42,  0, 346),
('333','Airbus A330-300',        'Airbus',  277, 0, 36,  0, 241),
('320','Airbus A320',            'Airbus',  150, 0,  8,  0, 142),
('738','Boeing 737-800',         'Boeing',  162, 0,  0,  0, 162);

-- ============================================================
-- FARE FAMILIES (one Economy Light + Flex per airline)
-- ============================================================
INSERT INTO pss_fare_families (airline_id, name, cabin_class, refundable, changeable, change_fee_usd, cancellation_fee_usd, seat_selection, extra_baggage_kg, miles_accrual_pct, description)
SELECT a.airline_id, ff.name, ff.cabin_class, ff.refundable, ff.changeable, ff.change_fee_usd, ff.cancellation_fee_usd, ff.seat_selection, ff.extra_baggage_kg, ff.miles_accrual_pct, ff.description
FROM pss_airlines a
CROSS JOIN (VALUES
  ('Economy Light',  'economy', false, false, 100, 150, false, 0,  50, 'Non-refundable, no changes'),
  ('Economy Flex',   'economy', true,  true,   50,  75, true,  0, 100, 'Fully flexible economy'),
  ('Business Flex',  'business',true,  true,    0,   0, true, 32, 150, 'Full-service business class')
) AS ff(name, cabin_class, refundable, changeable, change_fee_usd, cancellation_fee_usd, seat_selection, extra_baggage_kg, miles_accrual_pct, description);

-- ============================================================
-- TAXES
-- ============================================================
INSERT INTO pss_taxes (tax_code, description, amount_usd, percentage, applies_to) VALUES
('YQ', 'Fuel Surcharge',              45.00, 0,    'all'),
('YR', 'Carrier Imposed Surcharge',   15.00, 0,    'all'),
('US', 'US Federal Excise Tax',        0.00, 7.5,  'domestic'),
('XF', 'US Passenger Facility Charge', 4.50, 0,    'domestic'),
('AY', 'US APHIS Fee',                 5.50, 0,    'international'),
('IN', 'India Departure Tax',         20.00, 0,    'international'),
('UB', 'UK Air Passenger Duty',       82.00, 0,    'international'),
('QX', 'Dubai Departure Tax',         14.00, 0,    'international');

-- ============================================================
-- PASSENGERS (migrated from mock db)
-- ============================================================
INSERT INTO pss_passengers (legacy_id, title, first_name, last_name, email, frequent_flyer_number, loyalty_tier, miles_balance, apis_status) VALUES
('usr_94f83b', 'MRS', 'Jane',  'Smith',  'jane.smith@example.com',  'FF773910', 'gold',   45200, 'verified'),
('usr_28a71c', 'MR',  'Alex',  'Mercer', 'alex.mercer@example.com', 'FF998822', 'silver', 18500, 'verified');

-- ============================================================
-- FLIGHT SCHEDULES & FLIGHTS (from mock db)
-- We use a helper to insert both schedule + a concrete flight instance
-- ============================================================
DO $$
DECLARE
    v_flight_id   UUID;
    v_sched_id    UUID;
    v_airline_id  UUID;
    v_orig_id     UUID;
    v_dest_id     UUID;
    v_acft_id     UUID;
    v_dep_dt      TIMESTAMPTZ;

    -- cursor over route data
    r RECORD;
BEGIN
    -- Select 789 as default aircraft
    SELECT aircraft_type_id INTO v_acft_id FROM pss_aircraft_types WHERE iata_code = '789' LIMIT 1;

    FOR r IN SELECT * FROM (VALUES
        ('AI', 'AI101', 'BLR','JFK', '08:30', 950),
        ('BA', 'BA118', 'BLR','LHR', '11:45', 750),
        ('EK', 'EK565', 'BLR','DXB', '10:25', 320),
        ('SQ', 'SQ503', 'BLR','SIN', '23:10', 410),
        ('AF', 'AF191', 'BLR','CDG', '02:00', 720),
        ('AA', 'AA103', 'BLR','LAX', '04:15',1100),
        ('AI', 'AI175', 'BLR','SFO', '14:30',1250),
        ('AI', 'AI102', 'JFK','BLR', '13:30', 980),
        ('UA', 'UA510', 'JFK','LAX', '07:00', 290),
        ('DL', 'DL415', 'JFK','SFO', '09:15', 310),
        ('BA', 'BA178', 'JFK','LHR', '18:00', 550),
        ('AF', 'AF015', 'JFK','CDG', '19:30', 620),
        ('EK', 'EK202', 'JFK','DXB', '23:00', 850),
        ('SQ', 'SQ021', 'JFK','SIN', '22:30',1400),
        ('UA', 'UA511', 'LAX','JFK', '11:30', 310),
        ('UA', 'UA240', 'LAX','SFO', '10:15', 120),
        ('DL', 'DL882', 'LAX','SFO', '17:45',  95),
        ('VS', 'VS024', 'LAX','LHR', '20:45', 800),
        ('AF', 'AF065', 'LAX','CDG', '15:30', 850),
        ('EK', 'EK216', 'LAX','DXB', '16:45',1050),
        ('SQ', 'SQ037', 'LAX','SIN', '23:55',1350),
        ('AI', 'AI176', 'LAX','BLR', '21:30',1150),
        ('UA', 'UA241', 'SFO','LAX', '08:00', 125),
        ('WN', 'WN941', 'SFO','LAX', '21:00',  80),
        ('DL', 'DL416', 'SFO','JFK', '12:15', 325),
        ('BA', 'BA286', 'SFO','LHR', '19:10', 820),
        ('AF', 'AF083', 'SFO','CDG', '15:00', 900),
        ('EK', 'EK226', 'SFO','DXB', '16:00',1100),
        ('SQ', 'SQ031', 'SFO','SIN', '13:30',1300),
        ('AI', 'AI178', 'SFO','BLR', '20:30',1200),
        ('BA', 'BA119', 'LHR','BLR', '14:20', 720),
        ('VS', 'VS003', 'LHR','JFK', '09:00', 580),
        ('BA', 'BA269', 'LHR','LAX', '15:00', 850),
        ('BA', 'BA306', 'LHR','CDG', '07:20', 130),
        ('EK', 'EK002', 'LHR','DXB', '14:15', 620),
        ('SQ', 'SQ317', 'LHR','SIN', '11:25',1100),
        ('AF', 'AF006', 'CDG','JFK', '13:30', 650),
        ('AF', 'AF066', 'CDG','LAX', '10:15', 880),
        ('EK', 'EK074', 'CDG','DXB', '15:35', 640),
        ('SQ', 'SQ335', 'CDG','SIN', '12:00',1150),
        ('AF', 'AF192', 'CDG','BLR', '10:30', 740),
        ('EK', 'EK564', 'DXB','BLR', '03:30', 340),
        ('EK', 'EK201', 'DXB','JFK', '08:30', 900),
        ('EK', 'EK215', 'DXB','LAX', '08:55',1150),
        ('EK', 'EK001', 'DXB','LHR', '07:45', 650),
        ('EK', 'EK073', 'DXB','CDG', '08:20', 680),
        ('EK', 'EK354', 'DXB','SIN', '09:15', 590),
        ('SQ', 'SQ502', 'SIN','BLR', '20:05', 430),
        ('SQ', 'SQ022', 'SIN','JFK', '00:35',1450),
        ('SQ', 'SQ038', 'SIN','LAX', '20:45',1300),
        ('SQ', 'SQ308', 'SIN','LHR', '09:00',1150),
        ('EK', 'EK355', 'SIN','DXB', '21:00', 580)
    ) AS t(al_code, fnum, orig_code, dest_code, dep_time, price)
    LOOP
        SELECT airline_id  INTO v_airline_id FROM pss_airlines  WHERE iata_code = r.al_code   LIMIT 1;
        SELECT airport_id  INTO v_orig_id    FROM pss_airports  WHERE iata_code = r.orig_code LIMIT 1;
        SELECT airport_id  INTO v_dest_id    FROM pss_airports  WHERE iata_code = r.dest_code LIMIT 1;

        -- Flight departure = today + 30 days at schedule time (UTC proxy)
        v_dep_dt := (CURRENT_DATE + 30 + r.dep_time::INTERVAL);

        -- Insert schedule
        INSERT INTO pss_flight_schedules
            (airline_id, flight_number, origin_airport_id, destination_airport_id, aircraft_type_id, departure_time, effective_from)
        VALUES (v_airline_id, r.fnum, v_orig_id, v_dest_id, v_acft_id, r.dep_time::TIME, CURRENT_DATE)
        ON CONFLICT (flight_number, origin_airport_id, departure_time) DO NOTHING
        RETURNING schedule_id INTO v_sched_id;

        IF v_sched_id IS NULL THEN
            SELECT schedule_id INTO v_sched_id FROM pss_flight_schedules
            WHERE flight_number = r.fnum AND origin_airport_id = v_orig_id
            LIMIT 1;
        END IF;

        -- Insert concrete flight instance
        INSERT INTO pss_flights
            (schedule_id, airline_id, flight_number, origin_airport_id, destination_airport_id, aircraft_type_id, departure_datetime, arrival_datetime, gate, status)
        VALUES
            (v_sched_id, v_airline_id, r.fnum, v_orig_id, v_dest_id, v_acft_id,
             v_dep_dt, v_dep_dt + INTERVAL '8 hours',
             'B' || (1 + (random()*20)::INT)::TEXT, 'scheduled')
        ON CONFLICT (flight_number, departure_datetime) DO NOTHING
        RETURNING flight_id INTO v_flight_id;

        IF v_flight_id IS NULL THEN
            SELECT flight_id INTO v_flight_id FROM pss_flights
            WHERE flight_number = r.fnum AND departure_datetime = v_dep_dt LIMIT 1;
        END IF;

        -- Economy Y class inventory (overbooking: 5 seats)
        INSERT INTO pss_inventory
            (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
        VALUES (v_flight_id, 'Y', 'economy', 140, 140, 5, 0)
        ON CONFLICT (flight_id, booking_class) DO NOTHING;

        -- Economy B class (discounted)
        INSERT INTO pss_inventory
            (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
        VALUES (v_flight_id, 'B', 'economy', 60, 60, 3, 0)
        ON CONFLICT (flight_id, booking_class) DO NOTHING;

        -- Business J class
        INSERT INTO pss_inventory
            (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
        VALUES (v_flight_id, 'J', 'business', 28, 28, 2, 0)
        ON CONFLICT (flight_id, booking_class) DO NOTHING;

        -- Insert fares for Y and J
        INSERT INTO pss_fares
            (fare_basis_code, airline_id, origin_airport_id, destination_airport_id, cabin_class, booking_class, base_fare_usd, valid_from)
        VALUES
            (r.fnum || 'Y', v_airline_id, v_orig_id, v_dest_id, 'economy',  'Y', r.price,           CURRENT_DATE),
            (r.fnum || 'B', v_airline_id, v_orig_id, v_dest_id, 'economy',  'B', r.price * 0.8,     CURRENT_DATE),
            (r.fnum || 'J', v_airline_id, v_orig_id, v_dest_id, 'business', 'J', r.price * 3.5,     CURRENT_DATE)
        ON CONFLICT (fare_basis_code, origin_airport_id, destination_airport_id, booking_class, airline_id) DO NOTHING;

        -- Generate economy seat map rows 10-39 (A-F)
        FOR row_n IN 10..39 LOOP
            INSERT INTO pss_seat_map (flight_id, seat_number, row_number, seat_letter, cabin_class, seat_type, seat_category, extra_charge_usd)
            VALUES
                (v_flight_id, row_n||'A', row_n, 'A', 'economy', 'window', CASE WHEN row_n IN (20,21) THEN 'exit_row' ELSE 'standard' END, CASE WHEN row_n IN (20,21) THEN 25 ELSE 0 END),
                (v_flight_id, row_n||'B', row_n, 'B', 'economy', 'middle', 'standard', 0),
                (v_flight_id, row_n||'C', row_n, 'C', 'economy', 'aisle',  'standard', 0),
                (v_flight_id, row_n||'D', row_n, 'D', 'economy', 'aisle',  'standard', 0),
                (v_flight_id, row_n||'E', row_n, 'E', 'economy', 'middle', 'standard', 0),
                (v_flight_id, row_n||'F', row_n, 'F', 'economy', 'window', CASE WHEN row_n IN (20,21) THEN 'exit_row' ELSE 'standard' END, CASE WHEN row_n IN (20,21) THEN 25 ELSE 0 END)
            ON CONFLICT (flight_id, seat_number) DO NOTHING;
        END LOOP;

        -- Business class rows 1-5 (A-D)
        FOR row_n IN 1..5 LOOP
            INSERT INTO pss_seat_map (flight_id, seat_number, row_number, seat_letter, cabin_class, seat_type, seat_category, extra_charge_usd)
            VALUES
                (v_flight_id, row_n||'A', row_n, 'A', 'business', 'window', 'preferred', 0),
                (v_flight_id, row_n||'B', row_n, 'B', 'business', 'aisle',  'preferred', 0),
                (v_flight_id, row_n||'C', row_n, 'C', 'business', 'aisle',  'preferred', 0),
                (v_flight_id, row_n||'D', row_n, 'D', 'business', 'window', 'preferred', 0)
            ON CONFLICT (flight_id, seat_number) DO NOTHING;
        END LOOP;

    END LOOP;
END $$;

-- ============================================================
-- SEED PNR123 (from mock db — Jane Smith, JFK→LAX)
-- ============================================================
DO $$
DECLARE
    v_pax_id      UUID;
    v_flight_id   UUID;
    v_fare_id     UUID;
    v_pnr_id      UUID;
    v_seg_id      UUID;
    v_seat_id     UUID;
    v_ticket_id   UUID;
    v_payment_id  UUID;
BEGIN
    SELECT passenger_id INTO v_pax_id FROM pss_passengers WHERE legacy_id = 'usr_94f83b';
    SELECT flight_id    INTO v_flight_id FROM pss_flights WHERE flight_number = 'UA510' LIMIT 1;
    SELECT fare_id      INTO v_fare_id FROM pss_fares
        WHERE fare_basis_code = 'UA510Y' OR fare_basis_code LIKE 'UA510%'
        LIMIT 1;

    INSERT INTO pss_pnrs (pnr_code, primary_passenger_id, status, channel, total_base_fare_usd, total_taxes_usd, total_amount_usd, expires_at)
    VALUES ('PNR123', v_pax_id, 'ticketed', 'web', 290.00, 65.00, 355.00, NOW() + INTERVAL '24 hours')
    ON CONFLICT (pnr_code) DO NOTHING
    RETURNING pnr_id INTO v_pnr_id;

    IF v_pnr_id IS NULL THEN
        SELECT pnr_id INTO v_pnr_id FROM pss_pnrs WHERE pnr_code = 'PNR123';
        RETURN;
    END IF;

    -- PNR passenger link
    INSERT INTO pss_pnr_passengers (pnr_id, passenger_id, is_primary, passenger_type)
    VALUES (v_pnr_id, v_pax_id, TRUE, 'ADT')
    ON CONFLICT DO NOTHING;

    -- Get seat 14B
    SELECT seat_id INTO v_seat_id FROM pss_seat_map
    WHERE flight_id = v_flight_id AND seat_number = '14B' LIMIT 1;

    -- Segment
    INSERT INTO pss_pnr_segments (pnr_id, flight_id, fare_id, segment_number, booking_class, cabin_class, seat_id, segment_status, base_fare_usd, taxes_usd, baggage_allowance_kg)
    VALUES (v_pnr_id, v_flight_id, v_fare_id, 1, 'Y', 'economy', v_seat_id, 'confirmed', 290.00, 65.00, 23)
    RETURNING segment_id INTO v_seg_id;

    -- Mark seat occupied
    UPDATE pss_seat_map SET is_occupied = TRUE, passenger_id = v_pax_id, pnr_id = v_pnr_id
    WHERE seat_id = v_seat_id;

    -- Decrement inventory
    UPDATE pss_inventory SET available_seats = available_seats - 1, sold_seats = sold_seats + 1
    WHERE flight_id = v_flight_id AND booking_class = 'Y';

    -- Payment (captured)
    INSERT INTO pss_payments (pnr_id, amount_usd, payment_method, idempotency_key, status, three_ds_status, card_last_four, card_brand, captured_at)
    VALUES (v_pnr_id, 355.00, 'card', 'seed-pnr123-pay-001', 'captured', 'authenticated', '4242', 'Visa', NOW())
    RETURNING payment_id INTO v_payment_id;

    -- Ticket
    INSERT INTO pss_tickets (pnr_id, passenger_id, ticket_number, issuing_airline_id, ticket_status, fare_basis_code, total_fare_usd, total_taxes_usd)
    SELECT v_pnr_id, v_pax_id, '0162345678901',
           (SELECT airline_id FROM pss_airlines WHERE iata_code = 'UA'),
           'open', 'UA510Y', 290.00, 65.00
    ON CONFLICT (ticket_number) DO NOTHING
    RETURNING ticket_id INTO v_ticket_id;

    -- Coupon
    IF v_ticket_id IS NOT NULL THEN
        INSERT INTO pss_coupons (ticket_id, segment_id, coupon_number, flight_number, origin_iata, destination_iata, booking_class, cabin_class, coupon_status)
        VALUES (v_ticket_id, v_seg_id, 1, 'UA510', 'JFK', 'LAX', 'Y', 'economy', 'open')
        ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- ============================================================
-- VERIFY (quick sanity check)
-- ============================================================
SELECT 'pss_airlines'       AS tbl, COUNT(*) FROM pss_airlines        UNION ALL
SELECT 'pss_airports',              COUNT(*) FROM pss_airports         UNION ALL
SELECT 'pss_flights',               COUNT(*) FROM pss_flights          UNION ALL
SELECT 'pss_inventory',             COUNT(*) FROM pss_inventory        UNION ALL
SELECT 'pss_seat_map',              COUNT(*) FROM pss_seat_map         UNION ALL
SELECT 'pss_passengers',            COUNT(*) FROM pss_passengers       UNION ALL
SELECT 'pss_pnrs',                  COUNT(*) FROM pss_pnrs             UNION ALL
SELECT 'pss_payments',              COUNT(*) FROM pss_payments         UNION ALL
SELECT 'pss_tickets',               COUNT(*) FROM pss_tickets          UNION ALL
SELECT 'pss_coupons',               COUNT(*) FROM pss_coupons;

-- PART 3 COMPLETE
