import React, { useState } from "react";
import { Card, Form, Input, Button, Alert, Table, Typography } from "antd";
import { LockOutlined, UserOutlined, ArrowRightOutlined } from "@ant-design/icons";

const { Title, Paragraph } = Typography;

interface LoginProps {
  onLogin: (user: {
    username: string;
    role: "admin" | "passenger";
    passengerProfile?: {
      passenger_id: string;
      name: string;
      email: string;
      frequent_flyer_number: string;
    };
  }) => void;
}

export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleFinish = (values: any) => {
    setLoading(true);
    setErrorMsg("");

    setTimeout(() => {
      const { username, password } = values;

      // Validate Credentials
      if (username === "admin" && password === "admin123") {
        onLogin({
          username: "admin",
          role: "admin"
        });
      } else if (username === "jane.smith@example.com" && password === "password123") {
        onLogin({
          username: "jane.smith@example.com",
          role: "passenger",
          passengerProfile: {
            passenger_id: "usr_94f83b",
            name: "Jane Smith",
            email: "jane.smith@example.com",
            frequent_flyer_number: "FF773910"
          }
        });
      } else if (username === "alex.mercer@example.com" && password === "password123") {
        onLogin({
          username: "alex.mercer@example.com",
          role: "passenger",
          passengerProfile: {
            passenger_id: "usr_28a71c",
            name: "Alex Mercer",
            email: "alex.mercer@example.com",
            frequent_flyer_number: "FF998822"
          }
        });
      } else {
        setErrorMsg("Invalid username or password. Please use one of the credentials below.");
      }
      setLoading(false);
    }, 600);
  };

  const columns = [
    {
      title: "Role / Name",
      dataIndex: "name",
      key: "name",
      render: (text: string, record: any) => (
        <div>
          <strong style={{ display: "block" }}>{text}</strong>
          <span style={{ fontSize: "11px", color: "#8c8c8c" }}>{record.desc}</span>
        </div>
      )
    },
    {
      title: "Username / Email",
      dataIndex: "username",
      key: "username",
      render: (text: string) => <code style={{ color: "#096dd9" }}>{text}</code>
    },
    {
      title: "Password",
      dataIndex: "password",
      key: "password",
      render: (text: string) => <code style={{ color: "#d4380d" }}>{text}</code>
    }
  ];

  const credentialData = [
    {
      key: "1",
      name: "Jane Smith",
      desc: "Passenger Profile 1",
      username: "jane.smith@example.com",
      password: "password123"
    },
    {
      key: "2",
      name: "Alex Mercer",
      desc: "Passenger Profile 2",
      username: "alex.mercer@example.com",
      password: "password123"
    },
    {
      key: "3",
      name: "Administrator",
      desc: "Full access to ingestion & search tabs",
      username: "admin",
      password: "admin123"
    }
  ];

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      justifyContent: "center",
      alignItems: "center",
      background: "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%)",
      padding: "24px",
      fontFamily: "Inter, system-ui, -apple-system, sans-serif"
    }}>
      <div style={{ width: "100%", maxWidth: "580px", display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", color: "#fff" }}>
          <Title level={2} style={{ color: "#fff", margin: 0, fontWeight: 800, letterSpacing: "-0.5px" }}>
            ✈️ Apex Flight Portal
          </Title>
          <Paragraph style={{ color: "#94a3b8", marginTop: "8px", fontSize: "14px" }}>
            Welcome to the AI-powered passenger booking and management panel.
          </Paragraph>
        </div>

        {/* Login Box */}
        <Card
          style={{
            background: "rgba(255, 255, 255, 0.95)",
            border: "none",
            borderRadius: "16px",
            boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
          }}
          bodyStyle={{ padding: "36px" }}
        >
          <Form
            name="login_form"
            layout="vertical"
            initialValues={{ remember: true }}
            onFinish={handleFinish}
          >
            {errorMsg && (
              <Alert
                message={errorMsg}
                type="error"
                showIcon
                style={{ marginBottom: "20px", borderRadius: "8px" }}
              />
            )}

            <Form.Item
              name="username"
              rules={[{ required: true, message: "Please input your username or email!" }]}
            >
              <Input 
                prefix={<UserOutlined style={{ color: "#94a3b8" }} />} 
                placeholder="Username / Email" 
                size="large"
                style={{ borderRadius: "8px" }}
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: "Please input your password!" }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: "#94a3b8" }} />}
                placeholder="Password"
                size="large"
                style={{ borderRadius: "8px" }}
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button 
                type="primary" 
                htmlType="submit" 
                size="large" 
                loading={loading}
                block
                style={{ 
                  borderRadius: "8px", 
                  background: "linear-gradient(90deg, #1890ff, #0050b3)",
                  border: "none",
                  height: "46px",
                  fontSize: "15px",
                  fontWeight: "600",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "6px"
                }}
              >
                Sign In <ArrowRightOutlined />
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* Credentials Help Box */}
        <Card
          title={
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span>💡</span> Available Test Accounts
            </div>
          }
          style={{
            background: "rgba(30, 41, 59, 0.7)",
            border: "1px solid rgba(255, 255, 255, 0.1)",
            borderRadius: "12px",
            color: "#fff"
          }}
          headStyle={{
            color: "#fff",
            borderBottom: "1px solid rgba(255, 255, 255, 0.1)"
          }}
          bodyStyle={{ padding: "12px" }}
        >
          <Table
            columns={columns}
            dataSource={credentialData}
            pagination={false}
            size="small"
            style={{ background: "transparent" }}
            rowClassName={() => "login-table-row"}
          />
        </Card>
      </div>

      {/* Global CSS injection for transparency of antd table on login screen */}
      <style>{`
        .login-table-row {
          background: transparent !important;
        }
        .login-table-row td {
          color: #e2e8f0 !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        .login-table-row:hover td {
          background: rgba(255, 255, 255, 0.05) !important;
        }
        .ant-table-thead > tr > th {
          background: rgba(255, 255, 255, 0.05) !important;
          color: #94a3b8 !important;
          border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
      `}</style>
    </div>
  );
};
