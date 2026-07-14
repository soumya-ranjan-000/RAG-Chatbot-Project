import { useState, useEffect } from "react";
import { Tabs, message } from "antd";
import { UploadOutlined, SearchOutlined, HistoryOutlined } from "@ant-design/icons";
import { UploadForm } from "../components/UploadForm";
import { SearchForm } from "../components/SearchForm";
import { ResultsTable } from "../components/ResultsTable";
import { ChunkDetails } from "../components/ChunkDetails";
import { SearchHistory, useSearchHistory } from "../components/SearchHistory";
import type { DocumentChunk, SearchHistoryEntry } from "../types/api";
import { useQuery } from "../hooks/useQuery";
import { downloadChunk } from "../utils/export";
import { useSearchParams } from "react-router-dom";

export const Dashboard = () => {
  const [selectedTab, setSelectedTab] = useState("ingestion");
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunk | null>(null);
  const [showChunkDetails, setShowChunkDetails] = useState(false);

  const { results, query, loading, error } = useQuery();
  const { addSearch } = useSearchHistory();

  // Update tab from URL
  useEffect(() => {
    const tab = searchParams.get("tab") || "ingestion";
    setSelectedTab(tab);
  }, [searchParams]);

  const handleTabChange = (key: string) => {
    setSelectedTab(key);
    setSearchParams({ tab: key });
  };

  const handleSearch = async (
    searchQuery: string,
    topK: number,
    threshold: number
  ) => {
    // Add to history
    addSearch(searchQuery, topK, threshold);
  };

  const handleSearchAgain = (entry: SearchHistoryEntry) => {
    setSelectedTab("retrieval");
    setSearchParams({ tab: "retrieval" });

    // Auto-trigger the search
    setTimeout(() => {
      query(entry.query, entry.topK || 5, entry.threshold || 0.5);
    }, 300);
  };

  const handleViewDetails = (chunk: DocumentChunk) => {
    setSelectedChunk(chunk);
    setShowChunkDetails(true);
  };

  const handleExportChunk = (chunk: DocumentChunk) => {
    downloadChunk(chunk, "csv");
    message.success("Chunk exported as CSV");
  };

  const tabItems = [
    {
      key: "ingestion",
      label: (
        <>
          <UploadOutlined /> Upload & Ingest
        </>
      ),
      children: (
        <div style={{ padding: "24px" }}>
          <UploadForm />
        </div>
      ),
    },
    {
      key: "retrieval",
      label: (
        <>
          <SearchOutlined /> Search & Retrieve
        </>
      ),
      children: (
        <div style={{ padding: "24px" }}>
          <SearchForm 
            onSearch={handleSearch}
            queryFn={query}
            loading={loading}
            error={error}
          />
          <div style={{ marginTop: "20px" }}>
            <h3 style={{ marginBottom: "16px" }}>
              Results ({results.length})
            </h3>
            <ResultsTable
              results={results}
              onViewDetails={handleViewDetails}
              onExport={handleExportChunk}
            />
          </div>
        </div>
      ),
    },
    {
      key: "history",
      label: (
        <>
          <HistoryOutlined /> Search History
        </>
      ),
      children: (
        <div style={{ padding: "24px" }}>
          <SearchHistory onSelectSearch={handleSearchAgain} />
        </div>
      ),
    },
  ];

  return (
    <>
      <Tabs
        activeKey={selectedTab}
        onChange={handleTabChange}
        items={tabItems}
        style={{ 
          padding: "0",
          width: "100%",
        }}
        tabBarStyle={{
          margin: "0",
          padding: "0 24px",
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
        }}
      />

      <ChunkDetails
        chunk={selectedChunk}
        visible={showChunkDetails}
        onClose={() => setShowChunkDetails(false)}
      />
    </>
  );
};
