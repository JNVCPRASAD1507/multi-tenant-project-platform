import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store'
import AppLayout from './components/AppLayout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AuthCallback from './pages/AuthCallback'
import Projects from './pages/Projects'
import TaskBoard from './pages/TaskBoard'
import Chat from './pages/Chat'

function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.accessToken)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      <Route path="/" element={
        <PrivateRoute><AppLayout><Dashboard /></AppLayout></PrivateRoute>
      } />
      <Route path="/projects" element={
        <PrivateRoute><AppLayout><Projects /></AppLayout></PrivateRoute>
      } />
      <Route path="/org/:orgId/project/:projectId/board" element={
        <PrivateRoute><AppLayout><TaskBoard /></AppLayout></PrivateRoute>
      } />
      <Route path="/chat" element={
        <PrivateRoute><AppLayout><Chat /></AppLayout></PrivateRoute>
      } />
    </Routes>
  )
}
