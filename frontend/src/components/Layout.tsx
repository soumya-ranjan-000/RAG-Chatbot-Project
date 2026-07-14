import { Layout, Menu, Drawer, Button } from "antd";
import { MenuFoldOutlined } from "@ant-design/icons";
import { useState } from "react";
import { Link, useLocation } from "react-router-dom";

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout = ({ children }: AppLayoutProps) => {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();

  const menuItems = [
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
  ];

  const getSelectedKey = () => {
    const params = new URLSearchParams(location.search);
    return params.get("tab") || "ingestion";
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
        }}
      >
        <div
          style={{
            fontSize: "20px",
            fontWeight: "bold",
            color: "#1890ff",
          }}
        >
          RAG Chatbot Dashboard
        </div>

        {/* Desktop Menu Button */}
        {/* Mobile Menu Button */}
        <div
          style={{
            display: "none",
          }}
          className="mobile-menu-btn"
        >
          <Button
            type="text"
            icon={<MenuFoldOutlined />}
            onClick={() => setDrawerOpen(true)}
          />
        </div>
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
