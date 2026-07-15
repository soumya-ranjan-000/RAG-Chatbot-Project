import React, { useState, useEffect, useRef } from "react";
import { Button, Input, Tag } from "antd";
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClearOutlined,
  SearchOutlined,
  CopyOutlined,
  CheckOutlined,
  CodeOutlined,
  DatabaseOutlined,
  InfoCircleOutlined,
} from "@ant-design/icons";

interface ToolActivity {
  name: string;
  args?: any;
  result?: any;
  timestamp: string;
  status: "running" | "success" | "failed";
}

export const AgentLogPage: React.FC = () => {
  const [logs, setLogs] = useState<ToolActivity[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<"all" | "running" | "success" | "failed">("all");
  const [copied, setCopied] = useState(false);

  const channelRef = useRef<BroadcastChannel | null>(null);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("agent_tool_activity");
      if (saved) {
        const parsed = JSON.parse(saved);
        setLogs(parsed);
        if (parsed.length > 0) {
          setSelectedIdx(parsed.length - 1);
        }
      }
    } catch (_) {}

    const channel = new BroadcastChannel("agent_tool_activity");
    channelRef.current = channel;

    channel.onmessage = (event) => {
      const activity: ToolActivity = event.data;
      setLogs((prev) => {
        // Replace running entry with resolved one
        const filtered = prev.filter(
          (x) => !(x.name === activity.name && x.status === "running")
        );
        const next = [...filtered, activity];
        localStorage.setItem("agent_tool_activity", JSON.stringify(next));
        return next;
      });
    };

    return () => channel.close();
  }, []);

  // Auto-select latest log if nothing was selected or when a new log arrives
  useEffect(() => {
    if (logs.length > 0 && selectedIdx === null) {
      setSelectedIdx(logs.length - 1);
    }
  }, [logs, selectedIdx]);

  const handleClear = () => {
    setLogs([]);
    setSelectedIdx(null);
    localStorage.removeItem("agent_tool_activity");
  };

  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Filter logic
  const filteredLogs = logs.filter((log) => {
    const matchesSearch = log.name.toLowerCase().includes(search.toLowerCase());
    const matchesFilter = filter === "all" || log.status === filter;
    return matchesSearch && matchesFilter;
  });

  const selectedLog = selectedIdx !== null && logs[selectedIdx] ? logs[selectedIdx] : null;

  // Stats calculation
  const totalCalls = logs.length;
  const successCalls = logs.filter((l) => l.status === "success").length;
  const failedCalls = logs.filter((l) => l.status === "failed").length;
  const runningCalls = logs.filter((l) => l.status === "running").length;

  return (
    <div
      style={{
        height: "100vh",
        background: "#080c14",
        color: "#f1f5f9",
        display: "flex",
        flexDirection: "column",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        overflow: "hidden",
      }}
    >
      {/* Top Banner / Metrics bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "#0f172a",
          padding: "12px 24px",
          borderBottom: "1px solid #1e293b",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <div style={{ display: "flex", gap: "6px" }}>
            <span
              style={{
                width: "12px",
                height: "12px",
                borderRadius: "50%",
                background: "#ff5f56",
                cursor: "pointer",
              }}
              onClick={() => window.close()}
            />
            <span style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#ffbd2e" }} />
            <span style={{ width: "12px", height: "12px", borderRadius: "50%", background: "#27c93f" }} />
          </div>
          <div style={{ display: "flex", flexDirection: "column" }}>
            <span style={{ fontSize: "14px", fontWeight: "bold", color: "#f8fafc" }}>
              PSS Agent Inspector
            </span>
            <span style={{ fontSize: "11px", color: "#64748b", fontFamily: "monospace" }}>
              agent-executor@system — live trace logs
            </span>
          </div>
        </div>

        {/* Real-time stats display */}
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <div style={{ display: "flex", gap: "16px", fontSize: "12px" }}>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ color: "#64748b", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase" }}>Total</span>
              <span style={{ color: "#38bdf8", fontWeight: "bold", fontSize: "15px" }}>{totalCalls}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ color: "#64748b", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase" }}>Success</span>
              <span style={{ color: "#10b981", fontWeight: "bold", fontSize: "15px" }}>{successCalls}</span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
              <span style={{ color: "#64748b", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase" }}>Errors</span>
              <span style={{ color: "#ef4444", fontWeight: "bold", fontSize: "15px" }}>{failedCalls}</span>
            </div>
            {runningCalls > 0 && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <span style={{ color: "#64748b", fontSize: "10px", fontWeight: "bold", textTransform: "uppercase" }}>Active</span>
                <span style={{ color: "#3b82f6", fontWeight: "bold", fontSize: "15px", display: "flex", alignItems: "center", gap: "4px" }}>
                  {runningCalls} <SyncOutlined spin style={{ fontSize: "10px" }} />
                </span>
              </div>
            )}
          </div>

          <Button
            size="small"
            danger
            icon={<ClearOutlined />}
            onClick={handleClear}
            style={{
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              color: "#fca5a5",
              fontSize: "11px",
              fontWeight: "bold",
              borderRadius: "6px",
            }}
          >
            Clear Console
          </Button>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        {/* Left Panel: Executions List */}
        <div
          style={{
            width: "360px",
            background: "#090d16",
            borderRight: "1px solid #1e293b",
            display: "flex",
            flexDirection: "column",
            flexShrink: 0,
          }}
        >
          {/* Search and Filters */}
          <div style={{ padding: "12px", borderBottom: "1px solid #1e293b", display: "flex", flexDirection: "column", gap: "10px" }}>
            <Input
              placeholder="Search tools..."
              prefix={<SearchOutlined style={{ color: "#64748b" }} />}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{
                background: "#0d1321",
                border: "1px solid #1e293b",
                color: "#f8fafc",
                fontSize: "12px",
                borderRadius: "6px",
              }}
              className="terminal-search-input"
            />
            {/* Filter pills */}
            <div style={{ display: "flex", gap: "6px" }}>
              {(["all", "running", "success", "failed"] as const).map((t) => {
                const isActive = filter === t;
                const label = t === "failed" ? "Errors" : t.toUpperCase();
                const activeColor =
                  t === "success"
                    ? "#10b981"
                    : t === "failed"
                    ? "#ef4444"
                    : t === "running"
                    ? "#3b82f6"
                    : "#38bdf8";

                return (
                  <button
                    key={t}
                    onClick={() => setFilter(t)}
                    style={{
                      flex: 1,
                      padding: "4px 0",
                      background: isActive ? `${activeColor}15` : "#131b2e",
                      border: `1px solid ${isActive ? activeColor : "#1e293b"}`,
                      color: isActive ? activeColor : "#64748b",
                      fontSize: "10px",
                      fontWeight: "bold",
                      borderRadius: "4px",
                      cursor: "pointer",
                      textTransform: "uppercase",
                      transition: "all 0.15s ease",
                    }}
                  >
                    {label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* List items */}
          <div style={{ flex: 1, overflowY: "auto", padding: "8px" }} className="custom-scroll">
            {filteredLogs.length === 0 ? (
              <div style={{ textAlign: "center", color: "#475569", padding: "40px 10px", fontSize: "12px" }}>
                No operations recorded
              </div>
            ) : (
              filteredLogs.map((activity, idx) => {
                const actualIndex = logs.findIndex((l) => l === activity);
                const isSelected = selectedIdx === actualIndex;
                const isRunning = activity.status === "running";
                const isFailed = activity.status === "failed";
                const statusColor = isFailed ? "#ef4444" : isRunning ? "#3b82f6" : "#10b981";

                return (
                  <div
                    key={idx}
                    onClick={() => setSelectedIdx(actualIndex)}
                    style={{
                      padding: "10px 12px",
                      background: isSelected ? "rgba(56, 189, 248, 0.08)" : "transparent",
                      border: `1px solid ${isSelected ? "rgba(56, 189, 248, 0.2)" : "transparent"}`,
                      borderLeft: `3px solid ${isSelected ? statusColor : "transparent"}`,
                      borderRadius: "6px",
                      marginBottom: "6px",
                      cursor: "pointer",
                      display: "flex",
                      flexDirection: "column",
                      gap: "4px",
                      transition: "all 0.15s ease",
                    }}
                    className="log-item-hover"
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
                        <span style={{ display: "flex", alignItems: "center" }}>
                          {isRunning ? (
                            <SyncOutlined spin style={{ color: "#3b82f6", fontSize: "11px" }} />
                          ) : isFailed ? (
                            <CloseCircleOutlined style={{ color: "#ef4444", fontSize: "11px" }} />
                          ) : (
                            <CheckCircleOutlined style={{ color: "#10b981", fontSize: "11px" }} />
                          )}
                        </span>
                        <span
                          style={{
                            fontWeight: "bold",
                            fontSize: "12px",
                            color: isSelected ? "#38bdf8" : "#cbd5e1",
                            fontFamily: "monospace",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {activity.name}
                        </span>
                      </div>
                      <span style={{ fontSize: "10px", color: "#475569", fontFamily: "monospace" }}>
                        {activity.timestamp.split(" ")[1] || activity.timestamp}
                      </span>
                    </div>

                    {/* Quick args preview */}
                    {activity.args && Object.keys(activity.args).length > 0 && (
                      <div
                        style={{
                          fontSize: "10px",
                          color: "#64748b",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          fontFamily: "monospace",
                        }}
                      >
                        {Object.entries(activity.args)
                          .map(([k, v]) => `${k}:${JSON.stringify(v)}`)
                          .join(", ")}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Panel: Detailed Inspector */}
        <div style={{ flex: 1, background: "#06090f", overflowY: "auto", display: "flex", flexDirection: "column" }}>
          {selectedLog ? (
            <div style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
              {/* Header card info */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  background: "#0d1321",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  padding: "16px 20px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                  <div style={{ fontSize: "11px", color: "#64748b", fontWeight: "bold", textTransform: "uppercase" }}>
                    Selected Trace
                  </div>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: "bold",
                      color: "#38bdf8",
                      fontFamily: "monospace",
                    }}
                  >
                    {selectedLog.name}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <Tag
                    color={
                      selectedLog.status === "success"
                        ? "success"
                        : selectedLog.status === "failed"
                        ? "error"
                        : "processing"
                    }
                    style={{ margin: 0, fontWeight: "bold", textTransform: "uppercase" }}
                  >
                    {selectedLog.status}
                  </Tag>
                  <Button
                    icon={copied ? <CheckOutlined style={{ color: "#10b981" }} /> : <CopyOutlined />}
                    onClick={() => handleCopy(JSON.stringify(selectedLog, null, 2))}
                    style={{
                      background: "#1e293b",
                      border: "1px solid #334155",
                      color: "#cbd5e1",
                    }}
                  >
                    {copied ? "Copied" : "Copy Log Data"}
                  </Button>
                </div>
              </div>

              {/* Arguments box */}
              <div
                style={{
                  background: "#0a0e17",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  padding: "16px 20px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "11px",
                    color: "#f43f5e",
                    fontWeight: "bold",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    marginBottom: "12px",
                  }}
                >
                  <DatabaseOutlined /> Input Arguments
                </div>

                {selectedLog.args && Object.keys(selectedLog.args).length > 0 ? (
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))", gap: "10px" }}>
                    {Object.entries(selectedLog.args).map(([key, val]) => (
                      <div
                        key={key}
                        style={{
                          background: "#0f172a",
                          border: "1px solid #1e293b",
                          borderRadius: "6px",
                          padding: "8px 12px",
                          display: "flex",
                          flexDirection: "column",
                          gap: "2px",
                        }}
                      >
                        <span style={{ fontSize: "10px", color: "#64748b", fontFamily: "monospace" }}>{key}</span>
                        <span
                          style={{
                            fontSize: "12px",
                            color: "#f8fafc",
                            fontFamily: "monospace",
                            fontWeight: "bold",
                            wordBreak: "break-all",
                          }}
                        >
                          {typeof val === "object" ? JSON.stringify(val) : String(val)}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div style={{ fontSize: "12px", color: "#475569", fontStyle: "italic" }}>
                    No arguments passed to this tool.
                  </div>
                )}
              </div>

              {/* Response output */}
              <div
                style={{
                  background: "#0a0e17",
                  border: "1px solid #1e293b",
                  borderRadius: "8px",
                  padding: "16px 20px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    fontSize: "11px",
                    color: selectedLog.status === "failed" ? "#ef4444" : "#10b981",
                    fontWeight: "bold",
                    textTransform: "uppercase",
                    letterSpacing: "0.5px",
                    marginBottom: "12px",
                  }}
                >
                  <CodeOutlined /> Response Payload
                </div>

                {selectedLog.result !== undefined ? (
                  <pre
                    className="custom-scroll"
                    style={{
                      margin: 0,
                      background: "#04060a",
                      border: "1px solid #1e293b",
                      borderRadius: "6px",
                      padding: "16px",
                      fontSize: "12px",
                      color: selectedLog.status === "failed" ? "#fca5a5" : "#34d399",
                      fontFamily: "'Fira Code', monospace",
                      maxHeight: "450px",
                      overflow: "auto",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-all",
                    }}
                  >
                    {JSON.stringify(selectedLog.result, null, 2)}
                  </pre>
                ) : (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                      color: "#64748b",
                      fontSize: "12px",
                      fontStyle: "italic",
                    }}
                  >
                    <SyncOutlined spin /> Tool execution in progress...
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: "16px",
                color: "#475569",
              }}
            >
              <InfoCircleOutlined style={{ fontSize: "36px", color: "#1e293b" }} />
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: "14px", fontWeight: "bold", color: "#334155" }}>
                  Select an Execution
                </div>
                <div style={{ fontSize: "11px", color: "#1e293b", marginTop: "4px" }}>
                  Click an operation in the left pane to view inputs and outputs
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      <style>{`
        .log-item-hover:hover {
          background: rgba(56, 189, 248, 0.03) !important;
        }
        .terminal-search-input input {
          background: #0d1321 !important;
          color: #f8fafc !important;
          border-color: #1e293b !important;
        }
        .custom-scroll::-webkit-scrollbar {
          width: 5px;
        }
        .custom-scroll::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scroll::-webkit-scrollbar-thumb {
          background: #1e293b;
          border-radius: 4px;
        }
      `}</style>
    </div>
  );
};
