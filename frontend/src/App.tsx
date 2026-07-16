import { useState, useEffect } from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import { AppLayout } from "./components/Layout";
import { Dashboard } from "./pages/Dashboard";
import { Login } from "./components/Login";
import { PaymentGatewayPage } from "./pages/PaymentGatewayPage";
import { AgentLogPage } from "./pages/AgentLogPage";

interface UserSession {
  username: string;
  role: "admin" | "passenger";
  passengerProfile?: {
    passenger_id: string;
    name: string;
    email: string;
    frequent_flyer_number: string;
  };
}

function App() {
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const saved = localStorage.getItem("airline_user_session");
    if (saved) {
      try {
        const session = JSON.parse(saved);
        // Self-heal: If profile exists but is missing the 'name' field, reconstruct it
        if (session.passengerProfile && !session.passengerProfile.name) {
          const profile = session.passengerProfile;
          if (profile.first_name || profile.last_name) {
            profile.name = `${profile.first_name || ""} ${profile.last_name || ""}`.trim();
          } else {
            profile.name = session.username;
          }
          localStorage.setItem("airline_user_session", JSON.stringify(session));
        }
        setCurrentUser(session);
      } catch (e) {
        console.error("Failed to parse saved login session", e);
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (user: UserSession) => {
    setCurrentUser(user);
    localStorage.setItem("airline_user_session", JSON.stringify(user));
    // Clear any leftover chat session from previous use
    localStorage.removeItem("rag_chat_history");
    localStorage.removeItem("rag_chat_thread_id");
    localStorage.removeItem("agent_tool_activity");
    localStorage.removeItem("search_history");
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("airline_user_session");
    // Clear all session, chat, and tracking caches for security
    localStorage.removeItem("rag_chat_history");
    localStorage.removeItem("rag_chat_thread_id");
    localStorage.removeItem("agent_tool_activity");
    localStorage.removeItem("search_history");
  };

  if (loading) {
    return null;
  }

  if (!currentUser) {
    return <Login onLogin={handleLogin} />;
  }

  return (
    <Router>
      <Routes>
        <Route path="/payment" element={<PaymentGatewayPage />} />
        <Route path="/agent-log" element={<AgentLogPage />} />
        <Route path="/*" element={
          <AppLayout currentUser={currentUser} onLogout={handleLogout}>
            <Dashboard currentUser={currentUser} />
          </AppLayout>
        } />
      </Routes>
    </Router>
  );
}

export default App;
