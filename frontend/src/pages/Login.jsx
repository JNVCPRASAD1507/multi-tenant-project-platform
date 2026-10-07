import { useState } from 'react'
import { Link as RouterLink, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Box, Card, CardContent, TextField, Button, Typography, Alert, Divider, Link,
} from '@mui/material'
import GitHubIcon from '@mui/icons-material/GitHub'
import api from '../api'
import { useAuthStore } from '../store'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const oauthError = searchParams.get('error')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/auth/login', { email, password })
      setAuth(data.user, data.tokens.access_token, data.tokens.refresh_token)
      navigate('/')
    } catch (err) {
      setError(
        err.response?.data?.detail?.message ||
        err.response?.data?.detail ||
        'Login failed'
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
            Sign in
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={3}>
            Multi-Tenant Project Platform
          </Typography>

          {(error || oauthError) && (
            <Alert severity="error" sx={{ mb: 2 }}>{error || oauthError}</Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <TextField
              fullWidth label="Email" type="email" margin="normal"
              value={email} onChange={(e) => setEmail(e.target.value)} required
            />
            <TextField
              fullWidth label="Password" type="password" margin="normal"
              value={password} onChange={(e) => setPassword(e.target.value)} required
            />
            <Button
              fullWidth type="submit" variant="contained" size="large"
              disabled={loading} sx={{ mt: 2 }}
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </Box>

          <Divider sx={{ my: 3 }}>or</Divider>

          <Button
            fullWidth variant="outlined" size="large"
            startIcon={<GitHubIcon />}
            href={`${API_URL}/api/v1/auth/github/login`}
          >
            Continue with GitHub
          </Button>

          <Typography variant="body2" textAlign="center" mt={3}>
            No account?{' '}
            <Link component={RouterLink} to="/register">Register</Link>
          </Typography>
        </CardContent>
      </Card>
    </Box>
  )
}
