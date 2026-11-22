// Routes: "/" is the login; every other screen is protected by role (docs/spec/04).
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { es } from "./i18n/es";
import { LoginPage } from "./pages/LoginPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

// Every screen from the spec; each gets a placeholder until its module is built.
const SCREENS = Object.keys(es.screens);

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          {SCREENS.map((path) => (
            <Route key={path} path={path}
              element={<ProtectedRoute path={path}><PlaceholderPage path={path} /></ProtectedRoute>} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
