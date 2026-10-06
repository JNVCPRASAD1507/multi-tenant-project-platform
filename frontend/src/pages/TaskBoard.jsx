import { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import { useAuthStore } from '../store'

const COLUMNS = [
  { id: 'backlog', title: 'Backlog', color: '#64748b' },
  { id: 'todo', title: 'Todo', color: '#3b82f6' },
  { id: 'in_progress', title: 'In Progress', color: '#f59e0b' },
  { id: 'blocked', title: 'Blocked', color: '#ef4444' },
  { id: 'review', title: 'Review', color: '#8b5cf6' },
  { id: 'done', title: 'Done', color: '#22c55e' },
]

// Must match backend VALID_TRANSITIONS
const VALID_TRANSITIONS = {
  backlog: ['todo', 'cancelled'],
  todo: ['in_progress', 'backlog', 'cancelled'],
  in_progress: ['blocked', 'review', 'cancelled'],
  blocked: ['in_progress', 'cancelled'],
  review: ['done', 'in_progress', 'cancelled'],
  done: [],
  cancelled: [],
}

const PRIORITY_COLOR = {
  low: '#94a3b8',
  medium: '#3b82f6',
  high: '#f97316',
  urgent: '#ef4444',
}

export default function TaskBoard() {
  const params = useParams()
  const orgId = params.orgId || '1'
  const projectId = params.projectId || '1'
  const token = useAuthStore((s) => s.accessToken)

  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [newTitle, setNewTitle] = useState('')
  const [newPriority, setNewPriority] = useState('medium')
  const [creating, setCreating] = useState(false)
  const [message, setMessage] = useState('')

  const loadTasks = useCallback(async () => {
    try {
      const { data } = await api.get(
        `/organizations/${orgId}/projects/${projectId}/tasks?page_size=100`
      )
      setTasks(data.items || [])
      setError('')
    } catch (err) {
      setError(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Failed to load tasks'
      )
    } finally {
      setLoading(false)
    }
  }, [orgId, projectId])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  // WebSocket real-time
  useEffect(() => {
    if (!token) return
    const ws = new WebSocket(
      `ws://127.0.0.1:8000/api/v1/ws/notifications?token=${token}`
    )
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (['task_created', 'task_updated', 'task_status_changed'].includes(msg.type)) {
          loadTasks()
        }
      } catch {}
    }
    return () => ws.close()
  }, [token, loadTasks])

  const changeStatus = async (taskId, newStatus) => {
    try {
      await api.post(
        `/organizations/${orgId}/projects/${projectId}/tasks/${taskId}/status`,
        { status: newStatus }
      )
      setTasks((prev) =>
        prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t))
      )
      setMessage(`Task moved to ${newStatus.replace('_', ' ')}`)
      setTimeout(() => setMessage(''), 2000)
    } catch (err) {
      const msg =
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Cannot change status'
      setMessage(msg)
      alert(msg)
      loadTasks()
    }
  }

  const createTask = async (e) => {
    e.preventDefault()
    setMessage('')
    if (!newTitle.trim()) {
      setMessage('Please enter a task title')
      return
    }
    setCreating(true)
    try {
      await api.post(`/organizations/${orgId}/projects/${projectId}/tasks`, {
        title: newTitle.trim(),
        status: 'backlog',
        priority: newPriority,
      })
      setNewTitle('')
      setNewPriority('medium')
      setMessage('Task created successfully!')
      await loadTasks()
      setTimeout(() => setMessage(''), 2000)
    } catch (err) {
      const msg =
        err.response?.data?.detail?.message ||
        (Array.isArray(err.response?.data?.detail)
          ? err.response.data.detail.map((d) => d.msg).join(', ')
          : null) ||
        err.message ||
        'Failed to create task'
      setMessage(msg)
    } finally {
      setCreating(false)
    }
  }

  if (loading) return <p>Loading board…</p>

  return (
    <div>
      <h1 style={{ marginBottom: '0.25rem' }}>Task Board</h1>
      <p style={{ color: '#94a3b8', marginBottom: '1rem', fontSize: 14 }}>
        Org {orgId} · Project {projectId}
      </p>

      {error && <p className="error">{error}</p>}
      {message && (
        <p style={{
          color: message.toLowerCase().includes('success') || message.includes('moved')
            ? '#4ade80' : '#f87171',
          marginBottom: '0.75rem'
        }}>
          {message}
        </p>
      )}

      {/* Create form */}
      <form onSubmit={createTask} style={{
        display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', flexWrap: 'wrap'
      }}>
        <input
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          placeholder="New task title…"
          style={{ flex: 2, minWidth: 200 }}
        />
        <select
          value={newPriority}
          onChange={(e) => setNewPriority(e.target.value)}
          style={{ width: 120 }}
        >
          <option value="low">Low</option>
          <option value="medium">Medium</option>
          <option value="high">High</option>
          <option value="urgent">Urgent</option>
        </select>
        <button type="submit" disabled={creating}>
          {creating ? 'Adding…' : 'Add Task'}
        </button>
      </form>

      {/* Kanban */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
      }}>
        {COLUMNS.map((col) => {
          const colTasks = tasks.filter((t) => t.status === col.id)
          return (
            <div key={col.id} className="card" style={{ minHeight: 380 }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '1rem',
                borderBottom: `3px solid ${col.color}`,
                paddingBottom: '0.5rem',
              }}>
                <strong>{col.title}</strong>
                <span style={{
                  background: col.color,
                  color: '#fff',
                  borderRadius: 12,
                  padding: '2px 8px',
                  fontSize: 12,
                }}>
                  {colTasks.length}
                </span>
              </div>

              {colTasks.map((task) => {
                const allowed = VALID_TRANSITIONS[task.status] || []
                return (
                  <div key={task.id} style={{
                    background: '#0f172a',
                    borderRadius: 8,
                    padding: '0.75rem',
                    marginBottom: '0.75rem',
                    border: '1px solid #334155',
                  }}>
                    <div style={{ fontWeight: 500, marginBottom: 4 }}>{task.title}</div>
                    <div style={{
                      fontSize: 12,
                      color: PRIORITY_COLOR[task.priority] || '#94a3b8',
                      marginBottom: 8,
                      textTransform: 'capitalize',
                    }}>
                      {task.priority}
                    </div>

                    {allowed.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {allowed.map((next) => {
                          const nextCol = COLUMNS.find((c) => c.id === next)
                          return (
                            <button
                              key={next}
                              type="button"
                              onClick={() => changeStatus(task.id, next)}
                              style={{
                                fontSize: 11,
                                padding: '3px 7px',
                                background: '#334155',
                              }}
                            >
                              → {nextCol ? nextCol.title : next}
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}

              {colTasks.length === 0 && (
                <p style={{ color: '#64748b', fontSize: 13 }}>No tasks</p>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

