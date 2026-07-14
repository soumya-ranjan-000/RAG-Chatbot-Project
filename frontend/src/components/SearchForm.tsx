import { useState } from "react";
import { Form, Input, Button, Slider, Space, Card, Spin, message } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { QueryResponse } from "../types/api";

interface SearchFormProps {
  onSearch?: (query: string, topK: number, threshold: number) => void;
  queryFn?: (text: string, topK: number, threshold: number) => Promise<QueryResponse | null>;
  loading?: boolean;
  error?: string | null;
}

export const SearchForm = ({ onSearch, queryFn, loading: externalLoading, error: externalError }: SearchFormProps) => {
  const [form] = Form.useForm();
  const [topK, setTopK] = useState(5);
  const [threshold, setThreshold] = useState(0.5);
  const [localLoading, setLocalLoading] = useState(false);

  const loading = externalLoading ?? localLoading;
  const error = externalError;

  const handleSubmit = async (values: { searchQuery: string }) => {
    if (!values.searchQuery.trim()) {
      message.warning("Please enter a search query");
      return;
    }

    setLocalLoading(true);
    try {
      const result = await queryFn?.(values.searchQuery, topK, threshold);
      if (result) {
        onSearch?.(values.searchQuery, topK, threshold);
        message.success(`Found ${result.results_count} results`);
      }
    } finally {
      setLocalLoading(false);
    }
  };

  return (
    <Card style={{ marginBottom: "20px" }}>
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        {error && (
          <div
            style={{
              padding: "12px",
              background: "#ffebee",
              border: "1px solid #ef5350",
              borderRadius: "4px",
              marginBottom: "16px",
              color: "#d32f2f",
              fontSize: "14px",
            }}
          >
            {error}
          </div>
        )}

        <Form.Item
          label="Search Query"
          name="searchQuery"
          rules={[
            { required: true, message: "Please enter a search query" },
          ]}
        >
          <Input
            placeholder="e.g., What is the main topic of this document?"
            disabled={loading}
            size="large"
          />
        </Form.Item>

        <Form.Item label="Number of Results (Top K)">
          <Slider
            min={1}
            max={20}
            value={topK}
            onChange={setTopK}
            marks={{ 1: "1", 5: "5", 10: "10", 20: "20" }}
            disabled={loading}
          />
          <p style={{ textAlign: "center", color: "#999", marginTop: "8px" }}>
            Selected: {topK}
          </p>
        </Form.Item>

        <Form.Item label="Similarity Threshold">
          <Slider
            min={0}
            max={1}
            step={0.05}
            value={threshold}
            onChange={setThreshold}
            marks={{ 0: "0", 0.5: "0.5", 1: "1" }}
            disabled={loading}
          />
          <p style={{ textAlign: "center", color: "#999", marginTop: "8px" }}>
            Selected: {threshold.toFixed(2)}
          </p>
        </Form.Item>

        <Space style={{ width: "100%", justifyContent: "flex-end" }}>
          <Button onClick={() => form.resetFields()}>Reset</Button>
          <Button
            type="primary"
            htmlType="submit"
            icon={<SearchOutlined />}
            loading={loading}
            size="large"
          >
            Search Documents
          </Button>
        </Space>
      </Form>

      {loading && (
        <div style={{ textAlign: "center", margin: "20px 0" }}>
          <Spin tip="Searching..." />
        </div>
      )}
    </Card>
  );
};
