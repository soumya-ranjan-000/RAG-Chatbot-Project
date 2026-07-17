import React, { useState, useRef, useEffect } from "react";
import { Card, Input, Button, Space, Slider, Popover, Typography, Tooltip, message } from "antd";
import { SendOutlined, SettingOutlined, DeleteOutlined } from "@ant-design/icons";
import { ChatMessage as ChatMessageComponent } from "./ChatMessage";
import { chatService, type StreamEvent } from "../services/chatService";
import type { ChatMessage } from "../types/chat";
import { PSS_API_URL, apiService } from "../services/api";

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

export const ChatWindow: React.FC<ChatWindowProps> = ({ 
  passengerProfile,
  onBookingUpdate,
  onToolActivity
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputVal, setInputVal] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [activePnr, setActivePnr] = useState<string | null>(null);
  const [threadId, setThreadId] = useState<string>("");
  const [modelName, setModelName] = useState<string>("gpt-4o-mini");

  // Settings
  const [topK, setTopK] = useState<number>(5);
  const [threshold, setThreshold] = useState<number>(0.3);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const handleSendRef = useRef<any>(null);

  const generateUUID = () => {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  };

  // Load active LLM model name
  useEffect(() => {
    const fetchModelName = async () => {
      try {
        const settings = await apiService.getSettings();
        if (settings.model) {
          setModelName(settings.model);
        }
      } catch (err) {
        console.error("Failed to load model name settings", err);
      }
    };
    fetchModelName();

    window.addEventListener("focus", fetchModelName);
    return () => window.removeEventListener("focus", fetchModelName);
  }, []);

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

    // Set a new thread ID in memory on component mount (not cached in localStorage)
    const newThreadId = generateUUID();
    setThreadId(newThreadId);
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
    localStorage.removeItem("rag_chat_thread_id");
    const newThreadId = generateUUID();
    setThreadId(newThreadId);
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
        if (handleSendRef.current) {
          handleSendRef.current(`Confirm payment status for PNR ${pnr}`);
        }
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
            if (handleSendRef.current) {
              handleSendRef.current(`Confirm payment status for PNR ${activePnr}`);
            }
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
      isStreaming: true,
      threadId: threadId
    };

    // Update messages with user's message and placeholder assistant message
    setMessages(prev => [...prev, newUserMessage, newAssistantMessage]);

    // Format history in the way the API expects (history before this new query)
    const historyPayload = messages.map(msg => ({
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
        if (event.type === "info") {
          console.log(`[Observability] Session Thread ID: ${event.thread_id}, Current Run ID: ${event.run_id}`);
          setMessages(prev =>
            prev.map(msg =>
              msg.id === assistantMsgId
                ? { ...msg, runId: event.run_id, threadId: event.thread_id }
                : msg
            )
          );
        } else if (event.type === "tool_call" && event.name) {
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
                if (event.result.status === "pending-payment" || event.result.status === "held") {
                  setActivePnr(event.result.pnr);
                } else {
                  setActivePnr(null);
                }
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
      passengerProfile,
      threadId
    );
  };
  
  handleSendRef.current = handleSend;

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
        padding: "12px"
      }}
    >
      {/* Messages Scroll Area */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          paddingRight: "4px",
          marginBottom: "10px",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {messages.length === 0 ? (
          <div style={{ margin: "auto", textAlign: "center", color: "#475569", maxWidth: "80%", display: "flex", flexDirection: "column", alignItems: "center", gap: "16px" }}>
            <span style={{ fontSize: "40px" }}>🤖</span>
            <h3 style={{ fontSize: "16px", fontWeight: "bold", margin: 0, color: "#0f172a" }}>Apex Agent</h3>
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
        <div className={`input-glow-wrapper ${isStreaming ? "generating-glow" : ""}`} style={{ flex: 1 }}>
          <div className="input-glow-container">
            <Input.TextArea
              value={inputVal}
              onChange={(e) => setInputVal(e.target.value)}
              placeholder={isStreaming ? "Generating response..." : `Ask a question... [Model: ${modelName}]`}
              autoSize={{ minRows: 2, maxRows: 4 }}
              onPressEnter={(e) => {
                if (!e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isStreaming}
              style={{ borderRadius: "8px", paddingBottom: "24px" }}
            />
            <div style={{
              position: "absolute",
              bottom: "6px",
              right: "12px",
              fontSize: "10px",
              color: "#94a3b8",
              pointerEvents: "none",
              zIndex: 4,
              fontFamily: "monospace"
            }}>
              ⚡ {modelName}
            </div>
          </div>
        </div>
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={() => handleSend()}
          disabled={!inputVal.trim() || isStreaming}
          style={{ height: "auto" }}
        />
      </div>
      <style>{`
        @keyframes rotateGlow {
          0% {
            transform: translate(-50%, -50%) rotate(0deg);
          }
          100% {
            transform: translate(-50%, -50%) rotate(360deg);
          }
        }

        @keyframes pulseGlow {
          0% {
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.45), 0 0 16px rgba(56, 189, 248, 0.2);
          }
          25% {
            box-shadow: 0 0 8px rgba(236, 72, 153, 0.45), 0 0 16px rgba(236, 72, 153, 0.2);
          }
          50% {
            box-shadow: 0 0 8px rgba(251, 191, 36, 0.45), 0 0 16px rgba(251, 191, 36, 0.2);
          }
          75% {
            box-shadow: 0 0 8px rgba(168, 85, 247, 0.45), 0 0 16px rgba(168, 85, 247, 0.25);
          }
          100% {
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.45), 0 0 16px rgba(56, 189, 248, 0.2);
          }
        }

        .input-glow-wrapper {
          position: relative;
          display: flex;
          flex-direction: column;
          border-radius: 10px;
          background: transparent;
          transition: all 0.3s ease;
        }

        .input-glow-wrapper.generating-glow {
          animation: pulseGlow 4s linear infinite;
        }

        .input-glow-container {
          position: relative;
          display: flex;
          flex-direction: column;
          border-radius: 10px;
          padding: 2px;
          background: #e2e8f0;
          overflow: hidden;
          transition: all 0.3s ease;
          z-index: 2;
          width: 100%;
        }

        .input-glow-container:focus-within {
          background: #38bdf8;
          box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15);
        }

        /* Rotating border background when generating */
        .generating-glow .input-glow-container {
          background: transparent !important;
        }

        .generating-glow .input-glow-container::before {
          content: '';
          position: absolute;
          width: 150%;
          height: 0;
          padding-bottom: 150%;
          background: conic-gradient(
            from 0deg,
            #38bdf8 0deg,
            #ec4899 90deg,
            #fbbf24 180deg,
            #a855f7 270deg,
            #38bdf8 360deg
          );
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%) rotate(0deg);
          animation: rotateGlow 3s linear infinite;
          z-index: 1;
        }

        .input-glow-container .ant-input {
          position: relative;
          z-index: 3;
          border: none !important;
          box-shadow: none !important;
          background: #ffffff !important;
          color: #0f172a !important;
          border-radius: 8px !important;
          padding: 10px 14px !important;
        }

        .generating-glow .ant-input,
        .generating-glow .ant-input-disabled,
        .generating-glow .ant-input[disabled] {
          background: #ffffff !important;
          color: #0f172a !important;
          cursor: wait !important;
        }
      `}</style>
    </Card>
  );
};
