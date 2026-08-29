import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./hooks/useAuth";
import ProtectedRoute from "./components/ProtectedRoute";
import Nav from "./components/Nav";

import Login from "./pages/Login";
import DashboardPage from "./pages/DashboardPage";
import EventsPage from "./pages/EventsPage";
import AlertsPage from "./pages/AlertsPage";
import PersonsPage from "./pages/PersonsPage";
import UnknownReviewPage from "./pages/UnknownReviewPage";
import ZoneEditorPage from "./pages/ZoneEditorPage";
import StatsPage from "./pages/StatsPage";
import HealthPage from "./pages/HealthPage";

function AppShell({ children }) {
  const { isAuthenticated } = useAuth();
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      {isAuthenticated && <Nav />}
      {children}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppShell>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
            <Route path="/events" element={<ProtectedRoute><EventsPage /></ProtectedRoute>} />
            <Route path="/alerts" element={<ProtectedRoute><AlertsPage /></ProtectedRoute>} />
            <Route path="/persons" element={<ProtectedRoute><PersonsPage /></ProtectedRoute>} />
            <Route path="/unknown-review" element={<ProtectedRoute><UnknownReviewPage /></ProtectedRoute>} />
            <Route path="/zone-editor" element={<ProtectedRoute><ZoneEditorPage /></ProtectedRoute>} />
            <Route path="/stats" element={<ProtectedRoute><StatsPage /></ProtectedRoute>} />
            <Route path="/health" element={<ProtectedRoute><HealthPage /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppShell>
      </AuthProvider>
    </BrowserRouter>
  );
}