import { Table, Tag, Button, Space, Empty, Tooltip } from "antd";
import { EyeOutlined, DownloadOutlined } from "@ant-design/icons";
import type { DocumentChunk } from "../types/api";

interface ResultsTableProps {
  results: DocumentChunk[];
  loading?: boolean;
  onViewDetails?: (chunk: DocumentChunk) => void;
  onExport?: (chunk: DocumentChunk) => void;
}

export const ResultsTable = ({
  results,
  loading = false,
  onViewDetails,
  onExport,
}: ResultsTableProps) => {
  if (results.length === 0) {
    return <Empty description="No results found. Try a different search query." />;
  }

  const columns = [
    {
      title: "Document Name",
      dataIndex: ["metadata", "source"],
      key: "document_name",
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip title={text}>
          {text}
        </Tooltip>
      ),
    },
    {
      title: "Similarity",
      dataIndex: "similarity",
      key: "similarity",
      render: (score: number) => {
        const percentage = Math.round(score * 100);
        let color = "red";
        if (percentage >= 70) color = "green";
        else if (percentage >= 50) color = "orange";
        return <Tag color={color}>{percentage}%</Tag>;
      },
      sorter: (a: DocumentChunk, b: DocumentChunk) =>
        b.similarity - a.similarity,
    },
    {
      title: "Preview",
      dataIndex: "chunk_content",
      key: "preview",
      ellipsis: {
        showTitle: false,
      },
      render: (text: string) => (
        <Tooltip title={text} placement="topLeft">
          <span style={{
            display: "block",
            maxWidth: "200px",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            color: "#666",
          }}>
            {text}
          </span>
        </Tooltip>
      ),
    },
    {
      title: "Category",
      dataIndex: ["metadata", "category"],
      key: "category",
      render: (text: string | undefined) =>
        text ? <Tag>{text}</Tag> : <span style={{ color: "#999" }}>-</span>,
    },
    {
      title: "Date",
      dataIndex: ["metadata", "ingestion_date"],
      key: "ingestion_date",
      render: (text: string | undefined) => text || "-",
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, record: DocumentChunk) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => onViewDetails?.(record)}
            title="View full details"
          />
          <Button
            type="text"
            size="small"
            icon={<DownloadOutlined />}
            onClick={() => onExport?.(record)}
            title="Export chunk"
          />
        </Space>
      ),
    },
  ];

  return (
    <div style={{ width: "100%", overflow: "auto" }}>
      <Table
        columns={columns}
        dataSource={results}
        rowKey={(_, index) => index!.toString()}
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} results`,
        }}
        size="small"
        style={{ width: "100%" }}
      />
    </div>
  );
};
