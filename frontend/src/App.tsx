import { BrowserRouter as Router } from "react-router-dom"
import { AppLayout } from "./components/Layout"
import { Dashboard } from "./pages/Dashboard"

function App() {
  return (
    <Router>
      <AppLayout>
        <Dashboard />
      </AppLayout>
    </Router>
  )
}

export default App
