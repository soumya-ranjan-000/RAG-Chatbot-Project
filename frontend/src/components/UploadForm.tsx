import { useState, useEffect } from "react";
import {
  Upload,
  Button,
  Progress,
  Space,
  Alert,
  message,
  Card,
  Table,
  Tag,
  Row,
  Col,
  Tooltip,
  Popconfirm,
  Input,
} from "antd";
import {
  UploadOutlined,
  LinkOutlined,
  ReloadOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  SearchOutlined,
  DatabaseOutlined,
} from "@ant-design/icons";
import type { RcFile } from "antd/es/upload/interface";
import apiService from "../services/api";
import type { IngestionRequest, S3File, JobProgress } from "../types/api";
import { IngestionProgress } from "./IngestionProgress";

// Format bytes to human readable format
const formatBytes = (bytes: number, decimals = 2) => {
  if (!bytes) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
};

export const UploadForm = () => {
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<RcFile | null>(null);
  const [s3Uri, setS3Uri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  // S3 Files List States
  const [files, setFiles] = useState<S3File[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Fetch files on mount
  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    setFilesLoading(true);
    try {
      const data = await apiService.listFiles();
      setFiles(data);
    } catch (err) {
      console.error("Error loading S3 files:", err);
      message.error("Failed to load files from S3 bucket");
    } finally {
      setFilesLoading(false);
    }
  };

  const beforeUpload = (file: RcFile) => {
    const isPDF = file.type === "application/pdf";
    const isTXT = file.type === "text/plain";
    const isValid = isPDF || isTXT;

    if (!isValid) {
      setError("You can only upload PDF or TXT files");
    }

    const isLt50M = file.size / 1024 / 1024 < 50;
    if (!isLt50M) {
      setError("File must be smaller than 50MB");
    }

    return isValid && isLt50M;
  };

  const handleUpload = async () => {
    if (!uploadedFile) {
      setError("No file selected");
      return;
    }

    setLoading(true);
    setError(null);
    setProgress(0);

    try {
      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + Math.random() * 30;
        });
      }, 500);

      const response = await apiService.uploadFile(uploadedFile);

      clearInterval(progressInterval);
      setProgress(100);
      setS3Uri(response.s3_uri);

      message.success(`File uploaded successfully to S3!`);
      setUploadedFile(null); // Reset upload selector

      // Refresh files list immediately to show the new file
      fetchFiles();

      // Auto-trigger ingestion after upload
      setTimeout(() => {
        triggerIngestion(response.s3_uri);
      }, 1000);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Upload failed";
      setError(errorMsg);
      message.error(errorMsg);
    } finally {
      setLoading(false);
      setProgress(0);
    }
  };

  const triggerIngestion = async (s3Uri: string) => {
    try {
      const [bucket, key] = s3Uri.replace("s3://", "").split("/", 2);

      const ingestionRequest: IngestionRequest = {
        Records: [
          {
            s3: {
              bucket: { name: bucket },
              object: { key },
            },
          },
        ],
      };

      const response = await apiService.triggerIngestion(ingestionRequest);
      message.info(`Ingestion started with Job ID: ${response.job_id}`);
      setActiveJobId(response.job_id);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Ingestion failed";
      setError(errorMsg);
      message.error(errorMsg);
    }
  };

  const handleTriggerIngest = async (s3Uri: string) => {
    try {
      const [bucket, key] = s3Uri.replace("s3://", "").split("/", 2);

      const ingestionRequest: IngestionRequest = {
        Records: [
          {
            s3: {
              bucket: { name: bucket },
              object: { key },
            },
          },
        ],
      };

      const response = await apiService.triggerIngestion(ingestionRequest);
      message.success(`Ingestion restarted with Job ID: ${response.job_id}`);
      setActiveJobId(response.job_id);
    } catch (err) {
      console.error("Ingestion trigger failed:", err);
      message.error("Failed to start ingestion job");
    }
  };

  const handleDelete = async (key: string) => {
    try {
      await apiService.deleteFile(key);
      message.success(`Successfully deleted file and index: ${key}`);
      fetchFiles();
    } catch (err) {
      console.error("Delete failed:", err);
      message.error(`Failed to delete file ${key}`);
    }
  };

  const handleJobUpdate = (jobProgress: JobProgress) => {
    if (jobProgress.status === "completed" || jobProgress.status === "failed") {
      // Refresh the files list once the job is completed or failed
      fetchFiles();
    }
  };

  // Filter files based on search input
  const filteredFiles = files.filter((file) =>
    file.key.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const columns = [
    {
      title: "File Name",
      dataIndex: "key",
      key: "key",
      ellipsis: true,
      sorter: (a: S3File, b: S3File) => a.key.localeCompare(b.key),
      render: (text: string) => (
        <span style={{ fontWeight: 500, wordBreak: "break-all" }}>{text}</span>
      ),
    },
    {
      title: "Size",
      dataIndex: "size",
      key: "size",
      width: 100,
      sorter: (a: S3File, b: S3File) => a.size - b.size,
      render: (size: number) => formatBytes(size),
    },
    {
      title: "Status",
      dataIndex: "indexed",
      key: "indexed",
      width: 120,
      filters: [
        { text: "Indexed", value: true },
        { text: "Not Indexed", value: false },
      ],
      onFilter: (value: any, record: S3File) => record.indexed === value,
      render: (indexed: boolean) => (
        <Tag
          color={indexed ? "green" : "orange"}
          style={{ borderRadius: "12px", padding: "0 10px" }}
        >
          {indexed ? "Indexed" : "Not Indexed"}
        </Tag>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      width: 120,
      render: (_: any, record: S3File) => (
        <Space size="small">
          <Tooltip title={record.indexed ? "Already Indexed" : "Trigger Ingestion"}>
            <Button
              type="text"
              icon={<PlayCircleOutlined style={{ color: record.indexed ? "#bfbfbf" : "#1890ff" }} />}
              onClick={() => handleTriggerIngest(record.s3_uri)}
              disabled={loading || activeJobId !== null || record.indexed}
            />
          </Tooltip>
          <Popconfirm
            title="Delete File"
            description="Delete file from S3 and all its chunks from the database?"
            onConfirm={() => handleDelete(record.key)}
            okText="Delete"
            cancelText="Cancel"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="Delete File">
              <Button
                type="text"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Row gutter={[24, 24]} style={{ margin: 0, width: "100%" }}>
      {/* Upload Column */}
      <Col xs={24} lg={9}>
        <Space direction="vertical" style={{ width: "100%" }} size="large">
          <Card
            title={<><DatabaseOutlined /> Upload Document</>}
            bordered={false}
            style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
          >
            {error && (
              <Alert
                message="Error"
                description={error}
                type="error"
                closable
                style={{ marginBottom: "16px" }}
                onClose={() => setError(null)}
              />
            )}

            <Upload
              name="file"
              maxCount={1}
              beforeUpload={beforeUpload}
              onChange={(info) => {
                if (info.fileList.length > 0) {
                  setUploadedFile(info.fileList[0].originFileObj || null);
                } else {
                  setUploadedFile(null);
                }
              }}
              accept=".pdf,.txt"
              disabled={loading}
              fileList={uploadedFile ? [uploadedFile as any] : []}
              onRemove={() => setUploadedFile(null)}
            >
              <Button icon={<UploadOutlined />} disabled={loading} style={{ width: "100%" }}>
                Select PDF or TXT file
              </Button>
            </Upload>

            {uploadedFile && (
              <div style={{ marginTop: "16px" }}>
                {progress > 0 && (
                  <div style={{ marginBottom: "16px" }}>
                    <Progress percent={Math.round(progress)} />
                  </div>
                )}

                <Button
                  type="primary"
                  size="large"
                  onClick={handleUpload}
                  loading={loading}
                  style={{ width: "100%" }}
                >
                  Upload to S3
                </Button>
              </div>
            )}

            {s3Uri && !activeJobId && (
              <div
                style={{
                  marginTop: "24px",
                  padding: "16px",
                  background: "#f6ffed",
                  border: "1px solid #b7eb8f",
                  borderRadius: "4px",
                }}
              >
                <h3 style={{ marginBottom: "8px", color: "#52c41a", fontSize: "14px" }}>
                  Upload Successful!
                </h3>
                <p style={{ marginBottom: "12px", wordBreak: "break-all", fontSize: "12px" }}>
                  <LinkOutlined /> {s3Uri}
                </p>
                <p style={{ fontSize: "11px", color: "#666" }}>
                  File uploaded to S3. Ingestion should begin shortly.
                </p>
              </div>
            )}
          </Card>

          {/* Active Job Progress */}
          {activeJobId && (
            <div style={{ margin: "0 -24px" }}>
              <IngestionProgress
                jobId={activeJobId}
                onStreamUpdate={handleJobUpdate}
              />
            </div>
          )}
        </Space>
      </Col>

      {/* Files List Column */}
      <Col xs={24} lg={15}>
        <Card
          title={
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
              <span>Files in S3 Bucket</span>
              <Button
                type="text"
                icon={<ReloadOutlined spin={filesLoading} />}
                onClick={fetchFiles}
              />
            </div>
          }
          bordered={false}
          style={{ boxShadow: "0 4px 12px rgba(0,0,0,0.05)" }}
        >
          <Input
            placeholder="Search files..."
            prefix={<SearchOutlined />}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{ marginBottom: "16px" }}
            allowClear
          />

          <Table
            columns={columns}
            dataSource={filteredFiles}
            rowKey="key"
            loading={filesLoading}
            pagination={{ pageSize: 8 }}
            size="middle"
          />
        </Card>
      </Col>
    </Row>
  );
};
