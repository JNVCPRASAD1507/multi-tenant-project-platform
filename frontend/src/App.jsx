import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { useAuthStore } from './store'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import AuthCallback from './pages/AuthCallback'
import Projects from './pages/Projects'
import TaskBoard from './pages/TaskBoard'

function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.accessToken)
  return token ? children : <Navigate to="/login" replace />
}

function Layout({ children }) {
  const { user, logout } = useAuthStore()
  return (
    <>
      <nav className="nav">
        <Link to="/">Dashboard</Link>
        <Link to="/projects">Projects</Link>
        <Link to="/org/1/project/1/board">Task Board</Link>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {user && <span>{user.full_name || user.email}</span>}
          <button className="secondary" onClick={logout}>Logout</button>
        </div>
      </nav>
      <div className="container">{children}</div>
    </>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      <Route path="/" element={
        <PrivateRoute><Layout><Dashboard /></Layout></PrivateRoute>
      } />
      <Route path="/projects" element={
        <PrivateRoute><Layout><Projects /></Layout></PrivateRoute>
      } />
      <Route path="/org/:orgId/project/:projectId/board" element={
        <PrivateRoute><Layout><TaskBoard /></Layout></PrivateRoute>
      } />
    </Routes>
  )
}

