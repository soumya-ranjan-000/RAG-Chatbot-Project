-- ============================================================
-- PSS SUPABASE SCHEMA — PART 1: TABLES & INDEXES
-- Run this FIRST in the Supabase SQL Editor
-- Project: Passenger Service System (PSS)
-- ============================================================

-- Drop tables in dependency order (safe re-run)
DROP TABLE IF EXISTS pss_audit_log        CASCADE;
DROP TABLE IF EXISTS pss_ancillaries      CASCADE;
DROP TABLE IF EXISTS pss_coupons          CASCADE;
DROP TABLE IF EXISTS pss_tickets          CASCADE;
DROP TABLE IF EXISTS pss_payments         CASCADE;
DROP TABLE IF EXISTS pss_ssrs             CASCADE;
DROP TABLE IF EXISTS pss_pnr_passengers   CASCADE;
DROP TABLE IF EXISTS pss_pnr_segments     CASCADE;
DROP TABLE IF EXISTS pss_seat_map         CASCADE;
DROP TABLE IF EXISTS pss_inventory        CASCADE;
DROP TABLE IF EXISTS pss_pnrs             CASCADE;
DROP TABLE IF EXISTS pss_fares            CASCADE;
DROP TABLE IF EXISTS pss_fare_families    CASCADE;
DROP TABLE IF EXISTS pss_taxes            CASCADE;
DROP TABLE IF EXISTS pss_flights          CASCADE;
DROP TABLE IF EXISTS pss_flight_schedules CASCADE;
DROP TABLE IF EXISTS pss_aircraft_types   CASCADE;
DROP TABLE IF EXISTS pss_passengers       CASCADE;
DROP TABLE IF EXISTS pss_airports         CASCADE;
DROP TABLE IF EXISTS pss_airlines         CASCADE;


-- ============================================================
-- 1. pss_airlines
-- ============================================================
CREATE TABLE pss_airlines (
    airline_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iata_code    CHAR(2)      NOT NULL UNIQUE,
    icao_code    CHAR(3),
    name         VARCHAR(100) NOT NULL,
    country      VARCHAR(100),
    hub_airport  CHAR(3),
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 2. pss_airports
-- ============================================================
CREATE TABLE pss_airports (
    airport_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iata_code   CHAR(3)      NOT NULL UNIQUE,
    icao_code   CHAR(4),
    name        VARCHAR(150) NOT NULL,
    city        VARCHAR(100),
    country     VARCHAR(100),
    timezone    VARCHAR(60),
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ============================================================
-- 3. pss_aircraft_types
-- ============================================================
CREATE TABLE pss_aircraft_types (
    aircraft_type_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    iata_code           CHAR(3)      NOT NULL UNIQUE,
    name                VARCHAR(100) NOT NULL,
    manufacturer        VARCHAR(100),
    total_seats         INT          NOT NULL,
    first_class_seats   INT          NOT NULL DEFAULT 0,
    business_seats      INT          NOT NULL DEFAULT 0,
    premium_econ_seats  INT          NOT NULL DEFAULT 0,
    economy_seats       INT          NOT NULL DEFAULT 0
);

-- ============================================================
-- 4. pss_passengers  (before flight_schedules; seats FK needs it)
-- ============================================================
CREATE TABLE pss_passengers (
    passenger_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    legacy_id             VARCHAR(50)  UNIQUE,   -- backward-compat with mock IDs
    title                 VARCHAR(10)  CHECK (title IN ('MR','MRS','MS','DR','PROF')),
    first_name            VARCHAR(100) NOT NULL,
    last_name             VARCHAR(100) NOT NULL,
    email                 VARCHAR(200) NOT NULL UNIQUE,
    phone                 VARCHAR(30),
    date_of_birth         DATE,
    gender                CHAR(1)      CHECK (gender IN ('M','F','X')),
    nationality           CHAR(2),
    passport_number       VARCHAR(20),
    passport_expiry       DATE,
    passport_country      CHAR(2),
    frequent_flyer_number VARCHAR(30),
    loyalty_tier          VARCHAR(20)  NOT NULL DEFAULT 'none'
                              CHECK (loyalty_tier IN ('none','silver','gold','platinum')),
    miles_balance         INT          NOT NULL DEFAULT 0,
    apis_status           VARCHAR(20)  NOT NULL DEFAULT 'pending'
                              CHECK (apis_status IN ('pending','verified','failed')),
    known_traveler_number VARCHAR(30),
    redress_number        VARCHAR(30),
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 5. pss_flight_schedules
-- ============================================================
CREATE TABLE pss_flight_schedules (
    schedule_id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    airline_id             UUID         NOT NULL REFERENCES pss_airlines(airline_id),
    flight_number          VARCHAR(10)  NOT NULL,
    origin_airport_id      UUID         NOT NULL REFERENCES pss_airports(airport_id),
    destination_airport_id UUID         NOT NULL REFERENCES pss_airports(airport_id),
    aircraft_type_id       UUID         REFERENCES pss_aircraft_types(aircraft_type_id),
    departure_time         TIME         NOT NULL,
    arrival_time           TIME,
    duration_minutes       INT,
    effective_from         DATE         NOT NULL DEFAULT CURRENT_DATE,
    effective_to           DATE,
    days_of_week           SMALLINT[]   DEFAULT '{1,2,3,4,5,6,7}',
    status                 VARCHAR(20)  NOT NULL DEFAULT 'active'
                               CHECK (status IN ('active','inactive','suspended')),
    oag_flight_id          VARCHAR(50),
    gds_flight_ref         VARCHAR(50),
    created_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (flight_number, origin_airport_id, departure_time)
);

-- ============================================================
-- 6. pss_fare_families
-- ============================================================
CREATE TABLE pss_fare_families (
    fare_family_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    airline_id              UUID        NOT NULL REFERENCES pss_airlines(airline_id),
    name                    VARCHAR(50) NOT NULL,
    cabin_class             VARCHAR(20) NOT NULL
                                CHECK (cabin_class IN ('economy','premium_economy','business','first')),
    refundable              BOOLEAN     NOT NULL DEFAULT FALSE,
    changeable              BOOLEAN     NOT NULL DEFAULT FALSE,
    change_fee_usd          NUMERIC(10,2) NOT NULL DEFAULT 0,
    cancellation_fee_usd    NUMERIC(10,2) NOT NULL DEFAULT 0,
    seat_selection          BOOLEAN     NOT NULL DEFAULT FALSE,
    lounge_access           BOOLEAN     NOT NULL DEFAULT FALSE,
    extra_baggage_kg        INT         NOT NULL DEFAULT 0,
    priority_boarding       BOOLEAN     NOT NULL DEFAULT FALSE,
    miles_accrual_pct       NUMERIC(5,2) NOT NULL DEFAULT 100,
    description             TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 7. pss_taxes
-- ============================================================
CREATE TABLE pss_taxes (
    tax_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tax_code       VARCHAR(10)   NOT NULL UNIQUE,
    description    VARCHAR(200),
    amount_usd     NUMERIC(10,2) NOT NULL DEFAULT 0,
    percentage     NUMERIC(5,2)  NOT NULL DEFAULT 0,
    applies_to     VARCHAR(20)   NOT NULL DEFAULT 'all'
                       CHECK (applies_to IN ('domestic','international','all')),
    origin_country VARCHAR(100),
    is_active      BOOLEAN       NOT NULL DEFAULT TRUE
);

-- ============================================================
-- 8. pss_fares
-- ============================================================
CREATE TABLE pss_fares (
    fare_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fare_basis_code        VARCHAR(20)   NOT NULL,
    fare_family_id         UUID          REFERENCES pss_fare_families(fare_family_id),
    airline_id             UUID          NOT NULL REFERENCES pss_airlines(airline_id),
    origin_airport_id      UUID          NOT NULL REFERENCES pss_airports(airport_id),
    destination_airport_id UUID          NOT NULL REFERENCES pss_airports(airport_id),
    cabin_class            VARCHAR(20)   NOT NULL
                               CHECK (cabin_class IN ('economy','premium_economy','business','first')),
    booking_class          CHAR(1)       NOT NULL,  -- RBD
    base_fare_usd          NUMERIC(10,2) NOT NULL,
    currency               CHAR(3)       NOT NULL DEFAULT 'USD',
    valid_from             DATE          NOT NULL DEFAULT CURRENT_DATE,
    valid_to               DATE,
    min_stay_days          INT           NOT NULL DEFAULT 0,
    max_stay_days          INT           NOT NULL DEFAULT 365,
    advance_purchase_days  INT           NOT NULL DEFAULT 0,
    saturday_night_stay    BOOLEAN       NOT NULL DEFAULT FALSE,
    is_round_trip          BOOLEAN       NOT NULL DEFAULT FALSE,
    atpco_fare_type        VARCHAR(20)   NOT NULL DEFAULT 'published'
                               CHECK (atpco_fare_type IN ('published','negotiated','private','net')),
    created_at             TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (fare_basis_code, origin_airport_id, destination_airport_id, booking_class, airline_id)
);

-- ============================================================
-- 9. pss_flights  (actual flight instances)
-- ============================================================
CREATE TABLE pss_flights (
    flight_id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id            UUID        REFERENCES pss_flight_schedules(schedule_id),
    airline_id             UUID        NOT NULL REFERENCES pss_airlines(airline_id),
    flight_number          VARCHAR(10) NOT NULL,
    origin_airport_id      UUID        NOT NULL REFERENCES pss_airports(airport_id),
    destination_airport_id UUID        NOT NULL REFERENCES pss_airports(airport_id),
    aircraft_type_id       UUID        REFERENCES pss_aircraft_types(aircraft_type_id),
    departure_datetime     TIMESTAMPTZ NOT NULL,
    arrival_datetime       TIMESTAMPTZ,
    actual_departure       TIMESTAMPTZ,
    actual_arrival         TIMESTAMPTZ,
    gate                   VARCHAR(10),
    terminal               VARCHAR(10),
    status                 VARCHAR(20) NOT NULL DEFAULT 'scheduled'
                               CHECK (status IN ('scheduled','boarding','departed','arrived',
                                                 'delayed','cancelled','diverted')),
    delay_minutes          INT         NOT NULL DEFAULT 0,
    is_codeshare           BOOLEAN     NOT NULL DEFAULT FALSE,
    operating_airline_id   UUID        REFERENCES pss_airlines(airline_id),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (flight_number, departure_datetime)
);

-- ============================================================
-- 10. pss_inventory
-- ============================================================
CREATE TABLE pss_inventory (
    inventory_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id        UUID    NOT NULL REFERENCES pss_flights(flight_id) ON DELETE CASCADE,
    booking_class    CHAR(1) NOT NULL,
    cabin_class      VARCHAR(20) NOT NULL
                         CHECK (cabin_class IN ('economy','premium_economy','business','first')),
    total_seats      INT     NOT NULL DEFAULT 0,
    available_seats  INT     NOT NULL DEFAULT 0,
    oversell_limit   INT     NOT NULL DEFAULT 0,
    sold_seats       INT     NOT NULL DEFAULT 0,
    blocked_seats    INT     NOT NULL DEFAULT 0,
    waitlisted_seats INT     NOT NULL DEFAULT 0,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (flight_id, booking_class),
    CONSTRAINT chk_available  CHECK (available_seats  >= 0),
    CONSTRAINT chk_oversell   CHECK (oversell_limit   >= 0),
    CONSTRAINT chk_sold       CHECK (sold_seats        >= 0)
);

-- ============================================================
-- 11. pss_pnrs
-- ============================================================
CREATE TABLE pss_pnrs (
    pnr_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_code             VARCHAR(10)   NOT NULL UNIQUE,
    primary_passenger_id UUID          NOT NULL REFERENCES pss_passengers(passenger_id),
    status               VARCHAR(20)   NOT NULL DEFAULT 'held'
                             CHECK (status IN ('held','confirmed','ticketed','checked_in',
                                               'boarded','flown','cancelled','refunded',
                                               'no_show','waitlisted')),
    channel              VARCHAR(20)   NOT NULL DEFAULT 'web'
                             CHECK (channel IN ('web','gds','mobile','airport','phone')),
    gds_pnr_ref          VARCHAR(20),
    airline_pnr_ref      VARCHAR(10),
    total_base_fare_usd  NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_taxes_usd      NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_amount_usd     NUMERIC(12,2) NOT NULL DEFAULT 0,
    currency             CHAR(3)       NOT NULL DEFAULT 'USD',
    agent_id             VARCHAR(50),
    remarks              TEXT,
    expires_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 12. pss_seat_map
-- ============================================================
CREATE TABLE pss_seat_map (
    seat_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    flight_id        UUID        NOT NULL REFERENCES pss_flights(flight_id) ON DELETE CASCADE,
    seat_number      VARCHAR(4)  NOT NULL,
    row_number       INT         NOT NULL,
    seat_letter      CHAR(1)     NOT NULL,
    cabin_class      VARCHAR(20) NOT NULL
                         CHECK (cabin_class IN ('economy','premium_economy','business','first')),
    seat_type        VARCHAR(10) NOT NULL
                         CHECK (seat_type IN ('window','middle','aisle')),
    seat_category    VARCHAR(20) NOT NULL DEFAULT 'standard'
                         CHECK (seat_category IN ('standard','preferred','exit_row','bassinet','bulkhead')),
    is_occupied      BOOLEAN     NOT NULL DEFAULT FALSE,
    is_blocked       BOOLEAN     NOT NULL DEFAULT FALSE,
    extra_charge_usd NUMERIC(10,2) NOT NULL DEFAULT 0,
    passenger_id     UUID        REFERENCES pss_passengers(passenger_id),
    pnr_id           UUID        REFERENCES pss_pnrs(pnr_id),
    UNIQUE (flight_id, seat_number)
);

-- ============================================================
-- 13. pss_pnr_segments
-- ============================================================
CREATE TABLE pss_pnr_segments (
    segment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id              UUID        NOT NULL REFERENCES pss_pnrs(pnr_id) ON DELETE CASCADE,
    flight_id           UUID        NOT NULL REFERENCES pss_flights(flight_id),
    fare_id             UUID        REFERENCES pss_fares(fare_id),
    segment_number      INT         NOT NULL DEFAULT 1,
    booking_class       CHAR(1)     NOT NULL,
    cabin_class         VARCHAR(20) NOT NULL,
    seat_id             UUID        REFERENCES pss_seat_map(seat_id),
    segment_status      VARCHAR(20) NOT NULL DEFAULT 'confirmed'
                            CHECK (segment_status IN ('confirmed','waitlisted','cancelled',
                                                      'flown','no_show','standby')),
    base_fare_usd       NUMERIC(10,2) NOT NULL DEFAULT 0,
    taxes_usd           NUMERIC(10,2) NOT NULL DEFAULT 0,
    baggage_allowance_kg INT         NOT NULL DEFAULT 23,
    is_married          BOOLEAN     NOT NULL DEFAULT FALSE,
    married_group_id    UUID,
    check_in_sequence   INT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 14. pss_pnr_passengers
-- ============================================================
CREATE TABLE pss_pnr_passengers (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id          UUID        NOT NULL REFERENCES pss_pnrs(pnr_id) ON DELETE CASCADE,
    passenger_id    UUID        NOT NULL REFERENCES pss_passengers(passenger_id),
    is_primary      BOOLEAN     NOT NULL DEFAULT FALSE,
    passenger_type  VARCHAR(5)  NOT NULL DEFAULT 'ADT'
                        CHECK (passenger_type IN ('ADT','CHD','INF','STU','SEN')),
    osi_remarks     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (pnr_id, passenger_id)
);

-- ============================================================
-- 15. pss_ssrs  (Special Service Requests)
-- ============================================================
CREATE TABLE pss_ssrs (
    ssr_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id       UUID        NOT NULL REFERENCES pss_pnrs(pnr_id) ON DELETE CASCADE,
    passenger_id UUID        NOT NULL REFERENCES pss_passengers(passenger_id),
    segment_id   UUID        REFERENCES pss_pnr_segments(segment_id),
    ssr_code     VARCHAR(4)  NOT NULL,  -- WCHR, VGML, UMNR, BLND, DEAF, MEDA…
    status       VARCHAR(20) NOT NULL DEFAULT 'requested'
                     CHECK (status IN ('requested','confirmed','cancelled','unable')),
    remarks      TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 16. pss_payments
-- ============================================================
CREATE TABLE pss_payments (
    payment_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id              UUID          NOT NULL REFERENCES pss_pnrs(pnr_id),
    amount_usd          NUMERIC(12,2) NOT NULL,
    currency            CHAR(3)       NOT NULL DEFAULT 'USD',
    payment_method      VARCHAR(20)   NOT NULL
                            CHECK (payment_method IN ('card','wallet','bank_transfer','voucher','miles')),
    card_last_four      CHAR(4),
    card_brand          VARCHAR(20),
    gateway_ref         VARCHAR(100),
    idempotency_key     VARCHAR(100)  NOT NULL UNIQUE,
    status              VARCHAR(30)   NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending','authorized','captured','failed',
                                              'refunded','partially_refunded','voided')),
    three_ds_status     VARCHAR(20)   NOT NULL DEFAULT 'not_required'
                            CHECK (three_ds_status IN ('not_required','initiated',
                                                       'authenticated','failed','bypassed')),
    failure_reason      TEXT,
    pci_token           VARCHAR(200),
    authorized_at       TIMESTAMPTZ,
    captured_at         TIMESTAMPTZ,
    refunded_at         TIMESTAMPTZ,
    refund_amount_usd   NUMERIC(12,2),
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 17. pss_tickets
-- ============================================================
CREATE TABLE pss_tickets (
    ticket_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id             UUID         NOT NULL REFERENCES pss_pnrs(pnr_id),
    passenger_id       UUID         NOT NULL REFERENCES pss_passengers(passenger_id),
    ticket_number      VARCHAR(14)  NOT NULL UNIQUE,   -- 3-digit airline prefix + 10 digits
    issue_date         DATE         NOT NULL DEFAULT CURRENT_DATE,
    issuing_airline_id UUID         REFERENCES pss_airlines(airline_id),
    issuing_office     VARCHAR(50),
    ticket_status      VARCHAR(20)  NOT NULL DEFAULT 'open'
                           CHECK (ticket_status IN ('open','used','refunded','voided',
                                                    'exchanged','suspended','expired')),
    fare_basis_code    VARCHAR(20),
    total_fare_usd     NUMERIC(12,2),
    total_taxes_usd    NUMERIC(12,2),
    endorsements       TEXT,
    bsp_submitted      BOOLEAN      NOT NULL DEFAULT FALSE,
    arc_submitted      BOOLEAN      NOT NULL DEFAULT FALSE,
    exchange_ticket_id UUID         REFERENCES pss_tickets(ticket_id),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 18. pss_coupons
-- ============================================================
CREATE TABLE pss_coupons (
    coupon_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id        UUID        NOT NULL REFERENCES pss_tickets(ticket_id) ON DELETE CASCADE,
    segment_id       UUID        REFERENCES pss_pnr_segments(segment_id),
    coupon_number    INT         NOT NULL CHECK (coupon_number BETWEEN 1 AND 4),
    flight_number    VARCHAR(10),
    origin_iata      CHAR(3),
    destination_iata CHAR(3),
    flight_date      DATE,
    booking_class    CHAR(1),
    cabin_class      VARCHAR(20),
    coupon_status    VARCHAR(20) NOT NULL DEFAULT 'open'
                         CHECK (coupon_status IN ('open','used','flown','voided',
                                                  'refunded','exchanged','suspended','lifted')),
    fare_basis       VARCHAR(20),
    not_valid_before DATE,
    not_valid_after  DATE,
    baggage_allowance VARCHAR(20),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ticket_id, coupon_number)
);

-- ============================================================
-- 19. pss_ancillaries
-- ============================================================
CREATE TABLE pss_ancillaries (
    ancillary_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pnr_id         UUID          NOT NULL REFERENCES pss_pnrs(pnr_id),
    passenger_id   UUID          REFERENCES pss_passengers(passenger_id),
    segment_id     UUID          REFERENCES pss_pnr_segments(segment_id),
    ancillary_type VARCHAR(30)   NOT NULL
                       CHECK (ancillary_type IN ('seat','meal','extra_baggage','lounge_access',
                                                  'priority_boarding','fast_track','upgrade',
                                                  'pet','sports_equipment','insurance')),
    description    VARCHAR(200),
    ssr_code       VARCHAR(4),
    amount_usd     NUMERIC(10,2) NOT NULL DEFAULT 0,
    status         VARCHAR(20)   NOT NULL DEFAULT 'requested'
                       CHECK (status IN ('requested','confirmed','cancelled','refunded')),
    payment_id     UUID          REFERENCES pss_payments(payment_id),
    created_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- ============================================================
-- 20. pss_audit_log
-- ============================================================
CREATE TABLE pss_audit_log (
    log_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name     VARCHAR(100) NOT NULL,
    record_id      TEXT         NOT NULL,
    action         VARCHAR(10)  NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
    old_data       JSONB,
    new_data       JSONB,
    changed_fields TEXT[],
    performed_by   VARCHAR(100) NOT NULL DEFAULT 'system',
    ip_address     INET,
    session_id     VARCHAR(100),
    performed_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_flights_departure    ON pss_flights(departure_datetime);
CREATE INDEX idx_flights_origin       ON pss_flights(origin_airport_id);
CREATE INDEX idx_flights_destination  ON pss_flights(destination_airport_id);
CREATE INDEX idx_flights_status       ON pss_flights(status);
CREATE INDEX idx_flights_number       ON pss_flights(flight_number);

CREATE INDEX idx_inventory_flight     ON pss_inventory(flight_id);
CREATE INDEX idx_inventory_class      ON pss_inventory(booking_class);

CREATE INDEX idx_pnrs_code            ON pss_pnrs(pnr_code);
CREATE INDEX idx_pnrs_passenger       ON pss_pnrs(primary_passenger_id);
CREATE INDEX idx_pnrs_status          ON pss_pnrs(status);

CREATE INDEX idx_passengers_email     ON pss_passengers(email);
CREATE INDEX idx_passengers_ffn       ON pss_passengers(frequent_flyer_number);
CREATE INDEX idx_passengers_passport  ON pss_passengers(passport_number);
CREATE INDEX idx_passengers_legacy    ON pss_passengers(legacy_id);

CREATE INDEX idx_segments_pnr         ON pss_pnr_segments(pnr_id);
CREATE INDEX idx_segments_flight      ON pss_pnr_segments(flight_id);
CREATE INDEX idx_segments_married     ON pss_pnr_segments(married_group_id);

CREATE INDEX idx_payments_pnr         ON pss_payments(pnr_id);
CREATE INDEX idx_payments_status      ON pss_payments(status);
CREATE INDEX idx_payments_idempotency ON pss_payments(idempotency_key);

CREATE INDEX idx_tickets_pnr          ON pss_tickets(pnr_id);
CREATE INDEX idx_tickets_passenger    ON pss_tickets(passenger_id);
CREATE INDEX idx_coupons_ticket       ON pss_coupons(ticket_id);

CREATE INDEX idx_ssrs_pnr             ON pss_ssrs(pnr_id);
CREATE INDEX idx_seat_map_flight      ON pss_seat_map(flight_id);
CREATE INDEX idx_seat_map_occupied    ON pss_seat_map(flight_id, is_occupied);

CREATE INDEX idx_audit_table          ON pss_audit_log(table_name, performed_at);
CREATE INDEX idx_audit_record         ON pss_audit_log(record_id);

-- ============================================================
-- TRIGGER: auto-update updated_at on pss_passengers
-- ============================================================
CREATE OR REPLACE FUNCTION pss_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_passengers_updated_at
    BEFORE UPDATE ON pss_passengers
    FOR EACH ROW EXECUTE FUNCTION pss_set_updated_at();

CREATE TRIGGER trg_pnrs_updated_at
    BEFORE UPDATE ON pss_pnrs
    FOR EACH ROW EXECUTE FUNCTION pss_set_updated_at();

-- ============================================================
-- PART 1 COMPLETE — Run Part 2 (views) next
-- ============================================================
