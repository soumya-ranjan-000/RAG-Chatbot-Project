import { useState } from "react";
import { Card, Progress, Statistic, Space, Empty, Tag, List, Spin } from "antd";
import {
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  LoadingOutlined,
} from "@ant-design/icons";
import type { JobProgress, JobStatus } from "../types/api";
import { useSSE } from "../hooks/useSSE";

interface IngestionProgressProps {
  jobId: string | null;
  onStreamUpdate?: (progress: JobProgress) => void;
}

const statusConfig: Record<JobStatus, { color: string; icon: React.ReactNode }> =
  {
    pending: { color: "default", icon: <ClockCircleOutlined /> },
    in_progress: { color: "processing", icon: <LoadingOutlined /> },
    completed: { color: "success", icon: <CheckCircleOutlined /> },
    failed: { color: "error", icon: <ExclamationCircleOutlined /> },
  };

export const IngestionProgress = ({
  jobId,
  onStreamUpdate,
}: IngestionProgressProps) => {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);

  const streamUrl = jobId ? `${import.meta.env.VITE_API_URL}/ingest/stream/${jobId}` : null;

  useSSE(streamUrl, {
    onMessage: (data) => {
      setProgress(data);
      onStreamUpdate?.(data);
    },
    onError: (error) => {
      console.error("Stream error:", error);
      setStreamError(error.message);
    },
  });

  if (!jobId) {
    return (
      <Empty
        description="No active ingestion job"
        style={{ margin: "40px 0" }}
      />
    );
  }

  if (!progress) {
    return (
      <div style={{ textAlign: "center", padding: "40px 0" }}>
        <Spin size="large" tip="Waiting for ingestion updates..." />
      </div>
    );
  }

  const progressPercent = Math.round(
    (progress.processed_files / progress.total_files) * 100
  );

  const config = statusConfig[progress.status];

  return (
    <div style={{ padding: "24px" }}>
      <h2 style={{ marginBottom: "20px" }}>Ingestion Progress</h2>

      <Card style={{ marginBottom: "16px" }}>
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          <div>
            <div style={{ marginBottom: "8px", display: "flex", alignItems: "center", gap: "8px" }}>
              <span>{config.icon}</span>
              <Tag color={config.color}>{progress.status.toUpperCase()}</Tag>
              <span style={{ color: "#666", fontSize: "14px" }}>
                {progress.message}
              </span>
            </div>
            <Progress percent={progressPercent} />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "16px" }}>
            <Statistic
              title="Total Files"
              value={progress.total_files}
            />
            <Statistic
              title="Processed"
              value={progress.processed_files}
              suffix={`/ ${progress.total_files}`}
              valueStyle={{
                color: progress.status === "completed" ? "#52c41a" : "#1890ff",
              }}
            />
            <Statistic
              title="Progress"
              value={progressPercent}
              suffix="%"
            />
          </div>

          {progress.current_file && (
            <div
              style={{
                padding: "12px",
                background: "#f5f5f5",
                borderRadius: "4px",
              }}
            >
              <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                Current File:
              </p>
              <p style={{ margin: 0, wordBreak: "break-all" }}>
                {progress.current_file}
              </p>
            </div>
          )}

          {progress.errors && progress.errors.length > 0 && (
            <div>
              <h4 style={{ marginBottom: "8px", color: "#d32f2f" }}>Errors:</h4>
              <List
                dataSource={progress.errors}
                renderItem={(error, idx) => (
                  <List.Item
                    key={idx}
                    style={{
                      padding: "8px 12px",
                      background: "#ffebee",
                      marginBottom: "8px",
                      borderRadius: "4px",
                      borderLeft: "3px solid #d32f2f",
                    }}
                  >
                    <span style={{ color: "#d32f2f", fontSize: "12px" }}>
                      {error}
                    </span>
                  </List.Item>
                )}
              />
            </div>
          )}
        </Space>
      </Card>

      {streamError && (
        <div
          style={{
            padding: "12px",
            background: "#fff7e6",
            border: "1px solid #ffc069",
            borderRadius: "4px",
            marginBottom: "16px",
            fontSize: "12px",
            color: "#d46b08",
          }}
        >
          ⚠️ {streamError}
        </div>
      )}

      {progress.status === "completed" && (
        <div
          style={{
            padding: "16px",
            background: "#f6ffed",
            border: "1px solid #b7eb8f",
            borderRadius: "4px",
          }}
        >
          <p style={{ margin: 0, color: "#52c41a", fontWeight: "bold" }}>
            ✓ Ingestion completed successfully! Documents are now searchable.
          </p>
        </div>
      )}
    </div>
  );
};
