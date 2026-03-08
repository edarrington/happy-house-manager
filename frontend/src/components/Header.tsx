'use client'

import { useEffect, useState } from 'react'
import { getStoredUser, type User } from '@/lib/auth'

interface HeaderProps {
  title: string
  subtitle?: string
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    setUser(getStoredUser())
  }, [])

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
      <div>
        <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-500 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {user ? (
          <>
            <div className="text-right">
              <p className="text-sm font-medium text-gray-900">{user.name}</p>
              <p className="text-xs text-gray-500">{user.email}</p>
            </div>
            {user.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.picture}
                alt={user.name}
                className="w-9 h-9 rounded-full ring-2 ring-blue-500"
              />
            ) : (
              <div className="w-9 h-9 rounded-full bg-blue-500 flex items-center justify-center text-white font-bold">
                {user.name?.charAt(0) ?? '?'}
              </div>
            )}
          </>
        ) : (
          <span className="text-sm text-gray-400">Not signed in</span>
        )}
      </div>
    </header>
  )
}
