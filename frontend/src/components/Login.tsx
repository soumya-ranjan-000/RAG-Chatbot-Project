import React, { useState } from "react";
import { Card, Form, Input, Button, Alert, Typography, Tooltip } from "antd";
import { LockOutlined, UserOutlined, ArrowRightOutlined, SmileOutlined, CrownOutlined } from "@ant-design/icons";
import { PSS_API_URL } from "../services/api";

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
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [activeQuickLogin, setActiveQuickLogin] = useState<string | null>(null);

  const handleFinish = async (values: any) => {
    setLoading(true);
    setErrorMsg("");

    try {
      const { username, password, first_name, last_name } = values;

      if (isSignUp) {
        // Register new user
        const res = await fetch(`${PSS_API_URL}/passengers`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            first_name: first_name,
            last_name: last_name,
            email: username
          })
        });

        if (res.ok) {
          const newUser = await res.json();
          // Save mock password in local storage
          const stored = JSON.parse(localStorage.getItem("mock_passwords") || "{}");
          stored[username] = password;
          localStorage.setItem("mock_passwords", JSON.stringify(stored));

          onLogin({
            username: username,
            role: "passenger",
            passengerProfile: {
              passenger_id: newUser.passenger_id || newUser.legacy_id,
              name: `${newUser.first_name || ""} ${newUser.last_name || ""}`.trim(),
              email: newUser.email,
              frequent_flyer_number: newUser.frequent_flyer_number || ""
            }
          });
        } else {
          try {
            const data = await res.json();
            setErrorMsg(data.detail || "Registration failed. Please try again.");
          } catch (e) {
            setErrorMsg("Registration failed. Please try again.");
          }
        }
      } else {
        // Login logic
        if (username === "admin" && password === "admin123") {
          onLogin({ username: "admin", role: "admin" });
          return;
        }

        // Fetch all passengers to see if user exists
        const res = await fetch(`${PSS_API_URL}/passengers`);
        if (res.ok) {
          const passengers = await res.json();
          const found = passengers.find((p: any) => p.email === username);

          if (found) {
            const storedPasswords = JSON.parse(localStorage.getItem("mock_passwords") || "{}");
            const expectedPassword = storedPasswords[username] || "password123";

            if (password === expectedPassword) {
              onLogin({
                username: found.email,
                role: "passenger",
                passengerProfile: {
                  passenger_id: found.passenger_id || found.legacy_id,
                  name: `${found.first_name || ""} ${found.last_name || ""}`.trim(),
                  email: found.email,
                  frequent_flyer_number: found.frequent_flyer_number || ""
                }
              });
              return;
            }
          }
        }
        
        setErrorMsg("Invalid username or password.");
      }
    } catch (e) {
      setErrorMsg("Failed to connect to the authentication server.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickLogin = (role: string, user: string, pass: string) => {
    setActiveQuickLogin(role);
    form.setFieldsValue({
      username: user,
      password: pass
    });
    setTimeout(() => setActiveQuickLogin(null), 600);
  };

  return (
    <div className="login-container">
      {/* Background decoration circles */}
      <div className="bg-glow bg-glow-1"></div>
      <div className="bg-glow bg-glow-2"></div>

      <div className="login-card-wrapper">
        <div className="login-main-panel">
          {/* Brand Header */}
          <div className="brand-header">
            <div className="airplane-icon-container">
              <svg 
                className="floating-airplane" 
                viewBox="0 0 24 24" 
                fill="none" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  d="M21 16V14L13 9V3.5C13 2.67 12.33 2 11.5 2C10.67 2 10 2.67 10 3.5V9L2 14V16L10 13.5V19L8 20.5V22L11.5 21L15 22V20.5L13 19V13.5L21 16Z" 
                  fill="url(#plane-grad)"
                />
                <defs>
                  <linearGradient id="plane-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                    <stop stopColor="#38bdf8" />
                    <stop offset="1" stopColor="#0284c7" />
                  </linearGradient>
                </defs>
              </svg>
            </div>
            <Title level={1} className="brand-title">
              Apex Air
            </Title>
            <Paragraph className="brand-subtitle">
              Next-Gen AI-Powered Passenger Portal
            </Paragraph>
          </div>

          {/* Main Card */}
          <Card className="glass-card">
            <div className="tab-header">
            <button 
              type="button"
              className={`tab-btn ${!isSignUp ? "active" : ""}`}
              onClick={() => {
                setIsSignUp(false);
                setErrorMsg("");
              }}
            >
              Sign In
            </button>
            <button 
              type="button"
              className={`tab-btn ${isSignUp ? "active" : ""}`}
              onClick={() => {
                setIsSignUp(true);
                setErrorMsg("");
              }}
            >
              Sign Up
            </button>
            <div className={`tab-slider ${isSignUp ? "slide-right" : ""}`}></div>
          </div>

          <Form
            form={form}
            name="login_form"
            layout="vertical"
            onFinish={handleFinish}
            requiredMark={false}
            className="modern-form"
          >
            {errorMsg && (
              <Alert
                message={errorMsg}
                type="error"
                showIcon
                className="error-alert"
              />
            )}

            {isSignUp && (
              <div className="name-row">
                <Form.Item
                  name="first_name"
                  rules={[{ required: true, message: "Please input your first name!" }]}
                  style={{ flex: 1, marginBottom: 16 }}
                >
                  <Input 
                    placeholder="First Name" 
                    size="large" 
                    className="modern-input"
                  />
                </Form.Item>
                <Form.Item
                  name="last_name"
                  rules={[{ required: true, message: "Please input your last name!" }]}
                  style={{ flex: 1, marginBottom: 16 }}
                >
                  <Input 
                    placeholder="Last Name" 
                    size="large" 
                    className="modern-input"
                  />
                </Form.Item>
              </div>
            )}

            <Form.Item
              name="username"
              rules={[
                { required: true, message: "Please input your email or username!" },
                isSignUp ? { type: "email", message: "Please enter a valid email address!" } : {}
              ]}
              style={{ marginBottom: 20 }}
            >
              <Input 
                prefix={<UserOutlined className="input-icon" />} 
                placeholder={isSignUp ? "Email Address" : "Email or Username"} 
                size="large"
                className="modern-input"
              />
            </Form.Item>

            <Form.Item
              name="password"
              rules={[{ required: true, message: "Please input your password!" }]}
              style={{ marginBottom: 24 }}
            >
              <Input.Password
                prefix={<LockOutlined className="input-icon" />}
                placeholder="Password"
                size="large"
                className="modern-input"
              />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0 }}>
              <Button 
                type="primary" 
                htmlType="submit" 
                size="large" 
                loading={loading}
                block
                className="submit-btn"
              >
                <span>{isSignUp ? "Create Account" : "Sign In"}</span>
                <ArrowRightOutlined className="submit-arrow" />
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>

      {/* Demo accounts preview */}
        <div className="demo-accounts-section">
          <div className="demo-title">
            <span className="lightbulb-icon">💡</span>
            <span>Quick Login Accounts</span>
          </div>
          <div className="demo-list">
            {[
              {
                key: "passenger1",
                roleName: "Jane Smith",
                roleType: "Passenger",
                username: "jane.smith@example.com",
                password: "password123",
                icon: <SmileOutlined className="role-icon p-color" />
              },
              {
                key: "passenger2",
                roleName: "Alex Mercer",
                roleType: "Passenger",
                username: "alex.mercer@example.com",
                password: "password123",
                icon: <SmileOutlined className="role-icon p-color" />
              },
              {
                key: "admin",
                roleName: "System Administrator",
                roleType: "Admin",
                username: "admin",
                password: "admin123",
                icon: <CrownOutlined className="role-icon a-color" />
              }
            ].map((acc) => (
              <Tooltip key={acc.key} title="Click to auto-fill credentials" placement="right">
                <div 
                  className={`demo-row-card ${activeQuickLogin === acc.key ? "ripple-effect" : ""}`}
                  onClick={() => handleQuickLogin(acc.key, acc.username, acc.password)}
                >
                  <div className="demo-row-left">
                    {acc.icon}
                    <div className="demo-row-details">
                      <div className="demo-row-title">
                        <span className="demo-row-name">{acc.roleName}</span>
                        <span className={`demo-badge ${acc.roleType.toLowerCase()}`}>{acc.roleType}</span>
                      </div>
                      <div className="demo-row-creds">
                        <span className="demo-cred-label">User: <code>{acc.username}</code></span>
                        <span className="demo-cred-divider">•</span>
                        <span className="demo-cred-label">Pass: <code>{acc.password}</code></span>
                      </div>
                    </div>
                  </div>
                  <ArrowRightOutlined className="demo-row-arrow" />
                </div>
              </Tooltip>
            ))}
          </div>
        </div>
      </div>

      <style>{`
        /* Core Layout */
        .login-container {
          height: 100vh;
          width: 100%;
          display: flex;
          flex-direction: column;
          justify-content: center;
          align-items: center;
          background: #090d16;
          position: relative;
          overflow: hidden;
          font-family: 'Inter', system-ui, -apple-system, sans-serif;
          padding: 20px;
          box-sizing: border-box;
        }

        /* Ambient Glow Backgrounds */
        .bg-glow {
          position: absolute;
          border-radius: 50%;
          filter: blur(120px);
          opacity: 0.15;
          z-index: 1;
          pointer-events: none;
        }
        .bg-glow-1 {
          width: 500px;
          height: 500px;
          background: #38bdf8;
          top: -100px;
          left: -100px;
          animation: float-glow-1 20s infinite alternate;
        }
        .bg-glow-2 {
          width: 600px;
          height: 600px;
          background: #0369a1;
          bottom: -150px;
          right: -150px;
          animation: float-glow-2 25s infinite alternate;
        }

        @keyframes float-glow-1 {
          0% { transform: translate(0, 0) scale(1); }
          100% { transform: translate(80px, 50px) scale(1.1); }
        }
        @keyframes float-glow-2 {
          0% { transform: translate(0, 0) scale(1); }
          100% { transform: translate(-100px, -80px) scale(1.2); }
        }

        /* Card Wrapper */
        .login-card-wrapper {
          width: 100%;
          max-width: 480px;
          z-index: 10;
          display: flex;
          flex-direction: column;
          gap: 24px;
          max-height: 95vh;
          overflow-y: auto;
          scrollbar-width: none;
          -ms-overflow-style: none;
          animation: fade-in-up 0.8s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .login-card-wrapper::-webkit-scrollbar {
          display: none;
        }

        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        /* Brand Header */
        .brand-header {
          text-align: center;
        }
        .airplane-icon-container {
          display: inline-flex;
          align-items: center;
          justify-content: center;
          width: 64px;
          height: 64px;
          border-radius: 20px;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.08);
          margin-bottom: 16px;
          box-shadow: 0 10px 20px rgba(0, 0, 0, 0.2);
        }
        .floating-airplane {
          width: 36px;
          height: 36px;
          transform: rotate(-45deg);
          animation: bobbing 3s ease-in-out infinite;
        }

        @keyframes bobbing {
          0%, 100% { transform: rotate(-45deg) translateY(0); }
          50% { transform: rotate(-45deg) translateY(-5px); }
        }

        .brand-title {
          color: #f8fafc !important;
          margin: 0 !important;
          font-weight: 900 !important;
          letter-spacing: -1.5px !important;
          font-size: 2.25rem !important;
          background: linear-gradient(135deg, #fff 0%, #cbd5e1 100%);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
        }
        .brand-subtitle {
          color: #64748b !important;
          margin-top: 6px !important;
          margin-bottom: 0 !important;
          font-size: 0.95rem !important;
          font-weight: 500;
        }

        /* Glassmorphism Card styling */
        .glass-card {
          background: rgba(15, 23, 42, 0.5) !important;
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.07) !important;
          border-radius: 24px !important;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
          overflow: hidden;
        }
        .glass-card .ant-card-body {
          padding: 40px !important;
        }

        /* Modern Tabs Header */
        .tab-header {
          display: flex;
          position: relative;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 4px;
          border-radius: 12px;
          margin-bottom: 32px;
        }
        .tab-btn {
          flex: 1;
          background: transparent;
          border: none;
          color: #64748b;
          font-size: 0.95rem;
          font-weight: 600;
          padding: 10px 0;
          cursor: pointer;
          z-index: 2;
          transition: color 0.3s ease;
        }
        .tab-btn.active {
          color: #f8fafc;
        }
        .tab-slider {
          position: absolute;
          left: 4px;
          top: 4px;
          width: calc(50% - 4px);
          height: calc(100% - 8px);
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 8px;
          z-index: 1;
          transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }
        .tab-slider.slide-right {
          transform: translateX(100%);
        }

        /* Alert Styling */
        .error-alert {
          border-radius: 12px !important;
          background-color: rgba(239, 68, 68, 0.1) !important;
          border: 1px solid rgba(239, 68, 68, 0.15) !important;
          color: #fca5a5 !important;
          margin-bottom: 24px !important;
        }
        .error-alert .ant-alert-icon {
          color: #ef4444 !important;
        }

        /* Forms and Inputs */
        .name-row {
          display: flex;
          gap: 16px;
        }
        .modern-input::placeholder,
        .ant-input::placeholder {
          color: #94a3b8 !important;
          opacity: 1 !important;
        }
        .modern-input {
          background: rgba(255, 255, 255, 0.02) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          border-radius: 12px !important;
          color: #f1f5f9 !important;
          padding: 12px 16px !important;
          font-size: 0.95rem !important;
          transition: all 0.3s ease !important;
        }
        .modern-input:hover {
          border-color: rgba(255, 255, 255, 0.15) !important;
          background: rgba(255, 255, 255, 0.04) !important;
        }
        .modern-input:focus, .modern-input-focused {
          border-color: #38bdf8 !important;
          box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15) !important;
          background: rgba(255, 255, 255, 0.03) !important;
        }
        .ant-input-affix-wrapper {
          background: rgba(255, 255, 255, 0.02) !important;
          border: 1px solid rgba(255, 255, 255, 0.08) !important;
          border-radius: 12px !important;
          padding: 12px 16px !important;
          transition: all 0.3s ease !important;
        }
        .ant-input-affix-wrapper:hover {
          border-color: rgba(255, 255, 255, 0.15) !important;
          background: rgba(255, 255, 255, 0.04) !important;
        }
        .ant-input-affix-wrapper-focused {
          border-color: #38bdf8 !important;
          box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.15) !important;
          background: rgba(255, 255, 255, 0.03) !important;
        }
        .ant-input-affix-wrapper input {
          background: transparent !important;
          color: #f1f5f9 !important;
          font-size: 0.95rem !important;
        }
        .input-icon {
          color: #64748b !important;
          margin-right: 8px !important;
          font-size: 1rem !important;
        }
        .ant-input-password-icon {
          color: #64748b !important;
        }
        .ant-input-password-icon:hover {
          color: #f1f5f9 !important;
        }

        /* Submit Button */
        .submit-btn {
          height: 52px !important;
          border-radius: 12px !important;
          background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%) !important;
          border: none !important;
          font-weight: 700 !important;
          font-size: 1rem !important;
          box-shadow: 0 4px 20px rgba(56, 189, 248, 0.25) !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          gap: 8px !important;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
        }
        .submit-btn:hover {
          transform: translateY(-1px) !important;
          box-shadow: 0 6px 24px rgba(56, 189, 248, 0.35) !important;
          background: linear-gradient(135deg, #7dd3fc 0%, #0369a1 100%) !important;
        }
        .submit-btn:active {
          transform: translateY(1px) !important;
        }
        .submit-arrow {
          transition: transform 0.3s ease;
        }
        .submit-btn:hover .submit-arrow {
          transform: translateX(4px);
        }

        /* Demo Accounts Section */
        .demo-accounts-section {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .demo-title {
          display: flex;
          align-items: center;
          gap: 8px;
          color: #94a3b8;
          font-size: 0.85rem;
          font-weight: 600;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }
        .lightbulb-icon {
          font-size: 1rem;
        }
        .demo-list {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .demo-row-card {
          background: rgba(15, 23, 42, 0.4);
          border: 1px solid rgba(255, 255, 255, 0.04);
          border-radius: 14px;
          padding: 12px 16px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: space-between;
          transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
          position: relative;
          overflow: hidden;
        }
        .demo-row-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(90deg, rgba(56, 189, 248, 0.04) 0%, transparent 100%);
          opacity: 0;
          transition: opacity 0.3s ease;
        }
        .demo-row-card:hover {
          border-color: rgba(56, 189, 248, 0.25);
          background: rgba(15, 23, 42, 0.55);
          transform: translateX(4px);
        }
        .demo-row-card:hover::before {
          opacity: 1;
        }
        .demo-row-left {
          display: flex;
          align-items: center;
          gap: 14px;
          min-width: 0;
          z-index: 2;
        }
        .role-icon {
          font-size: 1.1rem;
          padding: 8px;
          border-radius: 10px;
          flex-shrink: 0;
        }
        .p-color {
          color: #38bdf8;
          background: rgba(56, 189, 248, 0.08);
        }
        .a-color {
          color: #fbbf24;
          background: rgba(251, 191, 36, 0.08);
        }
        .demo-row-details {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .demo-row-title {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .demo-row-name {
          color: #e2e8f0;
          font-size: 0.85rem;
          font-weight: 700;
        }
        .demo-badge {
          font-size: 0.65rem;
          font-weight: 700;
          padding: 1px 6px;
          border-radius: 4px;
          text-transform: uppercase;
          letter-spacing: 0.3px;
        }
        .demo-badge.passenger {
          color: #38bdf8;
          background: rgba(56, 189, 248, 0.12);
        }
        .demo-badge.admin {
          color: #fbbf24;
          background: rgba(251, 191, 36, 0.12);
        }
        .demo-row-creds {
          display: flex;
          align-items: center;
          gap: 6px;
          color: #64748b;
          font-size: 0.72rem;
        }
        .demo-cred-label code {
          color: #cbd5e1;
          font-family: inherit;
          font-weight: 600;
          background: rgba(255, 255, 255, 0.04);
          padding: 1px 4px;
          border-radius: 4px;
        }
        .demo-cred-divider {
          color: #334155;
        }
        .demo-row-arrow {
          color: #475569;
          font-size: 0.9rem;
          transition: all 0.3s ease;
          z-index: 2;
        }
        .demo-row-card:hover .demo-row-arrow {
          color: #38bdf8;
          transform: translateX(3px);
        }

        /* Success Click ripple effect */
        .ripple-effect {
          border-color: #38bdf8 !important;
          box-shadow: 0 0 16px rgba(56, 189, 248, 0.3) !important;
        }

        @media (max-width: 480px) {
          .name-row {
            flex-direction: column;
            gap: 0;
          }
        }

        @media (min-width: 1024px) {
          .login-card-wrapper {
            max-width: 900px !important;
            max-height: 85vh !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: center !important;
            gap: 40px !important;
            padding: 0 !important;
            overflow-y: visible !important;
          }
          .login-main-panel {
            flex: 1.2 !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 16px !important;
          }
          .glass-card .ant-card-body {
            padding: 24px 32px !important;
          }
          .brand-header {
            margin-bottom: 8px !important;
          }
          .airplane-icon-container {
            width: 48px !important;
            height: 48px !important;
            border-radius: 14px !important;
            margin-bottom: 8px !important;
          }
          .floating-airplane {
            width: 26px !important;
            height: 26px !important;
          }
          .brand-title {
            font-size: 1.75rem !important;
          }
          .tab-header {
            margin-bottom: 18px !important;
          }
          .demo-accounts-section {
            flex: 1 !important;
            background: rgba(15, 23, 42, 0.4) !important;
            backdrop-filter: blur(20px) !important;
            -webkit-backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(255, 255, 255, 0.07) !important;
            border-radius: 24px !important;
            padding: 24px 20px !important;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4) !important;
            height: fit-content !important;
            align-self: center !important;
          }
          .demo-list {
            gap: 8px !important;
          }
        }
      `}</style>
    </div>
  );
};
