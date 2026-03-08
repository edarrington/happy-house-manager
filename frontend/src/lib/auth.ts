const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? ''
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

export interface User {
  id: string
  email: string
  name: string
  picture: string
  has_todoist?: boolean
}

export function redirectToGoogleLogin(): void {
  // Fetch auth URL from backend and redirect
  fetch(`${BACKEND_URL}/users/auth/login`)
    .then((res) => res.json())
    .then((data) => {
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      }
    })
    .catch(console.error)
}

export function saveSession(sessionToken: string, user: User): void {
  localStorage.setItem('session_token', sessionToken)
  localStorage.setItem('user', JSON.stringify(user))
}

export function getStoredUser(): User | null {
  if (typeof window === 'undefined') return null
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try {
    return JSON.parse(raw) as User
  } catch {
    return null
  }
}

export function getSessionToken(): string | null {
  if (typeof window === 'undefined') return null
  return localStorage.getItem('session_token')
}

export function isAuthenticated(): boolean {
  return Boolean(getSessionToken())
}

export function logout(): void {
  localStorage.removeItem('session_token')
  localStorage.removeItem('user')
  window.location.href = '/'
}
