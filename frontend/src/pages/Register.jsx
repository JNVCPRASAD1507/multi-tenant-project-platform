import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuthStore } from '../store'

export default function Register() {
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', organization_name: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/register', form)
      // After register, auto-login
      const loginRes = await api.post('/auth/login', {
        email: form.email,
        password: form.password,
      })
      setAuth(loginRes.data.user, loginRes.data.tokens.access_token, loginRes.data.tokens.refresh_token)
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail?.message || err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="container" style={{ maxWidth: 420, marginTop: '3rem' }}>
      <div className="card">
        <h1 style={{ marginBottom: '1.5rem' }}>Create account</h1>
        {error && <p className="error">{error}</p>}
        <form onSubmit={handleSubmit}>
          <label>Full name</label>
          <input name="full_name" value={form.full_name} onChange={handleChange} required />
          <label>Email</label>
          <input type="email" name="email" value={form.email} onChange={handleChange} required />
          <label>Password</label>
          <input type="password" name="password" value={form.password} onChange={handleChange} required minLength={8} />
          <label>Organization name</label>
          <input name="organization_name" value={form.organization_name} onChange={handleChange} required />
          <button type="submit" disabled={loading} style={{ width: '100%', marginTop: '0.5rem' }}>
            {loading ? 'Creating…' : 'Register'}
          </button>
        </form>
        <p style={{ marginTop: '1.5rem', textAlign: 'center' }}>
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
