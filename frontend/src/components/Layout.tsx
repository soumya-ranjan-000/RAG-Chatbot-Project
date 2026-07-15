import { Layout, Menu, Drawer, Avatar, Dropdown } from "antd";
import { UserOutlined, LogoutOutlined } from "@ant-design/icons";
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
          padding: "0 24px",
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
          width={200}
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
            overflow: "auto",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <div style={{ padding: "24px", flex: 1 }}>
            {children}
          </div>
        </Layout.Content>
      </Layout>
    </Layout>
  );
};
