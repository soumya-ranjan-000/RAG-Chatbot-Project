import React, { useState } from "react";
import { Avatar, Typography, Button, Tag, Tooltip, Modal } from "antd";
import { UserOutlined, RobotOutlined, FileTextOutlined, DownOutlined, UpOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import type { ChatMessage as MessageType, ChunkSource } from "../types/chat";
import { PSS_API_URL } from "../services/api";


const { Text } = Typography;

const FlightsCardList: React.FC<{ flights: any[]; onSelect?: (flightNumber: string, date: string) => void }> = ({ flights, onSelect }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", margin: "12px 0", width: "100%" }}>
      {flights.map((flight, index) => (
        <div key={index} style={{
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          color: "#fff",
          padding: "12px 16px",
          borderRadius: "10px",
          border: "1px solid #334155",
          boxShadow: "0 4px 6px rgba(0,0,0,0.15)",
          display: "flex",
          flexDirection: "column",
          gap: "6px"
        }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontWeight: "bold", color: "#38bdf8", fontSize: "13px" }}>
              ✈️ {flight.airline || "Apex Air"} ({flight.flight_number})
            </span>
            <Tag color="cyan" style={{ margin: 0, fontWeight: "bold" }}>
              ${flight.price}
            </Tag>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
            <div>
              <div style={{ fontSize: "16px", fontWeight: "800" }}>{flight.origin}</div>
              <div style={{ fontSize: "10px", color: "#94a3b8" }}>Origin</div>
            </div>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 10px", position: "relative" }}>
              <span style={{ fontSize: "12px", color: "#38bdf8", transform: "translateY(-4px)" }}>✈</span>
              <div style={{ borderTop: "1px dashed #475569", width: "100%", marginTop: "-4px" }} />
            </div>
            <div style={{ textAlign: "right" }}>
              <div style={{ fontSize: "16px", fontWeight: "800" }}>{flight.destination}</div>
              <div style={{ fontSize: "10px", color: "#94a3b8" }}>Destination</div>
            </div>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#94a3b8", borderTop: "1px solid #334155", paddingTop: "6px", marginTop: "4px" }}>
            <span>Departure: <strong>{flight.departure_time || "N/A"}</strong></span>
            <span>Date: <strong>{flight.date || "Anydate"}</strong></span>
          </div>
          {onSelect && (
            <Button
              size="small"
              type="primary"
              style={{ background: "#38bdf8", border: "none", borderRadius: "4px", fontWeight: "bold", marginTop: "4px", width: "fit-content" }}
              onClick={() => onSelect(flight.flight_number, flight.date)}
            >
              Select & Book Flight
            </Button>
          )}
        </div>
      ))}
    </div>
  );
};

const TicketsCardList: React.FC<{ bookings: any[]; onSendMessage?: (text: string) => void }> = ({ bookings, onSendMessage }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", margin: "12px 0", width: "100%" }}>
      {bookings.map((booking, index) => {
        const isPaid = booking.status === "booked" || booking.status === "confirmed" || booking.status === "ticketed";
        const isPending = booking.status === "pending-payment";
        
        return (
          <div key={index} style={{
            background: "#f8fafc",
            color: "#1e293b",
            padding: "12px 16px",
            borderRadius: "10px",
            border: `1px solid ${isPaid ? "#bbf7d0" : isPending ? "#fef08a" : "#fecaca"}`,
            borderLeft: `4px solid ${isPaid ? "#10b981" : isPending ? "#eab308" : "#ef4444"}`,
            boxShadow: "0 2px 4px rgba(0,0,0,0.05)",
            display: "flex",
            flexDirection: "column",
            gap: "4px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: "11px", color: "#64748b", fontWeight: "bold" }}>
                PNR RECORD: <code style={{ background: "#e2e8f0", padding: "2px 6px", borderRadius: "4px", color: "#0f172a", fontFamily: "monospace" }}>{booking.pnr}</code>
              </span>
              <Tag color={isPaid ? "green" : isPending ? "gold" : "red"} style={{ margin: 0, fontWeight: "bold", fontSize: "10px" }}>
                {booking.status?.toUpperCase()}
              </Tag>
            </div>
            
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
              <span style={{ fontWeight: "700", fontSize: "13px" }}>{booking.origin} ➡️ {booking.destination}</span>
              <span style={{ fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>Flight {booking.flight_number}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
              <span>Passenger: <strong>{booking.passenger_name}</strong></span>
              <span>Date: <strong>{booking.date}</strong></span>
            </div>

            {isPending && (
              <div style={{ marginTop: "8px", borderTop: "1px dashed #e2e8f0", paddingTop: "8px", display: "flex", justifyContent: "flex-end" }}>
                <Button 
                  type="primary" 
                  size="small" 
                  href={`/payment?pnr=${booking.pnr}&amount=150&flight=${booking.flight_number}&origin=${booking.origin}&destination=${booking.destination}&date=${booking.date}&passenger_id=${booking.passenger_id || ""}`}
                  target="_blank"
                  rel="opener"
                  style={{ fontSize: "11px", background: "#eab308", border: "none", borderRadius: "4px", fontWeight: "bold" }}
                >
                  💳 Complete Payment
                </Button>
              </div>
            )}

            {onSendMessage && !isPending && booking.status !== "cancelled" && (
              <div style={{ marginTop: "10px", display: "flex", gap: "6px", flexWrap: "wrap", borderTop: "1px dashed #e2e8f0", paddingTop: "8px" }}>
                <Button 
                  size="small" 
                  onClick={() => onSendMessage(`Select seat for my booking ${booking.pnr}`)}
                  style={{ fontSize: "11px", borderRadius: "4px" }}
                >
                  💺 Choose Seat
                </Button>
                <Button 
                  size="small" 
                  onClick={() => onSendMessage(`Choose meal option for booking ${booking.pnr}`)}
                  style={{ fontSize: "11px", borderRadius: "4px" }}
                >
                  🍱 Choose Meal
                </Button>
                <Button 
                  size="small" 
                  onClick={() => onSendMessage(`Reschedule booking ${booking.pnr}`)}
                  style={{ fontSize: "11px", borderRadius: "4px" }}
                >
                  🔄 Reschedule
                </Button>
                <Button 
                  danger 
                  size="small" 
                  onClick={() => onSendMessage(`Cancel booking ${booking.pnr}`)}
                  style={{ fontSize: "11px", borderRadius: "4px" }}
                >
                  ❌ Cancel
                </Button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};

const PaymentLinkCard: React.FC<{ payment: any }> = ({ payment }) => {
  const checkoutUrl = `/payment?pnr=${payment.pnr}&amount=${payment.price || 150}&flight=${payment.flight_number || ""}&origin=${payment.origin || ""}&destination=${payment.destination || ""}&date=${payment.date || ""}&passenger_id=${payment.passenger_id || ""}`;
  
  return (
    <div style={{
      background: "linear-gradient(135deg, #1e1b4b 0%, #311042 100%)",
      color: "#fff",
      padding: "16px",
      borderRadius: "12px",
      border: "1px solid #4338ca",
      boxShadow: "0 6px 12px rgba(0,0,0,0.15)",
      margin: "12px 0",
      display: "flex",
      flexDirection: "column",
      gap: "8px",
      width: "100%"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ fontSize: "20px" }}>💳</span>
        <span style={{ fontWeight: "bold", fontSize: "14px", letterSpacing: "0.5px" }}>MOCK PAYMENT REQUIRED</span>
      </div>
      <p style={{ margin: 0, fontSize: "12px", color: "#cbd5e1" }}>
        A pending booking has been created. PNR: <strong>{payment.pnr}</strong>. Complete the checkout process below.
      </p>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "rgba(0,0,0,0.2)", padding: "8px 12px", borderRadius: "8px", margin: "4px 0" }}>
        <span style={{ fontSize: "12px", color: "#94a3b8" }}>Total Amount:</span>
        <span style={{ fontSize: "18px", fontWeight: "800", color: "#34d399" }}>${payment.price || 150}</span>
      </div>
      <Button 
        type="primary" 
        size="middle" 
        href={checkoutUrl}
        target="_blank"
        rel="opener"
        style={{ 
          background: "#10b981", 
          border: "none", 
          borderRadius: "6px", 
          fontWeight: "bold", 
          marginTop: "4px",
          boxShadow: "0 4px 6px rgba(16, 185, 129, 0.2)"
        }}
      >
        Proceed to Secure Payment ➔
      </Button>
    </div>
  );
};

const PassengerReviewCard: React.FC<{ data: any; onConfirm?: () => void }> = ({ data, onConfirm }) => {
  return (
    <div style={{
      background: "#f1f5f9",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      padding: "12px 16px",
      margin: "8px 0",
      color: "#1e293b",
      width: "100%"
    }}>
      <div style={{ fontWeight: "bold", marginBottom: "8px", borderBottom: "1px solid #cbd5e1", paddingBottom: "4px" }}>
        📝 Review Passenger Information
      </div>
      <div style={{ fontSize: "12px", display: "flex", flexDirection: "column", gap: "4px" }}>
        <div><strong>Name:</strong> {data.name}</div>
        <div><strong>Email:</strong> {data.email}</div>
        <div><strong>Frequent Flyer No:</strong> {data.frequent_flyer || "N/A"}</div>
      </div>
      {onConfirm && (
        <Button 
          type="primary" 
          size="small" 
          onClick={onConfirm}
          style={{ marginTop: "12px", background: "#0284c7", border: "none", borderRadius: "4px" }}
        >
          Confirm Information & Proceed
        </Button>
      )}
    </div>
  );
};

const SeatsOptionsCard: React.FC<{ seats: any; onSelect?: (seat: string) => void }> = ({ seats, onSelect }) => {
  const [visible, setVisible] = useState(false);
  const [seatMap, setSeatMap] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSeat, setSelectedSeat] = useState<string | null>(null);

  const isLegacyArray = Array.isArray(seats);

  const fetchSeatMap = async () => {
    if (isLegacyArray) return;
    setLoading(true);
    try {
      const flightId = seats.flight_id;
      const res = await fetch(`${PSS_API_URL}/flights/${flightId}/seats`);
      if (res.ok) {
        const data = await res.json();
        setSeatMap(data);
      }
    } catch (e) {
      console.error("Failed to fetch seat map", e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpen = () => {
    setVisible(true);
    fetchSeatMap();
  };

  const handleConfirm = () => {
    if (selectedSeat && onSelect) {
      onSelect(selectedSeat);
      setVisible(false);
    }
  };

  if (isLegacyArray) {
    return (
      <div style={{
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "8px",
        padding: "12px 16px",
        margin: "8px 0",
        width: "100%"
      }}>
        <div style={{ fontWeight: "bold", marginBottom: "8px", color: "#0f172a" }}>
          💺 Select Seat from Available Seats
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          {seats.map((s: any, idx: number) => (
            <Button
              key={idx}
              size="small"
              onClick={() => onSelect && onSelect(s.seat || s.seat_number)}
              style={{
                borderColor: s.class === "business" ? "#722ed1" : "#1890ff",
                color: s.class === "business" ? "#722ed1" : "#1890ff",
                borderRadius: "4px"
              }}
            >
              {s.seat || s.seat_number} ({s.class === "business" ? "Biz" : "Eco"}{s.extra ? ` +$${s.extra}` : ""})
            </Button>
          ))}
        </div>
      </div>
    );
  }

  const businessRows = Array.from(new Set(seatMap.filter(s => s.cabin_class === "business").map(s => s.row_number))).sort((a, b) => a - b);
  const economyRows = Array.from(new Set(seatMap.filter(s => s.cabin_class === "economy" || s.cabin_class === "premium_economy").map(s => s.row_number))).sort((a, b) => a - b);

  return (
    <div style={{
      background: "#faf5ff",
      border: "1px solid #e9d5ff",
      borderRadius: "10px",
      padding: "16px",
      margin: "12px 0",
      width: "100%",
      display: "flex",
      flexDirection: "column",
      gap: "10px",
      boxShadow: "0 2px 4px rgba(114, 46, 209, 0.05)"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ fontSize: "20px" }}>💺</span>
        <div>
          <div style={{ fontWeight: "bold", color: "#581c87", fontSize: "14px" }}>Interactive Flight Seat Map</div>
          <div style={{ fontSize: "11px", color: "#701a75" }}>PNR: {seats.pnr} | Flight: {seats.flight_id}</div>
        </div>
      </div>
      
      <Button 
        type="primary"
        onClick={handleOpen}
        style={{
          background: "linear-gradient(135deg, #722ed1 0%, #9254de 100%)",
          border: "none",
          fontWeight: "bold",
          borderRadius: "6px",
          marginTop: "4px"
        }}
      >
        💺 View Visual Seat Map & Select Seat
      </Button>

      <Modal
        title={
          <div style={{ borderBottom: "1px solid #f0f0f0", paddingBottom: "10px", display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "22px" }}>✈️</span>
            <div>
              <div style={{ fontSize: "16px", fontWeight: "800" }}>Aircraft Cabin Seat Map</div>
              <div style={{ fontSize: "12px", color: "#8c8c8c", fontWeight: "normal" }}>Flight {seats.flight_id} | Click on a seat to select</div>
            </div>
          </div>
        }
        open={visible}
        onCancel={() => setVisible(false)}
        footer={null}
        width={500}
        bodyStyle={{
          maxHeight: "65vh",
          overflowY: "auto",
          padding: "20px 24px",
          background: "#f8fafc"
        }}
      >
        {loading ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "#722ed1" }}>
            <span style={{ fontSize: "24px" }} className="streaming-dots">⏳ Loading Cabin Map...</span>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
            <div style={{
              display: "flex",
              justifyContent: "space-between",
              width: "100%",
              background: "#fff",
              padding: "10px 14px",
              borderRadius: "8px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
              marginBottom: "20px",
              fontSize: "11px",
              color: "#64748b",
              fontWeight: "600"
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "12px", background: "#f9f0ff", border: "1px solid #722ed1", borderRadius: "3px" }} /> Business
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "12px", background: "#e6f7ff", border: "1px solid #1890ff", borderRadius: "3px" }} /> Economy
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "12px", background: "#cbd5e1", border: "1px solid #94a3b8", borderRadius: "3px" }} /> Occupied
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                <div style={{ width: "12px", height: "12px", background: "#52c41a", border: "1px solid #52c41a", borderRadius: "3px" }} /> Selected
              </div>
            </div>

            <div style={{
              background: "#fff",
              border: "2px solid #e2e8f0",
              borderRadius: "30px 30px 10px 10px",
              padding: "30px 20px 20px 20px",
              width: "100%",
              maxWidth: "380px",
              boxShadow: "0 4px 6px rgba(0,0,0,0.02)",
              display: "flex",
              flexDirection: "column",
              gap: "8px"
            }}>
              <div style={{
                textAlign: "center",
                fontWeight: "bold",
                color: "#94a3b8",
                fontSize: "11px",
                letterSpacing: "2px",
                textTransform: "uppercase",
                marginBottom: "16px",
                borderBottom: "2px dashed #e2e8f0",
                paddingBottom: "8px"
              }}>
                Front of Aircraft (Flight Deck)
              </div>

              {businessRows.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ fontSize: "10px", color: "#722ed1", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px", textAlign: "center" }}>
                    ⭐ Business Class (2-2 configuration)
                  </div>
                  {businessRows.map(rowNum => {
                    const rowSeats = seatMap.filter(s => s.row_number === rowNum);
                    return (
                      <div key={rowNum} style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "10px" }}>
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'A'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'B'))}
                        <div style={{ width: "24px", textAlign: "center", fontWeight: "bold", fontSize: "11px", color: "#94a3b8" }}>{rowNum}</div>
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'C'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'D'))}
                      </div>
                    );
                  })}
                  <div style={{ height: "1px", background: "#e2e8f0", margin: "10px 0" }} />
                </div>
              )}

              {economyRows.length > 0 && (
                <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                  <div style={{ fontSize: "10px", color: "#1890ff", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "1px", marginBottom: "4px", textAlign: "center" }}>
                    ✈️ Economy Class (3-3 configuration)
                  </div>
                  {economyRows.map(rowNum => {
                    const rowSeats = seatMap.filter(s => s.row_number === rowNum);
                    const isExit = rowNum === 20 || rowNum === 21;
                    return (
                      <div key={rowNum} style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: "6px", position: "relative" }}>
                        {isExit && (
                          <span style={{ position: "absolute", left: "-10px", fontSize: "8px", color: "#ef4444", fontWeight: "bold" }}>EXIT</span>
                        )}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'A'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'B'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'C'))}
                        <div style={{ width: "24px", textAlign: "center", fontWeight: "bold", fontSize: "11px", color: "#94a3b8" }}>{rowNum}</div>
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'D'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'E'))}
                        {renderSeatButton(rowSeats.find(s => s.seat_letter === 'F'))}
                        {isExit && (
                          <span style={{ position: "absolute", right: "-10px", fontSize: "8px", color: "#ef4444", fontWeight: "bold" }}>EXIT</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div style={{
              width: "100%",
              background: "#fff",
              border: "1px solid #e2e8f0",
              borderRadius: "8px",
              padding: "16px",
              marginTop: "20px",
              display: "flex",
              flexDirection: "column",
              gap: "10px",
              boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                <span>Selected Seat: <strong style={{ color: "#722ed1", fontSize: "15px" }}>{selectedSeat || "None"}</strong></span>
                <span>Extra Charge: <strong>${selectedSeat ? (seatMap.find(s => s.seat_number === selectedSeat)?.extra_charge_usd || 0) : 0}</strong></span>
              </div>
              <Button
                type="primary"
                disabled={!selectedSeat}
                onClick={handleConfirm}
                style={{
                  background: selectedSeat ? "#52c41a" : undefined,
                  borderColor: selectedSeat ? "#52c41a" : undefined,
                  fontWeight: "bold",
                  borderRadius: "6px",
                  height: "38px"
                }}
              >
                Confirm Seat {selectedSeat || ""} Selection
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );

  function renderSeatButton(seat: any) {
    if (!seat) return <div style={{ width: "32px", height: "32px" }} />;
    const isSelected = selectedSeat === seat.seat_number;
    const isOcc = seat.is_occupied || seat.is_blocked;

    let bg = "#e6f7ff";
    let border = "1px solid #1890ff";
    let color = "#1890ff";

    if (seat.cabin_class === "business") {
      bg = "#f9f0ff";
      border = "1px solid #722ed1";
      color = "#722ed1";
    }

    if (isOcc) {
      bg = "#e2e8f0";
      border = "1px solid #cbd5e1";
      color = "#94a3b8";
    }

    if (isSelected) {
      bg = "#52c41a";
      border = "1px solid #52c41a";
      color = "#fff";
    }

    return (
      <Tooltip title={
        isOcc ? "Seat Occupied" : 
        `${seat.seat_number} - ${seat.cabin_class.toUpperCase()} (${seat.seat_type}) ${seat.extra_charge_usd > 0 ? `+$${seat.extra_charge_usd}` : 'No extra charge'}`
      }>
        <button
          disabled={isOcc}
          onClick={() => setSelectedSeat(seat.seat_number)}
          style={{
            width: "32px",
            height: "32px",
            background: bg,
            border: border,
            color: color,
            borderRadius: "6px",
            fontSize: "10px",
            fontWeight: "bold",
            cursor: isOcc ? "not-allowed" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: isSelected ? "0 2px 4px rgba(82, 196, 26, 0.2)" : "none",
            transition: "all 0.2s"
          }}
        >
          {isOcc ? "❌" : seat.seat_number}
        </button>
      </Tooltip>
    );
  }
};

const MealOptionsCard: React.FC<{ meals: any[]; onSelect?: (code: string) => void }> = ({ meals, onSelect }) => {
  return (
    <div style={{
      background: "#fdf8f6",
      border: "1px solid #fbd5c6",
      borderRadius: "8px",
      padding: "12px 16px",
      margin: "8px 0",
      width: "100%"
    }}>
      <div style={{ fontWeight: "bold", marginBottom: "8px", color: "#431407" }}>
        🍱 Select Meal Option
      </div>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        {meals.map((m, idx) => (
          <Button
            key={idx}
            size="small"
            onClick={() => onSelect && onSelect(m.code)}
            style={{
              borderColor: "#ea580c",
              color: "#ea580c",
              background: "#fff",
              borderRadius: "4px"
            }}
          >
            {m.code} - {m.label}
          </Button>
        ))}
      </div>
    </div>
  );
};

const OptionsCard: React.FC<{ options: any[]; onSelect?: (text: string) => void }> = ({ options, onSelect }) => {
  return (
    <div style={{
      background: "#f0fdf4",
      border: "1px solid #bbf7d0",
      borderRadius: "8px",
      padding: "12px 16px",
      margin: "8px 0",
      width: "100%"
    }}>
      <div style={{ fontWeight: "bold", marginBottom: "8px", color: "#14532d", fontSize: "13px" }}>
        💡 Select an Option to Proceed:
      </div>
      <div style={{ display: "flex", gap: "8px", flexDirection: "column" }}>
        {options.map((opt, idx) => (
          <Button
            key={idx}
            size="middle"
            onClick={() => onSelect && onSelect(opt.text)}
            style={{
              borderColor: "#16a34a",
              color: "#16a34a",
              background: "#fff",
              borderRadius: "6px",
              textAlign: "left",
              fontWeight: "500",
              height: "auto",
              padding: "6px 12px",
              whiteSpace: "normal"
            }}
          >
            {opt.label}
          </Button>
        ))}
      </div>
    </div>
  );
};

const ConfirmCard: React.FC<{ data: any; onSelect?: (val: string) => void }> = ({ data, onSelect }) => {
  return (
    <div style={{
      background: "#fffbeb",
      border: "1px solid #fde68a",
      borderRadius: "8px",
      padding: "12px 16px",
      margin: "8px 0",
      width: "100%",
      display: "flex",
      flexDirection: "column",
      gap: "10px"
    }}>
      <div style={{ fontWeight: "bold", color: "#78350f", fontSize: "13px" }}>
        ❓ Confirmation Required:
      </div>
      <div style={{ fontSize: "12px", color: "#92400e" }}>
        {data.question || "Would you like to proceed?"}
      </div>
      <div style={{ display: "flex", gap: "8px" }}>
        <Button
          type="primary"
          size="small"
          onClick={() => onSelect && onSelect(data.yes_text || "Yes")}
          style={{ background: "#10b981", border: "none", borderRadius: "4px", fontWeight: "bold" }}
        >
          {data.yes_label || "Yes, proceed"}
        </Button>
        <Button
          danger
          size="small"
          onClick={() => onSelect && onSelect(data.no_text || "No")}
          style={{ borderRadius: "4px", fontWeight: "bold" }}
        >
          {data.no_label || "No, cancel"}
        </Button>
      </div>
    </div>
  );
};

interface ChatMessageProps {
  message: MessageType;
  onSelectSource?: (index: number) => void;
  onSendMessage?: (text: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = React.memo(({ message, onSelectSource, onSendMessage }) => {
  const isUser = message.role === "user";
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  // Pre-process raw text to transform bracket citations into custom markdown links
  // e.g. [walmart_code_of_conduct.pdf, Page 23] -> [[2]](cite:1)
  const preprocessCitations = (text: string, sources: ChunkSource[] = []) => {
    if (!text) return "";
    
    // Regex matches [filename.pdf, Page X]
    const regex = /\[([^\]]+?\.pdf),\s*(Page\s*\d+)\]/g;
    
    return text.replace(regex, (fullMatch, docName, pageLabel) => {
      const sourceIdx = sources.findIndex(
        s => s.document_name.toLowerCase() === docName.toLowerCase() &&
             s.page_label.toLowerCase().replace(/\s+/g, "").includes(pageLabel.toLowerCase().replace(/\s+/g, ""))
      );
      
      if (sourceIdx !== -1) {
        return `[[${sourceIdx + 1}]](cite:${sourceIdx})`;
      }
      return fullMatch;
    });
  };

  // Determine which sources to display under the message bubble
  const displayedSources = message.citations && message.citations.length > 0
    ? message.citations.map(c => ({
        index: c.index,
        document_name: c.document_name,
        page_label: c.page_label,
        similarity: c.similarity
      }))
    : (message.sources || []).map((s, idx) => ({
        index: idx + 1,
        document_name: s.document_name,
        page_label: s.page_label,
        similarity: s.similarity
      }));

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
        marginBottom: "20px",
        width: "100%"
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: isUser ? "row-reverse" : "row",
          alignItems: "flex-start",
          maxWidth: "85%",
          gap: "12px"
        }}
      >
        <Avatar
          icon={isUser ? <UserOutlined /> : <RobotOutlined />}
          style={{
            backgroundColor: isUser ? "#1890ff" : "#87d068",
            flexShrink: 0,
            marginTop: "4px"
          }}
        />

        <div style={{ display: "flex", flexDirection: "column" }}>
          {/* Sender Name */}
          <Text
            type="secondary"
            style={{
              fontSize: "12px",
              marginBottom: "4px",
              textAlign: isUser ? "right" : "left",
              fontWeight: 500
            }}
          >
            {isUser ? "You" : "RAG Assistant"}
          </Text>

          {/* Bubble */}
          <div
            style={{
              backgroundColor: isUser ? "#1890ff" : "#ffffff",
              color: isUser ? "#ffffff" : "#000000",
              padding: "12px 16px",
              borderRadius: isUser ? "12px 12px 0 12px" : "12px 12px 12px 0",
              boxShadow: "0 2px 8px rgba(0, 0, 0, 0.05)",
              border: isUser ? "none" : "1px solid #f0f0f0",
              whiteSpace: isUser ? "pre-wrap" : "normal",
              fontSize: "14px",
              lineHeight: "1.5",
              textAlign: "left"
            }}
          >
            {isUser ? (
              message.content
            ) : (
              <ReactMarkdown
                components={{
                  a: ({ href, children }) => {
                    if (href && href.startsWith("cite:")) {
                      const sourceIdx = parseInt(href.substring(5), 10);
                      const source = message.sources ? message.sources[sourceIdx] : null;
                      const displayIndex = sourceIdx + 1;
                      
                      if (source) {
                        return (
                          <Tooltip title={`${source.document_name} (${source.page_label})`}>
                            <Tag
                              color="blue"
                              style={{
                                cursor: "pointer",
                                margin: "0 2px",
                                padding: "0 4px",
                                fontSize: "12px",
                                fontWeight: "bold",
                                lineHeight: "1.4",
                                borderRadius: "4px",
                                display: "inline-block"
                              }}
                              onClick={() => onSelectSource && onSelectSource(sourceIdx)}
                            >
                              [{displayIndex}]
                            </Tag>
                          </Tooltip>
                        );
                      }
                    }
                    return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
                  },
                  p: ({ children }) => <p style={{ margin: "0 0 8px 0", lineHeight: "1.5" }}>{children}</p>,
                  ul: ({ children }) => <ul style={{ margin: "0 0 8px 0", paddingLeft: "20px" }}>{children}</ul>,
                  ol: ({ children }) => <ol style={{ margin: "0 0 8px 0", paddingLeft: "20px" }}>{children}</ol>,
                  li: ({ children }) => <li style={{ marginBottom: "4px" }}>{children}</li>,
                  code: ({ inline, className, children, ...props }: any) => {
                    const match = /language-(\w+)/.exec(className || "");
                    let lang = match ? match[1] : "";
                    const content = String(children).replace(/\n$/, "");

                    if (!inline) {
                      let parsedData: any = null;
                      let isJson = false;
                      try {
                        parsedData = JSON.parse(content);
                        isJson = true;
                      } catch (e) {
                        // Not valid JSON
                      }

                      if (isJson && parsedData !== null) {
                        // Auto-detect schema if language is "json" or not specified
                        if (lang === "json" || lang === "") {
                          if (Array.isArray(parsedData)) {
                            if (parsedData.length > 0) {
                              const first = parsedData[0];
                              if (first.flight_number && (first.origin || first.destination)) {
                                lang = "flights";
                              } else if (first.pnr && first.passenger_name) {
                                lang = "tickets";
                              } else if (first.code && first.label) {
                                lang = "meal-options";
                              } else if (first.label && first.text) {
                                lang = "options";
                              }
                            }
                          } else {
                            if (parsedData.pnr && (parsedData.flight_id || parsedData.flight_number) && parsedData.passenger_id) {
                              lang = "seats-options";
                            } else if (parsedData.pnr && (parsedData.price !== undefined || parsedData.amount !== undefined) && parsedData.flight_number) {
                              lang = "payment";
                            } else if (parsedData.name && parsedData.email) {
                              lang = "passenger-review";
                            } else if (parsedData.question && parsedData.yes_text && parsedData.no_text) {
                              lang = "confirm";
                            }
                          }
                        }

                        // Render appropriate custom card component
                        if (lang === "flights" && Array.isArray(parsedData)) {
                          return (
                            <FlightsCardList 
                              flights={parsedData} 
                              onSelect={(flightNumber, date) => onSendMessage?.(`I want to book flight ${flightNumber} on ${date}`)} 
                            />
                          );
                        }
                        if (lang === "tickets" && Array.isArray(parsedData)) {
                          return <TicketsCardList bookings={parsedData} onSendMessage={onSendMessage} />;
                        }
                        if (lang === "payment") {
                          return <PaymentLinkCard payment={parsedData} />;
                        }
                        if (lang === "passenger-review") {
                          return (
                            <PassengerReviewCard 
                              data={parsedData} 
                              onConfirm={() => onSendMessage?.(`I confirm my passenger details: Name: ${parsedData.name}, Email: ${parsedData.email}. Please proceed.`)}
                            />
                          );
                        }
                        if (lang === "seats-options") {
                          if (parsedData.flight_number && !parsedData.flight_id) {
                            parsedData.flight_id = parsedData.flight_number;
                          }
                          return (
                            <SeatsOptionsCard 
                              seats={parsedData} 
                              onSelect={(seat) => onSendMessage?.(`I want to choose seat ${seat}`)}
                            />
                          );
                        }
                        if (lang === "meal-options" && Array.isArray(parsedData)) {
                          return (
                            <MealOptionsCard 
                              meals={parsedData} 
                              onSelect={(code) => onSendMessage?.(`I select meal option ${code}`)}
                            />
                          );
                        }
                        if (lang === "options" && Array.isArray(parsedData)) {
                          return (
                            <OptionsCard 
                              options={parsedData} 
                              onSelect={(text) => onSendMessage?.(text)}
                            />
                          );
                        }
                        if (lang === "confirm") {
                          return (
                            <ConfirmCard 
                              data={parsedData} 
                              onSelect={(text) => onSendMessage?.(text)}
                            />
                          );
                        }
                      }

                      return <pre className={className} {...props}><code>{children}</code></pre>;
                    }

                    return <code className={className} {...props}>{children}</code>;
                  }
                }}
              >
                {preprocessCitations(message.content, message.sources)}
              </ReactMarkdown>
            )}
            {message.isStreaming && message.content === "" && (
              <span className="streaming-dots">
                <span className="dot">.</span>
                <span className="dot">.</span>
                <span className="dot">.</span>
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Metrics (TTFT, Latency, Tokens, Cost) */}
      {!isUser && message.metrics && (
        <div
          style={{
            marginLeft: "48px",
            marginTop: "6px",
            fontSize: "11px",
            color: "#8c8c8c",
            display: "flex",
            flexWrap: "wrap",
            gap: "12px",
            alignItems: "center",
            background: "#fafafa",
            padding: "4px 10px",
            borderRadius: "6px",
            border: "1px dashed #e8e8e8",
            maxWidth: "80%"
          }}
        >
          <span>⚡ TTFT: <strong>{message.metrics.ttft_ms.toFixed(0)}ms</strong></span>
          <span>⏱️ Latency: <strong>{(message.metrics.latency_ms / 1000).toFixed(2)}s</strong></span>
          <span>📥 Input: <strong>{message.metrics.input_tokens} tkn</strong></span>
          <span>📤 Output: <strong>{message.metrics.output_tokens} tkn</strong></span>
          <span>🪙 Cost: <strong>${message.metrics.cost_usd.toFixed(6)}</strong></span>
        </div>
      )}

      {/* Sources / Citations list */}
      {!isUser && displayedSources.length > 0 && (
        <div
          style={{
            marginLeft: "48px",
            marginTop: "8px",
            maxWidth: "80%"
          }}
        >
          <Button
            type="text"
            size="small"
            icon={sourcesExpanded ? <UpOutlined /> : <DownOutlined />}
            onClick={() => setSourcesExpanded(!sourcesExpanded)}
            style={{
              fontSize: "12px",
              color: "#8c8c8c",
              padding: "0 4px",
              height: "auto",
              display: "flex",
              alignItems: "center"
            }}
          >
            <FileTextOutlined style={{ marginRight: "4px" }} />
            {sourcesExpanded 
              ? "Hide Sources" 
              : message.citations && message.citations.length > 0 
                ? `View Cited Sources (${message.citations.length})`
                : `View Sources (${displayedSources.length})`
            }
          </Button>

          {sourcesExpanded && (
            <div
              style={{
                marginTop: "6px",
                background: "#f9f9f9",
                border: "1px solid #f0f0f0",
                borderRadius: "6px",
                padding: "8px 12px",
                display: "flex",
                flexDirection: "column",
                gap: "6px"
              }}
            >
              {displayedSources.map((source, idx) => {
                const originalIdx = message.sources
                  ? message.sources.findIndex(
                      s => s.document_name.toLowerCase() === source.document_name.toLowerCase() &&
                           s.page_label.toLowerCase().replace(/\s+/g, "").includes(source.page_label.toLowerCase().replace(/\s+/g, ""))
                    )
                  : -1;

                return (
                  <div
                    key={idx}
                    style={{
                      fontSize: "12px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "8px"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", overflow: "hidden" }}>
                      <span style={{ color: "#1890ff", fontWeight: "bold" }}>[{source.index}]</span>
                      <Text ellipsis style={{ maxWidth: "200px", fontSize: "12px" }}>
                        {source.document_name}
                      </Text>
                      <Tag color="blue" style={{ fontSize: "10px", margin: 0, padding: "0 4px" }}>
                        {source.page_label}
                      </Tag>
                    </div>
                    {onSelectSource && originalIdx !== -1 && (
                      <Button
                        type="link"
                        size="small"
                        onClick={() => onSelectSource(originalIdx)}
                        style={{ fontSize: "11px", padding: 0, height: "auto" }}
                      >
                        Inspect Chunk
                      </Button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}, (prevProps, nextProps) => {
  return (
    prevProps.message.content === nextProps.message.content &&
    prevProps.message.isStreaming === nextProps.message.isStreaming &&
    prevProps.message.citations?.length === nextProps.message.citations?.length &&
    prevProps.message.metrics?.latency_ms === nextProps.message.metrics?.latency_ms
  );
});
