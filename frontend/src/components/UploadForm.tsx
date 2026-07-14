import { useState } from "react";
import { Upload, Button, Progress, Space, Alert, message } from "antd";
import { UploadOutlined, LinkOutlined } from "@ant-design/icons";
import type { RcFile } from "antd/es/upload/interface";
import apiService from "../services/api";
import type { IngestionRequest } from "../types/api";

export const UploadForm = () => {
  const [loading, setLoading] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<RcFile | null>(null);
  const [s3Uri, setS3Uri] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

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
      // TODO: Display ingestion progress component
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Ingestion failed";
      setError(errorMsg);
      message.error(errorMsg);
    }
  };

  return (
    <div style={{ 
      maxWidth: "600px",
      width: "100%",
      overflow: "hidden",
    }}>
      <h2 style={{ marginBottom: "20px" }}>Upload Document</h2>

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
          }
        }}
        accept=".pdf,.txt"
        disabled={loading}
      >
        <Button icon={<UploadOutlined />} disabled={loading}>
          Select PDF or TXT file
        </Button>
      </Upload>

      {uploadedFile && (
        <>
          <p style={{ marginTop: "16px", color: "#666" }}>
            Selected: <strong>{uploadedFile.name}</strong>
          </p>

          {progress > 0 && (
            <div style={{ marginBottom: "16px" }}>
              <Progress percent={Math.round(progress)} />
            </div>
          )}

          <Space>
            <Button
              type="primary"
              size="large"
              onClick={handleUpload}
              loading={loading}
            >
              Upload to S3
            </Button>
          </Space>
        </>
      )}

      {s3Uri && (
        <div
          style={{
            marginTop: "24px",
            padding: "16px",
            background: "#f6ffed",
            border: "1px solid #b7eb8f",
            borderRadius: "4px",
          }}
        >
          <h3 style={{ marginBottom: "8px", color: "#52c41a" }}>
            Upload Successful!
          </h3>
          <p style={{ marginBottom: "12px", wordBreak: "break-all" }}>
            <LinkOutlined /> {s3Uri}
          </p>
          <p style={{ fontSize: "12px", color: "#666" }}>
            File has been uploaded to S3 and ingestion pipeline has been triggered.
          </p>
        </div>
      )}
    </div>
  );
};
