import { Route, Routes } from "react-router-dom";
import { Sidebar } from "./components/layout/Sidebar";
import { WatchlistDashboardPage } from "./pages/WatchlistDashboardPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SearchAnalyzePage } from "./pages/SearchAnalyzePage";
import { StockDetailPage } from "./pages/StockDetailPage";
import { SettingsPage } from "./pages/SettingsPage";

export function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main-content">
        <Routes>
          <Route path="/" element={<WatchlistDashboardPage />} />
          <Route path="/overview" element={<OverviewPage />} />
          <Route path="/search" element={<SearchAnalyzePage />} />
          <Route path="/stock/:ticker" element={<StockDetailPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Routes>
      </main>
    </div>
  );
}
