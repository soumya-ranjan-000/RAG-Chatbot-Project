import React, { useState, useEffect } from "react";
import { 
  Card, Form, Input, Button, Select, Table, Tag, 
  DatePicker, Modal, message, Space, Typography, Steps, Alert, Row, Col, Badge
} from "antd";
import { 
  SearchOutlined, CreditCardOutlined, CheckCircleOutlined, 
  ArrowRightOutlined, ToolOutlined, UserOutlined, MailOutlined, NumberOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import { PSS_API_URL } from "../services/api";

const { Title, Text, Paragraph } = Typography;

interface BookingPortalProps {
  currentUser: {
    username: string;
    role: "admin" | "passenger";
    passengerProfile?: {
      passenger_id: string;
      name: string;
      email: string;
      frequent_flyer_number: string;
    };
  };
  onBookingCreated: (booking: any) => void;
}

export const BookingPortal: React.FC<BookingPortalProps> = ({ currentUser, onBookingCreated }) => {
  const [flights, setFlights] = useState<any[]>([]);
  const [loadingFlights, setLoadingFlights] = useState(false);
  
  // Booking Wizard states
  const [bookingModalVisible, setBookingModalVisible] = useState(false);
  const [selectedFlight, setSelectedFlight] = useState<any>(null);
  const [bookingDate, setBookingDate] = useState<string>("");
  const [currentStep, setCurrentStep] = useState(0);
  const [paymentLoading, setPaymentLoading] = useState(false);
  const [paymentResult, setPaymentResult] = useState<{ status: "success" | "error"; msg: string } | null>(null);

  // New Passenger details states
  const [passengerName, setPassengerName] = useState<string>("");
  const [passengerEmail, setPassengerEmail] = useState<string>("");
  const [frequentFlyer, setFrequentFlyer] = useState<string>("");

  // New Seat Selection states
  const [seatMap, setSeatMap] = useState<any[]>([]);
  const [loadingSeats, setLoadingSeats] = useState(false);
  const [selectedSeat, setSelectedSeat] = useState<string>("");

  // Search state
  const [hasSearched, setHasSearched] = useState(false);

  // Admin simulation states
  const [allBookings, setAllBookings] = useState<any[]>([]);
  const [loadingBookings, setLoadingBookings] = useState(false);
  const [adminNameFilter, setAdminNameFilter] = useState<string>("");

  // Fetch flights
  const fetchFlights = async (origin = "", destination = "") => {
    setLoadingFlights(true);
    try {
      const url = new URL(`${PSS_API_URL}/flights`);
      if (origin) url.searchParams.append("origin", origin);
      if (destination) url.searchParams.append("destination", destination);
      
      const res = await fetch(url.toString());
      if (res.ok) {
        const data = await res.json();
        setFlights(data);
      } else {
        message.error("Failed to load flights from PSS API");
      }
    } catch (e) {
      console.error(e);
      message.error("Network error connecting to PSS System");
    } finally {
      setLoadingFlights(false);
    }
  };

  // Fetch all bookings for admin operations
  const fetchAllBookings = async () => {
    if (currentUser.role !== "admin") return;
    setLoadingBookings(true);
    try {
      const res = await fetch(`${PSS_API_URL}/bookings`);
      if (res.ok) {
        const data = await res.json();
        setAllBookings(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoadingBookings(false);
    }
  };

  useEffect(() => {
    fetchAllBookings();
  }, [currentUser]);

  const handleSearch = (values: any) => {
    if (!values.origin && !values.destination) {
      message.warning("Please select at least an origin or destination to search flights.");
      return;
    }
    setHasSearched(true);
    fetchFlights(values.origin || "", values.destination || "");
  };

  // Fetch seat map for the selected flight
  const fetchFlightSeats = async (flightNum: string) => {
    setLoadingSeats(true);
    try {
      const res = await fetch(`${PSS_API_URL}/flights/${flightNum}/seats`);
      if (res.ok) {
        const data = await res.json();
        setSeatMap(data);
      } else {
        message.error("Failed to load seats for the flight.");
      }
    } catch (e) {
      console.error(e);
      message.error("Network error loading seat layout.");
    } finally {
      setLoadingSeats(false);
    }
  };

  const startBooking = (flight: any) => {
    setSelectedFlight(flight);
    setBookingDate(dayjs().add(7, "day").format("YYYY-MM-DD"));
    
    // Pre-fill passenger details with current session
    setPassengerName(currentUser.passengerProfile?.name || "System Admin");
    setPassengerEmail(currentUser.passengerProfile?.email || currentUser.username);
    setFrequentFlyer(currentUser.passengerProfile?.frequent_flyer_number || "FF_ADMIN");
    setSelectedSeat("");
    setSeatMap([]);
    
    setCurrentStep(0);
    setPaymentResult(null);
    setBookingModalVisible(true);
  };

  // Advance from Step 0 to Step 1 (Configure -> Seat Selection)
  const proceedToSeatSelection = () => {
    if (!passengerName || !passengerEmail) {
      message.warning("Please enter passenger name and email.");
      return;
    }
    fetchFlightSeats(selectedFlight.flight_number);
    setCurrentStep(1);
  };

  const handleMockPayment = (values: any) => {
    const { cardNumber } = values;
    setPaymentLoading(true);
    setPaymentResult(null);

    // Simulation delays and outcomes based on card number patterns
    setTimeout(async () => {
      // 1. Mastercard: Timeout rule
      if (cardNumber.startsWith("5100")) {
        setPaymentLoading(false);
        setPaymentResult({
          status: "error",
          msg: "Transaction Timeout: PSS payment gateway did not respond within 15 seconds. Please try again."
        });
        message.error("Payment timeout simulated.");
        return;
      }

      // 2. Amex: Insufficient Balance rule
      if (cardNumber.startsWith("3700")) {
        setPaymentLoading(false);
        setPaymentResult({
          status: "error",
          msg: "Payment Failed: Insufficient balance on account to clear the transaction ($" + selectedFlight.price + ")."
        });
        message.error("Payment failed: Insufficient balance.");
        return;
      }

      // 3. Discover: General decline
      if (cardNumber.startsWith("6011")) {
        setPaymentLoading(false);
        setPaymentResult({
          status: "error",
          msg: "Payment Declined: Transaction rejected by card issuing bank. (Response Code: 05 - DO NOT HONOR)"
        });
        message.error("Payment declined by bank.");
        return;
      }

      // 4. Visa / Fallback: Success rule
      try {
        const passenger_id = currentUser.passengerProfile?.passenger_id || "usr_94f83b";
        
        // 1. Create booking
        const res = await fetch(`${PSS_API_URL}/bookings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            passenger_id,
            origin: selectedFlight.origin,
            destination: selectedFlight.destination,
            date: bookingDate
          })
        });

        if (res.ok) {
          let bookingData = await res.json();
          
          // 2. Apply Custom Seat if selected
          if (selectedSeat) {
            try {
              const seatRes = await fetch(`${PSS_API_URL}/bookings/${bookingData.pnr}/seat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  passenger_id,
                  seat_number: selectedSeat
                })
              });
              if (seatRes.ok) {
                // Update bookingData local properties
                bookingData.seat = selectedSeat;
              }
            } catch (seatErr) {
              console.error("Failed to save chosen seat", seatErr);
            }
          }

          setPaymentLoading(false);
          setPaymentResult({
            status: "success",
            msg: `Ticketing Successful! Booking PNR: ${bookingData.pnr} generated and seat ${bookingData.seat || 'TBD'} allocated.`
          });
          onBookingCreated(bookingData);
          message.success("Flight booked successfully!");
          fetchAllBookings();
          setCurrentStep(3); // Go to final confirmation screen
        } else {
          const err = await res.json();
          setPaymentLoading(false);
          setPaymentResult({ status: "error", msg: err.detail || "Failed to create booking in PSS database" });
        }
      } catch (e) {
        setPaymentLoading(false);
        setPaymentResult({ status: "error", msg: "Failed to connect to passenger database server." });
      }
    }, 1500);
  };

  // Admin controls
  const handleUpdateStatus = async (pnr: string, status: string) => {
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${pnr}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status })
      });

      if (res.ok) {
        message.success(`Status updated to '${status}' successfully!`);
        fetchAllBookings();
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to update booking status");
      }
    } catch (e) {
      message.error("Failed to connect to API server");
    }
  };

  const handleCancelBooking = async (pnr: string) => {
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${pnr}/cancel`, {
        method: "POST"
      });

      if (res.ok) {
        message.success(`Booking ${pnr} successfully cancelled.`);
        fetchAllBookings();
      } else {
        message.error("Failed to cancel booking");
      }
    } catch (e) {
      message.error("Failed to connect to API server");
    }
  };

  const getStatusTag = (status: string) => {
    const s = status?.toLowerCase();
    switch (s) {
      case "booked": return <Tag color="blue">BOOKED</Tag>;
      case "checked-in": return <Tag color="purple">CHECKED IN</Tag>;
      case "boarding-pass-generated": return <Tag color="cyan">PASS ISSUED</Tag>;
      case "departed": return <Tag color="warning">DEPARTED</Tag>;
      case "landed":
      case "completed": return <Tag color="green">LANDED</Tag>;
      case "cancelled": return <Tag color="red">CANCELLED</Tag>;
      default: return <Tag color="default">{status?.toUpperCase()}</Tag>;
    }
  };

  // Build the seat grid visualizer
  const renderSeatGrid = () => {
    if (seatMap.length === 0) return <div>No seats layout available for this flight.</div>;

    const rowsMap: { [key: number]: any[] } = {};
    seatMap.forEach(seat => {
      const r = seat.row_number;
      if (!rowsMap[r]) rowsMap[r] = [];
      rowsMap[r].push(seat);
    });

    const sortedRows = Object.keys(rowsMap).map(Number).sort((a, b) => a - b);

    return (
      <div style={{ maxHeight: "300px", overflowY: "auto", padding: "16px", background: "var(--code-bg)", borderRadius: "8px", border: "1px solid var(--border)" }}>
        <Space style={{ marginBottom: "12px", display: "flex", justifyContent: "center" }} size="middle">
          <Badge status="success" text="Available" />
          <Badge status="processing" text="Business" />
          <Badge status="default" text="Occupied / Blocked" />
          <Badge color="gold" text="Your Selection" />
        </Space>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px", alignItems: "center" }}>
          {sortedRows.map(rowNum => {
            const rowSeats = rowsMap[rowNum].sort((a, b) => a.seat_letter.localeCompare(b.seat_letter));
            const isBusiness = rowSeats[0]?.cabin_class === "business";

            return (
              <div key={rowNum} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ width: "24px", fontWeight: "bold", textAlign: "right", fontSize: "11px" }}>{rowNum}</span>
                {rowSeats.map((seat, index) => {
                  const isSelected = selectedSeat === seat.seat_number;
                  const isOccupied = seat.is_occupied || seat.is_blocked;
                  
                  const addAisle = isBusiness ? index === 2 : index === 3;

                  let bgColor = "#1890ff"; 
                  if (isBusiness) bgColor = "#722ed1"; 
                  if (isOccupied) bgColor = "#d9d9d9"; 
                  if (isSelected) bgColor = "#faad14"; 

                  return (
                    <React.Fragment key={seat.seat_number}>
                      {addAisle && <div style={{ width: "16px" }} />}
                      <button
                        type="button"
                        onClick={() => !isOccupied && setSelectedSeat(seat.seat_number)}
                        disabled={isOccupied}
                        style={{
                          width: "28px",
                          height: "28px",
                          borderRadius: "4px",
                          border: isSelected ? "2px solid #d4b106" : "none",
                          background: bgColor,
                          color: isOccupied ? "#8c8c8c" : "#fff",
                          fontWeight: "bold",
                          cursor: isOccupied ? "not-allowed" : "pointer",
                          transition: "all 0.2s",
                          fontSize: "10px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                      >
                        {seat.seat_letter}
                      </button>
                    </React.Fragment>
                  );
                })}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  const flightColumns = [
    {
      title: "Airline",
      dataIndex: "airline",
      key: "airline",
      render: (text: string) => <span style={{ fontWeight: 500, color: "#262626" }}>{text || "Mock Airline"}</span>
    },
    {
      title: "Flight No",
      dataIndex: "flight_number",
      key: "flight_number",
      render: (text: string) => <code style={{ fontWeight: "bold", color: "#1890ff" }}>{text}</code>
    },
    {
      title: "Route",
      key: "route",
      render: (record: any) => (
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span>{record.origin}</span>
          <ArrowRightOutlined style={{ fontSize: "11px", color: "#8c8c8c" }} />
          <span>{record.destination}</span>
        </div>
      )
    },
    {
      title: "Date",
      dataIndex: "date",
      key: "date",
    },
    {
      title: "Dep Time",
      dataIndex: "departure_time",
      key: "departure_time",
    },
    {
      title: "Price",
      dataIndex: "price",
      key: "price",
      render: (val: number) => <strong style={{ color: "#3f8600" }}>${val}</strong>
    },
    {
      title: "Action",
      key: "action",
      render: (record: any) => (
        <Button 
          type="primary" 
          size="small" 
          onClick={() => startBooking(record)}
          style={{ background: "#1890ff", border: "none" }}
        >
          Book Now
        </Button>
      )
    }
  ];

  // Filter bookings for admin panel by name
  const filteredBookings = allBookings.filter(b => 
    !adminNameFilter || 
    (b.passenger_name || "").toLowerCase().includes(adminNameFilter.toLowerCase())
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. Passenger Search & Booking panel */}
      <Card
        title="✈️ Search & Book Scheduled Flights"
        style={{ borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
      >
        <Form layout="inline" onFinish={handleSearch} style={{ marginBottom: "20px" }}>
          <Form.Item name="origin" label="Origin">
            <Select style={{ width: 150 }} placeholder="Any" allowClear>
              <Select.Option value="BLR">BLR (Bangalore)</Select.Option>
              <Select.Option value="DEL">DEL (Delhi)</Select.Option>
              <Select.Option value="BOM">BOM (Mumbai)</Select.Option>
              <Select.Option value="JFK">JFK (New York)</Select.Option>
              <Select.Option value="LAX">LAX (Los Angeles)</Select.Option>
              <Select.Option value="SFO">SFO (San Francisco)</Select.Option>
              <Select.Option value="LHR">LHR (London)</Select.Option>
              <Select.Option value="CDG">CDG (Paris)</Select.Option>
              <Select.Option value="DXB">DXB (Dubai)</Select.Option>
              <Select.Option value="SIN">SIN (Singapore)</Select.Option>
            </Select>
          </Form.Item>
          
          <Form.Item name="destination" label="Destination">
            <Select style={{ width: 150 }} placeholder="Any" allowClear>
              <Select.Option value="BLR">BLR (Bangalore)</Select.Option>
              <Select.Option value="DEL">DEL (Delhi)</Select.Option>
              <Select.Option value="BOM">BOM (Mumbai)</Select.Option>
              <Select.Option value="JFK">JFK (New York)</Select.Option>
              <Select.Option value="LAX">LAX (Los Angeles)</Select.Option>
              <Select.Option value="SFO">SFO (San Francisco)</Select.Option>
              <Select.Option value="LHR">LHR (London)</Select.Option>
              <Select.Option value="CDG">CDG (Paris)</Select.Option>
              <Select.Option value="DXB">DXB (Dubai)</Select.Option>
              <Select.Option value="SIN">SIN (Singapore)</Select.Option>
            </Select>
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" icon={<SearchOutlined />} style={{ background: "#0050b3", border: "none" }}>
              Search
            </Button>
          </Form.Item>
        </Form>

        {hasSearched ? (
          <Table 
            columns={flightColumns} 
            dataSource={flights} 
            rowKey={(r) => `${r.flight_number}-${r.date}`} 
            loading={loadingFlights}
            pagination={false}
            size="small"
          />
        ) : (
          <Alert
            message="Search for Available Flights"
            description="Please select an origin and destination airport above, and click 'Search' to fetch and display the available flight connections."
            type="info"
            showIcon
            style={{ borderRadius: "8px" }}
          />
        )}
      </Card>

      {/* 2. Admin Flight Operations Simulator */}
      {currentUser.role === "admin" && (
        <Card
          title={
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <ToolOutlined style={{ color: "#fa8c16" }} />
              <span>⚙️ PSS Flight Operations & Passenger Simulation Control Panel</span>
            </div>
          }
          style={{ 
            borderRadius: "12px", 
            border: "1px solid #ffe7ba", 
            background: "#fffbe6",
            boxShadow: "0 4px 12px rgba(0,0,0,0.05)" 
          }}
          extra={
            <Button size="small" onClick={fetchAllBookings} type="dashed">
              Refresh Bookings
            </Button>
          }
        >
          <div style={{ display: "flex", gap: "16px", marginBottom: "16px", alignItems: "center" }}>
            <span style={{ fontWeight: "bold" }}>Filter Bookings by Passenger Name:</span>
            <Input 
              placeholder="Search passenger name..." 
              value={adminNameFilter} 
              onChange={(e) => setAdminNameFilter(e.target.value)} 
              style={{ width: "250px" }}
              allowClear
            />
          </div>

          <Table
            dataSource={filteredBookings}
            loading={loadingBookings}
            rowKey="pnr"
            size="small"
            style={{ background: "#fff" }}
            scroll={{ x: 'max-content', y: 400 }}
            columns={[
              {
                title: "PNR",
                dataIndex: "pnr",
                key: "pnr",
                render: (val: string) => <code style={{ fontWeight: "bold", background: "var(--code-bg)", padding: "2px 4px", borderRadius: "3px" }}>{val}</code>
              },
              {
                title: "Passenger Name",
                dataIndex: "passenger_name",
                key: "passenger_name",
              },
              {
                title: "Flight / Route",
                key: "flight_route",
                render: (record: any) => (
                  <div>
                    <code>{record.flight_number}</code>
                    <div style={{ fontSize: "11px", color: "#8c8c8c" }}>{record.origin} → {record.destination} ({record.date})</div>
                  </div>
                )
              },
              {
                title: "Status",
                dataIndex: "status",
                key: "status",
                render: (status: string) => getStatusTag(status)
              },
              {
                title: "Simulation Controls (Fast API calls)",
                key: "ops",
                render: (record: any) => {
                  const s = record.status?.toLowerCase();
                  const isCancelled = s === "cancelled";
                  const pastCheckIn = ["checked-in", "boarding-pass-generated", "departed", "completed", "landed"].includes(s);
                  const pastBoarding = ["boarding-pass-generated", "departed", "completed", "landed"].includes(s);
                  const pastDeparted = ["departed", "completed", "landed"].includes(s);
                  const pastLanded = ["completed", "landed"].includes(s);
                  
                  return (
                    <Space size={4} wrap>
                      <Button 
                        size="small" 
                        disabled={isCancelled || pastCheckIn}
                        onClick={() => handleUpdateStatus(record.pnr, "checked-in")}
                      >
                        ✔ Check In
                      </Button>
                      <Button 
                        size="small" 
                        type="dashed"
                        disabled={isCancelled || pastBoarding}
                        onClick={() => handleUpdateStatus(record.pnr, "boarding-pass-generated")}
                      >
                        🎟 Issue Pass
                      </Button>
                      <Button 
                        size="small" 
                        disabled={isCancelled || pastDeparted}
                        style={{ color: pastDeparted || isCancelled ? undefined : "#fa8c16", borderColor: pastDeparted || isCancelled ? undefined : "#ffe7ba" }}
                        onClick={() => handleUpdateStatus(record.pnr, "departed")}
                      >
                        🛫 Depart
                      </Button>
                      <Button 
                        size="small" 
                        type="primary"
                        disabled={isCancelled || pastLanded}
                        style={{ background: pastLanded || isCancelled ? undefined : "#3f8600", borderColor: pastLanded || isCancelled ? undefined : "#3f8600" }}
                        onClick={() => handleUpdateStatus(record.pnr, "completed")}
                      >
                        🛬 Land Flight
                      </Button>
                      <Button 
                        size="small" 
                        danger 
                        disabled={isCancelled}
                        onClick={() => handleCancelBooking(record.pnr)}
                      >
                        Cancel
                      </Button>
                    </Space>
                  );
                }
              }
            ]}
          />
        </Card>
      )}

      {/* 3. Booking Wizard Modal (Search -> Select Seat -> Pay -> Confirm) */}
      <Modal
        title="Airline Ticketing Wizard"
        open={bookingModalVisible}
        onCancel={() => !paymentLoading && setBookingModalVisible(false)}
        footer={null}
        width={550}
        destroyOnClose
      >
        <Steps 
          current={currentStep} 
          style={{ marginBottom: "24px" }} 
          size="small"
          items={[
            { title: "Configure" },
            { title: "Seat Selection" },
            { title: "Payment" },
            { title: "Confirm" }
          ]}
        />

        {/* Step 0: Configure Flight & Passenger details */}
        {currentStep === 0 && selectedFlight && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Card style={{ background: "#fafafa" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <Title level={5} style={{ margin: 0 }}>
                    {selectedFlight.origin} <ArrowRightOutlined style={{ fontSize: "12px" }} /> {selectedFlight.destination}
                  </Title>
                  <Text type="secondary" style={{ fontSize: "12px" }}>Flight No: {selectedFlight.flight_number} | Airline: {selectedFlight.airline}</Text>
                </div>
                <div style={{ textAlign: "right" }}>
                  <Title level={4} style={{ margin: 0, color: "#3f8600" }}>${selectedFlight.price}</Title>
                  <Text type="secondary" style={{ fontSize: "11px" }}>Date: {selectedFlight.date} ({selectedFlight.departure_time})</Text>
                </div>
              </div>
            </Card>

            <Form layout="vertical">
              <Form.Item label="Travel Date" required>
                <DatePicker 
                  style={{ width: "100%" }} 
                  value={dayjs(bookingDate)} 
                  onChange={(d) => d && setBookingDate(d.format("YYYY-MM-DD"))}
                  disabledDate={(current) => current && current < dayjs().startOf("day")}
                />
              </Form.Item>

              <Form.Item label="Passenger Name" required>
                <Input 
                  prefix={<UserOutlined />} 
                  value={passengerName} 
                  onChange={(e) => setPassengerName(e.target.value)} 
                  placeholder="e.g. John Doe"
                />
              </Form.Item>

              <Form.Item label="Email Address" required>
                <Input 
                  prefix={<MailOutlined />} 
                  value={passengerEmail} 
                  onChange={(e) => setPassengerEmail(e.target.value)} 
                  placeholder="e.g. john@example.com"
                />
              </Form.Item>

              <Form.Item label="Loyalty Frequent Flyer ID (Optional)">
                <Input 
                  prefix={<NumberOutlined />} 
                  value={frequentFlyer} 
                  onChange={(e) => setFrequentFlyer(e.target.value)} 
                  placeholder="e.g. FF-9382"
                />
              </Form.Item>

              <Button type="primary" block onClick={proceedToSeatSelection} style={{ height: 40, borderRadius: 6 }}>
                Select Seat <ArrowRightOutlined />
              </Button>
            </Form>
          </div>
        )}

        {/* Step 1: Interactive Seat Selection */}
        {currentStep === 1 && selectedFlight && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Card style={{ background: "#fafafa", padding: "4px 8px" }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span>Configure flight <strong>{selectedFlight.flight_number}</strong></span>
                <span>Seat Selected: {selectedSeat ? <Tag color="gold" style={{ fontWeight: "bold" }}>{selectedSeat}</Tag> : <Text type="warning">None (Auto-allocated)</Text>}</span>
              </div>
            </Card>

            {loadingSeats ? (
              <div style={{ textAlign: "center", padding: "40px 0" }}>Loading interactive seat map...</div>
            ) : (
              renderSeatGrid()
            )}

            <Space style={{ display: "flex", justifyContent: "space-between", marginTop: "12px" }}>
              <Button onClick={() => setCurrentStep(0)}>Back</Button>
              <Button type="primary" onClick={() => setCurrentStep(2)}>
                Proceed to Payment <ArrowRightOutlined />
              </Button>
            </Space>
          </div>
        )}

        {/* Step 2: Payment Gateway Form */}
        {currentStep === 2 && selectedFlight && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <Alert
              message={
                <div style={{ fontSize: "11px" }}>
                  <strong>💡 Simulation Payment Card Rules:</strong>
                  <ul style={{ margin: "4px 0 0 16px", padding: 0 }}>
                    <li>Use a <strong>Visa Card</strong> (starts with <code>4111</code>) to trigger <strong>Success</strong>.</li>
                    <li>Use a <strong>Mastercard</strong> (starts with <code>5100</code>) to trigger <strong>Network Timeout</strong>.</li>
                    <li>Use an <strong>Amex Card</strong> (starts with <code>3700</code>) to trigger <strong>Insufficient Balance</strong>.</li>
                    <li>Use a <strong>Discover Card</strong> (starts with <code>6011</code>) to trigger <strong>Bank Decline</strong>.</li>
                  </ul>
                </div>
              }
              type="info"
              showIcon
            />

            {paymentResult && paymentResult.status === "error" && (
              <Alert 
                message={paymentResult.msg} 
                type="error" 
                showIcon 
                closable 
                onClose={() => setPaymentResult(null)} 
              />
            )}

            <Form layout="vertical" onFinish={handleMockPayment}>
              <Form.Item 
                name="cardNumber" 
                label="Card Number (Input mock card to test scenarios)" 
                rules={[{ required: true, message: "Card number is required" }]}
              >
                <Input 
                  prefix={<CreditCardOutlined />} 
                  placeholder="4111 1111 1111 1111" 
                  maxLength={19}
                />
              </Form.Item>

              <Row gutter={16}>
                <Col span={12}>
                  <Form.Item name="expiry" label="Expiry Date" rules={[{ required: true }]}>
                    <Input placeholder="MM/YY" maxLength={5} />
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item name="cvv" label="CVV Code" rules={[{ required: true }]}>
                    <Input placeholder="123" maxLength={4} />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item name="cardName" label="Cardholder Name" initialValue={passengerName}>
                <Input placeholder="Jane Smith" />
              </Form.Item>

              <Space direction="vertical" style={{ width: "100%" }}>
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  block 
                  loading={paymentLoading}
                  style={{ 
                    height: 44, 
                    borderRadius: 8, 
                    background: "linear-gradient(90deg, #1890ff, #0050b3)",
                    border: "none",
                    fontWeight: "bold"
                  }}
                >
                  {paymentLoading ? "Contacting Payment Gateway..." : `Authorize Payment ($${selectedFlight.price})`}
                </Button>
                
                <Button block onClick={() => setCurrentStep(1)} disabled={paymentLoading}>
                  Back
                </Button>
              </Space>
            </Form>
          </div>
        )}

        {/* Step 3: Success & Ticket issuance Confirmation */}
        {currentStep === 3 && paymentResult && (
          <div style={{ textAlign: "center", padding: "20px 0" }}>
            <CheckCircleOutlined style={{ fontSize: "56px", color: "#52c41a", marginBottom: "16px" }} />
            <Title level={4}>Booking Processed Successfully</Title>
            <Paragraph style={{ color: "#666", padding: "0 24px" }}>
              {paymentResult.msg}
            </Paragraph>
            <Paragraph style={{ fontSize: "13px", color: "#8c8c8c" }}>
              You can now view your real-time boarding pass and active flight ticket status under the **My Bookings & Profile** tab.
            </Paragraph>
            <Button type="primary" onClick={() => setBookingModalVisible(false)} style={{ borderRadius: 6 }}>
              Done
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
};
