import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuthStore } from '../store'
import api from '../api'

export default function AuthCallback() {
  const [params] = useSearchParams()
  const setAuth = useAuthStore((s) => s.setAuth)
  const navigate = useNavigate()

  useEffect(() => {
    const access = params.get('access_token')
    const refresh = params.get('refresh_token')
    if (access) {
      localStorage.setItem('access_token', access)
      if (refresh) localStorage.setItem('refresh_token', refresh)
      // Fetch user
      api.get('/auth/me').then((res) => {
        setAuth(res.data, access, refresh)
        navigate('/')
      }).catch(() => {
        navigate('/login?error=Failed to complete GitHub login')
      })
    } else {
      navigate('/login?error=Missing tokens from GitHub')
    }
  }, [])

  return <div className="container"><p>Completing GitHub login…</p></div>
}
