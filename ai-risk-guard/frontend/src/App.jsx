import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Pipeline from './pages/Pipeline'
import Dashboard from './pages/Dashboard'
import Policy from './pages/Policy'
import Repositories from './pages/Repositories'
import RepositoryDetail from './pages/RepositoryDetail'
import ScanDetail from './pages/ScanDetail'
import FindingsExplorer from './pages/FindingsExplorer'
import Scans from './pages/Scans'
import Docs from './pages/Docs'
import Status from './pages/Status'
import Metrics from './pages/Metrics'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Landing />} />
        <Route path="/pipeline" element={<Pipeline />} />
        <Route path="/login" element={<Login />} />
        <Route path="/docs" element={<Docs />} />
        <Route path="/status" element={<Status />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/policy" element={<Policy />} />
        <Route path="/repositories" element={<Repositories />} />
        <Route path="/repositories/:repoId" element={<RepositoryDetail />} />
        <Route path="/scan/:scanId" element={<ScanDetail />} />
        <Route path="/findings" element={<FindingsExplorer />} />
        <Route path="/scans" element={<Scans />} />
        <Route path="/metrics" element={<Metrics />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
