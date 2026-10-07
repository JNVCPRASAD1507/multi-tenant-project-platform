import { useState } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert, Link,
} from '@mui/material'
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
      await api.post('/auth/register', form)
      const loginRes = await api.post('/auth/login', {
        email: form.email,
        password: form.password,
      })
      setAuth(
        loginRes.data.user,
        loginRes.data.tokens.access_token,
        loginRes.data.tokens.refresh_token
      )
      navigate('/')
    } catch (err) {
      setError(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Registration failed'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <Box minHeight="100vh" display="flex" alignItems="center" justifyContent="center" p={2}>
      <Card sx={{ width: '100%', maxWidth: 420 }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            Create account
          </Typography>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField fullWidth label="Full name" name="full_name" margin="normal"
              value={form.full_name} onChange={handleChange} required />
            <TextField fullWidth label="Email" name="email" type="email" margin="normal"
              value={form.email} onChange={handleChange} required />
            <TextField fullWidth label="Password" name="password" type="password" margin="normal"
              value={form.password} onChange={handleChange} required inputProps={{ minLength: 8 }} />
            <TextField fullWidth label="Organization name" name="organization_name" margin="normal"
              value={form.organization_name} onChange={handleChange} required />
            <Button fullWidth type="submit" variant="contained" size="large"
              disabled={loading} sx={{ mt: 2 }}>
              {loading ? 'Creating…' : 'Register'}
            </Button>
          </Box>

          <Typography variant="body2" textAlign="center" mt={3}>
            Already have an account?{' '}
            <Link component={RouterLink} to="/login">Sign in</Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
