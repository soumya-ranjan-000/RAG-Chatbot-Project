import React, { useState, useEffect } from "react";
import { 
  Card, Tag, Table, Button, Modal, Row, Col, Space, Typography, 
  message, Descriptions, Select, Radio, Divider, Badge
} from "antd";
import { 
  UserOutlined, RedoOutlined, SelectOutlined, 
  ShoppingOutlined, GiftOutlined, StarOutlined
} from "@ant-design/icons";
import dayjs from "dayjs";
import { PSS_API_URL } from "../services/api";

const { Title, Text } = Typography;

interface ProfilePanelProps {
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
  bookings: any[];
  onBookingUpdate: (updated: any) => void;
}

export const ProfilePanel: React.FC<ProfilePanelProps> = ({ 
  currentUser, 
  bookings, 
  onBookingUpdate 
}) => {
  const [loyalty, setLoyalty] = useState<{ loyalty_tier: string; miles_balance: number }>({
    loyalty_tier: "economy",
    miles_balance: 12500
  });
  
  // Interactive Modals State
  const [activeTabBooking, setActiveTabBooking] = useState<any>(null);
  
  // Seat selection states
  const [seatModalVisible, setSeatModalVisible] = useState(false);
  const [seatMap, setSeatMap] = useState<any[]>([]);
  const [loadingSeats, setLoadingSeats] = useState(false);
  const [selectedSeat, setSelectedSeat] = useState<string>("");

  // Ancillary states
  const [ancillaryModalVisible, setAncillaryModalVisible] = useState(false);
  const [ancillaryType, setAncillaryType] = useState<string>("extra_baggage");
  const [submittingAncillary, setSubmittingAncillary] = useState(false);

  // SSR states
  const [ssrModalVisible, setSsrModalVisible] = useState(false);
  const [ssrCode, setSsrCode] = useState<string>("VGML");
  const [ssrRemarks, setSsrRemarks] = useState<string>("");
  const [submittingSsr, setSubmittingSsr] = useState(false);

  // Load loyalty details
  useEffect(() => {
    const fetchLoyalty = async () => {
      const passengerId = currentUser.passengerProfile?.passenger_id || "usr_94f83b";
      try {
        const res = await fetch(`${PSS_API_URL}/passengers/${passengerId}/loyalty`);
        if (res.ok) {
          const data = await res.json();
          setLoyalty(data);
        }
      } catch (e) {
        console.error("Failed to fetch loyalty info", e);
      }
    };
    fetchLoyalty();
  }, [currentUser]);

  // Load seats for a booking
  const loadSeatMap = async (booking: any) => {
    setLoadingSeats(true);
    try {
      const flightNum = booking.flight_number;
      const res = await fetch(`${PSS_API_URL}/flights/${flightNum}/seats`);
      if (res.ok) {
        const data = await res.json();
        setSeatMap(data);
      } else {
        message.error("Failed to fetch seat map from PSS API");
      }
    } catch (e) {
      console.error(e);
      message.error("Network error fetching seat map");
    } finally {
      setLoadingSeats(false);
    }
  };

  const handleSeatClick = (seat: any) => {
    if (seat.is_occupied || seat.is_blocked) return;
    setSelectedSeat(seat.seat_number);
  };

  const submitSeatSelection = async () => {
    if (!selectedSeat) {
      message.warning("Please choose a seat from the map");
      return;
    }
    const passengerId = currentUser.passengerProfile?.passenger_id || "usr_94f83b";
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${activeTabBooking.pnr}/seat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          passenger_id: passengerId,
          seat_number: selectedSeat
        })
      });
      if (res.ok) {
        message.success(`Seat ${selectedSeat} successfully selected!`);
        // Update local state and propagate
        const updatedBooking = { ...activeTabBooking, seat: selectedSeat };
        setActiveTabBooking(updatedBooking);
        onBookingUpdate(updatedBooking);
        setSeatModalVisible(false);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to select seat");
      }
    } catch (e) {
      message.error("Failed to connect to backend server");
    }
  };

  const submitAncillary = async () => {
    const passengerId = currentUser.passengerProfile?.passenger_id || "usr_94f83b";
    let amount = 30.00;
    if (ancillaryType === "extra_baggage") amount = 45.00;
    else if (ancillaryType === "lounge_access") amount = 60.00;
    else if (ancillaryType === "wifi") amount = 15.00;

    setSubmittingAncillary(true);
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${activeTabBooking.pnr}/ancillary`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          passenger_id: passengerId,
          ancillary_type: ancillaryType,
          amount
        })
      });
      if (res.ok) {
        message.success(`Ancillary service '${ancillaryType}' added!`);
        setAncillaryModalVisible(false);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to add service");
      }
    } catch (e) {
      message.error("Failed to connect to backend server");
    } finally {
      setSubmittingAncillary(false);
    }
  };

  const submitSsr = async () => {
    const passengerId = currentUser.passengerProfile?.passenger_id || "usr_94f83b";
    setSubmittingSsr(true);
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${activeTabBooking.pnr}/ssr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          passenger_id: passengerId,
          ssr_code: ssrCode,
          remarks: ssrRemarks || "Requested via passenger portal"
        })
      });
      if (res.ok) {
        message.success(`Special Service Request (${ssrCode}) submitted successfully!`);
        setSsrModalVisible(false);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to submit request");
      }
    } catch (e) {
      message.error("Failed to connect to backend server");
    } finally {
      setSubmittingSsr(false);
    }
  };

  const handleOnlineCheckIn = async (booking: any) => {
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${booking.pnr}/status`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "checked-in" })
      });
      if (res.ok) {
        message.success("Online check-in complete! Boarding pass issued.");
        const updated = { ...booking, status: "checked-in" };
        if (activeTabBooking?.pnr === booking.pnr) {
          setActiveTabBooking(updated);
        }
        onBookingUpdate(updated);
      } else {
        const err = await res.json();
        message.error(err.detail || "Check-in failed");
      }
    } catch (e) {
      message.error("Failed to connect to PSS API");
    }
  };

  // Reschedule Simulator Helper
  const handleSimulateReschedule = async (booking: any) => {
    // Generate a different flight to test rescheduling
    const newFlight = booking.flight_number.startsWith("AI") ? "AI115" : "EK503";
    const newDate = dayjs(booking.date).add(2, "day").format("YYYY-MM-DD");
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${booking.pnr}/reschedule`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          new_date: newDate,
          new_flight: newFlight
        })
      });
      if (res.ok) {
        const data = await res.json();
        message.success(`Flight rescheduled to ${newFlight} on ${newDate}!`);
        if (activeTabBooking?.pnr === booking.pnr) {
          setActiveTabBooking(data);
        }
        onBookingUpdate(data);
      } else {
        const err = await res.json();
        message.error(err.detail || "Failed to reschedule booking");
      }
    } catch (e) {
      message.error("Failed to connect to PSS API");
    }
  };

  const handleCancelBooking = async (booking: any) => {
    try {
      const res = await fetch(`${PSS_API_URL}/bookings/${booking.pnr}/cancel`, {
        method: "POST"
      });
      if (res.ok) {
        message.success(`Booking ${booking.pnr} has been cancelled.`);
        const updated = { ...booking, status: "cancelled" };
        if (activeTabBooking?.pnr === booking.pnr) {
          setActiveTabBooking(updated);
        }
        onBookingUpdate(updated);
      } else {
        message.error("Failed to cancel booking");
      }
    } catch (e) {
      message.error("Failed to connect to PSS API");
    }
  };

  // Seat rendering grid builder
  const renderSeatGrid = () => {
    // Organize seats by row and seat letter
    const rowsMap: { [key: number]: any[] } = {};
    seatMap.forEach(seat => {
      const r = seat.row_number;
      if (!rowsMap[r]) rowsMap[r] = [];
      rowsMap[r].push(seat);
    });

    const sortedRows = Object.keys(rowsMap).map(Number).sort((a, b) => a - b);

    return (
      <div style={{ maxHeight: "400px", overflowY: "auto", padding: "10px", background: "#f5f5f5", borderRadius: "8px" }}>
        {/* Seat Legend */}
        <Space style={{ marginBottom: "16px", display: "flex", justifyContent: "center" }} size="middle">
          <Badge status="success" text="Available" />
          <Badge status="processing" text="Business" />
          <Badge status="default" text="Occupied / Blocked" />
          <Badge color="gold" text="Selected" />
        </Space>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px", alignItems: "center" }}>
          {sortedRows.map(rowNum => {
            const rowSeats = rowsMap[rowNum].sort((a, b) => a.seat_letter.localeCompare(b.seat_letter));
            const isBusiness = rowSeats[0]?.cabin_class === "business";

            return (
              <div key={rowNum} style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ width: "24px", fontWeight: "bold", textAlign: "right" }}>{rowNum}</span>
                {rowSeats.map((seat, index) => {
                  const isSelected = selectedSeat === seat.seat_number;
                  const isOccupied = seat.is_occupied || seat.is_blocked;
                  
                  // Add empty space/aisle in the middle
                  const addAisle = isBusiness ? index === 2 : index === 3;

                  let bgColor = "#1890ff"; // Economy Blue
                  if (isBusiness) bgColor = "#722ed1"; // Business Purple
                  if (isOccupied) bgColor = "#d9d9d9"; // Occupied Gray
                  if (isSelected) bgColor = "#faad14"; // Selected Gold

                  return (
                    <React.Fragment key={seat.seat_number}>
                      {addAisle && <div style={{ width: "20px" }} />}
                      <button
                        onClick={() => handleSeatClick(seat)}
                        disabled={isOccupied}
                        style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "6px",
                          border: isSelected ? "2px solid #d4b106" : "none",
                          background: bgColor,
                          color: isOccupied ? "#8c8c8c" : "#fff",
                          fontWeight: "bold",
                          cursor: isOccupied ? "not-allowed" : "pointer",
                          transition: "all 0.2s",
                          fontSize: "11px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                        title={`${seat.seat_number} - ${seat.cabin_class.toUpperCase()}${seat.extra_charge_usd > 0 ? ' (+$' + seat.extra_charge_usd + ')' : ''}`}
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

  const getStatusColor = (status: string) => {
    const s = status?.toLowerCase();
    if (s === "booked" || s === "confirmed") return "blue";
    if (s === "checked-in" || s === "boarding-pass-generated") return "purple";
    if (s === "cancelled") return "red";
    return "green";
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* 1. Passenger Profile Card */}
      <Card 
        style={{ 
          borderRadius: "12px", 
          boxShadow: "0 4px 12px rgba(0,0,0,0.05)",
          background: "linear-gradient(135deg, #ffffff 0%, #f6f9fc 100%)"
        }}
      >
        <Row gutter={24} align="middle">
          <Col xs={24} sm={4} style={{ textAlign: "center" }}>
            <div style={{
              width: "80px",
              height: "80px",
              borderRadius: "50%",
              background: "linear-gradient(135deg, #1890ff 0%, #0050b3 100%)",
              color: "#fff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "36px",
              margin: "0 auto 16px"
            }}>
              <UserOutlined />
            </div>
          </Col>
          <Col xs={24} sm={12}>
            <Title level={3} style={{ margin: 0 }}>{currentUser.passengerProfile?.name || "System Admin"}</Title>
            <Text type="secondary">{currentUser.username}</Text>
            <div style={{ marginTop: "12px" }}>
              <Space split={<Divider type="vertical" />}>
                <span>Passenger ID: <code style={{ fontWeight: "bold" }}>{currentUser.passengerProfile?.passenger_id || "admin"}</code></span>
                <span>Frequent Flyer No: <code style={{ fontWeight: "bold" }}>{currentUser.passengerProfile?.frequent_flyer_number || "FF_ADMIN"}</code></span>
              </Space>
            </div>
          </Col>
          <Col xs={24} sm={8} style={{ borderLeft: "1px solid #f0f0f0" }}>
            <Card size="small" style={{ background: "rgba(24fa, 140, 22, 0.05)", border: "1px solid #ffe7ba" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <GiftOutlined style={{ fontSize: "20px", color: "#fa8c16" }} />
                <div>
                  <div style={{ fontSize: "11px", color: "#8c8c8c", textTransform: "uppercase" }}>Loyalty Level</div>
                  <Tag color="orange" style={{ fontWeight: "bold", textTransform: "uppercase" }}>{loyalty.loyalty_tier}</Tag>
                </div>
              </div>
              <div style={{ marginTop: "12px" }}>
                <div style={{ fontSize: "11px", color: "#8c8c8c", textTransform: "uppercase" }}>Miles Balance</div>
                <div style={{ fontSize: "20px", fontWeight: "bold", color: "#d48806" }}>
                  {loyalty.miles_balance.toLocaleString()} miles
                </div>
              </div>
            </Card>
          </Col>
        </Row>
      </Card>

      {/* 2. My Bookings section */}
      <Card 
        title="✈️ My Active Bookings & Tickets"
        style={{ borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
      >
        <Table 
          dataSource={bookings} 
          rowKey="pnr" 
          pagination={false}
          columns={[
            {
              title: "PNR Code",
              dataIndex: "pnr",
              key: "pnr",
              render: (val: string) => <code style={{ fontWeight: "bold", background: "#f5f5f5", padding: "2px 4px", borderRadius: "3px" }}>{val}</code>
            },
            {
              title: "Flight",
              dataIndex: "flight_number",
              key: "flight_number",
            },
            {
              title: "Route",
              key: "route",
              render: (record: any) => <span>{record.origin} ➡️ {record.destination}</span>
            },
            {
              title: "Departure Date",
              dataIndex: "date",
              key: "date",
            },
            {
              title: "Seat",
              dataIndex: "seat",
              key: "seat",
              render: (val: string) => val ? <Tag color="blue">{val}</Tag> : <Text type="secondary">None</Text>
            },
            {
              title: "Status",
              dataIndex: "status",
              key: "status",
              render: (status: string) => <Tag color={getStatusColor(status)}>{status?.toUpperCase()}</Tag>
            },
            {
              title: "Actions",
              key: "actions",
              render: (record: any) => {
                const s = record.status?.toLowerCase();
                const isCancelled = s === "cancelled";
                return (
                  <Space>
                    <Button 
                      type="primary" 
                      size="small" 
                      onClick={() => setActiveTabBooking(record)}
                    >
                      Manage
                    </Button>
                    <Button
                      size="small"
                      disabled={isCancelled || s === "checked-in" || s === "boarding-pass-generated"}
                      onClick={() => handleOnlineCheckIn(record)}
                      style={{ background: "#52c41a", borderColor: "#52c41a", color: "#fff" }}
                    >
                      Check In
                    </Button>
                  </Space>
                );
              }
            }
          ]}
        />
      </Card>

      {/* 3. Detail Management Section (Interactive Boarding pass + service additions) */}
      {activeTabBooking && (
        <Card 
          title={`🔧 Manage Booking: PNR ${activeTabBooking.pnr}`} 
          style={{ borderRadius: "12px", boxShadow: "0 4px 12px rgba(0,0,0,0.05)", border: "1px solid #1890ff" }}
          extra={
            <Button size="small" type="link" onClick={() => setActiveTabBooking(null)}>Close Management</Button>
          }
        >
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Title level={4}>Services & Operations</Title>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginBottom: "20px" }}>
                <Button 
                  icon={<SelectOutlined />} 
                  disabled={activeTabBooking.status?.toLowerCase() === "cancelled"}
                  onClick={() => {
                    loadSeatMap(activeTabBooking);
                    setSeatModalVisible(true);
                  }}
                >
                  Select / Change Seat
                </Button>
                
                <Button 
                  icon={<ShoppingOutlined />} 
                  disabled={activeTabBooking.status?.toLowerCase() === "cancelled"}
                  onClick={() => setAncillaryModalVisible(true)}
                >
                  Add Baggage & Lounge
                </Button>

                <Button 
                  icon={<StarOutlined />} 
                  disabled={activeTabBooking.status?.toLowerCase() === "cancelled"}
                  onClick={() => setSsrModalVisible(true)}
                >
                  Request Special Meal / Wheelchair
                </Button>

                <Button 
                  icon={<RedoOutlined />} 
                  disabled={activeTabBooking.status?.toLowerCase() === "cancelled" || activeTabBooking.status?.toLowerCase() === "checked-in"}
                  onClick={() => handleSimulateReschedule(activeTabBooking)}
                >
                  Simulate Reschedule
                </Button>

                <Button 
                  danger 
                  disabled={activeTabBooking.status?.toLowerCase() === "cancelled"}
                  onClick={() => handleCancelBooking(activeTabBooking)}
                >
                  Cancel Reservation
                </Button>
              </div>

              <Descriptions title="Ticket Parameters" bordered size="small" column={1}>
                <Descriptions.Item label="Passenger">{activeTabBooking.passenger_name}</Descriptions.Item>
                <Descriptions.Item label="Flight">{activeTabBooking.flight_number}</Descriptions.Item>
                <Descriptions.Item label="Route">{activeTabBooking.origin} to {activeTabBooking.destination}</Descriptions.Item>
                <Descriptions.Item label="Travel Date">{activeTabBooking.date}</Descriptions.Item>
                <Descriptions.Item label="Seat Number">{activeTabBooking.seat || "Not Selected"}</Descriptions.Item>
                <Descriptions.Item label="Boarding Gate">{activeTabBooking.gate || "TBD"}</Descriptions.Item>
                <Descriptions.Item label="Status">
                  <Tag color={getStatusColor(activeTabBooking.status)}>{activeTabBooking.status?.toUpperCase()}</Tag>
                </Descriptions.Item>
              </Descriptions>
            </Col>

            {/* Boarding Pass Rendering */}
            <Col xs={24} md={12}>
              <Title level={4}>Boarding Pass</Title>
              <div style={{
                background: "#111827",
                color: "#fff",
                borderRadius: "12px",
                overflow: "hidden",
                boxShadow: "0 6px 18px rgba(0, 0, 0, 0.15)",
                border: "1px solid #374151",
                padding: "20px"
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px dashed #4b5563", paddingBottom: "12px" }}>
                  <span style={{ fontWeight: "bold", color: "#38bdf8" }}>APEX AIRLINES</span>
                  <span style={{ fontWeight: "bold" }}>PNR: {activeTabBooking.pnr}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", margin: "20px 0" }}>
                  <div>
                    <div style={{ fontSize: "36px", fontWeight: "800", color: "#f3f4f6" }}>{activeTabBooking.origin}</div>
                    <div style={{ fontSize: "11px", color: "#9ca3af" }}>Origin</div>
                  </div>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", flex: 1 }}>
                    <div style={{ fontSize: "20px", color: "#38bdf8" }}>✈</div>
                    <div style={{ width: "80%", borderTop: "1px dashed #4b5563" }} />
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "36px", fontWeight: "800", color: "#f3f4f6" }}>{activeTabBooking.destination}</div>
                    <div style={{ fontSize: "11px", color: "#9ca3af" }}>Destination</div>
                  </div>
                </div>

                <Row gutter={16} style={{ borderTop: "1px solid #1f2937", paddingTop: "12px", fontSize: "13px" }}>
                  <Col span={12}>
                    <Text type="secondary" style={{ color: "#9ca3af", display: "block" }}>PASSENGER</Text>
                    <span style={{ fontWeight: "bold" }}>{activeTabBooking.passenger_name}</span>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ color: "#9ca3af", display: "block" }}>FLIGHT</Text>
                    <span style={{ fontWeight: "bold" }}>{activeTabBooking.flight_number}</span>
                  </Col>
                </Row>

                <Row gutter={16} style={{ marginTop: "12px", fontSize: "13px" }}>
                  <Col span={12}>
                    <Text type="secondary" style={{ color: "#9ca3af", display: "block" }}>DATE</Text>
                    <span style={{ fontWeight: "bold" }}>{activeTabBooking.date}</span>
                  </Col>
                  <Col span={12}>
                    <Text type="secondary" style={{ color: "#9ca3af", display: "block" }}>SEAT / GATE</Text>
                    <span style={{ fontWeight: "bold", color: "#38bdf8" }}>{activeTabBooking.seat || "TBD"} / {activeTabBooking.gate || "B4"}</span>
                  </Col>
                </Row>

                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginTop: "24px", gap: "8px" }}>
                  <div style={{ background: "#fff", padding: "8px", borderRadius: "4px", width: "100%", display: "flex", justifyContent: "center" }}>
                    {/* Simulated barcode */}
                    <div style={{ display: "flex", gap: "2px", height: "30px", width: "90%" }}>
                      {[...Array(30)].map((_, i) => (
                        <div key={i} style={{ width: i % 4 === 0 ? "4px" : i % 3 === 0 ? "1px" : "2px", height: "100%", background: "#000" }} />
                      ))}
                    </div>
                  </div>
                  <span style={{ fontSize: "10px", color: "#6b7280" }}>SCAN TO BOARD</span>
                </div>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* Seat Selection Modal */}
      <Modal
        title={`Select Seat - Flight ${activeTabBooking?.flight_number}`}
        open={seatModalVisible}
        onCancel={() => setSeatModalVisible(false)}
        onOk={submitSeatSelection}
        okText="Confirm Seat"
        confirmLoading={loadingSeats}
        width={450}
        destroyOnClose
      >
        {loadingSeats ? (
          <div style={{ textAlign: "center", padding: "40px" }}>Loading flight seats...</div>
        ) : (
          <div>
            {renderSeatGrid()}
            {selectedSeat && (
              <div style={{ marginTop: "16px", textAlign: "center" }}>
                <Text>Selected seat: </Text>
                <Tag color="gold" style={{ fontSize: "16px", padding: "4px 8px", fontWeight: "bold" }}>{selectedSeat}</Tag>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Ancillary Services Modal */}
      <Modal
        title="Add Ancillary Services & Baggage"
        open={ancillaryModalVisible}
        onCancel={() => setAncillaryModalVisible(false)}
        onOk={submitAncillary}
        okText="Add Service"
        confirmLoading={submittingAncillary}
        destroyOnClose
      >
        <Radio.Group 
          value={ancillaryType} 
          onChange={(e) => setAncillaryType(e.target.value)}
          style={{ width: "100%", display: "flex", flexDirection: "column", gap: "16px" }}
        >
          <Card size="small" hoverable>
            <Radio value="extra_baggage">
              <div style={{ marginLeft: "8px" }}>
                <Text style={{ fontWeight: "bold", display: "block" }}>Extra Baggage Allowance (+23kg)</Text>
                <Text type="secondary" style={{ fontSize: "12px" }}>Add 23kg excess check-in luggage to this segment. Price: $45.00</Text>
              </div>
            </Radio>
          </Card>

          <Card size="small" hoverable>
            <Radio value="lounge_access">
              <div style={{ marginLeft: "8px" }}>
                <Text style={{ fontWeight: "bold", display: "block" }}>VIP Airport Lounge Pass</Text>
                <Text type="secondary" style={{ fontSize: "12px" }}>Access executive lounge (free buffet, shower facilities, drinks). Price: $60.00</Text>
              </div>
            </Radio>
          </Card>

          <Card size="small" hoverable>
            <Radio value="wifi">
              <div style={{ marginLeft: "8px" }}>
                <Text style={{ fontWeight: "bold", display: "block" }}>High-Speed In-Flight Wi-Fi</Text>
                <Text type="secondary" style={{ fontSize: "12px" }}>Unlimited messaging and browsing during the flight. Price: $15.00</Text>
              </div>
            </Radio>
          </Card>
        </Radio.Group>
      </Modal>

      {/* SSR Modal */}
      <Modal
        title="Request Special Services (SSR)"
        open={ssrModalVisible}
        onCancel={() => setSsrModalVisible(false)}
        onOk={submitSsr}
        okText="Submit Request"
        confirmLoading={submittingSsr}
        destroyOnClose
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <span style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>Service Request Type:</span>
            <Select 
              value={ssrCode} 
              onChange={setSsrCode}
              style={{ width: "100%" }}
              options={[
                { label: "VGML - Vegetarian Vegetarian Meal", value: "VGML" },
                { label: "GFML - Gluten-Free Meal", value: "GFML" },
                { label: "KSML - Kosher Meal", value: "KSML" },
                { label: "WCHR - Wheelchair assistance (to departure gate)", value: "WCHR" },
                { label: "DEAF - Deaf passenger (assistance required)", value: "DEAF" },
                { label: "PETC - Cabin pet reservation", value: "PETC" },
              ]}
            />
          </div>

          <div>
            <span style={{ display: "block", marginBottom: "8px", fontWeight: "bold" }}>Special Remarks:</span>
            <Select 
              mode="tags" 
              placeholder="e.g. Nut allergy, travel with guide dog" 
              style={{ width: "100%" }}
              onChange={(values: string[]) => setSsrRemarks(values.join(", "))}
            />
          </div>
        </div>
      </Modal>
    </div>
  );
};
