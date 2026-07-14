import { Modal, Divider, Tag, Space, Button, Dropdown, message } from "antd";
import { DownloadOutlined, CopyOutlined } from "@ant-design/icons";
import type { DocumentChunk } from "../types/api";
import { exportToCSV, exportToJSON } from "../utils/export";

interface ChunkDetailsProps {
  chunk: DocumentChunk | null;
  visible: boolean;
  onClose: () => void;
}

export const ChunkDetails = ({ chunk, visible, onClose }: ChunkDetailsProps) => {
  if (!chunk) return null;

  const handleExport = (format: "csv" | "json") => {
    try {
      if (format === "csv") {
        exportToCSV([chunk]);
      } else {
        exportToJSON([chunk]);
      }
      message.success(`Exported to ${format.toUpperCase()}`);
    } catch (error) {
      message.error("Export failed");
    }
  };

  const handleCopyContent = () => {
    navigator.clipboard.writeText(chunk.chunk_content);
    message.success("Chunk content copied to clipboard");
  };

  const exportItems = [
    {
      key: "csv",
      label: "Export as CSV",
      onClick: () => handleExport("csv"),
    },
    {
      key: "json",
      label: "Export as JSON",
      onClick: () => handleExport("json"),
    },
  ];

  return (
    <Modal
      title={`Chunk Details - ${chunk.metadata.source || "Unknown"}`}
      open={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="close" onClick={onClose}>
          Close
        </Button>,
        <Dropdown menu={{ items: exportItems }} key="export">
          <Button
            type="primary"
            icon={<DownloadOutlined />}
          >
            Export
          </Button>
        </Dropdown>,
      ]}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="large">
        {/* Score and metadata summary */}
        <div
          style={{
            padding: "16px",
            background: "#f0f5ff",
            borderRadius: "4px",
            border: "1px solid #b6e3ff",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ marginRight: "12px" }}>
                <strong>Similarity Score:</strong>
              </span>
              <Tag color="blue">{(chunk.similarity * 100).toFixed(1)}%</Tag>
            </div>
            <Button
              size="small"
              icon={<CopyOutlined />}
              onClick={handleCopyContent}
            >
              Copy Content
            </Button>
          </div>
        </div>

        {/* Chunk Content */}
        <div>
          <h3 style={{ marginBottom: "8px" }}>Content</h3>
          <div
            style={{
              padding: "12px",
              background: "#fafafa",
              borderRadius: "4px",
              border: "1px solid #d9d9d9",
              maxHeight: "300px",
              overflowY: "auto",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              lineHeight: "1.6",
              fontFamily: "monospace",
              fontSize: "12px",
            }}
          >
            {chunk.chunk_content}
          </div>
        </div>

        <Divider />

        {/* Metadata Section */}
        <div>
          <h3 style={{ marginBottom: "12px" }}>Metadata</h3>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
              gap: "16px",
            }}
          >
            {chunk.metadata.source && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Source:
                </p>
                <p style={{ margin: 0, wordBreak: "break-all" }}>
                  {chunk.metadata.source}
                </p>
              </div>
            )}

            {chunk.metadata.document_id && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Document ID:
                </p>
                <p style={{ margin: 0, fontSize: "12px", fontFamily: "monospace" }}>
                  {chunk.metadata.document_id}
                </p>
              </div>
            )}

            {chunk.metadata.chunk_index !== undefined && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Chunk Index:
                </p>
                <p style={{ margin: 0 }}>{chunk.metadata.chunk_index}</p>
              </div>
            )}

            {chunk.metadata.page_label && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Page Label:
                </p>
                <p style={{ margin: 0 }}>{chunk.metadata.page_label}</p>
              </div>
            )}

            {chunk.metadata.page_range && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Page Range:
                </p>
                <p style={{ margin: 0 }}>{chunk.metadata.page_range}</p>
              </div>
            )}

            {chunk.metadata.category && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Category:
                </p>
                <Tag>{chunk.metadata.category}</Tag>
              </div>
            )}

            {chunk.metadata.ingestion_date && (
              <div>
                <p style={{ margin: "0 0 4px 0", fontSize: "12px", color: "#999" }}>
                  Ingestion Date:
                </p>
                <p style={{ margin: 0 }}>{chunk.metadata.ingestion_date}</p>
              </div>
            )}

            {chunk.metadata.tags && chunk.metadata.tags.length > 0 && (
              <div style={{ gridColumn: "1 / -1" }}>
                <p style={{ margin: "0 0 8px 0", fontSize: "12px", color: "#999" }}>
                  Tags:
                </p>
                <div>
                  {chunk.metadata.tags.map((tag, idx) => (
                    <Tag key={idx} style={{ marginRight: "8px", marginBottom: "4px" }}>
                      {tag}
                    </Tag>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Space>
    </Modal>
  );
};
