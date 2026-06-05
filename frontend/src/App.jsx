import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './components/layout/AppShell.jsx'
import AnalysisLoadingPage from './pages/AnalysisLoadingPage.jsx'
import ComparisonPage from './pages/ComparisonPage.jsx'
import CreateComparisonPage from './pages/CreateComparisonPage.jsx'
import HistoryPage from './pages/HistoryPage.jsx'
import NotFoundPage from './pages/NotFoundPage.jsx'

function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<CreateComparisonPage />} />
        <Route path="/comparisons/:comparisonId/analyzing" element={<AnalysisLoadingPage />} />
        <Route path="/comparisons/:comparisonId" element={<ComparisonPage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/404" element={<NotFoundPage />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </AppShell>
  )
}

export default App
