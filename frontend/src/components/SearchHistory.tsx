import { useState, useEffect } from "react";
import { List, Empty, Button, Space, Tag, Popconfirm, message } from "antd";
import { DeleteOutlined, ClearOutlined } from "@ant-design/icons";
import type { SearchHistoryEntry } from "../types/api";

interface SearchHistoryProps {
  onSelectSearch?: (entry: SearchHistoryEntry) => void;
}

const MAX_HISTORY_ITEMS = 50;

export const SearchHistory = ({ onSelectSearch }: SearchHistoryProps) => {
  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = () => {
    try {
      const stored = localStorage.getItem("search_history");
      if (stored) {
        const parsed = JSON.parse(stored);
        setHistory(parsed);
      }
    } catch (error) {
      console.error("Failed to load search history:", error);
    }
  };


  const deleteEntry = (id: string) => {
    const updated = history.filter((entry) => entry.id !== id);
    setHistory(updated);
    localStorage.setItem("search_history", JSON.stringify(updated));
    message.success("Search removed from history");
  };

  const clearAllHistory = () => {
    setHistory([]);
    localStorage.removeItem("search_history");
    message.success("Search history cleared");
  };

  if (history.length === 0) {
    return (
      <Empty
        description="No search history"
        style={{ margin: "40px 0" }}
      />
    );
  }

  return (
    <div style={{ padding: "24px" }}>
      <div style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ margin: 0 }}>Search History</h2>
        <Popconfirm
          title="Clear all searches?"
          description="This action cannot be undone."
          onConfirm={clearAllHistory}
          okText="Clear"
          cancelText="Cancel"
        >
          <Button danger icon={<ClearOutlined />}>
            Clear All
          </Button>
        </Popconfirm>
      </div>

      <List
        dataSource={history}
        renderItem={(entry) => (
          <List.Item
            key={entry.id}
            style={{
              padding: "12px 16px",
              background: "#fafafa",
              marginBottom: "8px",
              borderRadius: "4px",
              border: "1px solid #f0f0f0",
            }}
            extra={
              <Space>
                <Button
                  type="primary"
                  size="small"
                  onClick={() => onSelectSearch?.(entry)}
                >
                  Search Again
                </Button>
                <Popconfirm
                  title="Delete this search?"
                  onConfirm={() => deleteEntry(entry.id)}
                  okText="Delete"
                  cancelText="Cancel"
                >
                  <Button
                    danger
                    size="small"
                    icon={<DeleteOutlined />}
                  />
                </Popconfirm>
              </Space>
            }
          >
            <List.Item.Meta
              title={
                <span>
                  <strong>"{entry.query}"</strong>
                  {entry.topK && (
                    <Tag style={{ marginLeft: "8px" }}>
                      Top K: {entry.topK}
                    </Tag>
                  )}
                  {entry.threshold !== undefined && (
                    <Tag style={{ marginLeft: "4px" }}>
                      Threshold: {entry.threshold.toFixed(2)}
                    </Tag>
                  )}
                </span>
              }
              description={
                <span style={{ fontSize: "12px", color: "#999" }}>
                  {new Date(entry.timestamp).toLocaleString()}
                </span>
              }
            />
          </List.Item>
        )}
      />
    </div>
  );
};

// Hook to manage search history
export const useSearchHistory = () => {
  const addSearch = (query: string, topK: number, threshold: number) => {
    try {
      const stored = localStorage.getItem("search_history") || "[]";
      const history = JSON.parse(stored) as SearchHistoryEntry[];

      const entry: SearchHistoryEntry = {
        id: Date.now().toString(),
        query,
        timestamp: Date.now(),
        topK,
        threshold,
      };

      const updated = [entry, ...history].slice(0, MAX_HISTORY_ITEMS);
      localStorage.setItem("search_history", JSON.stringify(updated));
    } catch (error) {
      console.error("Failed to save search history:", error);
    }
  };

  return { addSearch };
};
