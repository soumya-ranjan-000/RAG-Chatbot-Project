-- PSS SCHEMA — PART 4: SEED INDIA FLIGHTS AND ROUTE EXPANSION
-- Run this in your Supabase SQL Editor (Project: mcrulyrkewmspkzawxcl)

-- ============================================================
-- 1. INSERT NEW AIRPORTS & AIRLINES
-- ============================================================
INSERT INTO pss_airports (iata_code, icao_code, name, city, country, timezone) VALUES
('DEL','VIDP','Indira Gandhi International', 'Delhi', 'India', 'Asia/Kolkata'),
('BOM','VABB','Chhatrapati Shivaji Maharaj International', 'Mumbai', 'India', 'Asia/Kolkata')
ON CONFLICT (iata_code) DO NOTHING;

INSERT INTO pss_airlines (iata_code, icao_code, name, country, hub_airport) VALUES
('6E', 'IGO', 'IndiGo', 'India', 'DEL')
ON CONFLICT (iata_code) DO NOTHING;

-- ============================================================
-- 2. GENERATE EXPANDED ROUTE SCHEDULES & CONCRETE FLIGHTS
-- ============================================================
DO $$
DECLARE
    v_acft_id     UUID;
    v_airline_id  UUID;
    v_orig_id     UUID;
    v_dest_id     UUID;
    v_sched_id    UUID;
    v_flight_id   UUID;
    v_dep_dt      TIMESTAMP;
    day_offset    INT;
    row_n         INT;
    r             RECORD;
BEGIN
    -- Select Boeing 787-9 as default aircraft
    SELECT aircraft_type_id INTO v_acft_id FROM pss_aircraft_types WHERE iata_code = '789' LIMIT 1;

    -- Create flight availability for a range of 15 days in the future (multiple availability)
    FOR day_offset IN 5..20 LOOP
        FOR r IN SELECT * FROM (VALUES
            -- DEL -> LHR (Delhi to London)
            ('AI', 'AI111', 'DEL','LHR', '08:30', 950),
            ('AI', 'AI115', 'DEL','LHR', '14:20', 920),
            ('VS', 'VS301', 'DEL','LHR', '13:15', 850),
            ('VS', 'VS303', 'DEL','LHR', '23:55', 880),
            ('BA', 'BA256', 'DEL','LHR', '11:00', 900),
            ('BA', 'BA142', 'DEL','LHR', '02:15', 870),

            -- BOM -> DXB (Mumbai to Dubai)
            ('EK', 'EK501', 'BOM','DXB', '04:30', 350),
            ('EK', 'EK503', 'BOM','DXB', '10:20', 360),
            ('EK', 'EK505', 'BOM','DXB', '16:15', 380),
            ('EK', 'EK509', 'BOM','DXB', '22:25', 390),
            ('6E', '6E1451', 'BOM','DXB', '22:00', 250),
            ('6E', '6E1453', 'BOM','DXB', '08:15', 240),
            ('AI', 'AI909', 'BOM','DXB', '18:40', 310),

            -- BLR -> SIN (Bangalore to Singapore)
            ('SQ', 'SQ511', 'BLR','SIN', '23:10', 410),
            ('SQ', 'SQ503', 'BLR','SIN', '10:25', 430),
            ('6E', '6E1007', 'BLR','SIN', '06:30', 290),
            ('AI', 'AI380', 'BLR','SIN', '15:45', 340),

            -- LHR -> DEL (Return - London to Delhi)
            ('AI', 'AI112', 'LHR','DEL', '21:30', 980),
            ('AI', 'AI116', 'LHR','DEL', '09:15', 940),
            ('VS', 'VS302', 'LHR','DEL', '10:20', 890),
            ('BA', 'BA257', 'LHR','DEL', '18:45', 920),

            -- DXB -> BOM (Return - Dubai to Mumbai)
            ('EK', 'EK502', 'DXB','BOM', '09:15', 360),
            ('EK', 'EK506', 'DXB','BOM', '21:30', 370),
            ('6E', '6E1452', 'DXB','BOM', '03:10', 270),
            ('AI', 'AI910', 'DXB','BOM', '12:45', 330),

            -- SIN -> BLR (Return - Singapore to Bangalore)
            ('SQ', 'SQ512', 'SIN','BLR', '20:00', 420),
            ('SQ', 'SQ504', 'SIN','BLR', '07:15', 440),
            ('6E', '6E1008', 'SIN','BLR', '14:20', 310)
        ) AS t(al_code, fnum, orig_code, dest_code, dep_time, price)
        LOOP
            -- Get foreign keys
            SELECT airline_id  INTO v_airline_id FROM pss_airlines  WHERE iata_code = r.al_code   LIMIT 1;
            SELECT airport_id  INTO v_orig_id    FROM pss_airports  WHERE iata_code = r.orig_code LIMIT 1;
            SELECT airport_id  INTO v_dest_id    FROM pss_airports  WHERE iata_code = r.dest_code LIMIT 1;

            -- Calculate departure datetime
            v_dep_dt := (CURRENT_DATE + day_offset + r.dep_time::INTERVAL);

            -- Insert schedules
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
                 'C' || (1 + (random()*20)::INT)::TEXT, 'scheduled')
            ON CONFLICT (flight_number, departure_datetime) DO NOTHING
            RETURNING flight_id INTO v_flight_id;

            IF v_flight_id IS NULL THEN
                SELECT flight_id INTO v_flight_id FROM pss_flights
                WHERE flight_number = r.fnum AND departure_datetime = v_dep_dt LIMIT 1;
            END IF;

            -- Economy Y class inventory (140 seats)
            INSERT INTO pss_inventory
                (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
            VALUES (v_flight_id, 'Y', 'economy', 140, 140, 5, 0)
            ON CONFLICT (flight_id, booking_class) DO NOTHING;

            -- Economy B class (60 seats)
            INSERT INTO pss_inventory
                (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
            VALUES (v_flight_id, 'B', 'economy', 60, 60, 3, 0)
            ON CONFLICT (flight_id, booking_class) DO NOTHING;

            -- Business J class (28 seats)
            INSERT INTO pss_inventory
                (flight_id, booking_class, cabin_class, total_seats, available_seats, oversell_limit, sold_seats)
            VALUES (v_flight_id, 'J', 'business', 28, 28, 2, 0)
            ON CONFLICT (flight_id, booking_class) DO NOTHING;

            -- Insert fares for Y, B and J
            INSERT INTO pss_fares
                (fare_basis_code, airline_id, origin_airport_id, destination_airport_id, cabin_class, booking_class, base_fare_usd, valid_from)
            VALUES
                (r.fnum || 'Y', v_airline_id, v_orig_id, v_dest_id, 'economy',  'Y', r.price,           CURRENT_DATE),
                (r.fnum || 'B', v_airline_id, v_orig_id, v_dest_id, 'economy',  'B', r.price * 0.8,     CURRENT_DATE),
                (r.fnum || 'J', v_airline_id, v_orig_id, v_dest_id, 'business', 'J', r.price * 3.5,     CURRENT_DATE)
            ON CONFLICT (fare_basis_code, origin_airport_id, destination_airport_id, booking_class, airline_id) DO NOTHING;

            -- Generate economy seat map rows 10..39
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

            -- Business class rows 1-5
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
    END LOOP;
END $$;
