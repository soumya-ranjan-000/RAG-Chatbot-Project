import { useState, useEffect } from "react";
import { Card, Form, Input, Button, Select, Alert, message, Typography, Divider, Space } from "antd";
import { SettingOutlined, KeyOutlined, RobotOutlined, SaveOutlined, LockOutlined } from "@ant-design/icons";
import { apiService } from "../services/api";

const { Title, Paragraph } = Typography;
const { Option } = Select;

export const SettingsPanel = () => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [isKeyConfigured, setIsKeyConfigured] = useState(false);

  useEffect(() => {
    const fetchSettings = async () => {
      setLoading(true);
      try {
        const data = await apiService.getSettings();
        form.setFieldsValue({
          model: data.model,
          openai_api_key: data.openai_api_key || "",
        });
        setIsKeyConfigured(data.is_key_configured);
      } catch (err) {
        message.error("Failed to load settings from server.");
      } finally {
        setLoading(false);
      }
    };

    fetchSettings();
  }, [form]);

  const handleSubmit = async (values: { model: string; openai_api_key?: string }) => {
    setSaving(true);
    try {
      await apiService.updateSettings(values);
      message.success("Settings updated successfully!");
      // Re-fetch to get updated masked key
      const data = await apiService.getSettings();
      form.setFieldsValue({
        model: data.model,
        openai_api_key: data.openai_api_key || "",
      });
      setIsKeyConfigured(data.is_key_configured);
    } catch (err) {
      message.error("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div style={{ maxWidth: "680px", margin: "0 auto", padding: "8px 0" }}>
      <Card
        loading={loading}
        bordered={false}
        style={{
          borderRadius: "16px",
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.05)",
          background: "#ffffff",
        }}
      >
        <Space align="center" style={{ marginBottom: "20px" }}>
          <div style={{
            background: "linear-gradient(135deg, #1890ff 0%, #096dd9 100%)",
            width: "42px",
            height: "42px",
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 12px rgba(24, 144, 255, 0.2)",
            color: "#fff",
            fontSize: "20px"
          }}>
            <SettingOutlined />
          </div>
          <div>
            <Title level={3} style={{ margin: 0, fontWeight: 700 }}>AI Orchestrator Settings</Title>
            <Paragraph type="secondary" style={{ margin: 0, fontSize: "13px" }}>
              Configure the active LLM engine and credentials for the RAG Chatbot.
            </Paragraph>
          </div>
        </Space>

        <Divider style={{ margin: "16px 0 24px 0" }} />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          requiredMark={false}
        >
          {/* LLM Model Selection */}
          <Form.Item
            name="model"
            label={
              <Space>
                <RobotOutlined style={{ color: "#1890ff" }} />
                <span style={{ fontWeight: 600 }}>Active LLM Model</span>
              </Space>
            }
            rules={[{ required: true, message: "Please select an LLM model" }]}
          >
            <Select
              size="large"
              placeholder="Select an LLM model"
              style={{ width: "100%" }}
            >
              <Option value="gpt-4o-mini">gpt-4o-mini (Default - Fast & Cost-efficient)</Option>
              <Option value="gpt-4o">gpt-4o (High intelligence & capability)</Option>
              <Option value="gpt-3.5-turbo">gpt-3.5-turbo (Legacy model)</Option>
            </Select>
          </Form.Item>

          <Paragraph type="secondary" style={{ fontSize: "12px", marginTop: "-8px", marginBottom: "20px", paddingLeft: "4px" }}>
            The active model determines the speed, latency, cost, and overall intelligence of the booking agent executor.
          </Paragraph>

          {/* OpenAI API Key */}
          <Form.Item
            name="openai_api_key"
            label={
              <Space>
                <KeyOutlined style={{ color: "#fa8c16" }} />
                <span style={{ fontWeight: 600 }}>OpenAI API Key</span>
              </Space>
            }
            rules={[{ required: true, message: "Please provide an API key" }]}
          >
            <Input.Password
              size="large"
              placeholder={isKeyConfigured ? "••••••••••••••••" : "sk-...xxxxxxxx"}
              prefix={<LockOutlined style={{ color: "#bfbfbf" }} />}
            />
          </Form.Item>

          <div style={{ marginBottom: "24px" }}>
            {isKeyConfigured ? (
              <Alert
                message="API Key Status: Configured & Active"
                type="success"
                showIcon
                style={{ borderRadius: "8px" }}
              />
            ) : (
              <Alert
                message="API Key Status: Missing"
                description="Please configure your OpenAI API key to enable chatbot streaming."
                type="warning"
                showIcon
                style={{ borderRadius: "8px" }}
              />
            )}
          </div>

          <Divider style={{ margin: "24px 0" }} />

          <Form.Item style={{ margin: 0, textAlign: "right" }}>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={saving}
              size="large"
              style={{
                borderRadius: "8px",
                height: "44px",
                padding: "0 28px",
                fontWeight: 600,
                boxShadow: "0 4px 12px rgba(24, 144, 255, 0.25)"
              }}
            >
              Save Configuration
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};
