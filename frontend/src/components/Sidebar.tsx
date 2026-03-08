'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Mail, FolderOpen, Calendar, CheckSquare, Home, LogOut, RefreshCw } from 'lucide-react'
import { getStoredUser, logout, redirectToGoogleLogin, type User } from '@/lib/auth'
import { useState, useEffect } from 'react'
import clsx from 'clsx'

const navItems = [
  { href: '/', label: 'Dashboard', icon: Home },
  { href: '/gmail', label: 'Gmail', icon: Mail },
  { href: '/drive', label: 'Drive', icon: FolderOpen },
  { href: '/calendar', label: 'Calendar', icon: Calendar },
  { href: '/tasks', label: 'Tasks', icon: CheckSquare },
]

export default function Sidebar() {
  const pathname = usePathname()
  const [currentUser, setCurrentUser] = useState<User | null>(null)

  useEffect(() => {
    setCurrentUser(getStoredUser())
  }, [])

  return (
    <aside className="flex flex-col w-64 min-h-screen bg-gray-900 text-white">
      {/* Logo */}
      <div className="p-6 border-b border-gray-700">
        <h1 className="text-xl font-bold text-white">Happy House</h1>
        <p className="text-xs text-gray-400 mt-1">Darrington Family</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={clsx(
              'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
              pathname === href
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-800 hover:text-white'
            )}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>

      {/* User switcher */}
      <div className="p-4 border-t border-gray-700 space-y-3">
        <p className="text-xs text-gray-500 uppercase tracking-wider">Active User</p>
        {currentUser ? (
          <div className="flex items-center gap-3">
            {currentUser.picture ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={currentUser.picture}
                alt={currentUser.name}
                className="w-8 h-8 rounded-full"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm font-bold">
                {currentUser.name?.charAt(0) ?? '?'}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{currentUser.name}</p>
              <p className="text-xs text-gray-400 truncate">{currentUser.email}</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400">Not signed in</p>
        )}

        <button
          onClick={() => redirectToGoogleLogin()}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
        >
          <RefreshCw size={14} />
          Switch / Add User
        </button>

        <button
          onClick={logout}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:text-red-300 hover:bg-gray-800 rounded-lg transition-colors"
        >
          <LogOut size={14} />
          Sign Out
        </button>
      </div>
    </aside>
  )
}
