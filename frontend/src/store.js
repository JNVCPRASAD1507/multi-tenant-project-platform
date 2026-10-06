import { create } from 'zustand'

export const useAuthStore = create((set) => ({
  user: null,
  accessToken: localStorage.getItem('access_token'),
  setAuth: (user, accessToken, refreshToken) => {
    localStorage.setItem('access_token', accessToken)
    if (refreshToken) localStorage.setItem('refresh_token', refreshToken)
    set({ user, accessToken })
  },
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    set({ user: null, accessToken: null })
  },
  setUser: (user) => set({ user }),
}))
