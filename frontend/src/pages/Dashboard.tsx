import { useState, useEffect } from "react";
import { Tabs, message } from "antd";
import { UploadOutlined, SearchOutlined, HistoryOutlined, MessageOutlined, EnvironmentOutlined, UserOutlined } from "@ant-design/icons";
import { UploadForm } from "../components/UploadForm";
import { SearchForm } from "../components/SearchForm";
import { ResultsTable } from "../components/ResultsTable";
import { ChunkDetails } from "../components/ChunkDetails";
import { SearchHistory, useSearchHistory } from "../components/SearchHistory";
import type { DocumentChunk, SearchHistoryEntry } from "../types/api";
import { useQuery } from "../hooks/useQuery";
import { downloadChunk } from "../utils/export";
import { useSearchParams } from "react-router-dom";
import { ChatWindow } from "../components/ChatWindow";
import { FlightPreviewPanel } from "../components/FlightPreviewPanel";
import { BookingPortal } from "../components/BookingPortal";
import { ProfilePanel } from "../components/ProfilePanel";
import { PSS_API_URL } from "../services/api";


interface DashboardProps {
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
}

export const Dashboard = ({ currentUser }: DashboardProps) => {
  const [selectedTab, setSelectedTab] = useState("chat");
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunk | null>(null);
  const [showChunkDetails, setShowChunkDetails] = useState(false);
  const [activeBooking, setActiveBooking] = useState<any>(null);
  const [bookings, setBookings] = useState<any[]>([]);
  const [toolActivity, setToolActivity] = useState<any[]>([]);
  const [passengerProfile] = useState<any>(
    currentUser.passengerProfile || {
      passenger_id: "admin",
      name: "System Administrator",
      email: currentUser.username,
      frequent_flyer_number: "FF_ADMIN"
    }
  );

  // Load passenger bookings on mount
  useEffect(() => {
    const fetchPassengerBookings = async () => {
      if (currentUser.role === "passenger" && currentUser.passengerProfile?.passenger_id) {
        try {
          const res = await fetch(`${PSS_API_URL}/passengers/${currentUser.passengerProfile.passenger_id}`);
          if (res.ok) {
            const data = await res.json();
            if (data.bookings) {
              setBookings(data.bookings);
              if (data.bookings.length > 0) {
                // Default active booking to the most recent one
                setActiveBooking(data.bookings[data.bookings.length - 1]);
              }
            }
          }
        } catch (e) {
          console.error("Failed to load passenger profile & bookings", e);
        }
      }
    };
    fetchPassengerBookings();
  }, [currentUser]);

  // Handle updates to bookings
  const handleBookingUpdate = (updated: any) => {
    if (!updated || updated.error) return;
    
    // Handle array response or object response
    if (Array.isArray(updated)) {
      setBookings(updated);
      if (updated.length > 0) {
        setActiveBooking(updated[updated.length - 1]);
      }
    } else {
      setBookings(prev => {
        const exists = prev.some(b => b.pnr === updated.pnr);
        if (exists) {
          return prev.map(b => b.pnr === updated.pnr ? updated : b);
        } else {
          return [...prev, updated];
        }
      });
      setActiveBooking(updated);
    }
  };

  const { results, query, loading, error } = useQuery();
  const { addSearch } = useSearchHistory();

  // Update tab from URL and enforce role restrictions
  useEffect(() => {
    const tab = searchParams.get("tab") || "chat";
    const allowedPassengerTabs = ["chat", "booking", "profile"];
    if (currentUser.role === "passenger" && !allowedPassengerTabs.includes(tab)) {
      setSelectedTab("chat");
      setSearchParams({ tab: "chat" });
    } else {
      setSelectedTab(tab);
    }
  }, [searchParams, currentUser.role, setSearchParams]);


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
      key: "chat",
      label: (
        <>
          <MessageOutlined /> AI Chatbot
        </>
      ),
      children: (
        <div style={{ display: "flex", gap: "20px", height: "calc(100vh - 170px)", padding: "20px" }}>
          <div style={{ flex: "1 1 55%", minWidth: 0, height: "100%" }}>
            <ChatWindow 
              passengerProfile={passengerProfile}
              onBookingUpdate={handleBookingUpdate}
              onToolActivity={(activity) => {
                setToolActivity(prev => {
                  const filtered = prev.filter(x => !(x.name === activity.name && x.status === "running"));
                  return [...filtered, activity];
                });
              }}
            />
          </div>
          <div style={{ flex: "0 0 45%", minWidth: "360px", maxWidth: "520px", height: "100%" }}>
            <FlightPreviewPanel 
              activeBooking={activeBooking}
              bookings={bookings}
              onSelectBooking={setActiveBooking}
              toolActivity={toolActivity}
              onClearLogs={() => setToolActivity([])}
            />
          </div>
        </div>
      ),
    },
    {
      key: "booking",
      label: (
        <>
          <EnvironmentOutlined /> Flight Booking Portal
        </>
      ),
      children: (
        <div style={{ padding: "24px" }}>
          <BookingPortal 
            currentUser={currentUser} 
            onBookingCreated={(booking) => {
              handleBookingUpdate(booking);
              handleTabChange("chat");
            }}
          />
        </div>
      ),
    },
    {
      key: "profile",
      label: (
        <>
          <UserOutlined /> My Bookings & Profile
        </>
      ),
      children: (
        <div style={{ padding: "24px" }}>
          <ProfilePanel 
            currentUser={currentUser} 
            bookings={bookings} 
            onBookingUpdate={handleBookingUpdate}
          />
        </div>
      ),
    },
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
        renderTabBar={() => <></>}
        style={{ 
          padding: "0",
          width: "100%",
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
