'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { saveSession, type User } from '@/lib/auth'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8000'

export default function AuthCallbackPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState('Completing sign-in...')

  useEffect(() => {
    const code = searchParams.get('code')
    const errorParam = searchParams.get('error')

    if (errorParam) {
      setError(`Google OAuth error: ${errorParam}`)
      return
    }

    if (!code) {
      setError('No authorization code received from Google.')
      return
    }

    const exchangeCode = async () => {
      try {
        setStatus('Exchanging authorization code...')
        const res = await fetch(
          `${BACKEND_URL}/users/auth/callback?code=${encodeURIComponent(code)}`
        )
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error(body.detail ?? `HTTP ${res.status}`)
        }
        const data = await res.json()
        saveSession(data.session_token, data.user as User)
        setStatus('Signed in! Redirecting...')
        router.replace('/')
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err)
        setError(`Sign-in failed: ${message}`)
      }
    }

    exchangeCode()
  }, [searchParams, router])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center flex-1 p-8">
        <div className="card p-8 max-w-md w-full text-center">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={() => router.replace('/')}
            className="btn-secondary mt-4"
          >
            Back to Home
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center justify-center flex-1 p-8">
      <div className="card p-8 max-w-md w-full text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4" />
        <p className="text-gray-600">{status}</p>
      </div>
    </div>
  )
}
