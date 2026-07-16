import { Layout, Menu, Drawer, Avatar, Dropdown, Button, Tooltip } from "antd";
import { 
  UserOutlined, 
  LogoutOutlined, 
  CodeOutlined,
  MenuOutlined,
  MessageOutlined,
  EnvironmentOutlined,
  TeamOutlined,
  UploadOutlined,
  SearchOutlined,
  HistoryOutlined,
  SettingOutlined
} from "@ant-design/icons";
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
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const location = useLocation();

  const menuItems = [
    {
      key: "chat",
      icon: <MessageOutlined />,
      label: <Link to="/?tab=chat">AI Chatbot</Link>,
    },
    {
      key: "booking",
      icon: <EnvironmentOutlined />,
      label: <Link to="/?tab=booking">Flight Booking Portal</Link>,
    },
    {
      key: "profile",
      icon: <UserOutlined />,
      label: <Link to="/?tab=profile">My Bookings & Profile</Link>,
    },
    ...(currentUser.role === "admin"
      ? [
          {
            key: "passengers",
            icon: <TeamOutlined />,
            label: <Link to="/?tab=passengers">Passenger Management</Link>,
          },
          {
            key: "ingestion",
            icon: <UploadOutlined />,
            label: <Link to="/?tab=ingestion">Upload & Ingest</Link>,
          },
          {
            key: "retrieval",
            icon: <SearchOutlined />,
            label: <Link to="/?tab=retrieval">Search & Retrieve</Link>,
          },
          {
            key: "history",
            icon: <HistoryOutlined />,
            label: <Link to="/?tab=history">Search History</Link>,
          },
          {
            key: "settings",
            icon: <SettingOutlined />,
            label: <Link to="/?tab=settings">System Settings</Link>,
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
        danger: true,
      },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === "logout") {
        onLogout();
      }
    }
  };

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Layout.Header
        style={{
          background: "#fff",
          padding: "0 24px",
          height: "56px",
          lineHeight: "56px",
          borderBottom: "1px solid #f0f0f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          zIndex: 10
        }}
      >
        <div
          style={{
            fontSize: "18px",
            fontWeight: 800,
            color: "#1890ff",
            display: "flex",
            alignItems: "center",
            gap: "10px",
            letterSpacing: "-0.5px"
          }}
        >
          {isMobile && (
            <Button
              type="text"
              icon={<MenuOutlined />}
              onClick={() => setDrawerOpen(true)}
              style={{ fontSize: "16px", marginRight: "4px", display: "inline-flex", alignItems: "center", justifyContent: "center" }}
            />
          )}
          <div style={{
            background: "linear-gradient(135deg, #1890ff 0%, #096dd9 100%)",
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 4px 10px rgba(24, 144, 255, 0.25)",
            color: "#fff",
            fontSize: "16px"
          }}>
            ✈️
          </div>
          <span style={{ background: "linear-gradient(135deg, #1f1f1f 0%, #434343 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            Apex Air
          </span>
          <span style={{ fontSize: "12px", color: "#8c8c8c", fontWeight: 400, marginLeft: "4px", borderLeft: "1px solid #f0f0f0", paddingLeft: "10px" }} className="hide-on-mobile">
            Passenger Portal
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {/* Agent Log Terminal Button */}
          <Tooltip title="Open Agent Execution Log" placement="bottom">
            <Button
              icon={<CodeOutlined />}
              onClick={() => window.open("/agent-log", "agent_log", "width=820,height=640,resizable=yes,scrollbars=yes")}
              style={{
                background: "#090d16",
                border: "1px solid #1e293b",
                color: "#38bdf8",
                borderRadius: "8px",
                fontFamily: "'Fira Code', monospace",
                fontSize: "12px",
                fontWeight: "bold",
                display: "flex",
                alignItems: "center",
                gap: "6px",
                height: "34px",
                padding: "0 12px",
                transition: "all 0.3s ease",
                boxShadow: "0 4px 12px rgba(9, 13, 22, 0.15)"
              }}
              className="terminal-btn-pulse"
            >
              <span style={{ fontSize: "10px", color: "#64748b" }}>agent-executor</span>
              <span style={{ color: "#27c93f", animation: "pulse 2s infinite" }}>●</span>
            </Button>
          </Tooltip>

          {/* Profile / Logged-in passenger details in the header */}
          <Dropdown menu={profileMenu} trigger={["click"]} placement="bottomRight">
            <div 
              className="header-profile-trigger"
              style={{ 
                display: "flex", 
                alignItems: "center", 
                gap: "8px", 
                cursor: "pointer", 
                padding: "6px 12px", 
                borderRadius: "8px", 
                transition: "all 0.3s ease" 
              }}
            >
              <Avatar 
                icon={<UserOutlined />} 
                style={{ backgroundColor: currentUser.role === "admin" ? "#fa8c16" : "#1890ff", boxShadow: "0 2px 6px rgba(0,0,0,0.1)" }} 
              />
              <div style={{ textAlign: "left", lineHeight: "1.2" }} className="hide-on-mobile">
                <div style={{ fontWeight: 700, fontSize: "13px", color: "#262626" }}>
                  {currentUser.passengerProfile?.name || "Admin"}
                </div>
                <div style={{ fontSize: "11px", color: "#8c8c8c" }}>
                  {currentUser.role === "admin" ? "System Admin" : "Passenger"}
                </div>
              </div>
            </div>
          </Dropdown>
        </div>
      </Layout.Header>

      <Layout style={{ flex: 1 }}>
        {/* Desktop Sidebar */}
        <Layout.Sider
          collapsible
          collapsed={collapsed}
          onCollapse={(value) => setCollapsed(value)}
          width={240}
          collapsedWidth={isMobile ? 0 : 80}
          style={{
            background: "#fff",
            borderRight: "1px solid #f0f0f0"
          }}
          breakpoint="lg"
          onBreakpoint={(broken) => {
            setIsMobile(broken);
            if (broken) {
              setDrawerOpen(false);
              setCollapsed(true);
            } else {
              setCollapsed(false);
            }
          }}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{ border: "none", paddingTop: "8px" }}
            className="dashboard-menu"
          />
        </Layout.Sider>

        {/* Mobile Drawer Menu */}
        <Drawer
          placement="left"
          onClose={() => setDrawerOpen(false)}
          open={drawerOpen}
          bodyStyle={{ padding: "16px 0" }}
          width={260}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{ border: "none" }}
            onClick={() => setDrawerOpen(false)}
            className="dashboard-menu"
          />
        </Drawer>

        {/* Main Content */}
        <Layout.Content
          style={{
            background: "#fcfcfc",
            minHeight: 0,
            overflow: "hidden",
            display: "flex",
            flexDirection: "column",
          }}
        >
          {children}
        </Layout.Content>
      </Layout>

      <style>{`
        @keyframes pulse {
          0% { transform: scale(0.9); opacity: 0.6; }
          50% { transform: scale(1.15); opacity: 1; }
          100% { transform: scale(0.9); opacity: 0.6; }
        }
        
        .header-profile-trigger:hover {
          background: #f5f5f5 !important;
        }

        .terminal-btn-pulse:hover {
          transform: translateY(-1px);
          border-color: #38bdf8 !important;
          box-shadow: 0 6px 16px rgba(9, 13, 22, 0.25) !important;
        }

        .dashboard-menu .ant-menu-item {
          border-radius: 8px !important;
          margin: 4px 12px !important;
          width: calc(100% - 24px) !important;
          height: 40px !important;
          line-height: 40px !important;
          transition: all 0.2s ease !important;
        }

        .dashboard-menu .ant-menu-item-selected {
          background-color: #e6f7ff !important;
          color: #1890ff !important;
          font-weight: 600 !important;
        }

        .dashboard-menu .ant-menu-item-selected a {
          color: #1890ff !important;
        }

        .ant-layout-sider-trigger {
          background: #fff !important;
          border-top: 1px solid #f0f0f0 !important;
          border-right: 1px solid #f0f0f0 !important;
          color: #8c8c8c !important;
        }
        
        .ant-layout-sider-trigger:hover {
          color: #1890ff !important;
        }

        @media (max-width: 576px) {
          .hide-on-mobile {
            display: none !important;
          }
        }
      `}</style>
    </Layout>
  );
};
