// Routes: "/" is the login; every other screen is protected by role (docs/spec/04).
import { lazy, Suspense, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { AuthProvider } from "./auth/AuthContext";
import { ProtectedRoute } from "./components/ProtectedRoute";
import { es } from "./i18n/es";
import { LoginPage } from "./pages/LoginPage";
import { ApprovalsPage } from "./pages/ApprovalsPage";
import { BoardPage } from "./pages/BoardPage";
import { FamilyPage } from "./pages/FamilyPage";
import { MyVisitsPage } from "./pages/MyVisitsPage";
import { PlaceholderPage } from "./pages/PlaceholderPage";

// ECharts is large: the Panorama-AM screen is loaded only when someone opens it.
const SimulationPage = lazy(() => import("./pages/SimulationPage").then((m) => ({ default: m.SimulationPage })));
const ContingencyPage = lazy(() => import("./pages/ContingencyPage").then((m) => ({ default: m.ContingencyPage })));
const VoicePage = lazy(() => import("./pages/VoicePage").then((m) => ({ default: m.VoicePage })));
const VoiceReportsPage = lazy(() => import("./pages/VoiceReportsPage").then((m) => ({ default: m.VoiceReportsPage })));
const DemoPage = lazy(() => import("./pages/DemoPage").then((m) => ({ default: m.DemoPage })));
const BusinessPage = lazy(() => import("./pages/BusinessPage").then((m) => ({ default: m.BusinessPage })));
const PrivacyPage = lazy(() => import("./pages/PrivacyPage").then((m) => ({ default: m.PrivacyPage })));
const PanoramaPage = lazy(() => import("./pages/PanoramaPage").then((m) => ({ default: m.PanoramaPage })));

// Screens already built; the rest show a placeholder until their step.
const BUILT: Record<string, ComponentType> = {
  "/tablero": BoardPage,
  "/aprobaciones": ApprovalsPage,
  "/mis-visitas": MyVisitsPage,
  "/familia": FamilyPage,
  "/panorama": PanoramaPage,
  "/simulacion": SimulationPage,
  "/contingencia": ContingencyPage,
  "/demo": DemoPage,
  "/voz": VoicePage,
  "/reportes-voz": VoiceReportsPage,
  "/negocio": BusinessPage,
  "/privacidad": PrivacyPage,
};

// Every screen from the spec; each gets a placeholder until its module is built.
const SCREENS = Object.keys(es.screens);

function renderScreen(path: string) {
  const Page = BUILT[path];
  return Page ? <Suspense fallback={<p className="p-8">{es.shell.loading}</p>}><Page /></Suspense> : <PlaceholderPage path={path} />;
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          {SCREENS.map((path) => (
            <Route key={path} path={path}
              element={<ProtectedRoute path={path}>{renderScreen(path)}</ProtectedRoute>} />
          ))}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
