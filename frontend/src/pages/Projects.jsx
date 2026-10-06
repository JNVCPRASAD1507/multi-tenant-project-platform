import { useEffect, useState } from 'react'
import api from '../api'

export default function Projects() {
  const [projects, setProjects] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get('/projects')
      .then((r) => setProjects(r.data.items || r.data || []))
      .catch((e) => setError(e.response?.data?.detail?.message || 'Failed to load projects'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p>Loading projects…</p>
  if (error) return <p className="error">{error}</p>

  return (
    <div>
      <h1 style={{ marginBottom: '1rem' }}>Projects</h1>
      {projects.length === 0 ? (
        <div className="card"><p>No projects yet. Create one from the API or extend the UI.</p></div>
      ) : (
        projects.map((p) => (
          <div key={p.id} className="card">
            <h3>{p.name}</h3>
            <p style={{ color: '#94a3b8' }}>{p.description || 'No description'}</p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>Status: {p.status}</p>
          </div>
        ))
      )}
    </div>
  )
}
