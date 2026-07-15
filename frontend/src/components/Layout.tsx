import { Layout, Menu, Drawer, Avatar, Dropdown, Button, Tooltip } from "antd";
import { UserOutlined, LogoutOutlined, CodeOutlined } from "@ant-design/icons";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

interface AppLayoutProps {
  children: React.ReactNode;
  currentUser: {
    username: string;
    role: "admin" | "passenger";
    passengerProfile?: {
      passenger_id: string;
      name: string;
      email: string;
      frequent_flyer_number: string;
    };
  };
  onLogout: () => void;
}

export const AppLayout = ({ children, currentUser, onLogout }: AppLayoutProps) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  const menuItems = [
    {
      key: "chat",
      label: <Link to="/?tab=chat">AI Chatbot</Link>,
    },
    {
      key: "booking",
      label: <Link to="/?tab=booking">Flight Booking Portal</Link>,
    },
    {
      key: "profile",
      label: <Link to="/?tab=profile">My Bookings & Profile</Link>,
    },
    ...(currentUser.role === "admin"
      ? [
          {
            key: "ingestion",
            label: <Link to="/?tab=ingestion">Upload & Ingest</Link>,
          },
          {
            key: "retrieval",
            label: <Link to="/?tab=retrieval">Search & Retrieve</Link>,
          },
          {
            key: "history",
            label: <Link to="/?tab=history">Search History</Link>,
          },
        ]
      : []),
  ];

  const getSelectedKey = () => {
    const params = new URLSearchParams(location.search);
    return params.get("tab") || "chat";
  };

  const profileMenu = {
    items: [
      {
        key: "info",
        label: (
          <div style={{ padding: "4px 12px" }}>
            <div style={{ fontWeight: "bold", fontSize: "14px" }}>
              {currentUser.passengerProfile?.name || "Administrator"}
            </div>
            <div style={{ color: "#8c8c8c", fontSize: "12px" }}>
              {currentUser.username}
            </div>
            {currentUser.passengerProfile?.frequent_flyer_number && (
              <div style={{ marginTop: "4px", fontSize: "11px" }}>
                FF: <span style={{ color: "#fa8c16", fontWeight: "bold" }}>{currentUser.passengerProfile.frequent_flyer_number}</span>
              </div>
            )}
          </div>
        ),
      },
      {
        type: "divider" as const,
      },
      {
        key: "logout",
        icon: <LogoutOutlined />,
        label: "Log Out",
        onClick: onLogout,
        danger: true,
      },
    ],
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      {/* Header */}
      <Layout.Header
        style={{
          background: "#fff",
          padding: "0 20px",
          height: "52px",
          lineHeight: "52px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: "1px solid #f0f0f0",
          zIndex: 10
        }}
      >
        <div
          style={{
            fontSize: "20px",
            fontWeight: "bold",
            color: "#1890ff",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}
        >
          <span>✈️</span> Apex Flight Dashboard
        </div>

        {/* Agent Log Terminal Button */}
        <Tooltip title="Open Agent Execution Log" placement="bottom">
          <Button
            icon={<CodeOutlined />}
            onClick={() => window.open("/agent-log", "agent_log", "width=820,height=640,resizable=yes,scrollbars=yes")}
            style={{
              background: "#090d16",
              border: "1px solid #334155",
              color: "#38bdf8",
              borderRadius: "6px",
              fontFamily: "'Fira Code', monospace",
              fontSize: "12px",
              fontWeight: "bold",
              display: "flex",
              alignItems: "center",
              gap: "4px",
              height: "34px",
              padding: "0 12px"
            }}
          >
            <span style={{ fontSize: "10px", color: "#64748b" }}>agent-executor</span>
            <span style={{ color: "#27c93f", animation: "pulse 2s infinite" }}>●</span>
          </Button>
        </Tooltip>

        {/* Profile / Logged-in passenger details in the header */}
        <Dropdown menu={profileMenu} trigger={["click"]} placement="bottomRight">
          <div style={{ 
            display: "flex", 
            alignItems: "center", 
            gap: "8px", 
            cursor: "pointer", 
            padding: "4px 12px", 
            borderRadius: "6px", 
            transition: "background 0.3s" 
          }}>
            <Avatar 
              icon={<UserOutlined />} 
              style={{ backgroundColor: currentUser.role === "admin" ? "#f56a00" : "#1890ff" }} 
            />
            <div style={{ textAlign: "left", lineHeight: "1.2" }}>
              <div style={{ fontWeight: "bold", fontSize: "13px" }}>
                {currentUser.passengerProfile?.name || "Admin"}
              </div>
              <div style={{ fontSize: "11px", color: "#8c8c8c" }}>
                {currentUser.role === "admin" ? "System Admin" : "Passenger"}
              </div>
            </div>
          </div>
        </Dropdown>
      </Layout.Header>

      <Layout style={{ flex: 1 }}>
        {/* Desktop Sidebar */}
        <Layout.Sider
          width={160}
          style={{
            background: "#fff",
            borderRight: "1px solid #f0f0f0",
          }}
          breakpoint="lg"
          collapsedWidth={0}
          onBreakpoint={(broken) => {
            if (broken) setDrawerOpen(false);
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{ border: "none" }}
          />
        </Layout.Sider>

        {/* Mobile Drawer Menu */}
        <Drawer
          placement="left"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          bodyStyle={{ padding: 0 }}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{ border: "none" }}
            onClick={() => setDrawerOpen(false)}
          />
        </Drawer>

        {/* Main Content */}
        <Layout.Content
          style={{
            background: "#fafafa",
            minHeight: 0,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {children}
        </Layout.Content>
      </Layout>
    </Layout>
  );
};
