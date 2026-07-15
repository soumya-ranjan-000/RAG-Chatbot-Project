import React, { useState, useRef, useEffect } from "react";
import { Card, Input, Button, Space, Slider, Popover, Typography, Tooltip, message } from "antd";
import { SendOutlined, SettingOutlined, DeleteOutlined } from "@ant-design/icons";
import { ChatMessage as ChatMessageComponent } from "./ChatMessage";
import { chatService, type StreamEvent } from "../services/chatService";
import type { ChatMessage } from "../types/chat";

const { Text } = Typography;

interface ChatWindowProps {
  passengerProfile: {
    passenger_id: string;
    name: string;
    email: string;
    frequent_flyer_number: string;
  };
  onBookingUpdate: (booking: any) => void;
  onToolActivity: (activity: any) => void;
}

const PSS_API_URL = "http://localhost:8000/api/pss";

export const ChatWindow: React.FC<ChatWindowProps> = ({ 
  passengerProfile,
  onBookingUpdate,
  onToolActivity
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activePnr, setActivePnr] = useState<string | null>(null);

  // Settings
  const [topK, setTopK] = useState<number>(5);
  const [threshold, setThreshold] = useState<number>(0.3);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load message history from localStorage on mount
  useEffect(() => {
    const saved = localStorage.getItem("rag_chat_history");
    if (saved) {
      try {
        setMessages(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse saved chat history", e);
      }
    }
  }, []);

  // Save message history to localStorage on change
  useEffect(() => {
    localStorage.setItem("rag_chat_history", JSON.stringify(messages));
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleClearHistory = () => {
    setMessages([]);
    localStorage.removeItem("rag_chat_history");
    onBookingUpdate(null);
    setActivePnr(null);
  };

  // 1. Listen for window messages (cross-tab payment success notifications)
  useEffect(() => {
    const handleWindowMessage = async (event: MessageEvent) => {
      if (event.data && event.data.type === "PAYMENT_SUCCESS") {
        const { pnr } = event.data;
        message.success(`Payment for PNR ${pnr} detected!`);
        setActivePnr(null);
        
        // Auto-issue ticket
        try {
          await fetch(`${PSS_API_URL}/bookings/${pnr}/ticket`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ passenger_id: passengerProfile.passenger_id })
          });
          
          const bookingRes = await fetch(`${PSS_API_URL}/bookings/${pnr}`);
          if (bookingRes.ok) {
            const updatedBooking = await bookingRes.json();
            onBookingUpdate(updatedBooking);
          }
        } catch (e) {
          console.error("Failed to auto-issue ticket", e);
        }

        // Proceed automatically
        handleSend(`Confirm payment status for PNR ${pnr}`);
      }
    };
    window.addEventListener("message", handleWindowMessage);
    return () => window.removeEventListener("message", handleWindowMessage);
  }, [passengerProfile.passenger_id]);

  // 2. Poll active PNR status for background updates
  useEffect(() => {
    if (!activePnr) return;

    let intervalId: any = null;

    const checkPaymentStatus = async () => {
      try {
        const res = await fetch(`${PSS_API_URL}/bookings/${activePnr}`);
        if (res.ok) {
          const data = await res.json();
          if (data.status === "confirmed" || data.status === "ticketed") {
            clearInterval(intervalId);
            setActivePnr(null);
            
            // Auto issue ticket if confirmed
            if (data.status === "confirmed") {
              try {
                const ticketRes = await fetch(`${PSS_API_URL}/bookings/${activePnr}/ticket`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ passenger_id: passengerProfile.passenger_id })
                });
                
                if (ticketRes.ok) {
                  const bookingRes = await fetch(`${PSS_API_URL}/bookings/${activePnr}`);
                  if (bookingRes.ok) {
                    const updatedBooking = await bookingRes.json();
                    onBookingUpdate(updatedBooking);
                  }
                }
              } catch (e) {
                console.error("Auto ticketing failed", e);
              }
            } else {
              onBookingUpdate(data);
            }

            message.success(`Payment for PNR ${activePnr} confirmed!`);
            handleSend(`Confirm payment status for PNR ${activePnr}`);
          }
        }
      } catch (e) {
        console.error("Polling error", e);
      }
    };

    intervalId = setInterval(checkPaymentStatus, 3000);
    return () => clearInterval(intervalId);
  }, [activePnr, passengerProfile.passenger_id]);

  const handleSend = async (customText?: string) => {
    const userQuery = customText !== undefined ? customText.trim() : inputVal.trim();
    if (!userQuery || isStreaming) return;

    if (customText === undefined) {
      setInputVal("");
    }
    setIsStreaming(true);

    const userMsgId = Date.now().toString();
    const assistantMsgId = (Date.now() + 1).toString();

    const newUserMessage: ChatMessage = {
      id: userMsgId,
      role: "user",
      content: userQuery,
      timestamp: new Date().toLocaleTimeString()
    };

    const newAssistantMessage: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString(),
      sources: [],
      isStreaming: true
    };

    // Update messages with user's message and placeholder assistant message
    setMessages(prev => [...prev, newUserMessage, newAssistantMessage]);

    // Format history in the way the API expects
    // Note: read history from the state snapshot including the new user message
    const historyPayload = [...messages, newUserMessage].map(msg => ({
      role: msg.role,
      content: msg.content
    }));

    let currentResponseContent = "";
    let lastUpdateTime = 0;
    let updateTimeout: number | null = null;

    const scheduleContentUpdate = (content: string) => {
      const now = Date.now();
      if (now - lastUpdateTime > 60) {
        lastUpdateTime = now;
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, content }
              : msg
          )
        );
      } else {
        if (updateTimeout) window.clearTimeout(updateTimeout);
        updateTimeout = window.setTimeout(() => {
          lastUpdateTime = Date.now();
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, content }
                : msg
            )
          );
        }, 60);
      }
    };

    await chatService.streamChat(
      userQuery,
      historyPayload,
      async (event: StreamEvent) => {
        if (event.type === "tool_call" && event.name) {
          onToolActivity({
            name: event.name,
            args: event.args,
            timestamp: new Date().toLocaleTimeString(),
            status: "running"
          });
        } else if (event.type === "tool_result" && event.name) {
          onToolActivity({
            name: event.name,
            args: event.args,
            result: event.result,
            timestamp: new Date().toLocaleTimeString(),
            status: event.result?.error ? "failed" : "success"
          });

          // Handle booking state updates
          if (
            event.name === "check_booking_status" ||
            event.name === "book_flight" ||
            event.name === "reschedule_flight"
          ) {
            if (event.result && !event.result.error) {
              onBookingUpdate(event.result);
              if (event.result.pnr) {
                setActivePnr(event.result.pnr);
              }
            }
          } else if (event.name === "cancel_flight") {
            if (event.result && !event.result.error) {
              const pnr = event.args?.pnr;
              if (pnr) {
                try {
                  const bookingRes = await fetch(`${PSS_API_URL}/bookings/${pnr}`);
                  if (bookingRes.ok) {
                    const updatedBooking = await bookingRes.json();
                    onBookingUpdate(updatedBooking);
                  }
                } catch (e) {
                  console.error("Failed to update status on cancel", e);
                }
              }
            }
          }
        } else if (event.type === "token" && event.content) {
          currentResponseContent += event.content;
          scheduleContentUpdate(currentResponseContent);
        } else if (event.type === "citations" && event.citations) {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, citations: event.citations }
                : msg
            )
          );
        } else if (event.type === "metrics" && event.metrics) {
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, metrics: event.metrics }
                : msg
            )
          );
        } else if (event.type === "error" && event.message) {
          if (updateTimeout) window.clearTimeout(updateTimeout);
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? {
                    ...msg,
                    content: `Error: ${event.message}`,
                    isStreaming: false
                  }
                : msg
            )
          );
          setIsStreaming(false);
        }
      },
      () => {
        // Stream completed
        if (updateTimeout) window.clearTimeout(updateTimeout);
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMsgId
              ? { ...msg, content: currentResponseContent, isStreaming: false }
              : msg
          )
        );
        setIsStreaming(false);
      },
      () => {
        if (updateTimeout) window.clearTimeout(updateTimeout);
        setMessages(prev =>
          prev.map(msg =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  content: `Failed to connect or stream response. Make sure the backend is running.`,
                  isStreaming: false
                }
              : msg
          )
        );
        setIsStreaming(false);
      },
      topK,
      threshold,
      passengerProfile.passenger_id
    );
  };

  const handleSelectSource = (index: number) => {
    const element = document.getElementById(`chunk-card-${index}`);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "nearest" });
      
      // Highlight animation
      const originalShadow = element.style.boxShadow;
      const originalTransform = element.style.transform;
      
      element.style.boxShadow = "0 0 16px rgba(24, 144, 255, 0.8)";
      element.style.transform = "scale(1.03)";
      
      setTimeout(() => {
        element.style.boxShadow = originalShadow;
        element.style.transform = originalTransform;
      }, 1500);
    }
  };

  const settingsContent = (
    <div style={{ width: 220, padding: "8px 0" }}>
      <div style={{ marginBottom: 12 }}>
        <Text strong>Top K Chunks: {topK}</Text>
        <Slider
          min={1}
          max={10}
          value={topK}
          onChange={(val) => setTopK(val)}
        />
      </div>
      <div>
        <Text strong>Match Threshold: {threshold}</Text>
        <Slider
          min={0}
          max={1}
          step={0.05}
          value={threshold}
          onChange={(val) => setThreshold(val)}
        />
      </div>
    </div>
  );

  return (
    <Card
      title={
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>💬 AI Chatbot</span>
          <Space>
            <Popover content={settingsContent} title="Retrieval Settings" trigger="click" placement="bottomRight">
              <Button type="text" icon={<SettingOutlined />} title="Settings" />
            </Popover>
            <Tooltip title="Clear Chat History">
              <Button type="text" danger icon={<DeleteOutlined />} onClick={handleClearHistory} />
            </Tooltip>
          </Space>
        </div>
      }
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.05)",
        borderRadius: "8px",
        overflow: "hidden"
      }}
      bodyStyle={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        padding: "16px"
      }}
    >
      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          paddingRight: "4px",
          marginBottom: "16px",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: "auto", textAlign: "center", color: "#475569", maxWidth: "80%", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
            <span style={{ fontSize: "40px" }}>🤖</span>
            <h3 style={{ fontSize: "16px", fontWeight: "bold", margin: 0, color: "#0f172a" }}>Airline Booking Assistant</h3>
            <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 12px 0" }}>
              Welcome! Please select one of the available options below to get started immediately, or type your query in the chat box.
            </p>
            <div style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "10px",
              width: "100%"
            }}>
              {[
                { label: "🔍 Search Flights", text: "Search flights" },
                { label: "💺 Choose Seat", text: "Select seat for my booking" },
                { label: "🍱 Meal Options", text: "Choose meal option" },
                { label: "💼 Add Baggage", text: "Add baggage or service" },
                { label: "✈️ Show Bookings", text: "Show my bookings" },
                { label: "👤 Passenger Info", text: "Show passenger info" }
              ].map((opt, idx) => (
                <Button 
                  key={idx} 
                  onClick={() => handleSend(opt.text)}
                  style={{
                    height: "auto",
                    padding: "12px 16px",
                    borderRadius: "8px",
                    background: "#fff",
                    borderColor: "#e2e8f0",
                    color: "#334155",
                    textAlign: "left",
                    fontSize: "12px",
                    fontWeight: "600",
                    boxShadow: "0 1px 3px rgba(0,0,0,0.02)",
                    whiteSpace: "normal"
                  }}
                >
                  {opt.label}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          messages.map(msg => (
            <ChatMessageComponent 
              key={msg.id} 
              message={msg} 
              onSelectSource={handleSelectSource} 
              onSendMessage={handleSend}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={{ display: "flex", gap: "8px", borderTop: "1px solid #f0f0f0", paddingTop: "12px" }}>
        <Input.TextArea
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder="Ask a question about the loaded documents..."
          autoSize={{ minRows: 1, maxRows: 4 }}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          disabled={isStreaming}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={() => handleSend()}
          disabled={!inputVal.trim() || isStreaming}
          style={{ height: "auto" }}
        />
      </div>
    </Card>
  );
};
