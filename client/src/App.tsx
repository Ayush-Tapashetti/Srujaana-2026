import { MotionConfig } from "motion/react";
import { Link, Route, Routes } from "react-router-dom";
import { StatusIslandProvider } from "./components/motion/StatusIsland";
import { Shell } from "./components/Shell";
import { AgreementPage } from "./pages/AgreementPage";
import { AnalysisPage } from "./pages/AnalysisPage";
import { ConfirmPage } from "./pages/ConfirmPage";
import { ConversationLayout } from "./pages/ConversationLayout";
import { CertificatePage } from "./pages/CertificatePage";
import { EvaluationPage } from "./pages/EvaluationPage";
import { EvidencePage } from "./pages/EvidencePage";
import { EvidencePrintPage } from "./pages/EvidencePrintPage";
import { MaskedPreviewPage } from "./pages/MaskedPreviewPage";
import { PackPage } from "./pages/PackPage";
import { HomePage } from "./pages/HomePage";
import { LimitsPage } from "./pages/LimitsPage";

function NotFound() {
  return (
    <div className="mx-auto max-w-xl px-4 py-24 text-center">
      <h1 className="text-2xl font-semibold tracking-tight text-fg">Nothing at this address</h1>
      <p className="mt-2 text-fg-muted">The link may be mistyped, or the chat was removed.</p>
      <Link to="/" className="btn btn-primary mt-6">
        Upload a chat
      </Link>
    </div>
  );
}

export default function App() {
  return (
    // reducedMotion="user": every Motion animation respects the OS setting.
    <MotionConfig reducedMotion="user">
      <StatusIslandProvider>
        <AppRoutes />
      </StatusIslandProvider>
    </MotionConfig>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* The counterparty page has no app chrome: it isn't their app. */}
      <Route path="/confirm/:token" element={<ConfirmPage />} />
      {/* The CA / lawyer page: read-only, opened with a link token, no app chrome. */}
      <Route path="/pack/:token" element={<PackPage />} />
      <Route
        path="*"
        element={
          <Shell>
            <Routes>
              <Route path="/limits" element={<LimitsPage />} />
              <Route path="/evaluation" element={<EvaluationPage />} />
              <Route path="/" element={<HomePage />} />
              <Route path="/c/:id" element={<ConversationLayout />}>
                <Route index element={<AnalysisPage />} />
                <Route path="agreement" element={<AgreementPage />} />
                <Route path="privacy" element={<MaskedPreviewPage />} />
                <Route path="evidence" element={<EvidencePage />} />
                <Route path="evidence/certificate" element={<CertificatePage />} />
                <Route path="evidence/print" element={<EvidencePrintPage />} />
              </Route>
              <Route path="*" element={<NotFound />} />
            </Routes>
          </Shell>
        }
      />
    </Routes>
  );
}
