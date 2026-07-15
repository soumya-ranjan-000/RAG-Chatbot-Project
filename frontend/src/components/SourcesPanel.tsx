import React from "react";
import { Card, Badge, Empty, Tag, Typography } from "antd";
import { FilePdfOutlined, InfoCircleOutlined, TagsOutlined } from "@ant-design/icons";
import type { ChunkSource } from "../types/chat";

const { Text } = Typography;

interface SourcesPanelProps {
  sources: ChunkSource[];
  isLoading: boolean;
}

export const SourcesPanel: React.FC<SourcesPanelProps> = ({ sources, isLoading }) => {
  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "#52c41a"; // green
    if (score >= 0.6) return "#faad14"; // orange
    return "#f5222d"; // red
  };

  return (
    <Card
      title={
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <span>🔍 Retrieved Chunks (Debug)</span>
          <Badge count={sources.length} showZero color="#1890ff" />
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
        overflow: "auto",
        padding: "16px",
        background: "#fafafa"
      }}
    >
      {isLoading && sources.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0", color: "#8c8c8c" }}>
          <InfoCircleOutlined spin style={{ fontSize: "24px", marginBottom: "12px", color: "#1890ff" }} />
          <div>Retrieving relevant chunks...</div>
        </div>
      ) : sources.length === 0 ? (
        <Empty description="No chunks retrieved yet. Send a message to see the debug info." style={{ marginTop: "40px" }} />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {sources.map((source, index) => {
            const scoreColor = getScoreColor(source.similarity);
            const metadata = source.metadata || {};

            return (
              <Card
                key={index}
                id={`chunk-card-${index}`}
                size="small"
                style={{
                  borderLeft: `4px solid ${scoreColor}`,
                  borderRadius: "6px",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.02)",
                  transition: "all 0.3s ease"
                }}
                title={
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "70%" }}>
                      <FilePdfOutlined style={{ color: "#ff4d4f" }} />
                      <Text strong ellipsis title={source.document_name}>
                        {source.document_name}
                      </Text>
                    </div>
                    <Badge
                      count={`${Math.round(source.similarity * 100)}% Match`}
                      style={{
                        backgroundColor: scoreColor,
                        borderRadius: "4px",
                        padding: "0 6px"
                      }}
                    />
                  </div>
                }
              >
                <div style={{ marginBottom: "8px" }}>
                  <Tag color="blue">{source.page_label}</Tag>
                  {metadata.category && <Tag color="purple">{metadata.category}</Tag>}
                  {metadata.ingestion_date && <Tag color="default">{metadata.ingestion_date}</Tag>}
                </div>

                <div style={{
                  background: "#f0f2f5",
                  padding: "10px",
                  borderRadius: "4px",
                  fontSize: "13px",
                  maxHeight: "150px",
                  overflowY: "auto",
                  fontFamily: "monospace",
                  whiteSpace: "pre-wrap",
                  lineHeight: "1.4",
                  marginBottom: "8px"
                }}>
                  {source.chunk_content}
                </div>

                {metadata.tags && metadata.tags.length > 0 && (
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", flexWrap: "wrap" }}>
                    <TagsOutlined style={{ color: "#8c8c8c", fontSize: "12px" }} />
                    {metadata.tags.map((tag: string, tagIdx: number) => (
                      <Tag key={tagIdx} style={{ fontSize: "11px", margin: 0 }}>
                        {tag}
                      </Tag>
                    ))}
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </Card>
  );
};
