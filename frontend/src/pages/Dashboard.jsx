import { useEffect, useState } from 'react'
import { useAuthStore } from '../store'
import api from '../api'

export default function Dashboard() {
  const user = useAuthStore((s) => s.user)
  const [me, setMe] = useState(user)

  useEffect(() => {
    if (!user) {
      api.get('/auth/me').then((r) => {
        setMe(r.data)
        useAuthStore.getState().setUser(r.data)
      }).catch(() => {})
    }
  }, [user])

  return (
    <div>
      <h1 style={{ marginBottom: '1rem' }}>Dashboard</h1>
      <div className="card">
        <h2>Welcome{me ? `, ${me.full_name}` : ''}</h2>
        <p style={{ color: '#94a3b8', marginTop: '0.5rem' }}>
          Multi-tenant Project & Workflow Management Platform
        </p>
        <p style={{ marginTop: '1rem' }}>
          Use the navigation to manage Organizations, Projects and Tasks.
          GitHub OAuth is active – you can also sign in with GitHub from the login page.
        </p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
        <div className="card"><h3>Projects</h3><p>Manage your projects</p></div>
        <div className="card"><h3>Tasks</h3><p>Kanban board & workflows</p></div>
        <div className="card"><h3>Team</h3><p>Members & roles</p></div>
      </div>
    </div>
  )
}
