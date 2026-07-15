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
        setCurrentUser(JSON.parse(saved));
      } catch (e) {
        console.error("Failed to parse saved login session", e);
      }
    }
    setLoading(false);
  }, []);

  const handleLogin = (user: UserSession) => {
    setCurrentUser(user);
    localStorage.setItem("airline_user_session", JSON.stringify(user));
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem("airline_user_session");
    // Clear chat history on logout for security
    localStorage.removeItem("rag_chat_history");
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
