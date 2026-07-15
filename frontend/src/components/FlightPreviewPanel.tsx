import React from "react";
import { Card, Tag, Empty, Select } from "antd";
import { 
  CalendarOutlined
} from "@ant-design/icons";

interface FlightPreviewPanelProps {
  activeBooking: any;
  bookings?: any[];
  onSelectBooking?: (booking: any) => void;
}

export const FlightPreviewPanel: React.FC<FlightPreviewPanelProps> = ({
  activeBooking,
  bookings = [],
  onSelectBooking,
}) => {
  return (
    <div style={{ 
      display: "flex", 
      flexDirection: "column", 
      gap: "10px", 
      height: "100%", 
      overflowY: "auto",
      paddingRight: "4px"
    }}>
      {/* 2. Interactive Ticket & Boarding Pass Preview */}
      <Card
        title="✈️ Boarding Pass & Ticket Preview"
        style={{
          flex: "0 0 auto",
          borderRadius: "8px",
          boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
          overflow: "hidden"
        }}
        bodyStyle={{
          padding: "12px",
          background: "#fafafa"
        }}
      >
        {bookings && bookings.length > 1 && (
          <div style={{ marginBottom: "16px" }}>
            <span style={{ fontSize: "11px", color: "#64748b", display: "block", marginBottom: "4px", fontWeight: "bold" }}>
              SELECT RESERVATION ({bookings.length} ACTIVE):
            </span>
            <Select
              style={{ width: "100%" }}
              value={activeBooking?.pnr}
              onChange={(value) => {
                const found = bookings.find(b => b.pnr === value);
                if (found && onSelectBooking) {
                  onSelectBooking(found);
                }
              }}
              options={bookings.map(b => ({
                label: `PNR: ${b.pnr} | ${b.origin} ➡️ ${b.destination} (${b.date}) - [${b.status?.toUpperCase()}]`,
                value: b.pnr
              }))}
            />
          </div>
        )}
        {activeBooking ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* The Boarding Pass */}
            <div style={{
              background: "#1e293b",
              color: "#fff",
              borderRadius: "12px",
              overflow: "hidden",
              boxShadow: "0 6px 18px rgba(0, 0, 0, 0.15)",
              border: "1px solid #334155",
              position: "relative"
            }}>
              {/* Ticket Top Cut-out indicator */}
              <div style={{
                position: "absolute",
                top: "45%",
                left: "-8px",
                width: "16px",
                height: "16px",
                background: "#fafafa",
                borderRadius: "50%",
                zIndex: 2
              }} />
              <div style={{
                position: "absolute",
                top: "45%",
                right: "-8px",
                width: "16px",
                height: "16px",
                background: "#fafafa",
                borderRadius: "50%",
                zIndex: 2
              }} />

              {/* Boarding Pass Header */}
              <div style={{
                padding: "16px",
                background: "linear-gradient(90deg, #0f172a, #1e293b)",
                borderBottom: "1px dashed #475569",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center"
              }}>
                <span style={{ fontWeight: "bold", letterSpacing: "1px", color: "#38bdf8", fontSize: "13px" }}>
                  APEX AIRLINES
                </span>
                <Tag color={activeBooking.status === "cancelled" ? "red" : "green"} style={{ margin: 0, fontWeight: "bold" }}>
                  {activeBooking.status?.toUpperCase() || "BOOKED"}
                </Tag>
              </div>

              {/* Boarding Pass Body */}
              <div style={{ padding: "12px 14px" }}>
                {/* Routing display */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
                  <div>
                    <div style={{ fontSize: "26px", fontWeight: 800, color: "#f8fafc", lineHeight: "1" }}>
                      {activeBooking.origin}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>Origin Airport</div>
                  </div>
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", padding: "0 10px" }}>
                    <div style={{ fontSize: "18px", color: "#38bdf8", transform: "rotate(90deg) translateY(-2px)" }}>✈</div>
                    <div style={{ width: "100%", height: "2px", background: "dashed #475569", borderTop: "2px dashed #475569", marginTop: "4px" }} />
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "26px", fontWeight: 800, color: "#f8fafc", lineHeight: "1" }}>
                      {activeBooking.destination}
                    </div>
                    <div style={{ fontSize: "11px", color: "#94a3b8" }}>Destination</div>
                  </div>
                </div>

                {/* Details Grid */}
                <div style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "8px",
                  fontSize: "12px",
                  borderTop: "1px solid #334155",
                  paddingTop: "10px"
                }}>
                  <div>
                    <span style={{ display: "block", color: "#94a3b8", fontSize: "10px" }}>PASSENGER</span>
                    <span style={{ fontWeight: "600", color: "#f1f5f9" }}>{activeBooking.passenger_name}</span>
                  </div>
                  <div>
                    <span style={{ display: "block", color: "#94a3b8", fontSize: "10px" }}>FLIGHT NO</span>
                    <span style={{ fontWeight: "600", color: "#f1f5f9", fontFamily: "monospace" }}>{activeBooking.flight_number}</span>
                  </div>
                  <div>
                    <span style={{ display: "block", color: "#94a3b8", fontSize: "10px" }}>DEPARTURE DATE</span>
                    <span style={{ fontWeight: "600", color: "#f1f5f9" }}><CalendarOutlined /> {activeBooking.date}</span>
                  </div>
                  <div>
                    <span style={{ display: "block", color: "#94a3b8", fontSize: "10px" }}>GATE / SEAT</span>
                    <span style={{ fontWeight: "600", color: "#38bdf8" }}>{activeBooking.gate} / {activeBooking.seat}</span>
                  </div>
                </div>
              </div>

              {/* Barcode & PNR footer */}
              <div style={{
                background: "#0f172a",
                padding: "10px 16px",
                borderTop: "1px dashed #475569",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: "8px"
              }}>
                <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                  PNR RECORD: <span style={{ fontFamily: "monospace", fontWeight: "bold", color: "#f8fafc", background: "#334155", padding: "2px 6px", borderRadius: "4px" }}>{activeBooking.pnr}</span>
                </div>
                {/* Mock barcode lines */}
                <div style={{
                  display: "flex",
                  gap: "2px",
                  height: "36px",
                  width: "80%",
                  background: "#fff",
                  padding: "4px",
                  borderRadius: "2px",
                  justifyContent: "center"
                }}>
                  {[...Array(24)].map((_, i) => (
                    <div 
                      key={i} 
                      style={{ 
                        width: i % 3 === 0 ? "3px" : i % 5 === 0 ? "1px" : "2px", 
                        height: "100%", 
                        background: "#000" 
                      }} 
                    />
                  ))}
                </div>
              </div>
            </div>
            
            {activeBooking.status === "cancelled" && (
              <div style={{
                padding: "12px",
                background: "#fee2e2",
                border: "1px solid #fecaca",
                color: "#991b1b",
                borderRadius: "6px",
                fontSize: "12px",
                textAlign: "center",
                fontWeight: "500"
              }}>
                This ticket has been cancelled. If you wish to travel, please make a new booking.
              </div>
            )}
          </div>
        ) : (
          <Empty 
            description="No active ticket booked yet. Use the Chatbot to query flight details or make a new booking!"
            style={{ marginTop: "40px" }}
          />
        )}
      </Card>
    </div>
  );
};
