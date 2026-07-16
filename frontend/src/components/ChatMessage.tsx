import React, { useState, useRef } from "react";
import { Avatar, Typography, Button, Tag, Tooltip, Modal, Slider, Input, message } from "antd";
import { UserOutlined, RobotOutlined, FileTextOutlined, DownOutlined, UpOutlined } from "@ant-design/icons";
import ReactMarkdown from "react-markdown";
import type { ChatMessage as MessageType, ChunkSource } from "../types/chat";
import { PSS_API_URL } from "../services/api";


const { Text } = Typography;

const FlightsCardList: React.FC<{
  flights: any[];
  onSelect?: (flightNumber: string, date: string, bookingClass: string) => void;
}> = ({ flights, onSelect }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", margin: "12px 0", width: "100%" }}>
      {flights.map((flight, index) => {
        const fareOptions = flight.fares || [
          { class: "Economy Flex", booking_class: "Y", price: flight.price || 300, benefits: "Refundable, changeable, 23kg bag" }
        ];

        return (
          <div key={index} style={{
            background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
            color: "#fff",
            padding: "12px 14px",
            borderRadius: "12px",
            border: "1px solid #334155",
            boxShadow: "0 6px 12px rgba(0,0,0,0.2)",
            display: "flex",
            flexDirection: "column",
            gap: "10px"
          }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontWeight: "bold", color: "#38bdf8", fontSize: "14px" }}>
                ✈️ {flight.airline || "Apex Air"} ({flight.flight_number})
              </span>
              <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                {flight.direction && (
                  <span style={{ 
                    fontSize: "9px", 
                    fontWeight: "bold",
                    color: "#fff", 
                    background: flight.direction === "outbound" ? "#0284c7" : "#7c3aed", 
                    padding: "2px 8px", 
                    borderRadius: "12px",
                    textTransform: "uppercase"
                  }}>
                    {flight.direction}
                  </span>
                )}
                <span style={{ fontSize: "10px", color: "#94a3b8", background: "#334155", padding: "2px 8px", borderRadius: "12px" }}>
                  Scheduled
                </span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "4px" }}>
              <div>
                <div style={{ fontSize: "18px", fontWeight: "800" }}>{flight.origin}</div>
                <div style={{ fontSize: "10px", color: "#64748b" }}>Origin</div>
              </div>
              <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 10px", position: "relative" }}>
                <span style={{ fontSize: "14px", color: "#38bdf8", transform: "translateY(-4px)" }}>✈</span>
                <div style={{ borderTop: "1.5px dashed #475569", width: "100%", marginTop: "-4px" }} />
              </div>
              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: "18px", fontWeight: "800" }}>{flight.destination}</div>
                <div style={{ fontSize: "10px", color: "#64748b" }}>Destination</div>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "11px", color: "#94a3b8", borderBottom: "1px solid #334155", paddingBottom: "8px" }}>
              <span>Departure: <strong>{flight.departure_time || "N/A"}</strong></span>
              <span>Date: <strong>{flight.date || "Anydate"}</strong></span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "4px" }}>
              <div style={{ fontSize: "10px", fontWeight: "bold", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                Select Fare Family
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                {fareOptions.map((fare: any, fIdx: number) => {
                  const isBusiness = fare.class?.toLowerCase().includes("business");
                  const isFlex = fare.class?.toLowerCase().includes("flex");
                  const badgeColor = isBusiness ? "#a78bfa" : isFlex ? "#34d399" : "#38bdf8";

                  return (
                    <div
                      key={fIdx}
                      style={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "8px",
                        padding: "8px 10px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <div style={{ display: "flex", flexDirection: "column", gap: "2px", maxWidth: "70%" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ fontSize: "12px", fontWeight: "bold", color: "#fff" }}>{fare.class}</span>
                          <span style={{ fontSize: "9px", background: `${badgeColor}22`, color: badgeColor, border: `1px solid ${badgeColor}44`, padding: "1px 6px", borderRadius: "4px", fontWeight: "bold" }}>
                            {fare.booking_class}
                          </span>
                        </div>
                        <span style={{ fontSize: "9.5px", color: "#94a3b8" }}>{fare.benefits}</span>
                      </div>
                      
                      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "4px" }}>
                        <span style={{ fontSize: "14px", fontWeight: "bold", color: "#34d399" }}>${fare.price}</span>
                        {onSelect && (
                          <Button
                            size="small"
                            type="primary"
                            style={{
                              background: "transparent",
                              border: "1px solid #38bdf8",
                              color: "#38bdf8",
                              borderRadius: "4px",
                              fontSize: "10px",
                              fontWeight: "bold",
                              height: "22px",
                              lineHeight: "20px"
                            }}
                            onClick={() => onSelect(flight.flight_number, flight.date, fare.booking_class)}
                          >
                            Book
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

          </div>
        );
      })}
    </div>
  );
};

const AncillaryOptionsCard: React.FC<{
  ancillaries: any[];
  onSelect?: (messageText: string) => void;
}> = ({ ancillaries, onSelect }) => {
  const [selected, setSelected] = useState<Record<number, boolean>>({});

  const handleToggle = (idx: number) => {
    setSelected((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleConfirm = () => {
    const chosen = ancillaries.filter((_, idx) => selected[idx]);
    if (chosen.length === 0) return;
    
    const pnr = chosen[0].pnr || "my booking";
    const descriptions = chosen.map((c) => `add ${c.type} ancillary for ${c.amount} USD`).join(" and ");
    const msg = `I want to add the following to booking ${pnr}: ${descriptions}`;
    if (onSelect) {
      onSelect(msg);
    }
  };

  return (
    <div style={{
      background: "#f8fafc",
      border: "1px solid #e2e8f0",
      borderRadius: "10px",
      padding: "14px 16px",
      margin: "12px 0",
      width: "100%",
      boxShadow: "0 4px 6px rgba(0,0,0,0.05)"
    }}>
      <div style={{ fontWeight: "bold", fontSize: "14px", color: "#1e293b", marginBottom: "4px" }}>
        💼 Inflight Comforts & Extra Services
      </div>
      <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "12px" }}>
        Customize your trip by selecting additional ancillaries below:
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginBottom: "12px" }}>
        {ancillaries.map((anc, idx) => (
          <div
            key={idx}
            onClick={() => handleToggle(idx)}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              padding: "10px 12px",
              background: selected[idx] ? "#f0f9ff" : "#fff",
              border: `1px solid ${selected[idx] ? "#0ea5e9" : "#cbd5e1"}`,
              borderRadius: "6px",
              cursor: "pointer",
              transition: "all 0.2s"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <input
                type="checkbox"
                checked={!!selected[idx]}
                onChange={() => {}}
                style={{ cursor: "pointer" }}
              />
              <span style={{ fontSize: "12px", fontWeight: "600", color: "#334155" }}>
                {anc.label}
              </span>
            </div>
            <span style={{ fontSize: "12px", fontWeight: "bold", color: "#10b981" }}>
              +${anc.amount}
            </span>
          </div>
        ))}
      </div>
      <Button
        type="primary"
        onClick={handleConfirm}
        disabled={!Object.values(selected).some(Boolean)}
        style={{
          width: "100%",
          background: "#0ea5e9",
          border: "none",
          fontWeight: "bold",
          borderRadius: "6px",
          height: "36px"
        }}
      >
        Add Selected to Booking
      </Button>
    </div>
  );
};

const CheckinDeclarationCard: React.FC<{
  pnr: string;
  passengerName?: string;
  onConfirm?: () => void;
}> = ({ pnr, passengerName, onConfirm }) => {
  const [declared, setDeclared] = useState(false);

  return (
    <div style={{
      background: "linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)",
      border: "1px solid #cbd5e1",
      borderRadius: "12px",
      padding: "16px",
      margin: "12px 0",
      boxShadow: "0 4px 10px rgba(0,0,0,0.05)",
      width: "100%",
      color: "#1e293b"
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", borderBottom: "1px solid #e2e8f0", paddingBottom: "10px", marginBottom: "12px" }}>
        <span style={{ fontSize: "20px" }}>⚠️</span>
        <div>
          <div style={{ fontWeight: "800", fontSize: "14px", color: "#0f172a" }}>
            Hazardous Materials Safety Declaration
          </div>
          <div style={{ fontSize: "11px", color: "#64748b" }}>
            Required for PNR: <strong>{pnr}</strong> {passengerName ? `(${passengerName})` : ""}
          </div>
        </div>
      </div>

      <div style={{ fontSize: "11px", color: "#334155", lineHeight: "1.5", marginBottom: "14px", background: "#fff1f2", border: "1px solid #ffe4e6", borderRadius: "8px", padding: "10px 12px" }}>
        <strong style={{ color: "#be123c", display: "block", marginBottom: "4px" }}>Prohibited Dangerous Goods:</strong>
        To ensure flight safety, civil aviation regulations strictly prohibit passengers from carrying dangerous goods in checked or carry-on baggage. These include:
        <ul style={{ margin: "6px 0 0 0", paddingLeft: "16px" }}>
          <li>Explosives, fireworks, flares, and ammunition.</li>
          <li>Lithium-ion batteries (above 100Wh) or loose power banks in checked bags.</li>
          <li>Flammable liquids, lighter fuels, aerosols, and matches.</li>
          <li>Corrosives, toxic substances, radioactive or infectious materials.</li>
        </ul>
      </div>

      <div 
        onClick={() => setDeclared(!declared)}
        style={{
          display: "flex",
          alignItems: "flex-start",
          gap: "10px",
          padding: "10px",
          background: declared ? "#f0fdf4" : "#f8fafc",
          border: `1px solid ${declared ? "#4ade80" : "#cbd5e1"}`,
          borderRadius: "8px",
          cursor: "pointer",
          marginBottom: "14px",
          transition: "all 0.2s"
        }}
      >
        <input 
          type="checkbox" 
          checked={declared} 
          onChange={() => {}} 
          style={{ marginTop: "3px", cursor: "pointer" }}
        />
        <span style={{ fontSize: "11px", fontWeight: "600", color: "#334155", userSelect: "none" }}>
          I declare that I have read the hazardous materials list and certify that none of these items are present in my baggage.
        </span>
      </div>

      <Button
        type="primary"
        onClick={onConfirm}
        disabled={!declared}
        style={{
          width: "100%",
          background: declared ? "#22c55e" : "#cbd5e1",
          borderColor: declared ? "#22c55e" : "#cbd5e1",
          fontWeight: "bold",
          borderRadius: "6px",
          height: "36px"
        }}
      >
        Confirm Safety Declaration & Proceed
      </Button>
    </div>
  );
};

const TicketsCardList: React.FC<{ bookings: any[]; onSendMessage?: (text: string) => void }> = ({ bookings, onSendMessage }) => {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", margin: "8px 0", width: "100%" }}>
      {bookings.map((booking, index) => {
        const isPaid = booking.status === "booked" || booking.status === "confirmed" || booking.status === "ticketed";
        const isPending = booking.status === "pending-payment" || booking.status === "held";
        const isCheckedIn = booking.status === "checked-in" || booking.status === "checked_in";
        const isBoarded = booking.status === "boarded";
        const isCancelled = booking.status === "cancelled";

        const accentColor = isBoarded ? "#6366f1"
          : isCheckedIn ? "#0ea5e9"
          : isPaid ? "#10b981"
          : isPending ? "#f59e0b"
          : "#ef4444";

        const tagColor = isBoarded ? "purple"
          : isCheckedIn ? "blue"
          : isPaid ? "green"
          : isPending ? "gold"
          : "red";

        if (isCheckedIn) {
          return (
            <div key={index} style={{
              background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
              color: "#fff",
              borderRadius: "16px",
              border: "1px dashed #38bdf8",
              boxShadow: "0 8px 20px rgba(0,0,0,0.3)",
              padding: "16px",
              position: "relative",
              overflow: "hidden"
            }}>
              {/* Notch cut-outs */}
              <div style={{ position: "absolute", left: "-8px", top: "50%", transform: "translateY(-50%)", width: "16px", height: "16px", borderRadius: "50%", background: "#f1f5f9", borderRight: "1.5px dashed #38bdf8", zIndex: 2 }} />
              <div style={{ position: "absolute", right: "-8px", top: "50%", transform: "translateY(-50%)", width: "16px", height: "16px", borderRadius: "50%", background: "#f1f5f9", borderLeft: "1.5px dashed #38bdf8", zIndex: 2 }} />

              {/* Header */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px dashed #334155", paddingBottom: "10px", marginBottom: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  <span style={{ fontSize: "16px" }}>🎫</span>
                  <span style={{ fontWeight: "800", color: "#38bdf8", fontSize: "11px", letterSpacing: "1.5px", textTransform: "uppercase" }}>
                    {booking.airline || "APEX AIR"} BOARDING PASS
                  </span>
                </div>
                <Tag color="cyan" style={{ margin: 0, fontWeight: "bold", fontSize: "10px" }}>
                  BOARDING
                </Tag>
              </div>

              {/* Route */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
                <div>
                  <div style={{ fontSize: "28px", fontWeight: "900", color: "#fff", lineHeight: "1", letterSpacing: "0.5px" }}>{booking.origin}</div>
                  <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase", marginTop: "2px" }}>{booking.origin_city || "Departure"}</div>
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 14px", position: "relative" }}>
                  <span style={{ fontSize: "14px", color: "#38bdf8", transform: "translateY(-4px)" }}>✈</span>
                  <div style={{ borderTop: "1.5px dashed #475569", width: "100%", marginTop: "-4px" }} />
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "28px", fontWeight: "900", color: "#fff", lineHeight: "1", letterSpacing: "0.5px" }}>{booking.destination}</div>
                  <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase", marginTop: "2px" }}>{booking.destination_city || "Arrival"}</div>
                </div>
              </div>

              {/* Details grid */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: "10px 14px",
                borderBottom: "1px dashed #334155",
                paddingBottom: "12px",
                marginBottom: "12px",
                fontSize: "11px"
              }}>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Passenger</div>
                  <div style={{ fontWeight: "700", color: "#fff", marginTop: "2px" }}>{booking.passenger_name || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Flight</div>
                  <div style={{ fontWeight: "700", color: "#fff", fontFamily: "monospace", marginTop: "2px" }}>{booking.flight_number || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Date</div>
                  <div style={{ fontWeight: "700", color: "#fff", marginTop: "2px" }}>{booking.date || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Seat</div>
                  <div style={{ marginTop: "2px" }}>
                    <span style={{
                      fontWeight: "900", color: "#000",
                      background: "#34d399", padding: "1px 6px",
                      borderRadius: "4px", fontFamily: "monospace", fontSize: "12px"
                    }}>
                      {booking.seat || "TBD"}
                    </span>
                  </div>
                </div>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Gate</div>
                  <div style={{ marginTop: "2px" }}>
                    <span style={{
                      fontWeight: "900", color: "#000",
                      background: "#a78bfa", padding: "1px 6px",
                      borderRadius: "4px", fontFamily: "monospace", fontSize: "12px"
                    }}>
                      {booking.gate || "B3"}
                    </span>
                  </div>
                </div>
                <div>
                  <div style={{ color: "#64748b", fontSize: "8.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.5px" }}>Class</div>
                  <div style={{ fontWeight: "700", color: "#38bdf8", marginTop: "2px", textTransform: "uppercase", fontSize: "10px" }}>
                    {booking.cabin_class || "Economy"}
                  </div>
                </div>
              </div>

              {/* Barcode & PNR Stub */}
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px", background: "#fff", padding: "10px", borderRadius: "8px" }}>
                <div style={{ display: "flex", height: "35px", width: "100%", justifyContent: "center", overflow: "hidden", opacity: 0.9 }}>
                  {Array.from({ length: 42 }).map((_, i) => (
                    <div key={i} style={{
                      width: `${(i % 3 === 0 ? 3 : (i % 2 === 0 ? 1 : 2))}px`,
                      backgroundColor: "#000",
                      marginRight: `${(i % 5 === 0 ? 2 : 1)}px`,
                      height: "100%"
                    }} />
                  ))}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", width: "100%", fontSize: "9px", fontFamily: "monospace", color: "#64748b", fontWeight: "bold" }}>
                  <span>PNR: {booking.pnr}</span>
                  <span>SEQ: 00{index + 1}</span>
                </div>
              </div>
            </div>
          );
        }

        return (
          <div key={index} style={{
            background: "#ffffff",
            color: "#1e293b",
            borderRadius: "12px",
            border: `1px solid ${isCancelled ? "#fecaca" : "#e2e8f0"}`,
            boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
            overflow: "hidden",
            opacity: isCancelled ? 0.75 : 1,
          }}>
            {/* Card Header — airline + PNR + status */}
            <div style={{
              background: `linear-gradient(90deg, #0f172a, #1e293b)`,
              padding: "10px 14px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: `2px solid ${accentColor}`,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontSize: "14px" }}>✈️</span>
                <span style={{ color: "#38bdf8", fontWeight: "700", fontSize: "11px", letterSpacing: "1px", textTransform: "uppercase" }}>
                  {booking.airline || "APEX AIRLINES"}
                </span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#94a3b8", background: "#0f172a", padding: "2px 8px", borderRadius: "4px", fontWeight: "bold" }}>
                  {booking.pnr}
                </span>
                <Tag color={tagColor} style={{ margin: 0, fontWeight: "bold", fontSize: "10px" }}>
                  {booking.status?.toUpperCase().replace(/_/g, "-")}
                </Tag>
              </div>
            </div>

            {/* Route row */}
            <div style={{ padding: "12px 14px 8px 14px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                <div>
                  <div style={{ fontSize: "22px", fontWeight: "800", color: "#0f172a", lineHeight: "1" }}>{booking.origin}</div>
                  <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase", marginTop: "2px" }}>Origin</div>
                </div>
                <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 10px" }}>
                  <span style={{ fontSize: "14px", color: "#38bdf8" }}>✈</span>
                  <div style={{ width: "100%", borderTop: "1.5px dashed #cbd5e1", marginTop: "2px" }} />
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "22px", fontWeight: "800", color: "#0f172a", lineHeight: "1" }}>{booking.destination}</div>
                  <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase", marginTop: "2px" }}>Destination</div>
                </div>
              </div>

              {/* Details grid — all available fields */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr 1fr",
                gap: "8px 12px",
                borderTop: "1px solid #f1f5f9",
                paddingTop: "10px",
                fontSize: "11px"
              }}>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Passenger</div>
                  <div style={{ fontWeight: "700", color: "#1e293b", marginTop: "2px" }}>{booking.passenger_name || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Flight</div>
                  <div style={{ fontWeight: "700", color: "#1e293b", fontFamily: "monospace", marginTop: "2px" }}>{booking.flight_number || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Date</div>
                  <div style={{ fontWeight: "700", color: "#1e293b", marginTop: "2px" }}>{booking.date || "—"}</div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Seat</div>
                  <div style={{ marginTop: "2px" }}>
                    {booking.seat ? (
                      <span style={{
                        fontWeight: "800", color: "#0284c7",
                        background: "#e0f2fe", padding: "2px 8px",
                        borderRadius: "4px", fontFamily: "monospace", fontSize: "12px"
                      }}>
                        {booking.seat}
                      </span>
                    ) : (
                      <span style={{ color: "#94a3b8", fontStyle: "italic", fontSize: "10px" }}>Not assigned</span>
                    )}
                  </div>
                </div>
                <div>
                  <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Gate</div>
                  <div style={{ marginTop: "2px" }}>
                    {booking.gate ? (
                      <span style={{
                        fontWeight: "800", color: "#7c3aed",
                        background: "#ede9fe", padding: "2px 8px",
                        borderRadius: "4px", fontFamily: "monospace", fontSize: "12px"
                      }}>
                        {booking.gate}
                      </span>
                    ) : (
                      <span style={{ color: "#94a3b8", fontStyle: "italic", fontSize: "10px" }}>TBD</span>
                    )}
                  </div>
                </div>
                {booking.cabin_class && (
                  <div>
                    <div style={{ color: "#94a3b8", fontSize: "9px", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.5px" }}>Class</div>
                    <div style={{ fontWeight: "700", color: "#1e293b", marginTop: "2px", textTransform: "capitalize" }}>{booking.cabin_class}</div>
                  </div>
                )}
              </div>

              {/* Status-specific banners */}
              {isBoarded && (
                <div style={{ marginTop: "8px", background: "#f5f3ff", border: "1px solid #ddd6fe", borderRadius: "6px", padding: "6px 10px", fontSize: "11px", color: "#6d28d9", display: "flex", alignItems: "center", gap: "6px" }}>
                  🛫 <strong>Boarded</strong> — Have a great flight!
                </div>
              )}
              {isCancelled && (
                <div style={{ marginTop: "8px", background: "#fff1f2", border: "1px solid #fecdd3", borderRadius: "6px", padding: "6px 10px", fontSize: "11px", color: "#be123c", display: "flex", alignItems: "center", gap: "6px" }}>
                  ❌ <strong>Cancelled</strong> — This ticket is no longer valid.
                </div>
              )}
            </div>

            {/* Action bar */}
            {(isPending || (!isCancelled && !isBoarded && onSendMessage)) && (
              <div style={{ padding: "8px 14px 10px 14px", borderTop: "1px dashed #e2e8f0", display: "flex", gap: "6px", flexWrap: "wrap", alignItems: "center" }}>
                {isPending && (
                  <Button
                    type="primary"
                    size="small"
                    href={`/payment?pnr=${booking.pnr}&amount=150&flight=${booking.flight_number}&origin=${booking.origin}&destination=${booking.destination}&date=${booking.date}&passenger_id=${booking.passenger_id || ""}`}
                    target="_blank"
                    rel="opener"
                    style={{ fontSize: "11px", background: "#f59e0b", border: "none", borderRadius: "6px", fontWeight: "bold" }}
                  >
                    💳 Complete Payment
                  </Button>
                )}
                {onSendMessage && !isPending && !isBoarded && !isCancelled && (
                  <>
                    {!booking.seat && (
                      <Button size="small" onClick={() => onSendMessage(`Select seat for my booking ${booking.pnr}`)} style={{ fontSize: "11px", borderRadius: "4px" }}>
                        💺 Choose Seat
                      </Button>
                    )}
                    <Button size="small" onClick={() => onSendMessage(`Choose meal option for booking ${booking.pnr}`)} style={{ fontSize: "11px", borderRadius: "4px" }}>
                      🍱 Meal
                    </Button>
                    {!isCheckedIn && (
                      <Button size="small" onClick={() => onSendMessage(`Reschedule booking ${booking.pnr}`)} style={{ fontSize: "11px", borderRadius: "4px" }}>
                        🔄 Reschedule
                      </Button>
                    )}
                    {!isCheckedIn && (
                      <Button size="small" onClick={() => onSendMessage(`Check in for booking ${booking.pnr}`)} style={{ fontSize: "11px", borderRadius: "4px", background: "#f0f9ff", borderColor: "#0ea5e9", color: "#0ea5e9" }}>
                        🎫 Check In
                      </Button>
                    )}
                    <Button danger size="small" onClick={() => onSendMessage(`Cancel booking ${booking.pnr}`)} style={{ fontSize: "11px", borderRadius: "4px" }}>
                      ❌ Cancel
                    </Button>
                  </>
                )}
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
      padding: "12px 14px",
      borderRadius: "10px",
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

const PassengerReviewCard: React.FC<{ data: any; onConfirm?: (paxList: any[]) => void }> = ({ data, onConfirm }) => {
  // If data has passengers list, use it. Otherwise, construct a default list with 1 passenger.
  const initialPassengers = Array.isArray(data.passengers) && data.passengers.length > 0
    ? data.passengers.map((p: any) => ({
        first_name: p.first_name || "",
        last_name: p.last_name || "",
        email: p.email || "",
        passenger_type: p.passenger_type || "ADT",
        title: p.title || "MR"
      }))
    : [{
        first_name: data.first_name || data.name?.split(" ")[0] || "",
        last_name: data.last_name || data.name?.split(" ").slice(1).join(" ") || "",
        email: data.email || "",
        passenger_type: "ADT",
        title: "MR"
      }];

  const [passengers, setPassengers] = useState<any[]>(initialPassengers);

  const updatePassenger = (index: number, key: string, val: string) => {
    const updated = [...passengers];
    updated[index] = { ...updated[index], [key]: val };
    setPassengers(updated);
  };

  const handleConfirm = () => {
    for (let i = 0; i < passengers.length; i++) {
      if (!passengers[i].first_name || !passengers[i].last_name) {
        message.warning(`Please fill in name for passenger ${i + 1}`);
        return;
      }
    }
    if (onConfirm) {
      onConfirm(passengers);
    }
  };

  return (
    <div style={{
      background: "linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%)",
      border: "1px solid #bae6fd",
      borderLeft: "4px solid #0284c7",
      borderRadius: "10px",
      padding: "16px",
      margin: "8px 0",
      color: "#0c4a6e",
      width: "100%",
      boxShadow: "0 2px 8px rgba(2, 132, 199, 0.08)"
    }}>
      <div style={{ fontWeight: "700", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px", fontSize: "14px" }}>
        <span>📋</span> Passenger Details Review
      </div>
      
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
        {passengers.map((pax, idx) => (
          <div key={idx} style={{
            background: "rgba(255, 255, 255, 0.6)",
            border: "1px solid #e0f2fe",
            borderRadius: "8px",
            padding: "12px"
          }}>
            <div style={{ fontWeight: "600", fontSize: "12px", color: "#0369a1", marginBottom: "8px" }}>
              Passenger #{idx + 1} ({pax.passenger_type})
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "8px" }}>
              <div>
                <label style={{ fontSize: "10px", color: "#0284c7", display: "block", marginBottom: "2px" }}>First Name</label>
                <Input 
                  size="small"
                  value={pax.first_name}
                  onChange={(e) => updatePassenger(idx, "first_name", e.target.value)}
                  placeholder="First name"
                />
              </div>
              <div>
                <label style={{ fontSize: "10px", color: "#0284c7", display: "block", marginBottom: "2px" }}>Last Name</label>
                <Input 
                  size="small"
                  value={pax.last_name}
                  onChange={(e) => updatePassenger(idx, "last_name", e.target.value)}
                  placeholder="Last name"
                />
              </div>
            </div>
            <div>
              <label style={{ fontSize: "10px", color: "#0284c7", display: "block", marginBottom: "2px" }}>Email</label>
              <Input 
                size="small"
                value={pax.email}
                onChange={(e) => updatePassenger(idx, "email", e.target.value)}
                placeholder="Email address"
              />
            </div>
          </div>
        ))}
      </div>

      <Button 
        type="primary" 
        block
        onClick={handleConfirm}
        style={{ background: "#0284c7", border: "none", borderRadius: "6px", fontWeight: "bold", fontSize: "12px", height: "32px" }}
      >
        ✓ Confirm Passenger Details
      </Button>
    </div>
  );
};

const PassengerOptionsCard: React.FC<{
  data: any;
  onConfirm?: (adults: number, children: number, infants: number) => void;
}> = ({ data, onConfirm }) => {
  const [adults, setAdults] = useState(data.defaults?.adults ?? 1);
  const [children, setChildren] = useState(data.defaults?.children ?? 0);
  const [infants, setInfants] = useState(data.defaults?.infants ?? 0);

  return (
    <div style={{
      background: "linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%)",
      border: "1px solid #bfdbfe",
      borderLeft: "4px solid #3b82f6",
      borderRadius: "10px",
      padding: "16px",
      margin: "8px 0",
      width: "100%",
      boxShadow: "0 2px 8px rgba(59, 130, 246, 0.08)"
    }}>
      <div style={{ fontWeight: "700", color: "#1e3a8a", fontSize: "14px", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
        <span>👥</span> Select Passenger Counts
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "16px" }}>
        {/* Adults */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontWeight: "600", fontSize: "12px", color: "#1e40af" }}>Adults</div>
            <div style={{ fontSize: "11px", color: "#60a5fa" }}>Age 12+</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Button size="small" shape="circle" onClick={() => setAdults(Math.max(1, adults - 1))}>-</Button>
            <span style={{ fontWeight: "bold", width: "16px", textAlign: "center", fontSize: "13px", color: "#000" }}>{adults}</span>
            <Button size="small" shape="circle" onClick={() => setAdults(adults + 1)}>+</Button>
          </div>
        </div>

        {/* Children */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontWeight: "600", fontSize: "12px", color: "#1e40af" }}>Children</div>
            <div style={{ fontSize: "11px", color: "#60a5fa" }}>Age 2-11</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Button size="small" shape="circle" onClick={() => setChildren(Math.max(0, children - 1))}>-</Button>
            <span style={{ fontWeight: "bold", width: "16px", textAlign: "center", fontSize: "13px", color: "#000" }}>{children}</span>
            <Button size="small" shape="circle" onClick={() => setChildren(children + 1)}>+</Button>
          </div>
        </div>

        {/* Infants */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <div style={{ fontWeight: "600", fontSize: "12px", color: "#1e40af" }}>Infants</div>
            <div style={{ fontSize: "11px", color: "#60a5fa" }}>Under age 2</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Button size="small" shape="circle" onClick={() => setInfants(Math.max(0, infants - 1))}>-</Button>
            <span style={{ fontWeight: "bold", width: "16px", textAlign: "center", fontSize: "13px", color: "#000" }}>{infants}</span>
            <Button size="small" shape="circle" onClick={() => setInfants(infants + 1)}>+</Button>
          </div>
        </div>
      </div>
      
      <Button 
        type="primary" 
        block 
        onClick={() => onConfirm && onConfirm(adults, children, infants)}
        style={{ background: "#2563eb", borderColor: "#2563eb", borderRadius: "6px", fontWeight: "bold", fontSize: "12px", height: "32px" }}
      >
        Confirm Passengers
      </Button>
    </div>
  );
};

const TimeSliderCard: React.FC<{
  data: any;
  onConfirm?: (startHour: number, endHour: number) => void;
}> = ({ data, onConfirm }) => {
  const [range, setRange] = useState<[number, number]>([data.default?.[0] ?? 6, data.default?.[1] ?? 22]);

  const formatHour = (h: number) => {
    if (h === 0 || h === 24) return "12 AM";
    if (h === 12) return "12 PM";
    if (h < 12) return `${h} AM`;
    return `${h - 12} PM`;
  };

  return (
    <div style={{
      background: "linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%)",
      border: "1px solid #e9d5ff",
      borderLeft: "4px solid #a855f7",
      borderRadius: "10px",
      padding: "16px",
      margin: "8px 0",
      width: "100%",
      boxShadow: "0 2px 8px rgba(168, 85, 247, 0.08)"
    }}>
      <div style={{ fontWeight: "700", color: "#6b21a8", fontSize: "14px", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px" }}>
        <span>🕒</span> Select Departure Time Range
      </div>
      <div style={{ fontSize: "13px", color: "#7e22ce", marginBottom: "16px", textAlign: "center", fontWeight: "bold" }}>
        Selected Range: {formatHour(range[0])} to {formatHour(range[1])}
      </div>
      <div style={{ padding: "0 10px", marginBottom: "20px" }}>
        <Slider
          range
          min={0}
          max={24}
          step={1}
          value={range}
          onChange={(val) => setRange(val as [number, number])}
          tooltip={{
            formatter: (val) => formatHour(val ?? 0)
          }}
          marks={{
            0: "12 AM",
            6: "6 AM",
            12: "12 PM",
            18: "6 PM",
            24: "12 AM"
          }}
        />
      </div>
      <Button 
        type="primary" 
        block 
        onClick={() => onConfirm && onConfirm(range[0], range[1])}
        style={{ background: "#9333ea", borderColor: "#9333ea", borderRadius: "6px", fontWeight: "bold", fontSize: "12px", height: "32px" }}
      >
        Confirm Time Range
      </Button>
    </div>
  );
};

const CalendarCard: React.FC<{
  data: any;
  onSelect?: (date: string) => void;
}> = ({ data, onSelect }) => {
  const [selectedDate, setSelectedDate] = useState<string | null>(data.default || null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleInputClick = () => {
    try {
      if (inputRef.current && typeof inputRef.current.showPicker === "function") {
        inputRef.current.showPicker();
      }
    } catch (e) {
      console.warn("showPicker failed", e);
    }
  };

  const handleConfirm = () => {
    if (selectedDate && onSelect) {
      onSelect(selectedDate);
    }
  };

  const today = new Date();
  const formatStr = (d: Date) => d.toISOString().split("T")[0];
  
  const shortcuts = [
    { label: "📅 Today", date: today },
    { label: "🌅 Tomorrow", date: new Date(today.getTime() + 24 * 60 * 60 * 1000) },
    { label: "✈️ Next Monday", date: (() => {
      const resultDate = new Date(today);
      resultDate.setDate(today.getDate() + ((7 - today.getDay() + 1) % 7 || 7));
      return resultDate;
    })() },
  ];

  return (
    <div style={{
      background: "linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%)",
      border: "1px solid #bbf7d0",
      borderLeft: "4px solid #16a34a",
      borderRadius: "10px",
      padding: "16px",
      margin: "8px 0",
      width: "100%",
      boxShadow: "0 2px 8px rgba(22, 163, 74, 0.08)",
      color: "#14532d"
    }}>
      <div style={{ fontWeight: "700", marginBottom: "12px", display: "flex", alignItems: "center", gap: "6px", fontSize: "14px", color: "#14532d" }}>
        <span>📅</span> {data.title || "Select Travel Date"}
      </div>
      
      <div style={{ display: "flex", gap: "8px", marginBottom: "12px", flexWrap: "wrap" }}>
        {shortcuts.map((sc, idx) => {
          const dateStr = formatStr(sc.date);
          const isSelected = selectedDate === dateStr;
          return (
            <Button
              key={idx}
              size="small"
              onClick={() => setSelectedDate(dateStr)}
              style={{
                background: isSelected ? "#16a34a" : "#fff",
                color: isSelected ? "#fff" : "#14532d",
                borderColor: isSelected ? "#16a34a" : "#bbf7d0",
                borderRadius: "6px",
                fontSize: "11px",
                fontWeight: "600",
                height: "26px"
              }}
            >
              {sc.label} ({dateStr.slice(5)})
            </Button>
          );
        })}
      </div>

      <div style={{ marginBottom: "16px", display: "flex", flexDirection: "column", gap: "6px" }}>
        <span style={{ fontSize: "11px", color: "#166534", fontWeight: "600" }}>Choose date:</span>
        <input
          ref={inputRef}
          type="date"
          value={selectedDate || ""}
          min={formatStr(today)}
          onChange={(e) => setSelectedDate(e.target.value)}
          onClick={handleInputClick}
          onFocus={handleInputClick}
          style={{
            width: "100%",
            padding: "8px 12px",
            borderRadius: "6px",
            border: "1px solid #bbf7d0",
            fontSize: "13px",
            background: "#fff",
            color: "#0f172a",
            outline: "none",
            cursor: "pointer",
            boxShadow: "0 1px 2px rgba(0,0,0,0.05)"
          }}
        />
      </div>

      <Button
        type="primary"
        block
        onClick={handleConfirm}
        disabled={!selectedDate}
        style={{
          background: selectedDate ? "#16a34a" : "#cbd5e1",
          borderColor: selectedDate ? "#16a34a" : "#cbd5e1",
          borderRadius: "6px",
          fontWeight: "bold",
          fontSize: "12px",
          height: "32px"
        }}
      >
        Confirm Date
      </Button>
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
      
      <div style={{ display: "flex", gap: "8px", marginTop: "4px", width: "100%" }}>
        <Button 
          type="primary"
          onClick={handleOpen}
          style={{
            flex: 1,
            background: "linear-gradient(135deg, #722ed1 0%, #9254de 100%)",
            border: "none",
            fontWeight: "bold",
            borderRadius: "6px"
          }}
        >
          💺 View Seat Map
        </Button>
        <Button 
          onClick={() => onSelect && onSelect("system-assigned")}
          style={{
            flex: 1,
            borderColor: "#d9d9d9",
            fontWeight: "bold",
            borderRadius: "6px",
            color: "#595959"
          }}
        >
          🎲 Auto-Assign Seat
        </Button>
      </div>

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
              marginBottom: "12px",
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
      background: "linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)",
      border: "1px solid #fde68a",
      borderLeft: "4px solid #f59e0b",
      borderRadius: "10px",
      padding: "12px 14px",
      margin: "6px 0",
      width: "100%",
      display: "flex",
      flexDirection: "column",
      gap: "8px",
      boxShadow: "0 2px 8px rgba(245, 158, 11, 0.08)"
    }}>
      <div style={{ fontWeight: "700", color: "#78350f", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
        <span>❓</span> Confirm Action
      </div>
      <div style={{ fontSize: "12px", color: "#92400e", lineHeight: "1.5" }}>
        {data.question || "Would you like to proceed?"}
      </div>
      <div style={{ display: "flex", gap: "8px" }}>
        <Button
          type="primary"
          size="small"
          onClick={() => onSelect && onSelect(data.yes_text || "Yes")}
          style={{ background: "#10b981", border: "none", borderRadius: "6px", fontWeight: "bold", fontSize: "12px" }}
        >
          ✓ {data.yes_label || "Yes, proceed"}
        </Button>
        <Button
          danger
          size="small"
          onClick={() => onSelect && onSelect(data.no_text || "No")}
          style={{ borderRadius: "6px", fontWeight: "bold", fontSize: "12px" }}
        >
          ✗ {data.no_label || "No, cancel"}
        </Button>
      </div>
    </div>
  );
};

const LoyaltyUpgradeCard: React.FC<{ 
  data: any; 
  onUpgrade?: (pnr: string, miles: number) => void 
}> = ({ data, onUpgrade }) => {
  return (
    <div style={{
      background: "linear-gradient(135deg, #1e1b4b 0%, #311042 100%)",
      border: "1px solid #c084fc",
      borderLeft: "5px solid #a855f7",
      borderRadius: "12px",
      padding: "16px",
      margin: "10px 0",
      width: "100%",
      color: "#f3e8ff",
      display: "flex",
      flexDirection: "column",
      gap: "12px",
      boxShadow: "0 4px 15px rgba(168, 85, 247, 0.15)",
      position: "relative",
      overflow: "hidden"
    }}>
      <div style={{
        position: "absolute",
        top: "-20px",
        right: "-20px",
        width: "80px",
        height: "80px",
        background: "rgba(168, 85, 247, 0.3)",
        borderRadius: "50%",
        filter: "blur(20px)",
        pointerEvents: "none"
      }} />

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: "800", color: "#e9d5ff", fontSize: "13px", display: "flex", alignItems: "center", gap: "6px" }}>
          <span>👑</span> Loyalty Flight Upgrade
        </div>
        <span style={{
          background: "linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%)",
          color: "#78350f",
          fontSize: "9px",
          fontWeight: "800",
          padding: "2px 8px",
          borderRadius: "10px",
          textTransform: "uppercase",
          letterSpacing: "0.5px"
        }}>
          Gold Tier Exclusive
        </span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ fontSize: "12px", color: "#c084fc" }}>Passenger: <b>{data.passenger_name}</b></div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: "4px" }}>
          <div>
            <div style={{ fontSize: "9px", color: "#a5b4fc", textTransform: "uppercase" }}>Your Miles Balance</div>
            <div style={{ fontSize: "20px", fontWeight: "900", color: "#fff", lineHeight: "1" }}>
              {data.current_miles?.toLocaleString() || "0"} <span style={{ fontSize: "11px", fontWeight: "normal", color: "#cbd5e1" }}>miles</span>
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "9px", color: "#f472b6", textTransform: "uppercase" }}>Required for Upgrade</div>
            <div style={{ fontSize: "16px", fontWeight: "bold", color: "#f472b6" }}>
              {data.required_miles?.toLocaleString() || "5,000"} miles
            </div>
          </div>
        </div>
      </div>

      <div style={{ borderTop: "1px solid rgba(168, 85, 247, 0.2)", paddingTop: "10px" }} />

      <div style={{ fontSize: "11px", color: "#cbd5e1", lineHeight: "1.4" }}>
        Upgrade PNR <b>{data.pnr}</b> to Business Class immediately. Includes priority boarding, premium meals, extra baggage allowance, and luxury lounge access.
      </div>

      <Button
        type="primary"
        onClick={() => onUpgrade && onUpgrade(data.pnr, data.required_miles)}
        disabled={data.current_miles < data.required_miles}
        style={{
          background: data.current_miles >= data.required_miles 
            ? "linear-gradient(95deg, #a855f7 0%, #7c3aed 100%)" 
            : "#4b5563",
          border: "none",
          borderRadius: "8px",
          fontWeight: "800",
          fontSize: "12px",
          height: "34px",
          color: "#fff",
          boxShadow: data.current_miles >= data.required_miles ? "0 4px 10px rgba(124, 58, 237, 0.3)" : "none",
          transition: "all 0.3s ease"
        }}
      >
        ✨ Redeem Upgrade Now
      </Button>
    </div>
  );
};

const FlightStatusCard: React.FC<{ data: any }> = ({ data }) => {
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case "scheduled": return { bg: "rgba(59, 130, 246, 0.1)", border: "#3b82f6", text: "#60a5fa" };
      case "boarding": return { bg: "rgba(16, 185, 129, 0.1)", border: "#10b981", text: "#34d399" };
      case "departed": return { bg: "rgba(99, 102, 241, 0.1)", border: "#6366f1", text: "#818cf8" };
      case "arrived": return { bg: "rgba(16, 185, 129, 0.15)", border: "#059669", text: "#10b981" };
      case "delayed": return { bg: "rgba(245, 158, 11, 0.1)", border: "#f59e0b", text: "#fbbf24" };
      case "cancelled": return { bg: "rgba(239, 68, 68, 0.1)", border: "#ef4444", text: "#f87171" };
      default: return { bg: "rgba(156, 163, 175, 0.1)", border: "#9ca3af", text: "#d1d5db" };
    }
  };

  const colors = getStatusColor(data.status);
  const depTime = data.departure_datetime ? new Date(data.departure_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "N/A";
  const arrTime = data.arrival_datetime ? new Date(data.arrival_datetime).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "N/A";
  const depDate = data.departure_datetime ? new Date(data.departure_datetime).toLocaleDateString([], { month: 'short', day: 'numeric' }) : "";

  return (
    <div style={{
      background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
      border: `1px solid ${colors.border}`,
      borderLeft: `5px solid ${colors.border}`,
      borderRadius: "12px",
      padding: "16px",
      margin: "10px 0",
      width: "100%",
      color: "#f8fafc",
      boxShadow: "0 4px 15px rgba(0, 0, 0, 0.3)",
      fontFamily: "inherit"
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div>
          <div style={{ fontSize: "14px", fontWeight: "800", color: "#f1f5f9" }}>
            ✈️ {data.airline_name} <span style={{ color: "#38bdf8" }}>{data.flight_number}</span>
          </div>
          {depDate && <div style={{ fontSize: "10px", color: "#94a3b8" }}>{depDate}</div>}
        </div>
        <span style={{
          background: colors.bg,
          border: `1px solid ${colors.border}`,
          color: colors.text,
          fontSize: "10px",
          fontWeight: "800",
          padding: "3px 10px",
          borderRadius: "8px",
          textTransform: "uppercase",
          letterSpacing: "0.5px"
        }}>
          {data.status || "Unknown"}
        </span>
      </div>

      {/* Progress Track */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", margin: "18px 0" }}>
        <div style={{ width: "30%" }}>
          <div style={{ fontSize: "24px", fontWeight: "900", color: "#fff", lineHeight: "1" }}>{data.origin_iata}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>{data.origin_city}</div>
          <div style={{ fontSize: "12px", fontWeight: "bold", color: "#38bdf8", marginTop: "4px" }}>{depTime}</div>
        </div>

        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", position: "relative", padding: "0 10px" }}>
          {data.delay_minutes > 0 && (
            <div style={{ fontSize: "10px", color: "#fbbf24", fontWeight: "bold", position: "absolute", top: "-18px" }}>
              +{data.delay_minutes}m Delay
            </div>
          )}
          <div style={{ width: "100%", height: "2px", background: "rgba(255,255,255,0.15)", position: "relative" }}>
            <div style={{
              position: "absolute",
              left: data.status?.toLowerCase() === "arrived" ? "100%" : data.status?.toLowerCase() === "departed" ? "60%" : data.status?.toLowerCase() === "boarding" ? "20%" : "0%",
              top: "-5px",
              transform: "translateX(-50%)",
              transition: "left 1s ease-in-out",
              fontSize: "12px"
            }}>
              ✈️
            </div>
          </div>
        </div>

        <div style={{ width: "30%", textAlign: "right" }}>
          <div style={{ fontSize: "24px", fontWeight: "900", color: "#fff", lineHeight: "1" }}>{data.destination_iata}</div>
          <div style={{ fontSize: "11px", color: "#94a3b8", textOverflow: "ellipsis", overflow: "hidden", whiteSpace: "nowrap" }}>{data.destination_city}</div>
          <div style={{ fontSize: "12px", fontWeight: "bold", color: "#38bdf8", marginTop: "4px" }}>{arrTime}</div>
        </div>
      </div>

      <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", paddingTop: "12px" }} />

      {/* Terminal Info */}
      <div style={{ display: "flex", justifyContent: "space-between", gap: "10px" }}>
        <div>
          <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase" }}>Terminal</div>
          <div style={{ fontSize: "12px", fontWeight: "bold", color: "#f1f5f9" }}>{data.terminal || "N/A"}</div>
        </div>
        <div>
          <div style={{ fontSize: "9px", color: "#94a3b8", textTransform: "uppercase" }}>Gate</div>
          <div style={{ fontSize: "12px", fontWeight: "bold", color: "#f1f5f9" }}>{data.gate || "N/A"}</div>
        </div>
        {data.delay_minutes > 0 ? (
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "9px", color: "#fbbf24", textTransform: "uppercase" }}>Remarks</div>
            <div style={{ fontSize: "12px", fontWeight: "bold", color: "#fbbf24" }}>Delayed</div>
          </div>
        ) : (
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "9px", color: "#34d399", textTransform: "uppercase" }}>Remarks</div>
            <div style={{ fontSize: "12px", fontWeight: "bold", color: "#34d399" }}>On Time</div>
          </div>
        )}
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
          maxWidth: "92%",
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
              padding: "10px 14px",
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
                    // FIX: Use [\w-]+ to capture hyphenated tags like passenger-review, meal-options, seats-options
                    const match = /language-([\w-]+)/.exec(className || "");
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
                        const knownLangs = ["flights", "tickets", "payment", "passenger-review", "seats-options", "meal-options", "options", "confirm", "ancillary-options", "checkin-declaration", "loyalty-upgrade", "flight-status", "passenger-options", "time-slider", "calendar"];
                        if (lang === "json" || lang === "" || !knownLangs.includes(lang)) {
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
                              } else if (first.type && first.label && first.amount) {
                                lang = "ancillary-options";
                              }
                            }
                          } else {
                            if (parsedData.pnr && (parsedData.flight_id || parsedData.flight_number) && parsedData.passenger_id) {
                              parsedData.flight_id = parsedData.flight_number;
                              lang = "seats-options";
                            } else if (parsedData.pnr && (parsedData.price !== undefined || parsedData.amount !== undefined) && parsedData.flight_number) {
                              lang = "payment";
                            } else if ((parsedData.name && parsedData.email) || (parsedData.passengers && Array.isArray(parsedData.passengers))) {
                              lang = "passenger-review";
                            } else if (parsedData.title && parsedData.defaults && parsedData.defaults.adults !== undefined) {
                              lang = "passenger-options";
                            } else if (parsedData.title && (parsedData.type === "date" || parsedData.date !== undefined || parsedData.type === "calendar")) {
                              lang = "calendar";
                            } else if (parsedData.title && parsedData.min !== undefined && parsedData.max !== undefined && parsedData.default !== undefined) {
                              lang = "time-slider";
                            } else if (parsedData.question && parsedData.yes_text && parsedData.no_text) {
                              lang = "confirm";
                            } else if (parsedData.pnr && parsedData.passenger_name && parsedData.is_checkin) {
                              lang = "checkin-declaration";
                            } else if (parsedData.pnr && parsedData.current_miles !== undefined && parsedData.required_miles !== undefined) {
                              lang = "loyalty-upgrade";
                            } else if (parsedData.flight_number && parsedData.status && !parsedData.passenger_id) {
                              lang = "flight-status";
                            }
                          }
                        }

                        // Render appropriate custom card component
                        if (lang === "flights" && Array.isArray(parsedData)) {
                          return (
                            <FlightsCardList 
                              flights={parsedData} 
                              onSelect={(flightNumber, date, bookingClass) => onSendMessage?.(`I want to book flight ${flightNumber} on ${date} in class ${bookingClass}`)} 
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
                              onConfirm={(paxList) => onSendMessage?.(`I confirm my passenger details: ${JSON.stringify(paxList)}`)}
                            />
                          );
                        }
                        if (lang === "passenger-options") {
                          return (
                            <PassengerOptionsCard 
                              data={parsedData} 
                              onConfirm={(adults, children, infants) => {
                                onSendMessage?.(`I want to search for flights with ${adults} adults, ${children} children, ${infants} infants`);
                              }}
                            />
                          );
                        }
                        if (lang === "calendar") {
                          return (
                            <CalendarCard 
                              data={parsedData} 
                              onSelect={(date) => {
                                onSendMessage?.(date);
                              }}
                            />
                          );
                        }
                        if (lang === "time-slider") {
                          return (
                            <TimeSliderCard 
                              data={parsedData} 
                              onConfirm={(start, end) => {
                                onSendMessage?.(`Set departure time range to ${start}:00 - ${end}:00`);
                              }}
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
                        if (lang === "ancillary-options" && Array.isArray(parsedData)) {
                          return (
                            <AncillaryOptionsCard 
                              ancillaries={parsedData} 
                              onSelect={(text) => onSendMessage?.(text)}
                            />
                          );
                        }
                        if (lang === "checkin-declaration") {
                          return (
                            <CheckinDeclarationCard 
                              pnr={parsedData.pnr} 
                              passengerName={parsedData.passenger_name}
                              onConfirm={() => onSendMessage?.(`I confirm the safety declaration for PNR ${parsedData.pnr}. Please proceed.`)}
                            />
                          );
                        }
                        if (lang === "loyalty-upgrade") {
                          return (
                            <LoyaltyUpgradeCard 
                              data={parsedData} 
                              onUpgrade={(pnr, miles) => onSendMessage?.(`I want to upgrade PNR ${pnr} to Business Class using ${miles} miles`)}
                            />
                          );
                        }
                        if (lang === "flight-status") {
                          return <FlightStatusCard data={parsedData} />;
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
